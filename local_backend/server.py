#!/usr/bin/env python3
"""Forge 100K fully local API: SQLite, filesystem assets, cookie sessions, and worker queue."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, sqlite3, time, uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("FORGE_DATA_DIR", ROOT / "data")).resolve()
DB_PATH = DATA / "forge.sqlite3"
ASSET_DIR = DATA / "assets"
WEB_ROOT = ROOT
HOST = os.environ.get("FORGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("FORGE_PORT", "8000"))
WORKER_TOKEN = os.environ.get("FORGE_WORKER_TOKEN", "")
MAX_JSON = 128 * 1024
SESSION_TTL = 60 * 60 * 24 * 14

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires_at INTEGER NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS presets(id TEXT NOT NULL,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,name TEXT NOT NULL,config_json TEXT NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(user_id,id));
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),job_type TEXT NOT NULL,request_json TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',attempt_count INTEGER NOT NULL DEFAULT 0,max_attempts INTEGER NOT NULL DEFAULT 3,locked_by TEXT,locked_at INTEGER,last_heartbeat_at INTEGER,error_code TEXT,result_asset_id TEXT,created_at INTEGER NOT NULL,started_at INTEGER,completed_at INTEGER);
CREATE INDEX IF NOT EXISTS jobs_queue_idx ON jobs(status,job_type,created_at);
CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),job_id TEXT NOT NULL REFERENCES jobs(id),asset_code TEXT NOT NULL,title TEXT NOT NULL,quality_tier TEXT NOT NULL,object_path TEXT NOT NULL,sha256 TEXT NOT NULL,byte_size INTEGER NOT NULL,metadata_json TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS job_events(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL REFERENCES jobs(id),event_type TEXT NOT NULL,details_json TEXT NOT NULL,created_at INTEGER NOT NULL);
"""
def connect():
    c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); c.execute("PRAGMA journal_mode=WAL"); return c
def init_db():
    DATA.mkdir(parents=True,exist_ok=True); ASSET_DIR.mkdir(parents=True,exist_ok=True)
    with connect() as c: c.executescript(SCHEMA)
def now(): return int(time.time())
def password_hash(password,salt=None):
    salt=salt or secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000)
    return salt.hex()+":"+digest.hex()
def verify_password(password,stored):
    try:
        salt_hex,digest_hex=stored.split(":",1)
        return hmac.compare_digest(password_hash(password,bytes.fromhex(salt_hex)).split(":",1)[1],digest_hex)
    except Exception: return False
def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()

class Handler(SimpleHTTPRequestHandler):
    server_version="ForgeLocal/1.0"
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(WEB_ROOT),**kw)
    def log_message(self,fmt,*args):
        # Avoid logging cookies, authorization headers, or request bodies.
        print("%s - %s"%(self.client_address[0],fmt%args))
    def send_json(self,data,status=200,extra=None):
        raw=json.dumps(data,separators=(",",":")).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)
    def body(self,limit=MAX_JSON):
        n=int(self.headers.get("Content-Length","0"))
        if n<0 or n>limit: raise ValueError("request_too_large")
        raw=self.rfile.read(n)
        if len(raw)!=n: raise ValueError("incomplete_body")
        return raw
    def json_body(self):
        raw=self.body()
        try: return json.loads(raw or b"{}")
        except Exception: raise ValueError("invalid_json")
    def user(self):
        cookie=self.headers.get("Cookie","")
        token=""
        for item in cookie.split(";"):
            k,sep,v=item.strip().partition("=")
            if k=="forge_session" and sep: token=v
        if not token: return None
        with connect() as c:
            row=c.execute("SELECT u.id,u.email,u.name FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?",(token_hash(token),now())).fetchone()
            return dict(row) if row else None
    def worker_ok(self):
        supplied=self.headers.get("Authorization","")
        return bool(WORKER_TOKEN) and hmac.compare_digest(supplied,"Bearer "+WORKER_TOKEN)
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/api/health":
            with connect() as c: c.execute("SELECT 1").fetchone()
            return self.send_json({"ok":True,"service":"forge-local","database":"sqlite","storage":"filesystem"})
        if p=="/api/auth/session":
            u=self.user(); return self.send_json({"user":u})
        if p=="/api/presets":
            u=self.user()
            if not u:return self.send_json({"error":"unauthorized"},401)
            with connect() as c: rows=c.execute("SELECT id,name,config_json,updated_at FROM presets WHERE user_id=? ORDER BY updated_at DESC LIMIT 100",(u["id"],)).fetchall()
            return self.send_json({"presets":[{"id":r["id"],"name":r["name"],"config":json.loads(r["config_json"]),"updated_at":r["updated_at"]} for r in rows]})
        if p.startswith("/api/assets/"):
            u=self.user()
            if not u:return self.send_json({"error":"unauthorized"},401)
            asset_id=unquote(p.rsplit("/",1)[-1])
            with connect() as c: row=c.execute("SELECT object_path FROM assets WHERE id=? AND user_id=?",(asset_id,u["id"])).fetchone()
            if not row:return self.send_json({"error":"not_found"},404)
            path=(DATA/row["object_path"]).resolve()
            if not path.is_relative_to(ASSET_DIR):return self.send_json({"error":"invalid_path"},400)
            return self.send_file(path)
        if p=="/api/jobs":
            u=self.user()
            if not u:return self.send_json({"error":"unauthorized"},401)
            with connect() as c: rows=c.execute("SELECT id,job_type,status,attempt_count,error_code,created_at,completed_at,result_asset_id FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT 100",(u["id"],)).fetchall()
            return self.send_json({"jobs":[dict(r) for r in rows]})
        return super().do_GET()
    def send_file(self,path):
        if not path.is_file():return self.send_json({"error":"asset_missing"},404)
        size=path.stat().st_size
        self.send_response(200); self.send_header("Content-Type","model/gltf-binary"); self.send_header("Content-Length",str(size)); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers()
        with path.open("rb") as f:
            while chunk:=f.read(1024*1024): self.wfile.write(chunk)
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            if p=="/api/auth/signup":
                b=self.json_body(); email=str(b.get("email","")).strip().lower(); name=str(b.get("name","")).strip()[:100]; pw=b.get("password","")
                if len(email)>254 or "@" not in email or not name or not isinstance(pw,str) or len(pw)<12 or len(pw)>256:return self.send_json({"error":"invalid_signup"},400)
                uid=str(uuid.uuid4()); token=secrets.token_urlsafe(36); stamp=now()
                with connect() as c:
                    c.execute("INSERT INTO users(id,email,name,password_hash,created_at) VALUES(?,?,?,?,?)",(uid,email,name,password_hash(pw),stamp))
                    c.execute("INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",(token_hash(token),uid,stamp+SESSION_TTL,stamp))
                return self.send_json({"user":{"id":uid,"email":email,"name":name}},201,{"Set-Cookie":f"forge_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}"})
            if p=="/api/auth/login":
                b=self.json_body(); email=str(b.get("email","")).strip().lower(); pw=b.get("password","")
                with connect() as c: row=c.execute("SELECT id,email,name,password_hash FROM users WHERE email=?",(email,)).fetchone()
                if not row or not isinstance(pw,str) or not verify_password(pw,row["password_hash"]):return self.send_json({"error":"invalid_credentials"},401)
                token=secrets.token_urlsafe(36); stamp=now()
                with connect() as c:c.execute("INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",(token_hash(token),row["id"],stamp+SESSION_TTL,stamp))
                return self.send_json({"user":{"id":row["id"],"email":row["email"],"name":row["name"]}},200,{"Set-Cookie":f"forge_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}"})
            if p=="/api/auth/logout":
                u=self.user()
                if u:
                    cookie=self.headers.get("Cookie","")
                    for item in cookie.split(";"):
                        k,_,v=item.strip().partition("=")
                        if k=="forge_session":
                            with connect() as c:c.execute("DELETE FROM sessions WHERE token_hash=?",(token_hash(v),))
                return self.send_json({"ok":True},200,{"Set-Cookie":"forge_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            if p=="/api/presets":
                u=self.user()
                if not u:return self.send_json({"error":"unauthorized"},401)
                b=self.json_body(); pid=str(b.get("id",""))[:120]; name=str(b.get("name","Untitled"))[:120]; config=b.get("config",{})
                if not pid or not isinstance(config,dict):return self.send_json({"error":"invalid_preset"},400)
                with connect() as c:c.execute("INSERT INTO presets(id,user_id,name,config_json,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET name=excluded.name,config_json=excluded.config_json,updated_at=excluded.updated_at",(pid,u["id"],name,json.dumps(config),now()))
                return self.send_json({"ok":True})
            if p=="/api/jobs":
                u=self.user()
                if not u:return self.send_json({"error":"unauthorized"},401)
                b=self.json_body(); jt=b.get("job_type","character"); request=b.get("request")
                if jt!="character" or not isinstance(request,dict) or len(json.dumps(request))>32768:return self.send_json({"error":"invalid_job"},400)
                jid=str(uuid.uuid4()); stamp=now()
                with connect() as c:
                    c.execute("INSERT INTO jobs(id,user_id,job_type,request_json,created_at) VALUES(?,?,?,?,?)",(jid,u["id"],jt,json.dumps(request),stamp))
                    c.execute("INSERT INTO job_events(job_id,event_type,details_json,created_at) VALUES(?,?,?,?)",(jid,"queued","{}",stamp))
                return self.send_json({"job_id":jid,"status":"queued"},201)
            return self.worker_post(p)
        except sqlite3.IntegrityError as e:
            return self.send_json({"error":"conflict_or_invalid_reference"},409)
        except ValueError as e:
            return self.send_json({"error":str(e)},413 if str(e)=="request_too_large" else 400)
        except Exception as e:
            print("request failed:",type(e).__name__)
            return self.send_json({"error":"internal_error"},500)
    def worker_post(self,p):
        if not self.worker_ok():return self.send_json({"error":"unauthorized_worker"},401)
        if p=="/api/worker/claim":
            b=self.json_body(); wid=str(b.get("worker_id",""))[:120]
            if not wid:return self.send_json({"error":"invalid_worker"},400)
            stamp=now()
            with connect() as c:
                c.execute("BEGIN IMMEDIATE")
                c.execute("UPDATE jobs SET status='failed',error_code='lease_expired_max_attempts',completed_at=?,locked_by=NULL,locked_at=NULL WHERE status='running' AND locked_at<? AND attempt_count>=max_attempts",(stamp,stamp-900))
                row=c.execute("SELECT * FROM jobs WHERE job_type='character' AND (status='queued' OR (status='running' AND locked_at<? AND attempt_count<max_attempts)) ORDER BY created_at LIMIT 1",(stamp-900,)).fetchone()
                if not row:return self.send_json({"job":None})
                c.execute("UPDATE jobs SET status='running',attempt_count=attempt_count+1,locked_by=?,locked_at=?,last_heartbeat_at=?,started_at=COALESCE(started_at,?) WHERE id=?",(wid,stamp,stamp,stamp,row["id"]))
                c.execute("INSERT INTO job_events(job_id,event_type,details_json,created_at) VALUES(?,?,?,?)",(row["id"],"claimed",json.dumps({"worker_id":wid}),stamp))
                job=c.execute("SELECT * FROM jobs WHERE id=?",(row["id"],)).fetchone()
            return self.send_json({"job":{"id":job["id"],"user_id":job["user_id"],"job_type":job["job_type"],"request":json.loads(job["request_json"]),"attempt_count":job["attempt_count"]}})
        if p=="/api/worker/heartbeat":
            b=self.json_body(); stamp=now()
            with connect() as c:cur=c.execute("UPDATE jobs SET locked_at=?,last_heartbeat_at=? WHERE id=? AND status='running' AND locked_by=?",(stamp,stamp,b.get("job_id"),b.get("worker_id")))
            return self.send_json({"ok":cur.rowcount==1})
        if p=="/api/worker/fail":
            b=self.json_body(); stamp=now()
            with connect() as c:
                c.execute("BEGIN IMMEDIATE")
                cur=c.execute("UPDATE jobs SET status=CASE WHEN attempt_count<max_attempts THEN 'queued' ELSE 'failed' END,completed_at=CASE WHEN attempt_count<max_attempts THEN NULL ELSE ? END,error_code=?,locked_by=NULL,locked_at=NULL WHERE id=? AND status='running' AND locked_by=?",(stamp,str(b.get("error_code","worker_error"))[:100],b.get("job_id"),b.get("worker_id")))
                if cur.rowcount:c.execute("INSERT INTO job_events(job_id,event_type,details_json,created_at) VALUES(?,?,?,?)",(b["job_id"],"failed",json.dumps({"error_code":b.get("error_code","worker_error")}),stamp))
            return self.send_json({"ok":cur.rowcount==1})
        if p.startswith("/api/worker/upload/"):
            job_id=unquote(p.rsplit("/",1)[-1]); b=self.body(50*1024*1024)
            if len(b)<20 or b[:4]!=b"glTF":return self.send_json({"error":"invalid_glb"},400)
            with connect() as c: job=c.execute("SELECT user_id,locked_by,status FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not job or job["status"]!="running" or job["locked_by"]!=self.headers.get("X-Worker-Id"):return self.send_json({"error":"lease_lost"},409)
            dest=ASSET_DIR/job["user_id"]/job_id; dest.mkdir(parents=True,exist_ok=True); target=dest/"output.glb"; tmp=dest/"output.glb.tmp"
            tmp.write_bytes(b); os.replace(tmp,target)
            import hashlib
            return self.send_json({"object_path":str(target.relative_to(DATA)),"sha256":hashlib.sha256(b).hexdigest(),"byte_size":len(b)})
        if p=="/api/worker/complete":
            b=self.json_body(); a=b.get("asset",{}); stamp=now()
            with connect() as c:
                c.execute("BEGIN IMMEDIATE")
                job=c.execute("SELECT user_id FROM jobs WHERE id=? AND status='running' AND locked_by=?",(b.get("job_id"),b.get("worker_id"))).fetchone()
                if not job:return self.send_json({"error":"lease_lost"},409)
                # A worker may complete only the exact file written by its active job.
                # Never trust client-supplied paths, hashes, or byte counts.
                expected=(ASSET_DIR/job["user_id"]/b["job_id"]/"output.glb").resolve()
                supplied=(DATA/str(a.get("object_path",""))).resolve()
                if supplied != expected or not expected.is_relative_to(ASSET_DIR):
                    return self.send_json({"error":"invalid_asset_path"},400)
                if not expected.is_file():
                    return self.send_json({"error":"asset_missing"},400)
                actual_size=expected.stat().st_size
                digest=hashlib.sha256(expected.read_bytes()).hexdigest()
                if a.get("byte_size") != actual_size or not isinstance(a.get("sha256"),str) or not hmac.compare_digest(a["sha256"],digest):
                    return self.send_json({"error":"asset_integrity_mismatch"},400)
                if actual_size < 20:
                    return self.send_json({"error":"invalid_glb"},400)
                aid=str(uuid.uuid4())
                c.execute("INSERT INTO assets(id,user_id,job_id,asset_code,title,quality_tier,object_path,sha256,byte_size,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(aid,job["user_id"],b["job_id"],a["asset_code"],a.get("title",a["asset_code"]),a.get("quality_tier","blockout"),str(expected.relative_to(DATA)),digest,actual_size,json.dumps(a.get("metadata",{})),stamp))
                c.execute("UPDATE jobs SET status='succeeded',result_asset_id=?,completed_at=?,locked_by=NULL,locked_at=NULL WHERE id=? AND status='running' AND locked_by=?",(aid,stamp,b["job_id"],b["worker_id"]))
                c.execute("INSERT INTO job_events(job_id,event_type,details_json,created_at) VALUES(?,?,?,?)",(b["job_id"],"succeeded",json.dumps({"asset_id":aid}),stamp))
            return self.send_json({"ok":True,"asset_id":aid})
        return self.send_json({"error":"not_found"},404)
    def do_HEAD(self):
        return super().do_HEAD()
    def do_PUT(self):
        return self.send_json({"error":"method_not_allowed"},405)
    def do_DELETE(self):
        p=urlparse(self.path).path
        if p.startswith("/api/presets/"):
            u=self.user()
            if not u:return self.send_json({"error":"unauthorized"},401)
            pid=unquote(p.rsplit("/",1)[-1])
            with connect() as c: c.execute("DELETE FROM presets WHERE id=? AND user_id=?",(pid,u["id"]))
            return self.send_json({"ok":True})
        return self.send_json({"error":"not_found"},404)

if __name__=="__main__":
    init_db()
    print(f"Forge Local API listening on {HOST}:{PORT}; data={DATA}")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

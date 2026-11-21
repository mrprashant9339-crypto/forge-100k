#!/usr/bin/env python3
"""Local filesystem + SQLite generation worker. No cloud service required."""
from __future__ import annotations
import hashlib,json,os,socket,subprocess,tempfile,time,threading,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
PIPELINE=ROOT/"pipeline"
API=os.environ.get("FORGE_API_URL","http://api:8000").rstrip("/")
TOKEN=os.environ.get("FORGE_WORKER_TOKEN","")
WORKER_ID=os.environ.get("WORKER_ID",socket.gethostname())[:120]
BLENDER=os.environ.get("BLENDER_BIN","blender")
POLL=max(2,int(os.environ.get("WORKER_POLL_SECONDS","5")))

class WorkerError(RuntimeError):pass
def request(method,path,payload=None,data=None,extra=None):
    body=data if data is not None else (json.dumps(payload).encode() if payload is not None else None)
    headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/json"}
    if payload is not None:headers["Content-Type"]="application/json"
    if extra:headers.update(extra)
    req=urllib.request.Request(API+path,data=body,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=120) as r:
            raw=r.read(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:raise WorkerError(f"local_api_http_{e.code}") from e
    except urllib.error.URLError as e:raise WorkerError("local_api_unavailable") from e
def heartbeat(job):
    r=request("POST","/api/worker/heartbeat",{"job_id":job,"worker_id":WORKER_ID})
    if not r.get("ok"):raise WorkerError("lease_lost")
def run_blender(job_id,cmd):
    p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    stop=threading.Event(); errors=[]
    def beat():
        while not stop.wait(60):
            try:heartbeat(job_id)
            except Exception as e:errors.append(e);p.terminate();return
    t=threading.Thread(target=beat,daemon=True);t.start()
    try:
        try:out,err=p.communicate(timeout=int(os.environ.get("BLENDER_JOB_TIMEOUT","900")))
        except subprocess.TimeoutExpired:p.kill();p.communicate();raise WorkerError("generation_timeout")
    finally:stop.set();t.join(timeout=5)
    if errors:raise WorkerError("lease_lost")
    if p.returncode:raise WorkerError("blender_failed:"+((err or out)[-500:]))
def process(job):
    jid=job["id"];heartbeat(jid)
    req=job["request"];asset=req.get("asset")
    if not isinstance(asset,dict) or req.get("job_type","character") not in ("character",None):raise WorkerError("invalid_character_request")
    if asset.get("quality_tier")!="blockout" or asset.get("target")!="glTF2":raise WorkerError("only_blockout_gltf2_supported")
    with tempfile.TemporaryDirectory(prefix="forge-local-") as td:
        work=Path(td); manifest=work/"pipeline/manifests/job.json";manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"schema_version":"1.0.0","batch_id":"job-"+jid,"output_dir":"artifacts","jobs":[asset]}),encoding="utf-8")
        check=subprocess.run([os.environ.get("PYTHON","python3"),str(PIPELINE/"scripts/validate_manifest.py"),str(manifest)],cwd=ROOT,capture_output=True,text=True,timeout=60)
        if check.returncode:raise WorkerError("manifest_validation_failed")
        run_blender(jid,[BLENDER,"--background","--python",str(PIPELINE/"blender/generate_batch.py"),"--",str(manifest)])
        glb=work/"artifacts"/(asset["asset_id"]+".glb")
        if not glb.is_file():raise WorkerError("glb_missing")
        verify=subprocess.run([os.environ.get("PYTHON","python3"),str(PIPELINE/"scripts/validate_glb.py"),str(glb)],cwd=ROOT,capture_output=True,text=True,timeout=60)
        if verify.returncode:raise WorkerError("glb_validation_failed")
        heartbeat(jid)
        raw=glb.read_bytes()
        uploaded=request("POST","/api/worker/upload/"+quote(jid,safe=""),data=raw,extra={"Content-Type":"model/gltf-binary","X-Worker-Id":WORKER_ID})
        result=request("POST","/api/worker/complete",{"job_id":jid,"worker_id":WORKER_ID,"asset":{"asset_code":asset["asset_id"],"title":asset.get("archetype","Forge Character").replace("-"," ").title(),"quality_tier":"blockout","object_path":uploaded["object_path"],"sha256":uploaded["sha256"],"byte_size":uploaded["byte_size"],"metadata":{"provenance":asset.get("provenance",{}),"validation":"structural_glb_only"}}})
        print(json.dumps({"event":"completed","job_id":jid,"asset_id":result.get("asset_id")}),flush=True)
def main():
    if not TOKEN:raise SystemExit("FORGE_WORKER_TOKEN is required")
    print("Forge local worker started:",WORKER_ID,flush=True)
    while True:
        job=None
        try:
            claim=request("POST","/api/worker/claim",{"worker_id":WORKER_ID})
            job=claim.get("job")
            if not job:time.sleep(POLL);continue
            process(job)
        except KeyboardInterrupt:raise
        except Exception as e:
            print(json.dumps({"event":"worker_error","job_id":(job or {}).get("id"),"error":str(e)[:300]}),flush=True)
            if job:
                try:request("POST","/api/worker/fail",{"job_id":job["id"],"worker_id":WORKER_ID,"error_code":str(e)[:100]})
                except Exception:pass
            time.sleep(2)
if __name__=="__main__":main()

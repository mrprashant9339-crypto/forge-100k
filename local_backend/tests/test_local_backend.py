#!/usr/bin/env python3
"""Integration tests for the local SQLite/auth/worker API using only stdlib."""
import importlib.util, json, os, tempfile, threading, urllib.request, urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TEMP=tempfile.TemporaryDirectory(prefix="forge-local-test-")
os.environ["FORGE_DATA_DIR"]=TEMP.name
os.environ["FORGE_WORKER_TOKEN"]="test-worker-token"
os.environ["FORGE_HOST"]="127.0.0.1"
spec=importlib.util.spec_from_file_location("forge_local_server",ROOT/"local_backend/server.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
mod.init_db()
server=mod.ThreadingHTTPServer(("127.0.0.1",0),mod.Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
BASE=f"http://127.0.0.1:{server.server_address[1]}"

def call(path,method="GET",body=None,headers=None):
    data=None if body is None else (body if isinstance(body,bytes) else json.dumps(body).encode())
    h=dict(headers or {})
    if body is not None and not isinstance(body,bytes):h["Content-Type"]="application/json"
    req=urllib.request.Request(BASE+path,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,r.headers, r.read()
    except urllib.error.HTTPError as e:return e.code,e.headers,e.read()

try:
    status,_,raw=call("/api/health")
    assert status==200 and json.loads(raw)["database"]=="sqlite"
    status,headers,raw=call("/api/auth/signup","POST",{"email":"local@example.test","name":"Local Tester","password":"correct-horse-battery"})
    assert status==201,raw
    cookie=headers.get("Set-Cookie").split(";",1)[0]
    assert call("/api/presets")[0]==401
    status,_,_=call("/api/presets","POST",{"id":"p1","name":"Test","config":{"style":"Normal"}},{"Cookie":cookie})
    assert status==200
    status,_,raw=call("/api/presets",headers={"Cookie":cookie})
    assert status==200 and json.loads(raw)["presets"][0]["id"]=="p1"
    status,_,raw=call("/api/jobs","POST",{"job_type":"character","request":{"asset":{"asset_id":"FG-HUM-000001","quality_tier":"blockout","target":"glTF2","archetype":"test"}}},{"Cookie":cookie})
    assert status==201,raw
    job_id=json.loads(raw)["job_id"]
    worker={"Authorization":"Bearer test-worker-token"}
    status,_,raw=call("/api/worker/claim","POST",{"worker_id":"test-worker"},worker)
    job=json.loads(raw)["job"]; assert job and job["id"]==job_id
    fake_glb=b"glTF"+bytes([2,0,0,0])+bytes([20,0,0,0])+b"TESTDATA"
    status,_,raw=call("/api/worker/upload/"+job_id,"POST",fake_glb,{**worker,"X-Worker-Id":"test-worker","Content-Type":"model/gltf-binary"})
    assert status==200,raw
    uploaded=json.loads(raw)
    forged={"job_id":job_id,"worker_id":"test-worker","asset":{"asset_code":"FG-HUM-000001","object_path":"assets/other-user/other-job/output.glb","sha256":uploaded["sha256"],"byte_size":uploaded["byte_size"]}}
    status,_,raw=call("/api/worker/complete","POST",forged,worker)
    assert status==400 and json.loads(raw)["error"]=="invalid_asset_path",raw
    forged["asset"]={"asset_code":"FG-HUM-000001","object_path":uploaded["object_path"],"sha256":"0"*64,"byte_size":uploaded["byte_size"]}
    status,_,raw=call("/api/worker/complete","POST",forged,worker)
    assert status==400 and json.loads(raw)["error"]=="asset_integrity_mismatch",raw
    status,_,raw=call("/api/worker/complete","POST",{"job_id":job_id,"worker_id":"test-worker","asset":{"asset_code":"FG-HUM-000001","object_path":uploaded["object_path"],"sha256":uploaded["sha256"],"byte_size":uploaded["byte_size"]}},worker)
    assert status==200,raw
    asset_id=json.loads(raw)["asset_id"]
    status,headers,raw=call("/api/assets/"+asset_id,headers={"Cookie":cookie})
    assert status==200 and raw==fake_glb
    status,headers2,raw=call("/api/auth/signup","POST",{"email":"second@example.test","name":"Second User","password":"another-correct-password"})
    assert status==201,raw
    second_cookie=headers2.get("Set-Cookie").split(";",1)[0]
    status,_,raw=call("/api/presets",headers={"Cookie":second_cookie})
    assert status==200 and json.loads(raw)["presets"]==[]
    assert call("/api/assets/"+asset_id,headers={"Cookie":second_cookie})[0]==404
    assert call("/api/worker/claim","POST",{"worker_id":"bad"})[0]==401
    print("Local backend integration tests passed: health, signup, sessions, per-user presets, job queue, worker auth, path/hash integrity, GLB storage, and two-account data isolation.")
finally:
    server.shutdown();server.server_close();TEMP.cleanup()

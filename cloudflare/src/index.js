const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});
const now=()=>new Date().toISOString();
const id=()=>crypto.randomUUID();
async function event(db,job,type,details={}){await db.prepare("INSERT INTO forge_job_events(job_id,event_type,details_json) VALUES(?,?,?)").bind(job,type,JSON.stringify(details)).run();}
export default {
 async fetch(req,env){
  const url=new URL(req.url), db=env.DB;
  if(req.method==="GET"&&url.pathname==="/health"){
   const r=await db.prepare("SELECT COUNT(*) AS tables_count FROM sqlite_master WHERE type='table' AND name LIKE 'forge_%'").first();
   return json({ok:true,service:"forge-100k-api",database:"cloudflare-d1",tables:r?.tables_count??0});
  }
  if(!env.FORGE_API_TOKEN)return json({error:"server_not_configured"},503);
  const auth=req.headers.get("authorization")||"";
  if(auth!==`Bearer ${env.FORGE_API_TOKEN}`)return json({error:"unauthorized"},401);
  if(req.method==="POST"&&url.pathname==="/v1/jobs"){
   const body=await req.json().catch(()=>null);
   if(!body||typeof body.user_id!=="string"||!body.user_id||!["character","garment","retopology","texture_bake","rigging","animation"].includes(body.job_type)||!body.request||JSON.stringify(body.request).length>32768)return json({error:"invalid_job"},400);
   const job=id();
   await db.batch([
    db.prepare("INSERT INTO forge_jobs(id,user_id,job_type,request_json,max_attempts) VALUES(?,?,?,?,?)").bind(job,body.user_id,body.job_type,JSON.stringify(body.request),Math.min(10,Math.max(1,Number(body.max_attempts)||3))),
    db.prepare("INSERT INTO forge_job_events(job_id,event_type,details_json) VALUES(?,?,?)").bind(job,"queued","{}")
   ]);
   return json({job_id:job,status:"queued"},201);
  }
  if(req.method==="POST"&&url.pathname==="/v1/worker/claim"){
   const body=await req.json().catch(()=>({}));
   if(typeof body.worker_id!=="string"||!body.worker_id||body.worker_id.length>120||typeof body.job_type!=="string")return json({error:"invalid_worker"},400);
   const stale=new Date(Date.now()-15*60*1000).toISOString();
   await db.prepare("UPDATE forge_jobs SET status='failed',error_code='lease_expired_max_attempts',completed_at=?,locked_at=NULL,locked_by=NULL WHERE status='running' AND job_type=? AND locked_at<? AND attempt_count>=max_attempts").bind(now(),body.job_type,stale).run();
   const job=await db.prepare("SELECT * FROM forge_jobs WHERE job_type=? AND (status='queued' OR (status='running' AND locked_at<? AND attempt_count<max_attempts)) ORDER BY created_at LIMIT 1").bind(body.job_type,stale).first();
   if(!job)return json({job:null});
   const stamp=now();
   const changed=await db.prepare("UPDATE forge_jobs SET status='running',attempt_count=attempt_count+1,started_at=COALESCE(started_at,?),locked_at=?,locked_by=?,last_heartbeat_at=?,error_code=NULL WHERE id=? AND (status='queued' OR (status='running' AND locked_at<?))").bind(stamp,stamp,body.worker_id,stamp,job.id,stale).run();
   if(!changed.meta?.changes)return json({job:null});
   await event(db,job.id,"claimed",{worker_id:body.worker_id});
   const claimed=await db.prepare("SELECT * FROM forge_jobs WHERE id=?").bind(job.id).first();
   return json({job:{...claimed,request:JSON.parse(claimed.request_json)}});
  }
  if(req.method==="POST"&&url.pathname==="/v1/worker/heartbeat"){
   const b=await req.json().catch(()=>({})), stamp=now();
   const r=await db.prepare("UPDATE forge_jobs SET locked_at=?,last_heartbeat_at=? WHERE id=? AND status='running' AND locked_by=?").bind(stamp,stamp,b.job_id,b.worker_id).run();
   return json({ok:!!r.meta?.changes});
  }
  if(req.method==="POST"&&url.pathname==="/v1/worker/fail"){
   const b=await req.json().catch(()=>({})),stamp=now();
   const r=await db.prepare("UPDATE forge_jobs SET status=CASE WHEN attempt_count<max_attempts THEN 'queued' ELSE 'failed' END,completed_at=CASE WHEN attempt_count<max_attempts THEN NULL ELSE ? END,error_code=?,locked_at=NULL,locked_by=NULL,last_heartbeat_at=NULL WHERE id=? AND status='running' AND locked_by=?").bind(stamp,String(b.error_code||"worker_error").slice(0,100),b.job_id,b.worker_id).run();
   if(r.meta?.changes)await event(db,b.job_id,"failed",{error_code:b.error_code||"worker_error"});
   return json({ok:!!r.meta?.changes});
  }
  if(req.method==="POST"&&url.pathname==="/v1/worker/complete"){
   const b=await req.json().catch(()=>({}));
   if(!b.asset||!b.job_id||!b.worker_id)return json({error:"invalid_completion"},400);
   const asset=b.asset, aid=id(), stamp=now();
   const job=await db.prepare("SELECT * FROM forge_jobs WHERE id=? AND status='running' AND locked_by=?").bind(b.job_id,b.worker_id).first();
   if(!job)return json({error:"lease_lost"},409);
   await db.batch([
    db.prepare("INSERT INTO forge_assets(id,user_id,asset_code,title,quality_tier,release_status,metadata_json) VALUES(?,?,?,?,?,'pending_review',?)").bind(aid,job.user_id,asset.asset_code,asset.title||asset.asset_code,asset.quality_tier||"blockout",JSON.stringify(asset.metadata||{})),
    db.prepare("INSERT INTO forge_asset_versions(id,asset_id,version,object_key,sha256,byte_size,validation_status,validation_report_json) VALUES(?,?,1,?,?,?,'passed',?)").bind(id(),aid,asset.object_key,asset.sha256,asset.byte_size,JSON.stringify(asset.validation_report||{})),
    db.prepare("UPDATE forge_jobs SET status='succeeded',result_asset_id=?,completed_at=?,locked_at=NULL,locked_by=NULL,last_heartbeat_at=NULL WHERE id=? AND status='running' AND locked_by=?").bind(aid,stamp,b.job_id,b.worker_id),
    db.prepare("INSERT INTO forge_job_events(job_id,event_type,details_json) VALUES(?,?,?)").bind(b.job_id,"succeeded",JSON.stringify({asset_id:aid}))
   ]);
   return json({ok:true,asset_id:aid});
  }
  return json({error:"not_found"},404);
 }
};
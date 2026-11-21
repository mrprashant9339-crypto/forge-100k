const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
const now = () => new Date().toISOString();
const uuid = () => crypto.randomUUID();
const JOB_TYPES = new Set(["character", "garment", "retopology", "texture_bake", "rigging", "animation"]);
const QUALITY_TIERS = new Set(["blockout", "prototype", "production", "game_ready"]);
const MAX_BODY_BYTES = 40 * 1024;

async function readJson(request) {
  const declared = Number(request.headers.get("content-length") || 0);
  if (declared > MAX_BODY_BYTES) return { error: "body_too_large" };
  const raw = await request.text();
  if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) return { error: "body_too_large" };
  try {
    return JSON.parse(raw);
  } catch {
    return { error: "invalid_json" };
  }
}

function validText(value, max = 120) {
  return typeof value === "string" && value.trim().length > 0 && value.length <= max;
}

function validSha256(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
}

function bearerMatches(request, token) {
  const supplied = request.headers.get("authorization") || "";
  const expected = `Bearer ${token}`;
  if (supplied.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= supplied.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

async function recordEvent(db, jobId, type, details = {}) {
  return db.prepare(
    "INSERT INTO forge_job_events(job_id,event_type,details_json) VALUES(?,?,?)"
  ).bind(jobId, type, JSON.stringify(details)).run();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const db = env.DB;

    if (request.method === "GET" && url.pathname === "/health") {
      if (!db) return json({ ok: false, error: "database_not_configured" }, 503);
      try {
        const row = await db.prepare(
          "SELECT COUNT(*) AS tables_count FROM sqlite_master WHERE type='table' AND name LIKE 'forge_%'"
        ).first();
        return json({
          ok: true,
          service: "forge-100k-api",
          database: "cloudflare-d1",
          tables: row?.tables_count ?? 0,
        });
      } catch {
        return json({ ok: false, error: "database_unavailable" }, 503);
      }
    }

    if (!db || !env.FORGE_API_TOKEN) return json({ error: "server_not_configured" }, 503);
    if (!bearerMatches(request, env.FORGE_API_TOKEN)) return json({ error: "unauthorized" }, 401);

    // This is a private service-to-service API. Do not expose it to browsers or end users.
    if (request.method === "POST" && url.pathname === "/v1/jobs") {
      const body = await readJson(request);
      if (body.error) return json({ error: body.error }, body.error === "body_too_large" ? 413 : 400);
      if (
        !validText(body.user_id, 128) ||
        !JOB_TYPES.has(body.job_type) ||
        !body.request || typeof body.request !== "object" || Array.isArray(body.request) ||
        JSON.stringify(body.request).length > 32768
      ) return json({ error: "invalid_job" }, 400);

      const attempts = body.max_attempts === undefined ? 3 : Number(body.max_attempts);
      if (!Number.isInteger(attempts) || attempts < 1 || attempts > 10) {
        return json({ error: "invalid_max_attempts" }, 400);
      }

      const jobId = uuid();
      try {
        await db.batch([
          db.prepare(
            "INSERT INTO forge_jobs(id,user_id,job_type,request_json,max_attempts) VALUES(?,?,?,?,?)"
          ).bind(jobId, body.user_id.trim(), body.job_type, JSON.stringify(body.request), attempts),
          db.prepare(
            "INSERT INTO forge_job_events(job_id,event_type,details_json) VALUES(?,?,?)"
          ).bind(jobId, "queued", "{}"),
        ]);
        return json({ job_id: jobId, status: "queued" }, 201);
      } catch {
        return json({ error: "job_enqueue_failed" }, 500);
      }
    }

    if (request.method !== "POST") return json({ error: "method_not_allowed" }, 405);

    if (url.pathname === "/v1/worker/claim") {
      const body = await readJson(request);
      if (body.error) return json({ error: body.error }, body.error === "body_too_large" ? 413 : 400);
      if (!validText(body.worker_id) || !JOB_TYPES.has(body.job_type)) {
        return json({ error: "invalid_worker_claim" }, 400);
      }
      const stale = new Date(Date.now() - 15 * 60 * 1000).toISOString();
      const stamp = now();
      try {
        await db.prepare(
          "UPDATE forge_jobs SET status='failed',error_code='lease_expired_max_attempts',completed_at=?,locked_at=NULL,locked_by=NULL,last_heartbeat_at=NULL WHERE status='running' AND job_type=? AND locked_at<? AND attempt_count>=max_attempts"
        ).bind(stamp, body.job_type, stale).run();

        const candidate = await db.prepare(
          "SELECT id FROM forge_jobs WHERE job_type=? AND (status='queued' OR (status='running' AND locked_at<? AND attempt_count<max_attempts)) ORDER BY created_at LIMIT 1"
        ).bind(body.job_type, stale).first();
        if (!candidate) return json({ job: null });

        const claimed = await db.prepare(
          "UPDATE forge_jobs SET status='running',attempt_count=attempt_count+1,started_at=COALESCE(started_at,?),locked_at=?,locked_by=?,last_heartbeat_at=?,error_code=NULL WHERE id=? AND (status='queued' OR (status='running' AND locked_at<?))"
        ).bind(stamp, stamp, body.worker_id.trim(), stamp, candidate.id, stale).run();
        if (!claimed.meta?.changes) return json({ job: null });

        await recordEvent(db, candidate.id, "claimed", { worker_id: body.worker_id.trim() });
        const row = await db.prepare("SELECT * FROM forge_jobs WHERE id=?").bind(candidate.id).first();
        return json({ job: { ...row, request: JSON.parse(row.request_json) } });
      } catch {
        return json({ error: "job_claim_failed" }, 500);
      }
    }

    if (url.pathname === "/v1/worker/heartbeat") {
      const body = await readJson(request);
      if (body.error) return json({ error: body.error }, 400);
      if (!validText(body.job_id, 64) || !validText(body.worker_id)) {
        return json({ error: "invalid_heartbeat" }, 400);
      }
      const stamp = now();
      const result = await db.prepare(
        "UPDATE forge_jobs SET locked_at=?,last_heartbeat_at=? WHERE id=? AND status='running' AND locked_by=?"
      ).bind(stamp, stamp, body.job_id, body.worker_id).run();
      return json({ ok: !!result.meta?.changes });
    }

    if (url.pathname === "/v1/worker/fail") {
      const body = await readJson(request);
      if (body.error) return json({ error: body.error }, 400);
      if (!validText(body.job_id, 64) || !validText(body.worker_id)) {
        return json({ error: "invalid_failure_report" }, 400);
      }
      const errorCode = validText(body.error_code, 100) ? body.error_code : "worker_error";
      const stamp = now();
      const result = await db.prepare(
        "UPDATE forge_jobs SET status=CASE WHEN attempt_count<max_attempts THEN 'queued' ELSE 'failed' END,completed_at=CASE WHEN attempt_count<max_attempts THEN NULL ELSE ? END,error_code=?,locked_at=NULL,locked_by=NULL,last_heartbeat_at=NULL WHERE id=? AND status='running' AND locked_by=?"
      ).bind(stamp, errorCode, body.job_id, body.worker_id).run();
      if (result.meta?.changes) {
        await recordEvent(db, body.job_id, "failed", { error_code: errorCode });
      }
      return json({ ok: !!result.meta?.changes });
    }

    if (url.pathname === "/v1/worker/complete") {
      const body = await readJson(request);
      if (body.error) return json({ error: body.error }, body.error === "body_too_large" ? 413 : 400);
      if (!validText(body.job_id, 64) || !validText(body.worker_id) || !body.asset || typeof body.asset !== "object") {
        return json({ error: "invalid_completion" }, 400);
      }
      const asset = body.asset;
      if (
        !validText(asset.asset_code, 80) ||
        !validText(asset.object_key, 512) ||
        asset.object_key.startsWith("/") || asset.object_key.includes("..") ||
        !validSha256(asset.sha256) ||
        !Number.isSafeInteger(asset.byte_size) || asset.byte_size < 20 ||
        !QUALITY_TIERS.has(asset.quality_tier || "blockout")
      ) return json({ error: "invalid_asset_metadata" }, 400);

      const assetId = uuid();
      const versionId = uuid();
      const stamp = now();
      try {
        // Each insert is lease-gated. D1 batch executes atomically, so a stale worker
        // cannot publish metadata after its lease has been taken by another worker.
        const results = await db.batch([
          db.prepare(
            "INSERT INTO forge_assets(id,user_id,asset_code,title,quality_tier,release_status,metadata_json) SELECT ?,user_id,?,?,?,'pending_review',? FROM forge_jobs WHERE id=? AND status='running' AND locked_by=?"
          ).bind(
            assetId, asset.asset_code, asset.title || asset.asset_code,
            asset.quality_tier || "blockout", JSON.stringify(asset.metadata || {}),
            body.job_id, body.worker_id
          ),
          db.prepare(
            "INSERT INTO forge_asset_versions(id,asset_id,version,object_key,sha256,byte_size,validation_status,validation_report_json) SELECT ?,?,?,?, ?,?,'pending',? WHERE EXISTS (SELECT 1 FROM forge_assets WHERE id=?)"
          ).bind(
            versionId, assetId, 1, asset.object_key, asset.sha256.toLowerCase(),
            asset.byte_size, JSON.stringify(asset.validation_report || {}), assetId
          ),
          db.prepare(
            "UPDATE forge_jobs SET status='succeeded',result_asset_id=?,completed_at=?,locked_at=NULL,locked_by=NULL,last_heartbeat_at=NULL WHERE id=? AND status='running' AND locked_by=?"
          ).bind(assetId, stamp, body.job_id, body.worker_id),
          db.prepare(
            "INSERT INTO forge_job_events(job_id,event_type,details_json) SELECT ?, 'succeeded', ? WHERE EXISTS (SELECT 1 FROM forge_jobs WHERE id=? AND status='succeeded' AND result_asset_id=?)"
          ).bind(body.job_id, JSON.stringify({ asset_id: assetId }), body.job_id, assetId),
        ]);
        if (!results[0]?.meta?.changes || !results[2]?.meta?.changes) {
          return json({ error: "lease_lost" }, 409);
        }
        return json({ ok: true, asset_id: assetId });
      } catch {
        return json({ error: "asset_completion_failed" }, 500);
      }
    }

    return json({ error: "not_found" }, 404);
  },
};

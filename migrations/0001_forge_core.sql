-- Cloudflare D1 backend schema for Forge 100K.
-- SQLite-compatible; D1 is the source of truth for queue metadata and asset records.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS forge_jobs (
 id TEXT PRIMARY KEY,
 user_id TEXT NOT NULL,
 job_type TEXT NOT NULL CHECK(job_type IN ('character','garment','retopology','texture_bake','rigging','animation')),
 request_json TEXT NOT NULL CHECK(length(request_json) <= 32768),
 status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
 attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
 max_attempts INTEGER NOT NULL DEFAULT 3 CHECK(max_attempts BETWEEN 1 AND 10),
 locked_at TEXT, locked_by TEXT, last_heartbeat_at TEXT, result_asset_id TEXT, error_code TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 started_at TEXT, completed_at TEXT,
 CHECK(attempt_count <= max_attempts)
);
CREATE INDEX IF NOT EXISTS forge_jobs_claim_idx ON forge_jobs(job_type,status,created_at);
CREATE INDEX IF NOT EXISTS forge_jobs_lease_idx ON forge_jobs(status,locked_at);
CREATE INDEX IF NOT EXISTS forge_jobs_user_idx ON forge_jobs(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS forge_assets (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL, asset_code TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL, quality_tier TEXT NOT NULL CHECK(quality_tier IN ('blockout','prototype','production','game_ready')),
 release_status TEXT NOT NULL DEFAULT 'draft' CHECK(release_status IN ('draft','pending_review','approved','rejected')),
 metadata_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS forge_assets_user_idx ON forge_assets(user_id,created_at DESC);

CREATE TABLE IF NOT EXISTS forge_asset_versions (
 id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES forge_assets(id) ON DELETE CASCADE,
 version INTEGER NOT NULL, object_key TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL,
 byte_size INTEGER NOT NULL CHECK(byte_size > 0), mime_type TEXT NOT NULL DEFAULT 'model/gltf-binary',
 validation_status TEXT NOT NULL CHECK(validation_status IN ('passed','failed','pending')),
 validation_report_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(asset_id,version)
);

CREATE TABLE IF NOT EXISTS forge_job_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES forge_jobs(id) ON DELETE CASCADE,
 event_type TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS forge_job_events_job_idx ON forge_job_events(job_id,id);

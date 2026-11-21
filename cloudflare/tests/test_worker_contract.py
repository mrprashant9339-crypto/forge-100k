#!/usr/bin/env python3
"""Static security/contract checks for the Cloudflare Worker source."""
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "src" / "index.js").read_text(encoding="utf-8")

required = [
    'request.method === "GET" && url.pathname === "/health"',
    "if (!db || !env.FORGE_API_TOKEN)",
    "bearerMatches(request, env.FORGE_API_TOKEN)",
    "MAX_BODY_BYTES = 40 * 1024",
    "JOB_TYPES.has(body.job_type)",
    "validSha256(asset.sha256)",
    'asset.object_key.includes("..")',
    "status='running' AND locked_by=?",
    "INSERT INTO forge_assets",
    "validation_status,validation_report_json",
    'return json({ error: "lease_lost" }, 409)',
]
for fragment in required:
    assert fragment in source, f"missing Worker contract: {fragment}"

assert "SUPABASE_SERVICE_ROLE_KEY" not in source
assert "Access-Control-Allow-Origin" not in source
assert '"passed"' not in source, "Worker must not self-certify assets"
print("Cloudflare Worker static security and API contract checks passed.")

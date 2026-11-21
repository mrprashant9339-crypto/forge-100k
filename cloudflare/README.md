# Forge 100K Cloudflare backend

Cloudflare D1 database: `forge-100k-production` (APAC). The schema is applied to the account and tracked in `migrations/0001_forge_core.sql`.

## Worker API

- `GET /health` — public readiness check.
- `POST /v1/jobs` — service-authenticated job enqueue.
- `POST /v1/worker/claim`, `heartbeat`, `fail`, `complete` — service-authenticated worker lifecycle.

Bind D1 as `DB` and set `FORGE_API_TOKEN` as a Cloudflare Worker secret. Never commit the token or place it in browser code.

**Security boundary:** this is a private service-to-service API, not an end-user API. Every non-health route requires the shared bearer token. The `user_id` on enqueue is trusted only because the caller is a trusted backend; it is not independently authenticated by this Worker. Do not expose this endpoint to browsers or public clients until end-user authentication and per-user authorization are implemented.

The Worker validates payload sizes and asset metadata, verifies worker lease ownership, and lease-gates asset metadata insertion in a D1 batch. The asset version is marked `pending`, not `passed`; metadata supplied by a worker is not proof of production certification.

## Storage and current deployment blockers

D1 stores queue and asset metadata only. Generated GLB bytes must be uploaded to Cloudflare R2 before a job can be completed with a real retrievable asset. R2 is not enabled on the connected account yet. Enable R2 in the Cloudflare dashboard, create a private bucket, and configure an R2 binding before implementing/enabling binary upload and download routes.

The Python generation worker currently uses the legacy Supabase queue and storage APIs. It has not yet been migrated to this Cloudflare Worker API. Do not run the legacy worker against the new D1 queue; the two queues are not synchronized.

## Deployment

From this directory, configure the D1 binding and secret, then deploy with Wrangler after CI passes. Verify `/health` and authenticated queue lifecycle calls in a non-production test environment before routing production traffic. No production deployment is implied by a passing GitHub Actions workflow.

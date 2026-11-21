# Forge 100K Cloudflare backend

Cloudflare D1 database: `forge-100k-production` (APAC).
The D1 schema is applied in the account and mirrored in `migrations/0001_forge_core.sql`.

## Worker API
- `GET /health` — public readiness only.
- `POST /v1/jobs` — authenticated job enqueue.
- `POST /v1/worker/claim`, `heartbeat`, `fail`, `complete` — authenticated worker lease lifecycle.

Set the Worker secret `FORGE_API_TOKEN` before deploying. Bind D1 as `DB`.
Never place the token in Git or browser code.

## Asset bytes
D1 stores queue and asset metadata only. GLB bytes must be stored in Cloudflare R2; R2 is not enabled on the connected account yet. Enable R2 in the Cloudflare dashboard, then configure an R2 bucket and binding before enabling asset upload/completion.

## Security and limits
The API uses one shared server-side bearer secret as a service boundary. Add user authentication/authorization before exposing enqueue to public clients. The current worker completion route trusts the authenticated worker and should be called only from the private worker environment.

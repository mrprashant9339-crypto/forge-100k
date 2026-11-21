# Local deployment and offline operation

## Runtime architecture

```text
Browser (localhost:8000)
       |
       v
Python local API ---- SQLite (users, sessions, presets, jobs, assets)
       |                              |
       |                              +---- local data volume
       v
Local Blender worker ---- filesystem GLB storage
```

No Supabase, Cloudflare, remote database, object storage, hosted authentication or public API is used by the local Compose profile.

## Fully offline / air-gapped caveat

The backend, auth, queue, database and asset storage are local. The current index.html imports Three.js from jsDelivr. For a genuinely air-gapped workstation, vendor the exact pinned Three.js modules and transitive dependencies into the repository, change imports to local relative paths, and verify the application with network access disabled. Do not describe the current browser frontend as fully offline until that dependency is vendored and an offline browser smoke test passes.

## Data location

Docker named volume forge-data stores:
- forge.sqlite3 — SQLite database
- assets/<user-id>/<job-id>/output.glb — generated assets

Use docker volume inspect forge-100k_forge-data to locate the volume. Back up the volume before deleting it.

## Password reset

No email server is configured in local mode. Password recovery is deliberately not simulated. An administrator can reset a password from the host with `docker compose -f docker-compose.local.yml exec api python local_backend/admin.py reset-password user@example.com`. This prompts for the new password and revokes existing sessions; do not expose unauthenticated password-reset endpoints.

## Scope

The current local worker supports only character blockout jobs. It does not certify production/game-ready output. The 100K catalogue is a deterministic preset space, not 100K generated GLB files.

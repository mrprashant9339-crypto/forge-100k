# Forge 100K — 3D Character & Asset Library

Forge 100K is an original procedural 3D character catalogue prototype. It combines archetypes, body forms, outfit families and material palettes to create 100,000 deterministic catalogue entries on demand.

## Run locally
Serve this folder with `python -m http.server 8000` and open http://localhost:8000. Three.js loads from jsDelivr, so an internet connection is required.

## Features
- 20 asset groups covering humans, animals, fantasy, robots, voxel-inspired mobs, mascots and living objects.
- Deterministic 100,000-entry catalogue with search, category filters and pagination.
- Interactive Three.js viewport with orbit and zoom.
- Outfit, body-form and palette controls.
- GLB export and GLB upload preview.
- Browser-local saved presets, with optional per-account cloud sync after Supabase setup.
- Email/password sign-up, sign-in, email verification and password recovery UI (requires a configured Supabase project).
- GitHub Pages workflow.

## Scope and legal note
The 100,000 entries are procedural presets, not 100,000 separately authored AAA-quality models. Starter meshes are original low-detail prototypes, not production-rigged assets. Do not copy or redistribute proprietary Free Fire, PUBG, GTA or Minecraft assets. Third-party assets must be added only after checking their individual licences.

See [Product Specification](docs/PRODUCT_SPEC.md), [Roadmap](docs/ROADMAP.md), [Authentication setup](docs/AUTH_SETUP.md), and the [Phase 4 advanced character pipeline](pipeline/PHASE4.md).

## Enable accounts and cloud presets

The sign-in UI is present, but authentication remains disabled until the owner configures a Supabase project. Follow [docs/AUTH_SETUP.md](docs/AUTH_SETUP.md), set the public project URL/key in `supabase-config.js`, and apply the base schema plus the platform migration. Never place a Supabase service-role key in the frontend.

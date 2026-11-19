# Forge 100K Roadmap

## Phase 1 — Character quality foundation
- [x] Deterministic Blender blockout generation and UV/material creation
- [x] Humanoid skeleton, top-four skinning and idle animation
- [x] GLB structural validation and Blender deformation QA
- [x] CI artifacts for generated GLBs and reports

## Phase 2 — Modular character and morphology foundation
- [x] Public competitor architecture research documented
- [x] Deterministic face/body morphology contracts with strict ranges and stable seeds; [x] Phase 2 Blender worker enforces canonical ranges and module species/slot compatibility at runtime
- [x] 10 localized facial shape-key controls on human head
- [x] 7 body morphology shape-key controls on modular human body parts
- [x] Data-driven modular part catalog with slots, sockets, species, LOD and provenance
- [x] Duplicate module and occupied-slot conflict validation
- [x] Blender modular assembly worker; [x] CI executes Phase 2 character generation and validates exact face/body morph-target sets and module reports
- [x] CI morph-target gate, rigging and animation verification
- [ ] Continuous body deformation on production basemesh topology
- [ ] Production facial sculpt, ARKit 52-unit and viseme mapping
- [x] Prototype garment proxy fitting and semantic body-zone groups; [x] Blender fixture integration test and GLB/report validation; [ ] runtime occlusion, pose-space collision and cloth integrity certification
- [x] Prototype humanoid/mechanical/quadruped/avian skeleton profiles exercised in CI; [x] each profile exported and structurally validated in Blender CI; [ ] species-specific mesh fitting, retargeting and deformation certification
- [x] Automated Blender LOD0/LOD1/LOD2 decimation exports with GLB validation in CI (prototype; not performance-certified)
- [x] Material-preserving static mesh merge worker (shape-key meshes protected); [x] Blender fixture integration test and GLB/report validation; [ ] texture atlas baking
- [x] Measurable GLB structural/runtime-budget preflight in CI (prototype thresholds; target-engine profiling still required)

## Phase 3 — Production character content (partially implemented)
- [x] PBR material manifest contract, texture-reference validator and unit tests
- [x] Deterministic Blender PBR texture authoring for base-color, metallic-roughness, normal and occlusion maps; CI generation/validation integrated (procedural, not high-to-low bake)
- [ ] Original high-resolution sculpted basemeshes, artist-authored retopology and production UV/edge-flow review
- [x] Blender high-to-low diffuse/normal/AO and packed metallic-roughness output worker added; [x] strict map/report validation and dedicated negative-case tests; [ ] approved sculpt/retopo bake fixture, metallic-roughness channel bake/packing and target-engine material verification
- [x] Procedural facial expression, blink morph and five-viseme morph-target pack with Blender GLB integration test (starter quality; not ARKit/production animation certified)
- [x] Timed starter expression/viseme clips and double-blink animation at 30 FPS with GLB export and CI structural validation; [ ] dedicated eye rig/gaze, ARKit 52, audio-synchronized phonemes and artist facial approval
- [ ] Artist-finished clothing, groomed hair and armour packs with cloth/pose/collision validation (current CC0 modules are blockout prototypes)
- [x] Automated GLB container preflight added (explicitly not certification); [ ] signed artist review and Unity/Unreal/Godot import/performance certification
- [x] Production asset package schema, runtime Draft 2020-12 validation, provenance hash verification, safe package-path checks, referenced evidence-file checks and release-gate validator; [x] CI tests prevent game-ready promotion without review and declared-engine evidence

## Phase 4 — Character quality and animation (in progress)
- [x] Existing procedural IK targets/poles, IK influence switch, finger chains, facial joints and eye aim controls; CI GLB structural validation
- [x] Existing procedural walk, run, jump, combat-ready, idle/interaction and reach animation clips; CI generation and GLB validation
- [x] Existing facial expression/viseme morph pack, timed curves and audio-timeline lip-sync worker; CI morph/GLB validation
- [x] Existing garment proxy fitting and sampled body/self-intersection preflight
- [x] Blender cloth-scene preparation worker adds body collision modifiers, garment cloth/self-collision settings and a reusable simulation scene; CI validates its report
- [x] Real Blender point-cache bake worker with evaluated frame sampling, geometry integrity and pin-weight preflight; CI fixture invokes the bake (not a continuous collision/tear certification)
- [x] Existing Quadriflow retopology candidate, topology metrics, UV-based Cycles diffuse/normal/AO baking and strict report validation
- [x] Full-scene-range Blender cloth point-cache bake worker; persisted cache and evaluated frame integrity report
- [x] World-space garment/body triangle collision, inside-body, non-adjacent self-overlap, topology-stability and pin-weight QA workers with CI report validation
- [ ] Run full-frame QA on real walk/run/jump/combat skeletal actions, resolve all findings, validate tear-capable workflow and obtain artist-approved garment fit
- [ ] Production IK/FK snapping and control-rig export/retarget validation in Unity, Unreal and Godot
- [ ] Full ARKit 52 sculpted facial target set, audio-derived phoneme timing and reviewed eye/eyelid performance
- [ ] Motion-capture quality clips, foot locking, root-motion extraction and target-engine loop/contact review
- [ ] Artist-approved deformation topology, production UV packing, cage/seam/mipmap review and target-engine PBR validation
- [ ] Signed artist review and target-engine import/performance certification

## Phase 5 — Scale, accounts and platform (partially implemented)
- [x] Supabase email/password sign-up, sign-in, email-verification flow and password-reset UI integrated into the static site (requires owner project configuration)
- [x] Postgres profiles and saved-presets schema with per-user Row Level Security policies
- [x] Persistent browser auth session and cloud preset synchronization module
- [x] CI contract tests for auth flows, public-key boundary and RLS ownership policies
- [ ] Create/configure the Supabase project, set public URL/key, apply SQL migration, configure email confirmation and production SMTP
- [ ] Verify two-account isolation against the live Supabase project and test password recovery end-to-end
- [ ] Private upload bucket, object-path RLS, signed upload/download URLs, file-size/type limits and malware scanning
- [ ] Server-side GLB validation workers; never trust client-side validation for publication
- [ ] Queue-backed batch workers, job retries, cancellation, idempotency and storage/CDN
- [ ] Asset registry, immutable versions, provenance/licence evidence and moderation review
- [ ] Search indexing, asset analytics, audit logs and usage telemetry
- [ ] AI generation backends with human QA and licence checks

## Phase 6 — Production operations and release
- [ ] Separate authenticated API/worker deployment from the static GitHub Pages frontend
- [ ] Secret management, least-privilege service identities, rate limiting and abuse protection
- [ ] Backups, restore drills, database migrations and retention/deletion workflows
- [ ] Monitoring, error reporting, SLOs and incident runbooks
- [ ] Security review, accessibility audit, browser/device matrix and load testing
- [ ] Production asset intake, signed artist review and Unity/Unreal/Godot certification

## Quality policy
Do not label an asset game-ready until geometry, UVs, PBR maps, LODs, rig, animation, bounds, collisions, licence provenance and target-engine import pass automated checks and artist review.

### Phase 2 acceptance status
Phase 2 remains incomplete: production basemesh deformation, ARKit/viseme facial system, cloth/collision validation, species retargeting certification, atlas baking and target-engine profiling require further implementation and/or artist/engine validation. Phase 3 implementation is proceeding in parallel at the user's explicit direction; this does not waive the Phase 2 gates.

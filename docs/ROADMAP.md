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
- [ ] Full animation-range cloth cache bake, evaluated skeletal-pose collision sweep and artist-approved garment fit
- [ ] Production IK/FK snapping and control-rig export/retarget validation in Unity, Unreal and Godot
- [ ] Full ARKit 52 sculpted facial target set, audio-derived phoneme timing and reviewed eye/eyelid performance
- [ ] Motion-capture quality clips, foot locking, root-motion extraction and target-engine loop/contact review
- [ ] Artist-approved deformation topology, production UV packing, cage/seam/mipmap review and target-engine PBR validation
- [ ] Signed artist review and target-engine import/performance certification

## Phase 5 — Scale and platform
- [ ] Queue-backed batch workers and storage/CDN
- [ ] Authenticated creator uploads, versioning and moderation
- [ ] Search indexing, asset analytics and usage telemetry
- [ ] AI generation backends with human QA and licence checks

## Quality policy
Do not label an asset game-ready until geometry, UVs, PBR maps, LODs, rig, animation, bounds, collisions, licence provenance and target-engine import pass automated checks and artist review.

### Phase 2 acceptance status
Phase 2 remains incomplete: production basemesh deformation, ARKit/viseme facial system, cloth/collision validation, species retargeting certification, atlas baking and target-engine profiling require further implementation and/or artist/engine validation. Phase 3 implementation is proceeding in parallel at the user's explicit direction; this does not waive the Phase 2 gates.

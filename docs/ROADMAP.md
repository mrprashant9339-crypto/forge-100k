# Forge 100K Roadmap

## Phase 1 — Character quality foundation
- [x] Deterministic Blender blockout generation and UV/material creation
- [x] Humanoid skeleton, top-four skinning and idle animation
- [x] GLB structural validation and Blender deformation QA
- [x] CI artifacts for generated GLBs and reports

## Phase 2 — Modular character and morphology foundation
- [x] Public competitor architecture research documented
- [x] Deterministic face/body morphology contracts with strict ranges and stable seeds
- [x] 10 localized facial shape-key controls on human head
- [x] 7 body morphology shape-key controls on modular human body parts
- [x] Data-driven modular part catalog with slots, sockets, species, LOD and provenance
- [x] Duplicate module and occupied-slot conflict validation
- [x] Blender modular assembly worker
- [x] CI morph-target gate, rigging and animation verification
- [ ] Continuous body deformation on production basemesh topology
- [ ] Production facial sculpt, ARKit 52-unit and viseme mapping
- [ ] Garment proxy fitting, body-zone hiding, collision and cloth integrity
- [ ] Multi-species skeleton profiles and retargeting
- [x] Automated Blender LOD0/LOD1/LOD2 decimation exports with GLB validation in CI (prototype; not performance-certified)\n- [ ] Texture atlas/mesh merge\n- [x] Measurable GLB structural/runtime-budget preflight in CI (prototype thresholds; target-engine profiling still required)

## Phase 3 — Production character content
- [ ] Original high-resolution base meshes and sculpt-to-game retopology
- [ ] PBR texture baking and material authoring
- [ ] Facial expression and phoneme animation packs
- [ ] Game-ready clothing, hair and armour packs
- [ ] Artist review and target-engine import certification

## Phase 4 — Scale and platform
- [ ] Queue-backed batch workers and storage/CDN
- [ ] Authenticated creator uploads, versioning and moderation
- [ ] Search indexing, asset analytics and usage telemetry
- [ ] AI generation backends with human QA and licence checks

## Quality policy
Do not label an asset game-ready until geometry, UVs, PBR maps, LODs, rig, animation, bounds, collisions, licence provenance and target-engine import pass automated checks and artist review.

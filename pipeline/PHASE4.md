# Phase 4 — Advanced character quality & animation

## Implementation status

Phase 4 is an implementation and verification phase, not a promise that generated blockout assets are AAA. Existing Blender workers already provide starter garment fitting/collision preflight, IK target controls, finger/facial bones, six full-body clip categories, facial morph/viseme curves, Quadriflow retopology candidates, topology metrics and Cycles high-to-low texture baking. This phase hardens the pipeline and adds a real cloth-physics scene-preparation stage.

## Pipeline commands

### 1. Garment fit and collision
```bash
blender -b --python pipeline/blender/fit_garment.py -- body.glb garment.glb fitted.glb fit-report.json
blender -b --python pipeline/blender/garment_collision_qa.py -- fitted.glb fit-report.json collision-report.json
blender -b --python pipeline/blender/prepare_cloth_scene.py -- fitted.glb cloth-sim.blend cloth-report.json 120
```
The fit worker remains a proxy shrinkwrap. Collision QA is a sampled geometric preflight. The new cloth worker adds Blender Collision modifiers to body parts and Cloth modifiers with self-collision to garment meshes, saves a reusable .blend scene, and reports the cache range. The simulation is deliberately reported as unbaked until a Blender simulation cache has actually been baked and reviewed.

### 2. Rigging and animation
```bash
blender -b --python pipeline/blender/advanced_rig_controls.py -- rigged.glb advanced-rig.glb rig-report.json
blender -b --python pipeline/blender/animation_library.py -- advanced-rig.glb animated.glb animation-report.json
```
The current humanoid worker adds finger chains, IK targets/poles, IK influence property, eye aim constraints and jaw/eye joints. It is a Blender DCC control rig; glTF export cannot preserve every Blender constraint or animator control. Exported runtime clips must be baked and verified in the target engine. The animation library provides procedural walk, run, jump, combat-ready, idle/interaction and reach clips; it is not motion capture or combat choreography certification.

### 3. Facial animation
```bash
blender -b --python pipeline/blender/facial_morph_pack.py -- input.glb face.glb face-report.json
blender -b --python pipeline/blender/facial_animation_clips.py -- face.glb face-animated.glb facial-report.json
```
The current pack includes named expression morphs and 12 starter visemes. It is not the full ARKit 52 set, audio-derived phoneme alignment, or a capture-quality facial performance system. Eye aim is provided by the advanced rig worker. Production facial approval requires sculpted targets and target-engine playback.

### 4. Retopology and texture baking
```bash
blender -b --python pipeline/blender/retopologize.py -- high.glb retopo.glb 300
blender -b --python pipeline/blender/retopo_quality_qa.py -- retopo.glb retopo-quality.json
blender -b --python pipeline/blender/bake_pbr_textures.py -- high.glb low.glb baked/ 2048
python pipeline/scripts/validate_phase3_mesh_reports.py --retopo retopo.glb.retopo.json
python pipeline/scripts/validate_phase3_mesh_reports.py --bake baked/bake-report.json --min-resolution 2048
```
The bake worker performs actual UV-targeted Cycles selected-to-active diffuse, tangent-normal and AO bakes. Its metallic/roughness map currently packs authored low-poly material factors; it is not a high-to-low geometric bake of metallic/roughness. Quadriflow output is a retopology candidate; edge flow, deformation loops, UV packing and texel density still require artist approval.

## Release gates

An asset must remain draft/review-required until all applicable evidence exists:
- Cloth cache baked across the full animation range; no unacceptable body penetration, garment self-intersection, tearing or pin instability.
- IK/FK switching and deformation tested at extreme joint poses; finger chains and facial joints inspected.
- Every animation clip has correct timing, loop seams, foot contacts, root-motion policy and target-engine playback evidence.
- Facial target names, sculpt quality, eye gaze, blink and audio/viseme synchronization approved.
- Retopology has artist-approved edge flow and deformation loops; UVs have seam and texel-density review.
- Bakes have projection/cage review, seam inspection, tangent-space validation, mipmap checks and target-engine material inspection.
- Provenance/licensing, GLB validation, LOD budgets, signed artist review and target-engine import/performance evidence are complete.

Automated preflight is not visual certification. Do not mark an asset game-ready from CI-only evidence.

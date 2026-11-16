# Phase 4 — Character Quality & Animation

## Implemented pipeline workers

| Area | Worker | Automated coverage |
|---|---|---|
| Garment collision | `pipeline/blender/garment_collision_qa.py` | Rest-pose body penetration, non-adjacent self-overlap candidates and three rigid pose samples |
| Advanced rigging | `pipeline/blender/advanced_rig_controls.py` | Finger chains, IK targets, IK/FK switch property, eye aim constraints and jaw/eye facial joints |
| Full-body animation | `pipeline/blender/animation_library.py` | Walk, run, jump, combat-ready, idle-interaction and reach clips at 30 FPS |
| Facial animation | `pipeline/blender/facial_morph_pack.py`, `facial_animation_clips.py`, `facial_lipsync.py` | Expanded expression and viseme morphs, timed expression clips and externally timed phoneme-to-viseme cues |
| Retopology QA | `pipeline/blender/retopo_quality_qa.py` | UV presence, welded seam-aware manifold checks, boundary edges, valence histogram, edge-length variation and deformation review flags |
| Texture baking | `pipeline/blender/bake_pbr_textures.py` | Cycles selected-to-active UV baking for diffuse color, tangent normals and AO; metallic/roughness channels packed from authored material factors |

## Automated acceptance

GitHub Actions creates deterministic Blender fixtures and runs the workers. It validates exported GLB files and JSON reports. The garment fixture must pass the sampled clearance preflight. Retopology QA rejects missing UVs, open boundaries and non-manifold edges. The bake validator checks map completeness, dimensions, channels, output containment and SHA-256 digests. Facial lip-sync CI consumes `pipeline/manifests/sample-lipsync-timeline.json`.

## Important limitations — not production certification

- Garment pose sampling currently uses three synthetic rigid rotations, not a complete skeletal animation sweep. It does not run cloth simulation, continuous collision detection or runtime physics.
- Self-overlap checks are BVH candidate checks; complex cloth intersections need DCC/engine visual confirmation.
- IK/FK controls and pole positions need animator calibration. Blender custom control widgets and constraints are not preserved as a complete runtime control rig in glTF; constraints must be baked for runtime delivery.
- Finger and facial-joint weights are proximity-seeded and require weight painting and deformation review.
- Full-body clips are deterministic keyframe blockouts, not motion-captured animation. Foot locking, root-motion retargeting, contact solving and combat choreography are not certified.
- Facial cues require external phoneme timestamps. The pipeline does not infer phonemes from raw audio. The expanded morphs are not an ARKit 52 mapping.
- Quadriflow output is an automated candidate. Edge-flow metrics cannot establish anatomically correct deformation loops; artist topology approval remains required.
- Diffuse, tangent-normal and AO are real UV-based high-to-low Cycles bakes. Metallic/roughness is packed from authored Principled BSDF factors, not inferred from sculpt geometry.
- Unity/Unreal import, target-device performance, memory and visual approval require external engine runs and human review.

## Release gate

The pipeline reports `artist_review_required: true` and `engine_certified: false`. Do not label the character assets game-ready until a qualified artist signs off on topology, weights, poses, facial performance and materials, and target-engine import/performance evidence is attached to the production package.

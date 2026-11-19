# Phase 5 — Stylized Character Asset Factory v1

## Objective
Move the character prototype into a reproducible Blender-authored asset path. The first original stylized explorer candidate includes layered garments, facial landmarks, hair locks, hands with five fingers, footwear, accessories, PBR materials, a humanoid skeleton, normalized skin weights and a looping idle action.

## Generate locally
Requires Blender 4.2+ with the glTF 2.0 exporter and Python 3.10+.

```bash
mkdir -p artifacts/stylized
blender --background --python pipeline/blender/generate_stylized_character.py -- artifacts/stylized FG-HUM-STYLIZED-000001 100001
python pipeline/scripts/validate_glb.py --require-rig artifacts/stylized/FG-HUM-STYLIZED-000001.glb
python pipeline/scripts/validate_stylized_character.py artifacts/stylized/FG-HUM-STYLIZED-000001-report.json
```

## Deliverables
- Self-contained GLB with mesh objects, PBR materials, skin and animation.
- Editable `.blend` source.
- JSON report with deterministic seed, geometry counts and GLB checksum.
- Explicit release boundary: generated candidate, artist review required, engine certification false.

## Quality boundary
This is a significant upgrade from the primitive web preview, but it is not an AAA sculpt or a certified production character. The generator uses assembled smooth meshes, procedural weights and a simple idle action. It still requires retopology review, UV/material inspection, weight-paint correction, facial morph authoring, full animation suite, cloth collision QA, and Unity/Unreal/Godot import validation before any game-ready claim.

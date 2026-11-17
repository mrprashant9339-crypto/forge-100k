# Phase 4 real-asset intake

Before running garment fitting, inspect the actual body and garment assets:

```bash
blender -b --python pipeline/blender/inspect_phase4_assets.py -- body.glb garment.glb intake-report.json
python pipeline/scripts/validate_phase4_intake_report.py intake-report.json
```

The preflight checks:
- A mesh and exactly one armature in each GLB.
- Compatible body/garment bone names.
- UVs, material slots, finite coordinates and non-degenerate triangles.
- A garment armature modifier.
- A non-empty authored cloth pin group and a `Forge_Tear_Seam` path.

The script is intentionally fail-closed. glTF may not preserve arbitrary Blender vertex groups as named editable groups. If pin/seam metadata is missing from the GLB, provide the source `.blend` and preserve the authored groups there; do not invent them from a fixture or assume the GLB contains them.

A passed intake report only permits the next fit stage. It never marks the asset game-ready. Continue with shared-rig fitting, full action-specific cloth cache baking, collision QA, artist review and target-engine playback. Keep body/garment source files and SHA-256 hashes with the production asset record.

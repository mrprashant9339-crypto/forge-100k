# Rigging stage (prototype)

The rig worker imports a generated GLB, creates a humanoid armature, assigns deterministic rigid per-part weights and authors a looping idle clip. It exports a new GLB plus a rig report.

```bash
blender --background --python pipeline/blender/rig_character.py -- artifacts/FG-HUM-000001.glb artifacts/rigged/FG-HUM-000001-rigged.glb
python pipeline/scripts/validate_glb.py artifacts/rigged/FG-HUM-000001-rigged.glb
```

**Quality limitation:** this first rig stage is an integration prototype. Mesh parts are rigidly weighted to bones; it does not provide smooth deformation, corrective shapes, retargeting, facial rigging, motion capture, or production animation QA. Do not label its outputs game-ready.

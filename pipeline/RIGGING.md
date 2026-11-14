# Rigging and deformation validation

Run the complete local sequence:

```bash
blender --background --python pipeline/blender/generate_batch.py -- pipeline/manifests/sample-batch.json
mkdir -p artifacts/rigged
blender --background --python pipeline/blender/rig_character.py -- artifacts/FG-HUM-000001.glb artifacts/rigged/FG-HUM-000001-rigged.glb
python pipeline/scripts/validate_glb.py --require-rig artifacts/rigged/FG-HUM-000001-rigged.glb
blender --background --python pipeline/blender/qa_character.py -- artifacts/rigged/FG-HUM-000001-rigged.glb artifacts/rigged/FG-HUM-000001-qa.json
```

The rig uses top-four inverse-distance normalized weights per vertex and a looping idle animation. The QA worker checks UV presence, Principled shader materials, armature modifiers, applied scales, animation presence and actual evaluated mesh movement at frame 16.

This is an automated prototype gate for the current modular blockout. It is not a substitute for joint-specific weight painting, corrective shapes, retargeting, deformation review across extreme poses, or artist sign-off.

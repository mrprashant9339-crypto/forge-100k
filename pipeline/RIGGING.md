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


## Sampled deformation QA for all rig profiles

The CI pipeline now runs `pipeline/blender/rig_deformation_qa.py` for
`humanoid_v1`, `mechanical_v1`, `quadruped_v1` and `avian_v1` after
GLB rig validation. The worker samples the animation's keyed frames plus
standard checkpoints, checks finite/nonnegative normalized skin weights,
the four-influence ceiling, armature binding, evaluated vertex coordinates,
mesh bounds and triangle degeneracy. It writes a per-profile JSON report.

Run it locally with:

```bash
blender --background --python pipeline/blender/rig_deformation_qa.py -- input-rigged.glb rig-deformation-qa.json
```

A passing report is an automated geometry/weight gate only. Joint-specific
deformation quality, foot/hand contact, retargeting, corrective shapes,
species-specific motion and Unity/Unreal/Godot runtime behavior still require
review in the target DCC/engine by qualified artists and technical animators.

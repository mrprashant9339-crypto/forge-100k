# Phase 1 — Character quality foundation

## Implemented pipeline gates

- Deterministic Blender blockout generation with UV unwrap and Principled BSDF materials.
- Humanoid armature generation and looping idle animation.
- Top-four inverse-distance normalized vertex weights, replacing rigid per-part assignments.
- GLB structural validator with strict skin + animation mode.
- Blender-side QA for UV presence, Principled material nodes, armature modifiers, applied object scale, active animation and evaluated mesh deformation.

## CI proof

The pipeline CI generates human and robot GLBs, validates both, rigs the human GLB, runs strict GLB checks, then evaluates the rigged file in Blender and fails the build if any QA check fails.

## Important quality boundary

This completes the automated Phase 1 foundation for the current stylized humanoid blockout. It does **not** mean production-ready character art. The current generated models are low-poly blockouts. PBR materials are Principled shader materials with base color / metallic / roughness parameters; dedicated baked texture maps, high-resolution sculpting, retopology, corrective shapes, facial rigs, motion-capture animation, multiple body archetypes, creature-specific skeletons and human artist sign-off remain future production work. Outputs must not be marketed as AAA or game-ready.

# Phase 3 — Production character content

Phase 3 is now open for implementation in parallel with the explicitly outstanding Phase 2 production acceptance gates. Starting Phase 3 does not mark Phase 2 complete.

## First implementation slice: PBR material contracts
- A versioned metallic-roughness material manifest schema.
- Explicit base-color (sRGB), metallic-roughness (linear) and normal (linear) texture declarations.
- Numeric factor bounds, unique material IDs, required provenance and relative texture-path checks.
- Unit tests and CI validation.

The starter material manifest is a contract fixture. Its texture references are intentionally not shipped as fabricated image assets. Run the validator with `--allow-missing-textures` to validate the contract only. A full validation requires the real referenced texture files.

## Still required for production
Texture baking, channel packing verification from image pixels, UV validation, tangent-space normal validation, resolution/mipmap checks, artist review and target-engine import/performance certification. Passing this manifest gate is not proof of game-ready quality.

## Next Phase 3 slices
1. Texture bake/packing worker with real image fixtures and deterministic outputs.
2. Facial expression/viseme clip schema and animation validation.
3. Original garment, hair and armour asset pack manifests with provenance and LOD requirements.
4. Artist review checklist and Unity/Unreal/Godot import test harnesses.

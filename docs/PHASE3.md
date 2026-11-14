# Phase 3 — Production character content

## Implemented foundation
- Versioned metallic-roughness material manifest schema with bounded factors and provenance.
- Texture-reference validator and unit tests.
- Blender procedural PBR texture authoring worker: deterministic base-color, metallic-roughness, tangent-normal and occlusion PNG maps at power-of-two resolutions (64–2048).
- Explicit channel packing: metallic-roughness G=roughness, B=metallic; normal map RGB=tangent normal; AO grayscale.
- CI generates real PNG files, validates file references, and uploads texture/report artifacts.

## Honest limitations
The procedural map worker authors maps; it does not bake a production mesh's high-resolution sculpt into UV textures. The starter material is dielectric clay with metallic=0. The normal and AO maps are procedural approximations, not sculpt-derived detail or physically validated occlusion. UV seam, tangent basis, mipmap, compression, color-management and target-engine visual checks still need implementation/review. No output is labelled game-ready.

## Remaining Phase 3
1. Production high-resolution base meshes and sculpt-to-game retopology.
2. High-to-low UV texture baking and verified channel packing.
3. Facial expression/viseme animation packs.
4. Original production clothing, hair and armour packs.
5. Artist review and Unity/Unreal/Godot import certification.

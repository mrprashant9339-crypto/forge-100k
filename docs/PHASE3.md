# Phase 3 — Production character content

## Implemented pipeline foundations

- Versioned metallic-roughness material manifest schema, texture-reference validator and unit tests.
- Deterministic procedural PBR texture authoring for base-color, metallic-roughness, tangent-normal and AO maps. These are starter maps, not sculpt-derived bakes.
- `pipeline/blender/retopologize.py`: Blender Quadriflow retopology-candidate worker. It preserves the source mesh, creates a low-poly candidate, generates a starter Smart UV Project layout and reports topology metrics. This is automated retopology draft output, not artist-authored deformation topology.
- `pipeline/blender/bake_pbr_textures.py`: Blender Cycles high-to-low selected-to-active baking worker with configurable resolution (64–4096), default projection distances, per-mesh output names, diffuse-color, tangent-normal and AO maps. Metallic/roughness remain authored material data and are not synthesized from a sculpt.
- `pipeline/scripts/validate_phase3_mesh_reports.py`: validates retopology reports, UV presence, closed-mesh edge checks and existence/resolution of baked PNG maps.
- CI creates high/low mesh fixtures, runs Quadriflow retopology and Cycles high-to-low baking, then validates the generated GLB, report JSON and PNG dimensions.
- `pipeline/blender/facial_morph_pack.py`: six expression morphs and five starter visemes.
- `pipeline/blender/facial_animation_clips.py`: timed starter expression/viseme curves at 30 FPS, exported as GLB animation data. This is a procedural clip set, not audio-synchronized phoneme performance or ARKit 52.
- `pipeline/scripts/validate_production_asset.py`: GLB container preflight that explicitly keeps artist approval and engine certification false unless external acceptance is supplied.
- CI syntax-checks the baking/animation workers and runs the timed facial animation worker against the generated facial fixture, then validates the resulting GLB morph structure and report.
- `pipeline/schemas/production-asset.schema.json` and `pipeline/scripts/validate_production_package.py` define a versioned asset-package contract, source-file SHA-256/provenance checks, path traversal protection and explicit release gates for artist review, geometry/UV/PBR approval, rigging/animation and declared target-engine import evidence. Draft packages can be checked without falsely claiming game-ready status.
- `pipeline/tests/test_production_package.py` exercises schema validity, invalid enums/timestamps, valid draft packages, source hash mismatch, path traversal, missing approval evidence and blocked game-ready promotion. The package validator now executes Draft 2020-12 JSON Schema validation (including date-time formats), verifies every referenced source/GLB/LOD/PBR/texture/clip/review-evidence file remains inside the package root, and checks source SHA-256.

## Production gates that remain open

1. **Production basemesh and retopology:** the automated Quadriflow candidate worker and CI fixture now exist. A real production human/creature sculpt, artist-approved edge flow and deformation loops, production UV packing, and approved retopology for each supported species are still required.
2. **High-to-low baking:** the Cycles worker is now exercised against a generated high/low fixture in CI. It bakes diffuse color, tangent normals and AO. It is not yet validated against an approved sculpt/retopo asset; tune cage/ray settings per asset, author metallic/roughness packing, and inspect skew, seams, tangent basis, mipmaps and engine appearance.
3. **Facial animation:** timed starter curves are present. ARKit 52 mapping, phoneme/audio synchronization, eye blink/gaze controls, capture-quality performance and artist facial approval remain open.
4. **Clothing, hair and armour:** existing CC0 procedural modules are blockout accessories. They are not production garments, groomed hair assets, cloth-simulated pieces or pose-tested armour packs.
5. **Artist review and engine certification:** these require a qualified human reviewer and actual Unity, Unreal and/or Godot imports on target versions/devices. CI's GLB/container checks cannot certify visual quality, runtime materials, skinning, animation, memory or frame time.

## Required evidence before Phase 3 can be marked complete

- Approved source sculpt and artist-reviewed retopologized low-poly mesh for each supported body/species (automated Quadriflow output alone is insufficient).
- UV inspection report and reproducible high-to-low bake report from the approved sculpt/retopo pair, with per-asset cage settings, packed material channels and target-engine inspection.
- Facial clip review with audio timing, eye rig and target-engine playback.
- Original clothing/hair/armour source files, topology, UVs, PBR maps, LODs, rig/cloth/collision tests and provenance.
- Signed artist review plus engine import/performance test reports for each claimed target engine.

No asset is labelled game-ready until those gates have evidence. This phase is **partially implemented**, not production-complete.

# Phase 3 — Production character content

## Implemented pipeline foundations

- Versioned metallic-roughness material manifest schema, texture-reference validator and unit tests.
- Deterministic procedural PBR texture authoring for base-color, metallic-roughness, tangent-normal and AO maps. These are starter maps, not sculpt-derived bakes.
- `pipeline/blender/bake_pbr_textures.py`: Blender Cycles high-to-low selected-to-active baking worker for matching high/low mesh names and low-mesh UVs. It authors diffuse-color, tangent-normal and AO maps and emits a report. It does not synthesize metallic/roughness from a sculpt; those values remain authored material data. UV/cage quality still requires review.
- `pipeline/blender/facial_morph_pack.py`: six expression morphs and five starter visemes.
- `pipeline/blender/facial_animation_clips.py`: timed starter expression/viseme curves at 30 FPS, exported as GLB animation data. This is a procedural clip set, not audio-synchronized phoneme performance or ARKit 52.
- `pipeline/scripts/validate_production_asset.py`: GLB container preflight that explicitly keeps artist approval and engine certification false unless external acceptance is supplied.
- CI syntax-checks the baking/animation workers and runs the timed facial animation worker against the generated facial fixture, then validates the resulting GLB morph structure and report.

## Production gates that remain open

1. **Production basemesh and retopology:** no sculpted high-resolution human/creature basemesh, artist-authored edge flow, deformation loops, production UV layout, or retopology result is present. A procedural blockout or voxel remesh is not an acceptable substitute.
2. **High-to-low baking:** a real baking worker now exists, but it has not been validated against an approved sculpt/retopo pair. Metallic/roughness packing is not derived from the sculpt, and cage, skew, seam, tangent, mipmap and engine checks require evidence.
3. **Facial animation:** timed starter curves are present. ARKit 52 mapping, phoneme/audio synchronization, eye blink/gaze controls, capture-quality performance and artist facial approval remain open.
4. **Clothing, hair and armour:** existing CC0 procedural modules are blockout accessories. They are not production garments, groomed hair assets, cloth-simulated pieces or pose-tested armour packs.
5. **Artist review and engine certification:** these require a qualified human reviewer and actual Unity, Unreal and/or Godot imports on target versions/devices. CI's GLB/container checks cannot certify visual quality, runtime materials, skinning, animation, memory or frame time.

## Required evidence before Phase 3 can be marked complete

- Approved source sculpt and retopologized low-poly mesh for each supported body/species.
- UV inspection report and reproducible high-to-low bake report with approved cage settings and packed material channels.
- Facial clip review with audio timing, eye rig and target-engine playback.
- Original clothing/hair/armour source files, topology, UVs, PBR maps, LODs, rig/cloth/collision tests and provenance.
- Signed artist review plus engine import/performance test reports for each claimed target engine.

No asset is labelled game-ready until those gates have evidence. This phase is **partially implemented**, not production-complete.

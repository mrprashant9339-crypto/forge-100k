# Phase 2 — Modular character and morphology foundation

## Competitor research translated into original implementation

Research inspected public repositories and their published technical documentation:
- M3-org/CharacterStudio: data-driven trait manifests, separate app and asset packs, batch VRM/preview export, mesh merging and texture atlasing, face culling and optimizer workflows.
- kblood/CharacterCreator: engine-agnostic GLB output, morph-target body controls, clothing as separate skinned packs, per-asset provenance, on-demand part loading and garment/body fit validation.
- makehumancommunity/mpfb2: sparse vertex-delta target format, macro/detail morphology, target metadata and shape-key propagation to proxy meshes.
- InFaNsO/AssetForge: declarative 13-stage pipeline, typed algorithmic/ML/hybrid/manual stages, pluggable backends, validation and provenance records.

Forge implements original versions of the data-contract and deterministic-generation ideas. No competitor code or proprietary models are copied.

## Delivered in this phase

- Deterministic morphology core with 10 face controls and 7 body controls, strict numeric ranges and stable per-asset seeds.
- Data-only modular asset catalog with slots, species compatibility, sockets, layers, LOD declarations and per-item CC0 provenance.
- Duplicate module and occupied-slot conflict validation.
- Blender Phase 2 worker that adds 10 localized facial shape keys plus 7 body-part morphology shape keys, and attaches selected procedural hair, helmet, chest armour, backpack, shoulder and footwear modules.
- GLB validator supports a required morph-target gate.
- CI generates Phase 2 human GLB, validates morph targets, rigs the modular output and re-validates skin, animation and morph targets.
- Unit tests cover deterministic controls, range errors, duplicate modules and slot conflicts.\n- Blender LOD worker creates independent LOD0/LOD1/LOD2 GLBs from a common source, preserves selected armature/empty hierarchy, reports measured triangle counts and is exercised by CI GLB validation.

## Honest limitations

These are procedural starter facial shape keys, not a photorealistic face system, not 52 ARKit face units, and not a complete phoneme/viseme solution. Body-profile shape keys now deform the current separate blockout meshes. They are not yet calibrated against a continuous production basemesh. Current procedural modules are prototypes, not artist-finished clothing. Clothing fit, body-zone occlusion, cloth simulation, mesh retopology, PBR texture baking, creature-specific skeletons, texture atlasing/mesh merging, engine performance budgets and Unity/Unreal/Godot import certification remain open. Automated LOD decimation is now present, but it is not a substitute for silhouette review, animation deformation checks at each LOD or measured engine budgets.


## Additional Phase 2 pipeline workers

- `pipeline/blender/fit_garment.py` imports a body and garment GLB, applies a bounded nearest-surface Shrinkwrap proxy fit, and emits semantic body-zone vertex groups plus a machine-readable report. It explicitly does not claim cloth simulation, certified collision detection or runtime body occlusion.
- `pipeline/blender/merge_meshes.py` merges static meshes that share a material signature while preserving UV/material slots. Meshes with shape keys are deliberately isolated to avoid breaking morph vertex correspondence. This is not texture-atlas baking.
- CI now syntax-checks both workers. They remain prototype pipeline stages until fixture-based geometry tests and target-engine validation are added.

## Phase 2 completion gate

Phase 2 is not considered production-complete while any of these remain open: continuous production basemesh deformation, sculpt-quality facial topology and ARKit/viseme mapping, garment pose/collision/cloth validation, species-specific retargeting and deformation certification, texture-atlas baking, and measured Unity/Unreal/Godot import/performance tests. The current repository supplies starter workers and structural gates, not artist-certified game assets.

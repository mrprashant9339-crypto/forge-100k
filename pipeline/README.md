# Forge 100K Production Character Pipeline

This directory starts the reproducible asset factory. It is deliberately separate from the browser demo.

## Pipeline contract

1. **Intake** — accept a versioned JSON job manifest with a stable asset ID, archetype, style, seed, target profile and provenance record.
2. **Generate** — run Blender in background mode; deterministic geometry and material parameters derive from the job seed.
3. **Prepare** — UV unwrap, apply transforms, calculate bounds and export GLB.
4. **Rig / animate** — dedicated workers add approved humanoid or creature skeletons, skin weights and animation clips. The initial worker emits an explicit rigging-pending state; it must not silently label an unrigged model as game-ready.
5. **Validate** — parse GLB container, validate glTF 2.0 JSON/chunks, scene graph, meshes, accessors, material/texture references, bounds and configured budgets.
6. **Review** — human QA checks silhouette, deformation, topology, UVs, materials, cultural accuracy and licensing.
7. **Publish** — only approved immutable artifacts are copied to object storage/CDN and entered in the asset registry.

## Run locally

Requires Blender 4.2+ with glTF export enabled and Python 3.10+.

```bash
blender --background --python pipeline/blender/generate_batch.py -- pipeline/manifests/sample-batch.json
python pipeline/scripts/validate_glb.py artifacts/FG-HUM-000001.glb
```

The first generator is a deterministic stylized blockout worker for pipeline integration. It is not an AAA sculpt/retopology/texture/animation system. The manifest and report explicitly record this quality tier.

## Production deployment

Run workers in isolated containers with pinned Blender builds, CPU/GPU quotas, timeouts, per-job temporary directories and signed input/output manifests. Keep source .blend files, generated GLBs, validation reports and provenance records. Do not publish on generation success alone.

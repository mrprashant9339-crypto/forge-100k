# Phase 5 — Stylized Character Factory and 100K Preset Engine

## Character generation

Requires Blender 4.0.2+ with the glTF 2.0 exporter and Python 3.10+. The generator selects a render engine supported by the installed Blender build; rendering is not required for GLB export.

```bash
mkdir -p artifacts/stylized
blender --background --python pipeline/blender/generate_stylized_character.py -- artifacts/stylized FG-HUM-STYLIZED-000001 100001
python pipeline/scripts/validate_glb.py --require-rig artifacts/stylized/FG-HUM-STYLIZED-000001.glb
python pipeline/scripts/validate_stylized_character.py artifacts/stylized/FG-HUM-STYLIZED-000001-report.json
blender --background --python pipeline/blender/rig_deformation_qa.py -- artifacts/stylized/FG-HUM-STYLIZED-000001.glb artifacts/stylized/deformation-qa.json
```

The generated candidate contains assembled stylized geometry, PBR materials, a humanoid skeleton, normalized four-influence skin weights, and an idle action. Blender 4.0 bone naming is aligned with the shared humanoid rig pipeline.

## Advanced rig, face and motion stages

The CI pipeline chains the candidate through:
- Rig deformation QA: weight normalization, influence cap, finite evaluated geometry, non-collapsed meshes and sampled animation movement.
- Advanced rig controls: arm/leg IK targets and poles, an IK/FK switch property, finger chains, eye aim and jaw/eye facial joints.
- Facial morph pack: starter expression and viseme shape keys.
- Timestamped lip-sync: viseme animation driven by externally supplied phoneme/viseme cues.
- Animation library: walk, run, jump, combat-ready, idle-interaction and reach-interaction NLA clips.

These are procedural starter controls and clips. They are not motion-captured or artist-certified. The Blender constraints and control UI are DCC authoring features; glTF does not preserve all Blender constraint UI. Runtime IK/FK must be baked or implemented in the target engine. Lip-sync currently consumes authored timestamps and does not perform speech recognition or raw-audio phoneme extraction.

## 100K procedural preset catalogue and queue manifests

The dimensional catalogue is defined in `pipeline/catalog/character-dimensions.json`. Its Cartesian product is exactly 100,000 unique combinations:

- 10 archetypes
- 5 body profiles
- 8 face profiles
- 5 hair profiles
- 10 outfit profiles
- 5 material palettes

Generate a bounded local catalogue and queue batches:

```bash
python pipeline/scripts/build_character_catalog.py --output artifacts/catalog --batch-size 500
```

The builder streams deterministic preset records to `presets.jsonl`, writes bounded queue manifests under `queue/`, and emits `catalog-report.json`. Each queue entry is wrapped in the existing generation worker's `job_type=character` and `request.asset` contract, with original-procedural provenance, a GLB2 target, a supported starter style, and a deterministic seed. The 100K catalogue remains a preset index; queue entries request blockout generation, not 100K prebuilt GLBs. Use `--offset` and `--limit` for resumable ranges. Preset IDs and hashes are deterministic; batch execution policy records concurrency, retries and idempotency keys.

## Queue, storage and release boundaries

The repository also contains a Supabase-backed generation worker, private object storage uploads, owner-scoped asset catalog/version records, job leases/heartbeats, retry/failure handling, GLB header checks and a blockout-only worker policy. The 100K preset catalogue and its local batch manifests are now deterministic, but they are not yet automatically enqueued into a live Supabase project by this builder. The current cloud worker deliberately accepts only blockout jobs; stylized candidate jobs require a separately authorized worker stage and matching RLS/storage deployment.

CI validates the generated candidate, its deformation report, the advanced rig, facial morphs, lipsync, animation library, and the 100K catalogue builder. Generated GLB/Blend/report outputs remain CI artifacts rather than source-controlled binaries.

## Release status

All generated character outputs remain `generated_candidate` pending artist review. Automated structural and deformation checks do not certify visual quality, cloth/body collision in every pose, topology, UV layout, material appearance, or Unity/Unreal/Godot runtime behavior. Never label these outputs AAA or game-ready until target-engine import, animation playback, collision review, performance budgets and human approval are recorded.

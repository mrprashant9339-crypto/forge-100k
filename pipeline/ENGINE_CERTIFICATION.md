# Phase A/B real-asset and engine certification

## Phase A — real source asset
1. Record original source, body and garment GLBs, creator, licence and SHA-256 hashes.
2. Run real-asset intake, retopology, UV, PBR bake, rig deformation, facial morph/lip-sync, garment fitting, pose and self-intersection QA.
3. Bake and inspect walk, run, jump and combat; require zero body penetration and zero garment self-intersection in sampled frames.
4. Collect reviewer identity, dated artist approval and review evidence. Automated checks cannot sign this review.

Existing commands:
```bash
blender -b --python pipeline/blender/inspect_phase4_assets.py -- body.glb garment.glb intake-report.json
python pipeline/scripts/validate_phase4_intake_report.py intake-report.json
python pipeline/scripts/validate_phase4_release.py asset.release.json --report asset.release-report.json
```

## Phase B — native engine certification
Run the asset in the actual supported Unity and Unreal editor/runtime versions. Capture a JSON report from each native engine harness and attach non-empty evidence (for example, test log plus capture/video). Include exact engine version and target platform; successful model/material/texture/skeleton/animation import; zero missing materials/textures; walk/run/jump/combat playback with evaluated frames; at least 12 collision pose samples with zero penetration/intersection; and at least 300 performance samples.

Validate each engine report:
```bash
python pipeline/scripts/validate_engine_certification.py unity-report.json --root ./production/FG-HUM-REAL-0001 --require-engine unity
python pipeline/scripts/validate_engine_certification.py unreal-report.json --root ./production/FG-HUM-REAL-0001 --require-engine unreal
```

Default budgets: minimum 30 FPS, p95 frame time at most 33.34 ms, peak memory at most 4096 MB, at most 250 draw calls and 150,000 triangles. Projects may tighten or explicitly override these in the report `budgets` object. Record hardware/platform; these budgets are not universal device guarantees.

## Gate integrity
The report contract is demonstrated by `pipeline/tests/test_engine_certification.py`. The validator checks report structure, gate values and evidence-file presence. It does not launch Unity/Unreal, measure FPS itself, authenticate an artist, or prove that supplied media corresponds to the tested build. Those results must originate from native editor/runtime tests and human review. Missing engine installations, real source assets or signed review evidence remain BLOCKED, never auto-passed.

## Performance regression policy
Keep asset revision, engine version, platform, hardware, render pipeline and quality settings identical for before/after comparisons. Save raw frame-time samples and profiler captures. Compare minimum FPS, p95 frame time, memory, draw calls and triangles; do not substitute estimates for measurements.
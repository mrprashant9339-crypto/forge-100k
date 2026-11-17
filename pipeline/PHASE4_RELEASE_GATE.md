# Phase 4 production release gate

The automated Blender fixtures prove that pipeline workers execute; they do not prove that a real character is production-ready. Phase 4 release promotion is therefore fail-closed and requires evidence from real source assets, all four animation actions, collision sampling, artist approval, provenance and target-engine playback.

## Validate a production evidence manifest

```bash
python pipeline/scripts/validate_phase4_release.py production/FG-HUM-PROD-0001.release.json --report production/FG-HUM-PROD-0001.release-report.json
```

Use `--require-physical-tear` when a project explicitly requires stress-driven physical tearing. The current authored seam split + shape-key animation is recorded honestly as `authored_seam_animation`; it is not a physical fabric tear solver.

## Required manifest

```json
{
  "schema_version": "1.0",
  "asset_id": "FG-HUM-PROD-0001",
  "asset_kind": "humanoid",
  "is_synthetic_fixture": false,
  "source_assets": {
    "body_glb": "body.glb",
    "garment_glb": "garment.glb",
    "body_sha256": "actual 64-character SHA-256",
    "garment_sha256": "actual 64-character SHA-256"
  },
  "pose_validation": {
    "actions": {
      "walk": {"cache_baked": true, "frames_checked": 32, "issues": []},
      "run": {"cache_baked": true, "frames_checked": 32, "issues": []},
      "jump": {"cache_baked": true, "frames_checked": 32, "issues": []},
      "combat": {"cache_baked": true, "frames_checked": 32, "issues": []}
    },
    "body_penetration_vertices": 0,
    "self_intersection_pairs": 0
  },
  "collision_validation": {
    "status": "passed",
    "pose_samples": 12,
    "body_triangle_intersections": 0,
    "self_triangle_intersections": 0
  },
  "tear_validation": {
    "mode": "authored_seam_animation",
    "validated": true,
    "report": "tear-report.json"
  },
  "artist_review": {"approved": true, "reviewer": "Reviewer", "date": "2026-11-17", "evidence": "artist-review.pdf"},
  "target_engine": {
    "name": "Unity",
    "version": "6.x",
    "import_validated": true,
    "playback_validated": true
  },
  "provenance": {"source": "Original asset", "license": "Owned"}
}
```

## Promotion rules

- Synthetic fixtures are always rejected.
- Walk, run, jump and combat must each have a baked cache, at least one checked frame and an empty issue list.
- Body penetration and self-intersection counters must be zero; collision QA must pass with at least one pose sample.
- Artist approval, reviewer identity and ISO date are mandatory.
- Target-engine import and animation playback must both be verified.
- Asset source and license must be recorded.
- Physical tearing is optional by default, but can be made mandatory with `--require-physical-tear`.

The CLI resolves evidence paths relative to the manifest directory, verifies that body/garment files exist and that their SHA-256 values match, and requires tear, artist-review and target-engine evidence files. It still cannot authenticate reviewer identity or independently prove that a video shows the claimed target-engine build; those require a trusted review process. It does not replace Blender collision QA. Only generate this manifest from completed pipeline reports and signed review records. Never hand-edit counters to force a pass.

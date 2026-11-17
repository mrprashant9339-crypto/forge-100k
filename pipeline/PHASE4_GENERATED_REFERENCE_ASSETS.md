# Phase 4 generated reference assets

The Phase 4 CI pipeline now generates a deterministic Blender reference asset pack
under `artifacts/phase4-reference/`:

- `body.glb` — simple UV-mapped proxy mannequin with a single-bone reference rig
- `garment.glb` — simple upper-body shell proxy, shared reference rig, pin and seam groups
- `forge-phase4-reference.blend` — editable source scene retaining Blender vertex groups
- `reference-asset-report.json` — SHA-256 hashes, generation facts and explicit limitations

Run locally:

```bash
blender --background --python pipeline/blender/generate_phase4_reference_assets.py -- artifacts/phase4-reference
python pipeline/scripts/validate_glb.py --require-rig artifacts/phase4-reference/body.glb
python pipeline/scripts/validate_glb.py --require-rig artifacts/phase4-reference/garment.glb
```

## Certification boundary

These are **synthetic reference fixtures**, generated to test the asset-generation
and validation workflow. They are not production anatomy, production garment
patterns, a production multi-bone rig, approved motion capture, or artist-reviewed
assets. The generator hard-codes `is_synthetic_fixture: true` and
`production_release_approved: false`; CI asserts both facts. They must never be
copied into a production release manifest or used to bypass the Phase 4 release gate.

Full production certification still requires original/licensed production assets,
real garment fitting and corrective deformation, action-specific baked cloth
caches, geometric collision QA, provenance, artist approval, and target-engine
import plus playback evidence. Physical cloth tearing must be separately proven
when the product specification requires it; an authored seam animation is not a
stress-driven physical tear solver.

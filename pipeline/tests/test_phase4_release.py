"""Unit tests for the fail-closed Phase 4 production release gate."""
import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_phase4_release import validate_manifest

def valid_manifest():
    return {
        "schema_version": "1.0",
        "asset_id": "FG-HUM-PROD-0001",
        "asset_kind": "humanoid",
        "is_synthetic_fixture": False,
        "source_assets": {
            "body_glb": "body.glb", "garment_glb": "garment.glb",
            "body_sha256": "a" * 64, "garment_sha256": "b" * 64
        },
        "pose_validation": {
            "actions": {
                name: {"cache_baked": True, "frames_checked": 32, "issues": []}
                for name in ("walk", "run", "jump", "combat")
            },
            "body_penetration_vertices": 0,
            "self_intersection_pairs": 0
        },
        "collision_validation": {
            "status": "passed", "pose_samples": 12,
            "body_triangle_intersections": 0, "self_triangle_intersections": 0
        },
        "tear_validation": {
            "mode": "authored_seam_animation", "validated": True,
            "report": "tear-report.json"
        },
        "artist_review": {"approved": True, "reviewer": "QA Artist", "date": "2026-11-17", "evidence": "artist-review.pdf"},
        "target_engine": {
            "name": "Unity", "version": "6.x",
            "import_validated": True, "playback_validated": True, "evidence": "unity-playback.mp4"
        },
        "provenance": {"source": "Original studio asset", "license": "Owned"}
    }

class ReleaseGateTests(unittest.TestCase):
    def test_valid_evidence_passes_with_authored_tear_warning(self):
        errors, warnings = validate_manifest(valid_manifest())
        self.assertEqual(errors, [])
        self.assertIn("authored_seam_animation_is_not_stress_driven_physical_tearing", warnings)

    def test_synthetic_fixture_is_never_releasable(self):
        data = valid_manifest()
        data["is_synthetic_fixture"] = True
        errors, _ = validate_manifest(data)
        self.assertIn("synthetic_fixture_cannot_be_released", errors)

    def test_missing_pose_action_blocks_release(self):
        data = valid_manifest()
        del data["pose_validation"]["actions"]["combat"]
        errors, _ = validate_manifest(data)
        self.assertIn("pose_action_combat_missing", errors)

    def test_nonzero_collision_blocks_release(self):
        data = valid_manifest()
        data["collision_validation"]["body_triangle_intersections"] = 1
        errors, _ = validate_manifest(data)
        self.assertIn("body_triangle_intersections_not_zero", errors)

    def test_unapproved_artist_review_blocks_release(self):
        data = valid_manifest()
        data["artist_review"]["approved"] = False
        errors, _ = validate_manifest(data)
        self.assertIn("artist_review_not_approved", errors)

    def test_physical_tear_can_be_made_mandatory(self):
        errors, _ = validate_manifest(valid_manifest(), require_physical_tear=True)
        self.assertIn("physical_tear_solver_required", errors)

    def test_missing_engine_playback_blocks_release(self):
        data = valid_manifest()
        data["target_engine"]["playback_validated"] = False
        errors, _ = validate_manifest(data)
        self.assertIn("target_engine_playback_not_validated", errors)

    def test_invalid_root_is_rejected(self):
        errors, _ = validate_manifest([])
        self.assertIn("manifest_root_must_be_object", errors)


    def test_evidence_root_verifies_real_asset_hashes_and_review_files(self):
        with tempfile.TemporaryDirectory() as root:
            payloads = {
                "body.glb": b"body-asset",
                "garment.glb": b"garment-asset",
                "tear-report.json": b'{"status":"pass"}',
                "artist-review.pdf": b"review-evidence",
                "unity-playback.mp4": b"engine-evidence"
            }
            for name, payload in payloads.items():
                with open(os.path.join(root, name), "wb") as handle:
                    handle.write(payload)
            data = valid_manifest()
            data["source_assets"]["body_sha256"] = hashlib.sha256(payloads["body.glb"]).hexdigest()
            data["source_assets"]["garment_sha256"] = hashlib.sha256(payloads["garment.glb"]).hexdigest()
            errors, _ = validate_manifest(data, evidence_root=root)
            self.assertEqual(errors, [])
            data["source_assets"]["body_sha256"] = "0" * 64
            errors, _ = validate_manifest(data, evidence_root=root)
            self.assertIn("source_body_glb_sha256_mismatch", errors)

    def test_missing_review_and_engine_evidence_blocks_release(self):
        data = valid_manifest()
        data["artist_review"].pop("evidence")
        data["target_engine"].pop("evidence")
        errors, _ = validate_manifest(data)
        self.assertIn("artist_review_evidence_missing", errors)
        self.assertIn("target_engine_evidence_file_missing", errors)

if __name__ == "__main__":
    unittest.main()

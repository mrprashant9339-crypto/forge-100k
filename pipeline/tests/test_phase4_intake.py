"""Tests for fail-closed Phase 4 asset intake report validation."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_phase4_intake_report import validate_report


def report():
    return {
        "schema_version": "1.0",
        "status": "asset_intake_passed",
        "fit_allowed": True,
        "production_release_approved": False,
        "errors": [],
        "body": {"sha256": "a" * 64, "mesh_count": 2, "armatures": ["BodyRig"], "meshes": [{"name": "Body"}]},
        "garment": {"sha256": "b" * 64, "mesh_count": 1, "armatures": ["GarmentRig"], "meshes": [{"name": "Jacket"}]}
    }


class IntakeReportTests(unittest.TestCase):
    def test_valid_report_passes_without_claiming_release(self):
        self.assertEqual(validate_report(report()), [])

    def test_blocked_intake_cannot_pass(self):
        data = report()
        data["status"] = "asset_intake_blocked"
        data["fit_allowed"] = False
        data["errors"] = ["pin_group_missing"]
        self.assertIn("asset_intake_not_passed", validate_report(data))
        self.assertIn("report_contains_errors", validate_report(data))

    def test_missing_body_armature_blocks(self):
        data = report()
        data["body"]["armatures"] = []
        self.assertIn("body_armature_count_invalid", validate_report(data))

    def test_invalid_hash_blocks(self):
        data = report()
        data["garment"]["sha256"] = "not-a-hash"
        self.assertIn("garment_sha256_invalid", validate_report(data))

    def test_intake_cannot_claim_production_release(self):
        data = report()
        data["production_release_approved"] = True
        self.assertIn("intake_must_not_claim_production_release", validate_report(data))

    def test_non_object_report_rejected(self):
        self.assertIn("report_root_must_be_object", validate_report([]))


if __name__ == "__main__":
    unittest.main()

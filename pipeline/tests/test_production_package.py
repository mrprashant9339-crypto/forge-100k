"""Unit tests for production package schema, integrity and release gates."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "validate_production_package.py")


class ProductionPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for name, content in (("source.blend", b"source"), ("character.glb", b"glTF-package"),
                              ("pbr.json", b'{"materials":[]}')):
            with open(os.path.join(self.root, name), "wb") as stream:
                stream.write(content)
        digest = hashlib.sha256(b"source").hexdigest()
        self.data = {
            "schema_version": "1.0", "asset_id": "FG-HUM-0001", "asset_type": "humanoid",
            "target_engines": ["unity", "unreal", "godot"],
            "source": {"file": "source.blend", "creator": "Forge team", "license": "CC0",
                       "license_evidence": "Original source authored in-house", "sha256": digest},
            "geometry": {"glb": "character.glb", "retopology_review": "pending",
                         "uv_review": "pending", "lod_files": []},
            "materials": {"pbr_manifest": "pbr.json", "bake_review": "pending", "texture_files": []},
            "rigging": {"required": True, "review": "pending", "skeleton_profile": "humanoid_v1"},
            "animation": {"required": True, "review": "pending", "clips": []},
            "reviews": {"artist": {"status": "pending"}, "engines": []},
            "release_status": "draft"
        }
        for name, content in (("review.pdf", b"artist review evidence"),
                              ("import-report.json", b'{"import":"passed"}')):
            with open(os.path.join(self.root, name), "wb") as stream:
                stream.write(content)
        self.manifest = os.path.join(self.root, "package.json")
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        with open(self.manifest, "w", encoding="utf-8") as stream:
            json.dump(self.data, stream)

    def run_validator(self):
        return subprocess.run([sys.executable, SCRIPT, self.manifest, "--root", self.root],
                              capture_output=True, text=True)

    def test_draft_package_passes_schema_file_and_provenance_checks(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PACKAGE_FILES_AND_PROVENANCE_VALID", result.stdout)

    def test_hash_mismatch_fails(self):
        self.data["source"]["sha256"] = "0" * 64
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 mismatch", result.stderr)

    def test_path_traversal_fails(self):
        self.data["source"]["file"] = "../outside.blend"
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes asset root", result.stderr)

    def test_schema_rejects_invalid_asset_type(self):
        self.data["asset_type"] = "unknown_species"
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema validation failed", result.stderr)

    def test_schema_rejects_invalid_timestamp(self):
        self.data["reviews"]["artist"] = {
            "status": "approved", "reviewer": "Artist", "reviewed_at": "not-a-date",
            "evidence": "review.pdf"
        }
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema validation failed", result.stderr)

    def test_approved_review_evidence_must_exist(self):
        self.data["reviews"]["artist"] = {
            "status": "approved", "reviewer": "Artist",
            "reviewed_at": "2026-11-14T10:00:00Z", "evidence": "missing-review.pdf"
        }
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing package file", result.stderr)

    def test_game_ready_is_blocked_without_signed_reviews(self):
        self.data["release_status"] = "game_ready"
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RELEASE BLOCKED", result.stderr)

    def test_game_ready_requires_all_declared_engine_evidence(self):
        self.data["geometry"]["retopology_review"] = "approved"
        self.data["geometry"]["uv_review"] = "approved"
        self.data["materials"]["bake_review"] = "approved"
        self.data["rigging"]["review"] = "approved"
        self.data["animation"]["review"] = "approved"
        self.data["reviews"]["artist"] = {
            "status": "approved", "reviewer": "Artist",
            "reviewed_at": "2026-11-14T10:00:00Z", "evidence": "review.pdf"
        }
        self.data["reviews"]["engines"] = [
            {"name": name, "status": "passed", "version": "test-version", "evidence": "import-report.json"}
            for name in ("unity", "unreal")
        ]
        self.data["release_status"] = "game_ready"
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("versioned import evidence is incomplete", result.stderr)


if __name__ == "__main__":
    unittest.main()

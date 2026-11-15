"""Tests for Phase 3 retopology and bake report validation."""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_phase3_mesh_reports.py"


def write_png(path, width=256, height=256, color_type=2):
    header = (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" +
              struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
    Path(path).write_bytes(header)


class Phase3ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.maps = {}
        for kind in ("diffuse", "normal", "ao", "metallic_roughness"):
            path = self.root / (kind + ".png")
            write_png(path)
            self.maps[kind] = [str(path)]
        self.report = self.root / "bake-report.json"
        self.data = {
            "status": "baked", "resolution": [256, 256],
            "meshes": [{"mesh": "Body", "uv_layer": "UVMap",
                        "metallic_factor": 0.15, "roughness_factor": 0.65}],
            "maps": self.maps,
            "channel_packing": {"metallic_roughness": "glTF channels: G=roughness, B=metallic"}
        }
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.report.write_text(json.dumps(self.data), encoding="utf-8")

    def run_validator(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--bake", str(self.report),
                               "--min-resolution", "256", *args],
                              capture_output=True, text=True)

    def test_valid_report_and_all_four_maps(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BAKE_REPORT_VALID", result.stdout)
        self.assertIn('"verified_maps": 4', result.stdout)

    def test_missing_map_category_fails(self):
        self.data["maps"].pop("normal")
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing bake map category", result.stderr)

    def test_path_traversal_fails(self):
        self.data["maps"]["normal"] = [str(self.root.parent / "outside.png")]
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes report directory", result.stderr)

    def test_resolution_mismatch_fails(self):
        write_png(self.root / "normal.png", 128, 128)
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dimensions differ", result.stderr)

    def test_invalid_material_factor_fails(self):
        self.data["meshes"][0]["metallic_factor"] = 2.0
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid metallic factor", result.stderr)

    def test_channel_packing_contract_is_required(self):
        self.data["channel_packing"]["metallic_roughness"] = "wrong channels"
        self.write()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("channel packing metadata is invalid", result.stderr)


if __name__ == "__main__":
    unittest.main()

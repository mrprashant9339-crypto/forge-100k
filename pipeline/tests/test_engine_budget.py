import json
import struct
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_engine_budget import load_gltf, triangle_total

class EngineBudgetTests(unittest.TestCase):
    def test_indexed_and_nonindexed_triangle_counts(self):
        gltf = {
            "accessors": [{"count": 9}, {"count": 6}],
            "meshes": [{"primitives": [
                {"indices": 0, "attributes": {"POSITION": 1}},
                {"attributes": {"POSITION": 1}},
            ]}],
        }
        self.assertEqual(triangle_total(gltf), 5)

    def test_load_glb_json_chunk(self):
        payload = json.dumps({"asset": {"version": "2.0"}}).encode("utf-8")
        payload += b" " * ((4 - len(payload) % 4) % 4)
        glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(payload))
        glb += struct.pack("<II", len(payload), 0x4E4F534A) + payload
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.glb"
            path.write_bytes(glb)
            self.assertEqual(load_gltf(path)["asset"]["version"], "2.0")

if __name__ == "__main__":
    unittest.main()

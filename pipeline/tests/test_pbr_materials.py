import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_pbr_materials import validate

def fixture(root):
    tex=root/"textures"; tex.mkdir(exist_ok=True)
    for name in ("basecolor.png","metallic_roughness.png","normal.png"): (tex/name).write_bytes(b"fixture")
    return {"schema_version":"1.0","materials":[{"material_id":"test_material","workflow":"metallic_roughness","base_color_factor":[0.5,0.5,0.5,1],"metallic_factor":0.1,"roughness_factor":0.8,"textures":{"base_color":{"path":"textures/basecolor.png","color_space":"sRGB"},"metallic_roughness":{"path":"textures/metallic_roughness.png","color_space":"linear"},"normal":{"path":"textures/normal.png","color_space":"linear"}},"provenance":{"creator":"unit test","license":"CC0-1.0","evidence":"Original test fixture."}}]}

class PBRTests(unittest.TestCase):
    def test_valid_manifest_and_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=fixture(root)
            result=validate(data,root/"manifest.json")
            self.assertEqual(result["status"],"pass")
            self.assertFalse(result["game_ready"])
    def test_missing_required_map(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=fixture(root); del data["materials"][0]["textures"]["normal"]
            with self.assertRaises(SystemExit): validate(data,root/"manifest.json",False)
    def test_wrong_color_space(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=fixture(root); data["materials"][0]["textures"]["normal"]["color_space"]="sRGB"
            with self.assertRaises(SystemExit): validate(data,root/"manifest.json",False)
    def test_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=fixture(root); data["materials"].append(data["materials"][0].copy())
            with self.assertRaises(SystemExit): validate(data,root/"manifest.json",False)
    def test_out_of_range_roughness(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=fixture(root); data["materials"][0]["roughness_factor"]=1.5
            with self.assertRaises(SystemExit): validate(data,root/"manifest.json",False)

if __name__=="__main__": unittest.main()

import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_engine_certification import validate_report

class EngineCertificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=self.tmp.name
        Path(self.root,"engine-evidence.txt").write_text("native engine evidence",encoding="utf-8")
        self.report={"schema_version":"1.0","asset_id":"FG-HUM-REAL-0001","engine":"unity","engine_version":"6000.0.30f1","is_synthetic_fixture":False,
          "import":{"status":"passed","checks":["model","materials","textures","skeleton","animations"],"missing_materials":0,"missing_textures":0},
          "animation":{"clips":[{"name":n,"status":"passed","frames_evaluated":60} for n in ("walk","run","jump","combat")]},
          "collision":{"status":"passed","body_penetrations":0,"self_intersections":0,"pose_samples":12},
          "performance":{"sample_count":300,"min_fps":60,"p95_frame_ms":20,"peak_memory_mb":2048,"draw_calls":120,"triangles":80000},
          "evidence":{"file":"engine-evidence.txt"}}
    def tearDown(self): self.tmp.cleanup()
    def test_valid_report(self): self.assertEqual(validate_report(self.report,self.root),[])
    def test_synthetic_rejected(self):
        self.report["is_synthetic_fixture"]=True; self.assertTrue(any("synthetic" in x for x in validate_report(self.report,self.root)))
    def test_missing_clip_rejected(self):
        self.report["animation"]["clips"].pop(); self.assertTrue(any("walk, run, jump and combat" in x for x in validate_report(self.report,self.root)))
    def test_collision_rejected(self):
        self.report["collision"]["body_penetrations"]=1; self.assertTrue(any("penetrations" in x for x in validate_report(self.report,self.root)))
    def test_performance_regression_rejected(self):
        self.report["performance"]["p95_frame_ms"]=80; self.assertTrue(any("p95_frame_ms exceeds" in x for x in validate_report(self.report,self.root)))
    def test_missing_evidence_rejected(self):
        self.report["evidence"]["file"]="missing.mp4"; self.assertTrue(any("evidence file" in x for x in validate_report(self.report,self.root)))
    def test_path_traversal_rejected(self):
        self.report["evidence"]["file"]="../outside.mp4"; self.assertTrue(any("outside asset root" in x for x in validate_report(self.report,self.root)))
    def test_missing_import_check_rejected(self):
        self.report["import"]["checks"].remove("textures"); self.assertTrue(any("import checks" in x for x in validate_report(self.report,self.root)))
if __name__=="__main__": unittest.main()

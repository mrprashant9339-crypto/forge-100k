import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("generation_worker", ROOT / "generation_worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

class WorkerContractTests(unittest.TestCase):
    def test_accepts_valid_original_blockout_job(self):
        job = {
            "job_type": "character",
            "request": {"asset": {
                "asset_id": "FG-HUM-000042",
                "archetype": "field-explorer",
                "species": "human",
                "style": "armored",
                "seed": 420042,
                "quality_tier": "blockout",
                "target": "glTF2",
                "provenance": {"kind": "original_procedural"}
            }}
        }
        self.assertEqual(worker.safe_job_spec(job)["asset_id"], "FG-HUM-000042")

    def test_rejects_unsafe_or_unsupported_jobs(self):
        with self.assertRaises(worker.WorkerError):
            worker.safe_job_spec({"job_type": "retopology", "request": {}})
        with self.assertRaises(worker.WorkerError):
            worker.safe_job_spec({"job_type": "character", "request": {"asset": {
                "asset_id": "../../etc/passwd", "quality_tier": "blockout"
            }}})
        with self.assertRaises(worker.WorkerError):
            worker.safe_job_spec({"job_type": "character", "request": {"asset": {
                "asset_id": "FG-HUM-000042", "quality_tier": "game_ready"
            }}})

    def test_worker_never_runs_client_shell_commands(self):
        source = (ROOT / "generation_worker.py").read_text(encoding="utf-8")
        self.assertIn("subprocess.run([BLENDER", source)
        self.assertNotIn("shell=True", source)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", source)
        self.assertIn("forge-private-uploads", source)

if __name__ == "__main__":
    unittest.main()

"""Assertions for the garment QA report emitted by qa_garment_fit.py."""
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["status"] == "geometry_qa_passed", report
assert report["garment_count"] > 0, report
assert report["validated_count"] == report["garment_count"], report
assert report["collision_free_pose_certified"] is False, report
assert report["cloth_simulation_certified"] is False, report
for garment in report["garments"]:
    assert garment["status"] == "geometry_validated", garment
    assert garment["vertex_count"] >= 3, garment
    assert garment["triangle_count"] > 0, garment
    assert garment["zone_groups"], garment
    assert garment["material_slot_count"] > 0, garment
    assert not garment["issues"], garment
print("Garment fit geometry QA report passed")

"""Assertions for Phase 2 Blender worker integration reports."""
import json
import sys
from pathlib import Path

root=Path(sys.argv[1])
fit=json.loads((root/"fit-report.json").read_text())
assert fit["status"]=="proxy_fit_complete",fit
assert fit["garments"] and fit["garments"][0]["status"]=="proxy_fit_applied",fit
merge=json.loads((root/"merge-report.json").read_text())
assert merge["status"]=="mesh_merge_complete",merge
assert merge["merged_groups"],"Expected compatible static meshes to merge"
assert merge["shape_key_meshes_preserved"],"Morph mesh must remain isolated"
for profile in ("humanoid_v1","mechanical_v1","quadruped_v1","avian_v1"):
    report=json.loads((root/("rig-"+profile+".glb.rig-report.json")).read_text())
    assert report["rig_profile"]==profile,report
    assert report["weighted_vertices"]>0,report
    assert report["mesh_count"]>0,report
print("Phase 2 Blender worker integration reports passed")

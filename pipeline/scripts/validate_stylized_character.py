#!/usr/bin/env python3
import json,sys,hashlib
from pathlib import Path
def fail(m): print("FAIL:",m); raise SystemExit(1)
def main():
 if len(sys.argv)!=2: fail("Usage: validate_stylized_character.py report.json")
 p=Path(sys.argv[1]).resolve()
 if not p.is_file(): fail("report missing")
 d=json.loads(p.read_text(encoding="utf-8"))
 for k in ("schema","asset_id","seed","status","quality_tier","artist_review_required","engine_certified","files","geometry","rig","features"):
  if k not in d: fail("missing field "+k)
 if d["schema"]!="forge.stylized-character.v1" or d["status"]!="generated_candidate": fail("invalid schema/status")
 if d["artist_review_required"] is not True or d["engine_certified"] is not False: fail("candidate release boundary must remain explicit")
 root=p.parent; glb=root/d["files"]["glb"]; blend=root/d["files"]["blend"]
 if not glb.is_file() or not blend.is_file(): fail("GLB or source blend missing")
 digest=hashlib.sha256(glb.read_bytes()).hexdigest()
 if digest!=d["files"]["glb_sha256"]: fail("GLB SHA-256 mismatch")
 if d["geometry"]["mesh_objects"]<30 or d["geometry"]["vertices"]<1000: fail("geometry below detail floor")
 if d["geometry"]["materials"]<5: fail("insufficient material variety")
 if d["rig"]["bones"]<40: fail("rig is missing limb/finger bones")
 if d["rig"]["skin_binding"]!="top4_normalized" or not d["rig"]["animation"]: fail("skin/animation metadata missing")
 for f in ("layered jacket","utility backpack","articulated hands","five fingers per hand","facial landmarks","hair locks"):
  if f not in d["features"]: fail("missing feature "+f)
 print(json.dumps({"status":"pass","asset_id":d["asset_id"],"mesh_objects":d["geometry"]["mesh_objects"],"vertices":d["geometry"]["vertices"],"materials":d["geometry"]["materials"],"bones":d["rig"]["bones"],"glb_sha256":digest,"release_status":"candidate_not_game_ready"},indent=2))
if __name__=="__main__": main()

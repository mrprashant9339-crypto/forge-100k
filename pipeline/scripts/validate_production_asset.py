"""Structural acceptance preflight for Forge production character packages.
This is not a substitute for artist sign-off or target-engine certification.
"""
import argparse,json,os,sys
def main():
 p=argparse.ArgumentParser();p.add_argument("glb");p.add_argument("--report");p.add_argument("--require-uv",action="store_true");p.add_argument("--require-rig",action="store_true");p.add_argument("--require-morphs",action="store_true")
 a=p.parse_args()
 if not os.path.isfile(a.glb) or os.path.getsize(a.glb)<20: raise SystemExit("FAIL: missing/empty GLB")
 with open(a.glb,"rb") as f:
  h=f.read(12)
 if h[:4]!=b"glTF": raise SystemExit("FAIL: invalid GLB magic")
 length=int.from_bytes(h[8:12],"little")
 if length!=os.path.getsize(a.glb): raise SystemExit("FAIL: GLB declared length mismatch")
 data={"file":a.glb,"bytes":length,"container_valid":True,"uv_check":"requires Blender inspection" if a.require_uv else "not_requested","rig_check":"requires Blender inspection" if a.require_rig else "not_requested","morph_check":"requires Blender inspection" if a.require_morphs else "not_requested","artist_approved":False,"engine_certified":False,"status":"container_preflight_only"}
 if a.report:
  with open(a.report,"w",encoding="utf-8") as f:json.dump(data,f,indent=2)
 print(json.dumps(data))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Validate Forge PBR material manifests and referenced texture files."""
import json, sys
from pathlib import Path

def fail(message):
    print("FAIL:", message)
    raise SystemExit(1)

def validate(data, manifest_path, check_files=True):
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        fail("Expected schema_version 1.0")
    materials=data.get("materials")
    if not isinstance(materials,list) or not materials:
        fail("materials must be a non-empty array")
    seen=set()
    for material in materials:
        mid=material.get("material_id")
        if not isinstance(mid,str) or mid in seen: fail("Missing or duplicate material_id: "+str(mid))
        seen.add(mid)
        if material.get("workflow") != "metallic_roughness": fail(mid+": unsupported PBR workflow")
        factor=material.get("base_color_factor")
        if not isinstance(factor,list) or len(factor)!=4 or any(not isinstance(v,(int,float)) or not 0<=v<=1 for v in factor):
            fail(mid+": base_color_factor must contain four values in [0,1]")
        for key in ("metallic_factor","roughness_factor"):
            value=material.get(key)
            if not isinstance(value,(int,float)) or not 0<=value<=1: fail(mid+": "+key+" must be in [0,1]")
        textures=material.get("textures",{})
        for name in ("base_color","metallic_roughness","normal"):
            if name not in textures: fail(mid+": missing required texture "+name)
        for name, texture in textures.items():
            expected="sRGB" if name=="base_color" else "linear"
            if texture.get("color_space") != expected: fail(mid+": "+name+" must use "+expected+" color space")
            path=Path(texture.get("path",""))
            if not str(path) or path.is_absolute(): fail(mid+": texture path must be relative")
            if check_files and not (manifest_path.parent/path).is_file():
                fail(mid+": texture file not found: "+str(manifest_path.parent/path))
        provenance=material.get("provenance",{})
        for key in ("creator","license","evidence"):
            if not isinstance(provenance.get(key),str) or not provenance[key].strip():
                fail(mid+": provenance."+key+" is required")
    return {"status":"pass","materials":len(materials),"texture_references":sum(len(m["textures"]) for m in materials),"gate":"manifest-and-texture-reference-validation","game_ready":False}

def main():
    if len(sys.argv) not in (2,3): fail("Usage: validate_pbr_materials.py manifest.json [--allow-missing-textures]")
    path=Path(sys.argv[1])
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: fail("Cannot read JSON: "+str(exc))
    result=validate(data,path,check_files="--allow-missing-textures" not in sys.argv[2:])
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()

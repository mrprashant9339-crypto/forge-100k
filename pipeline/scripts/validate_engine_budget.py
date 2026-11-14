#!/usr/bin/env python3
"""Validate measurable GLB runtime budgets for Forge 100K.

Counts triangles from indexed/non-indexed glTF primitives and checks structural
budgets. This is a deterministic preflight, not a substitute for target-engine
profiling or artist review.
"""
import json
import struct
import sys
from pathlib import Path

MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A


def load_gltf(path):
    data = Path(path).read_bytes()
    if len(data) < 20:
        raise ValueError("GLB is too short")
    magic, version, length = struct.unpack_from("<III", data)
    if magic != MAGIC or version != 2 or length != len(data):
        raise ValueError("Invalid GLB header")
    offset = 12
    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + chunk_len]
        if len(chunk) != chunk_len:
            raise ValueError("Truncated GLB chunk")
        if chunk_type == JSON_CHUNK:
            return json.loads(chunk.decode("utf-8").rstrip(" \\t\\r\\n\\0"))
        offset += chunk_len
    raise ValueError("GLB JSON chunk missing")


def triangle_total(gltf):
    total = 0
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            mode = primitive.get("mode", 4)
            if mode != 4:
                continue
            if "indices" in primitive:
                accessor = gltf.get("accessors", [])[primitive["indices"]]
                count = accessor.get("count", 0)
            else:
                position = primitive.get("attributes", {}).get("POSITION")
                if position is None:
                    raise ValueError("Primitive has no POSITION accessor")
                count = gltf.get("accessors", [])[position].get("count", 0)
            total += count // 3
    return total


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage: validate_engine_budget.py model.glb [budget.json]")
    path = Path(sys.argv[1])
    gltf = load_gltf(path)
    metrics = {
        "file_bytes": path.stat().st_size,
        "triangles": triangle_total(gltf),
        "nodes": len(gltf.get("nodes", [])),
        "meshes": len(gltf.get("meshes", [])),
        "materials": len(gltf.get("materials", [])),
        "textures": len(gltf.get("textures", [])),
        "images": len(gltf.get("images", [])),
        "skins": len(gltf.get("skins", [])),
        "animations": len(gltf.get("animations", [])),
    }
    limits = {}
    if len(sys.argv) == 3:
        limits = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    failures = [
        f"{key}={value} exceeds limit {limits[key]}"
        for key, value in metrics.items()
        if key in limits and value > limits[key]
    ]
    result = {"status": "fail" if failures else "pass", "file": str(path),
              "metrics": metrics, "limits": limits, "issues": failures,
              "quality_gate": "structural-budget-preflight-only"}
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

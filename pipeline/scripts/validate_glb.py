#!/usr/bin/env python3
"""Dependency-free GLB container and glTF JSON validator for Forge 100K."""
import json
import struct
import sys
from pathlib import Path

MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942

def fail(message):
    print("FAIL:", message)
    raise SystemExit(1)

def main():
    require_rig = "--require-rig" in sys.argv
    require_morphs = "--require-morphs" in sys.argv
    paths = [arg for arg in sys.argv[1:] if arg not in ("--require-rig","--require-morphs")]
    if len(paths) != 1:
        fail("Usage: python pipeline/scripts/validate_glb.py [--require-rig] path/to/model.glb")
    path = Path(paths[0])
    if not path.is_file():
        fail("File does not exist: " + str(path))
    data = path.read_bytes()
    if len(data) < 20:
        fail("GLB is shorter than the 20-byte minimum")
    magic, version, declared_length = struct.unpack_from("<III", data, 0)
    if magic != MAGIC:
        fail("Invalid GLB magic")
    if version != 2:
        fail("Expected GLB version 2, got " + str(version))
    if declared_length != len(data):
        fail("Header length does not match file size")
    offset = 12
    gltf = None
    binary_chunks = 0
    while offset < len(data):
        if offset + 8 > len(data):
            fail("Truncated chunk header")
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        end = offset + chunk_length
        if end > len(data):
            fail("Chunk extends beyond file boundary")
        chunk = data[offset:end]
        if chunk_type == JSON_CHUNK:
            if gltf is not None:
                fail("Multiple JSON chunks are not allowed")
            try:
                gltf = json.loads(chunk.decode("utf-8").rstrip(" \\t\\r\\n\\0"))
            except Exception as exc:
                fail("Invalid glTF JSON: " + str(exc))
        elif chunk_type == BIN_CHUNK:
            binary_chunks += 1
        offset = end
    if offset != len(data):
        fail("Chunk alignment or trailing bytes error")
    if not isinstance(gltf, dict) or "asset" not in gltf or gltf["asset"].get("version") != "2.0":
        fail("Missing glTF 2.0 asset metadata")
    if not gltf.get("scenes") or not gltf.get("nodes"):
        fail("No scene or nodes found")
    if not gltf.get("meshes"):
        fail("No mesh geometry found")
    buffers = gltf.get("buffers", [])
    if buffers and not binary_chunks:
        fail("Buffer declared but GLB has no BIN chunk")
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if "POSITION" not in primitive.get("attributes", {}):
                fail("Mesh primitive missing POSITION attribute")
    for image in gltf.get("images", []):
        if "uri" in image:
            fail("External image URI found; production GLBs must be self-contained")
    morph_targets = max((len(p.get("targets",[])) for m in gltf.get("meshes",[]) for p in m.get("primitives",[])),default=0)
    if require_morphs and morph_targets < 1:
        fail("Morphology gate requires at least one morph target")
    summary = {
        "status": "pass",
        "max_morph_targets_per_primitive": morph_targets,
        "file": str(path),
        "bytes": len(data),
        "nodes": len(gltf.get("nodes", [])),
        "meshes": len(gltf.get("meshes", [])),
        "materials": len(gltf.get("materials", [])),
        "skins": len(gltf.get("skins", [])),
        "animations": len(gltf.get("animations", [])),
        "quality_gate": "container-and-structure-only"
    }
    print(json.dumps(summary, indent=2))
    if not gltf.get("skins") or not gltf.get("animations"):
        if require_rig:
            fail("Rigging gate requires at least one skin and one animation")
        print("WARN: Rigging/animation gate is not satisfied; do not mark as game-ready.")

if __name__ == "__main__":
    main()

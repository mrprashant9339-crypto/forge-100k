"""Validate Phase 3 retopology and bake reports, output containment and PNG maps."""
import argparse
import hashlib
import json
import os
import struct
import sys


def png_info(path):
    with open(path, "rb") as stream:
        header = stream.read(29)
    if len(header) != 29 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("Invalid PNG: " + path)
    width, height = struct.unpack(">II", header[16:24])
    bit_depth, color_type = header[24], header[25]
    return width, height, bit_depth, color_type


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained_file(root, value):
    if not isinstance(value, str) or not value:
        raise ValueError("Bake map path must be a non-empty string")
    base = os.path.realpath(root)
    path = os.path.realpath(value if os.path.isabs(value) else os.path.join(base, value))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("Bake output escapes report directory: " + value)
    if not os.path.isfile(path):
        raise ValueError("Missing bake output: " + value)
    return path


def validate_retopology(report_path):
    with open(report_path, encoding="utf-8") as stream:
        data = json.load(stream)
    if data.get("status") != "retopology_candidate_created" or not data.get("meshes"):
        raise ValueError("Retopology report is incomplete")
    for mesh in data["meshes"]:
        after = mesh.get("after", {})
        if after.get("faces", 0) <= 0 or not after.get("uv_layers"):
            raise ValueError("Retopology mesh missing faces or UVs: " + str(mesh.get("name")))
        if after.get("non_manifold_edges", 0) > 0:
            raise ValueError("Retopology mesh has boundary/non-manifold edges: " + str(mesh.get("name")))
    print("RETOPO_REPORT_VALID")


def validate_bake(report_path, min_resolution):
    root = os.path.dirname(os.path.realpath(report_path))
    with open(report_path, encoding="utf-8") as stream:
        data = json.load(stream)
    if data.get("status") != "baked" or not data.get("meshes"):
        raise ValueError("Bake report is incomplete")
    resolution = data.get("resolution")
    if not isinstance(resolution, list) or len(resolution) != 2 or any(not isinstance(x, int) or x <= 0 for x in resolution):
        raise ValueError("Bake report resolution is invalid")
    expected_width, expected_height = resolution
    if min(expected_width, expected_height) < min_resolution:
        raise ValueError("Bake resolution is below minimum")
    required = ("diffuse", "normal", "ao", "metallic_roughness")
    hashes = {}
    for mesh in data["meshes"]:
        name = mesh.get("mesh", "<unnamed>")
        if not mesh.get("uv_layer"):
            raise ValueError("Bake mesh has no active UV layer: " + name)
        metallic = mesh.get("metallic_factor")
        roughness = mesh.get("roughness_factor")
        if not isinstance(metallic, (int, float)) or not 0 <= metallic <= 1:
            raise ValueError("Invalid metallic factor: " + name)
        if not isinstance(roughness, (int, float)) or not 0 <= roughness <= 1:
            raise ValueError("Invalid roughness factor: " + name)
    for kind in required:
        paths = data.get("maps", {}).get(kind, [])
        if len(paths) != len(data["meshes"]):
            raise ValueError("Missing bake map category: " + kind)
        hashes[kind] = []
        for value in paths:
            path = contained_file(root, value)
            width, height, bit_depth, color_type = png_info(path)
            if (width, height) != (expected_width, expected_height):
                raise ValueError("Bake map dimensions differ from report resolution: " + path)
            if width < min_resolution or height < min_resolution:
                raise ValueError("Bake map below minimum resolution: " + path)
            if kind in ("normal", "ao", "metallic_roughness") and color_type not in (2, 6):
                raise ValueError("Non-color bake map must be RGB/RGBA: " + path)
            hashes[kind].append(sha256(path))
    packing = data.get("channel_packing", {}).get("metallic_roughness", "")
    if "G=roughness" not in packing or "B=metallic" not in packing:
        raise ValueError("Metallic-roughness channel packing metadata is invalid")
    print("BAKE_REPORT_VALID")
    print(json.dumps({"resolution": resolution, "mesh_count": len(data["meshes"]),
                      "verified_maps": sum(map(len, hashes.values())),
                      "sha256": hashes}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retopo")
    parser.add_argument("--bake")
    parser.add_argument("--min-resolution", type=int, default=64)
    args = parser.parse_args()
    try:
        if args.retopo:
            validate_retopology(args.retopo)
        if args.bake:
            validate_bake(args.bake, args.min_resolution)
        if not args.retopo and not args.bake:
            parser.error("provide --retopo and/or --bake")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print("PHASE3_REPORT_INVALID: " + str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

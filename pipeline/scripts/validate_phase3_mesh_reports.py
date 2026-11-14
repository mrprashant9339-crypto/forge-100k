"""Validate retopology and bake reports plus generated PNG map files."""
import argparse, json, os, struct, sys

def png_size(path):
    with open(path, "rb") as f:
        header = f.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("Invalid PNG: " + path)
    return struct.unpack(">II", header[16:24])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--retopo")
    p.add_argument("--bake")
    p.add_argument("--min-resolution", type=int, default=64)
    a = p.parse_args()
    if a.retopo:
        data = json.load(open(a.retopo, encoding="utf-8"))
        if data.get("status") != "retopology_candidate_created" or not data.get("meshes"):
            raise SystemExit("Retopology report is incomplete")
        for mesh in data["meshes"]:
            after = mesh["after"]
            if after["faces"] <= 0 or not after["uv_layers"]:
                raise SystemExit("Retopology mesh missing faces or UVs")
            if after["non_manifold_edges"] > 0:
                raise SystemExit("Retopology mesh has boundary/non-manifold edges: " + mesh["name"])
        print("RETOPO_REPORT_VALID")
    if a.bake:
        data = json.load(open(a.bake, encoding="utf-8"))
        if data.get("status") != "baked" or not data.get("meshes"):
            raise SystemExit("Bake report is incomplete")
        required = ("diffuse", "normal", "ao")
        for kind in required:
            paths = data.get("maps", {}).get(kind, [])
            if len(paths) != len(data["meshes"]):
                raise SystemExit("Missing bake map category: " + kind)
            for path in paths:
                if not os.path.isfile(path):
                    raise SystemExit("Missing bake output: " + path)
                w, h = png_size(path)
                if w < a.min_resolution or h < a.min_resolution:
                    raise SystemExit("Bake map below minimum resolution: " + path)
        print("BAKE_REPORT_VALID")
    if not a.retopo and not a.bake:
        p.error("provide --retopo and/or --bake")

if __name__ == "__main__":
    main()

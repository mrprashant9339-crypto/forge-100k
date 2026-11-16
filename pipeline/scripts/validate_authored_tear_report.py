"""Validate authored cloth tear setup evidence emitted by authored_cloth_tear.py."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args()
    with open(args.report, encoding="utf-8") as handle:
        report = json.load(handle)
    if report.get("schema") != "forge.authored-cloth-tear.v1":
        raise SystemExit("Unexpected authored tear report schema")
    if report.get("status") != "authored_tear_ready" or report.get("issues"):
        raise SystemExit("Authored tear setup is not ready")
    garments = report.get("garments")
    if not garments:
        raise SystemExit("No garments were validated")
    for row in garments:
        if row.get("status") != "authored_tear_ready":
            raise SystemExit("Garment tear setup failed: " + str(row.get("mesh")))
        if row.get("seam_edges_split", 0) < 1 or row.get("duplicated_seam_vertex_pairs", 0) < 2:
            raise SystemExit("No usable split seam was recorded: " + str(row.get("mesh")))
        if row.get("tear_shape_key") != "Forge_Tear_Progress" or not row.get("tear_progress_animated"):
            raise SystemExit("Animated tear shape key missing: " + str(row.get("mesh")))
        if row.get("pin_weights", {}).get("status") != "range_validated":
            raise SystemExit("Pin weights are not valid: " + str(row.get("mesh")))
    print("AUTHORED_CLOTH_TEAR_VALID garments=%d" % len(garments))


if __name__ == "__main__":
    main()

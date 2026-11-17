#!/usr/bin/env python3
"""Validate the structure and fail-closed result of a Phase 4 intake report."""
import argparse
import json
import sys


def validate_report(report):
    errors = []
    if not isinstance(report, dict):
        return ["report_root_must_be_object"]
    if report.get("schema_version") != "1.0":
        errors.append("schema_version_invalid")
    if report.get("status") != "asset_intake_passed":
        errors.append("asset_intake_not_passed")
    if report.get("fit_allowed") is not True:
        errors.append("fit_not_allowed")
    if report.get("production_release_approved") is not False:
        errors.append("intake_must_not_claim_production_release")
    for asset_name in ("body", "garment"):
        asset = report.get(asset_name)
        if not isinstance(asset, dict):
            errors.append(asset_name + "_record_missing")
            continue
        if not isinstance(asset.get("sha256"), str) or len(asset["sha256"]) != 64:
            errors.append(asset_name + "_sha256_invalid")
        if not isinstance(asset.get("mesh_count"), int) or asset["mesh_count"] < 1:
            errors.append(asset_name + "_mesh_count_invalid")
        if not isinstance(asset.get("armatures"), list) or len(asset["armatures"]) != 1:
            errors.append(asset_name + "_armature_count_invalid")
        if not isinstance(asset.get("meshes"), list) or not asset["meshes"]:
            errors.append(asset_name + "_mesh_records_missing")
    if report.get("errors") != []:
        errors.append("report_contains_errors")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args()
    with open(args.report, encoding="utf-8") as handle:
        report = json.load(handle)
    errors = validate_report(report)
    print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fail-closed production release gate for Phase 4 character/garment assets.

The manifest is evidence supplied by the production pipeline and reviewers.
This validator never treats synthetic CI fixtures as production assets.
"""
import argparse
import json
import os
import sys
from datetime import date

REQUIRED_ACTIONS = ("walk", "run", "jump", "combat")


def _is_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def validate_manifest(data, require_physical_tear=False):
    errors = []
    warnings = []

    if not isinstance(data, dict):
        return ["manifest_root_must_be_object"], warnings
    if data.get("schema_version") != "1.0":
        errors.append("schema_version_must_be_1.0")
    if not _is_nonempty_string(data.get("asset_id")):
        errors.append("asset_id_missing")
    if data.get("asset_kind") not in ("humanoid", "mechanical", "quadruped", "avian", "custom"):
        errors.append("asset_kind_invalid")
    if data.get("is_synthetic_fixture") is not False:
        errors.append("synthetic_fixture_cannot_be_released")

    source = data.get("source_assets")
    if not isinstance(source, dict):
        errors.append("source_assets_missing")
    else:
        for key in ("body_glb", "garment_glb"):
            if not _is_nonempty_string(source.get(key)):
                errors.append("source_" + key + "_missing")
        if source.get("body_sha256") and len(source["body_sha256"]) != 64:
            errors.append("source_body_sha256_invalid")
        if source.get("garment_sha256") and len(source["garment_sha256"]) != 64:
            errors.append("source_garment_sha256_invalid")

    pose = data.get("pose_validation")
    if not isinstance(pose, dict):
        errors.append("pose_validation_missing")
    else:
        actions = pose.get("actions")
        if not isinstance(actions, dict):
            errors.append("pose_actions_missing")
        else:
            for action in REQUIRED_ACTIONS:
                record = actions.get(action)
                if not isinstance(record, dict):
                    errors.append("pose_action_" + action + "_missing")
                    continue
                if record.get("cache_baked") is not True:
                    errors.append("pose_action_" + action + "_cache_not_baked")
                if not isinstance(record.get("frames_checked"), int) or record["frames_checked"] < 1:
                    errors.append("pose_action_" + action + "_frames_invalid")
                if record.get("issues") != []:
                    errors.append("pose_action_" + action + "_issues_present")
        if pose.get("body_penetration_vertices") != 0:
            errors.append("body_penetration_not_zero")
        if pose.get("self_intersection_pairs") != 0:
            errors.append("self_intersection_not_zero")

    collision = data.get("collision_validation")
    if not isinstance(collision, dict):
        errors.append("collision_validation_missing")
    else:
        for field in ("body_triangle_intersections", "self_triangle_intersections"):
            if collision.get(field) != 0:
                errors.append(field + "_not_zero")
        if collision.get("pose_samples", 0) < 1:
            errors.append("collision_pose_samples_missing")
        if collision.get("status") != "passed":
            errors.append("collision_status_not_passed")

    tear = data.get("tear_validation")
    if not isinstance(tear, dict):
        errors.append("tear_validation_missing")
    else:
        mode = tear.get("mode")
        if mode not in ("physical_solver", "authored_seam_animation", "none"):
            errors.append("tear_mode_invalid")
        if tear.get("validated") is not True:
            errors.append("tear_not_validated")
        if not _is_nonempty_string(tear.get("report")):
            errors.append("tear_report_missing")
        if require_physical_tear and mode != "physical_solver":
            errors.append("physical_tear_solver_required")
        if mode == "authored_seam_animation":
            warnings.append("authored_seam_animation_is_not_stress_driven_physical_tearing")
        if mode == "none":
            warnings.append("tear_workflow_not_available")

    review = data.get("artist_review")
    if not isinstance(review, dict) or review.get("approved") is not True:
        errors.append("artist_review_not_approved")
    else:
        if not _is_nonempty_string(review.get("reviewer")):
            errors.append("artist_reviewer_missing")
        try:
            date.fromisoformat(review.get("date", ""))
        except (TypeError, ValueError):
            errors.append("artist_review_date_invalid")

    engine = data.get("target_engine")
    if not isinstance(engine, dict):
        errors.append("target_engine_evidence_missing")
    else:
        for field in ("name", "version"):
            if not _is_nonempty_string(engine.get(field)):
                errors.append("target_engine_" + field + "_missing")
        if engine.get("import_validated") is not True:
            errors.append("target_engine_import_not_validated")
        if engine.get("playback_validated") is not True:
            errors.append("target_engine_playback_not_validated")

    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance_missing")
    else:
        for field in ("source", "license"):
            if not _is_nonempty_string(provenance.get(field)):
                errors.append("provenance_" + field + "_missing")

    return sorted(set(errors)), sorted(set(warnings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="Production release evidence JSON")
    parser.add_argument("--require-physical-tear", action="store_true",
                        help="Reject authored seam animation; require physical solver evidence")
    parser.add_argument("--report", help="Optional output JSON report path")
    args = parser.parse_args()
    with open(args.manifest, encoding="utf-8") as handle:
        data = json.load(handle)
    errors, warnings = validate_manifest(data, args.require_physical_tear)
    report = {
        "schema_version": "1.0",
        "status": "release_gate_passed" if not errors else "release_gate_blocked",
        "manifest": os.path.abspath(args.manifest),
        "errors": errors,
        "warnings": warnings,
        "game_ready": not errors
    }
    rendered = json.dumps(report, indent=2)
    print("FORGE_PHASE4_RELEASE_GATE " + json.dumps(report))
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())

"""Validate cloth QA report structure; optionally enforce promotion gates."""
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--require-geometric-clean", action="store_true",
                        help="fail on geometry issues, unbaked caches or invalid pin groups")
    parser.add_argument("--require-clean", action="store_true",
                        help="also require named pose coverage and a tear-capable workflow")
    args = parser.parse_args()
    with open(args.report, encoding="utf-8") as handle:
        report = json.load(handle)
    required = {
        "schema", "status", "frame_range", "sampled_frames", "cache_checks",
        "pose_action_inventory", "named_pose_coverage", "pose_coverage_complete",
        "garment_aggregate", "frame_checks", "pin_weight_checks", "issues",
        "warnings", "authored_tear_checks", "tearing_detection", "continuous_collision_detection",
        "collision_free_certified", "self_intersection_certified",
        "artist_review_required", "engine_certified"
    }
    missing = sorted(required - set(report))
    if missing:
        raise SystemExit("Missing report fields: " + ", ".join(missing))
    if report["schema"] != "forge.cloth-integrity-report.v1":
        raise SystemExit("Unexpected cloth integrity report schema")
    if report["status"] not in ("cloth_integrity_preflight_passed", "cloth_integrity_issues_found"):
        raise SystemExit("Unexpected cloth integrity status")
    if not isinstance(report["frame_checks"], list) or not report["frame_checks"]:
        raise SystemExit("No evaluated frame checks were recorded")
    if not isinstance(report["cache_checks"], list) or not report["cache_checks"]:
        raise SystemExit("No cloth cache checks were recorded")
    for key in ("continuous_collision_detection", "collision_free_certified",
                "self_intersection_certified", "engine_certified"):
        if report[key] is not False:
            raise SystemExit("Report must not overclaim certification: " + key)
    if report["artist_review_required"] is not True:
        raise SystemExit("Artist review must remain required")
    coverage = report["named_pose_coverage"]
    if set(coverage) != {"walking", "running", "jumping", "combat"}:
        raise SystemExit("Named pose coverage must report walk/run/jump/combat")
    if args.require_geometric_clean or args.require_clean:
        if report["status"] != "cloth_integrity_preflight_passed" or report["issues"]:
            raise SystemExit("Promotion blocked: cloth geometry findings remain")
        if any(not row.get("is_baked") for row in report["cache_checks"]):
            raise SystemExit("Promotion blocked: one or more cloth caches are not baked")
        if any(row.get("status") != "range_validated" for row in report["pin_weight_checks"]):
            raise SystemExit("Promotion blocked: every garment needs a configured, range-validated pin group")
    if args.require_clean:
        if not report["pose_coverage_complete"]:
            raise SystemExit("Promotion blocked: walk/run/jump/combat action coverage is incomplete")
        tear = report.get("tearing_detection", {})
        if not (tear.get("physical_fabric_tear_solver_available") is True or
                tear.get("authored_tear_workflow_available") is True):
            raise SystemExit("Promotion blocked: no validated physical or authored tear workflow is configured")
        if tear.get("authored_tear_workflow_available") is True:
            checks = report.get("authored_tear_checks", [])
            if not checks or any(row.get("status") != "authored_tear_ready" for row in checks):
                raise SystemExit("Promotion blocked: authored tear checks are incomplete")
    print("CLOTH_INTEGRITY_REPORT_VALID status=%s frames=%d issues=%d pose_coverage=%s" % (
        report["status"], len(report["frame_checks"]), len(report["issues"]),
        report["pose_coverage_complete"]))

if __name__ == "__main__":
    main()

"""Validate the structure and conservative claims of a cloth integrity report."""
import json
import sys

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_cloth_integrity_report.py report.json")
    with open(sys.argv[1], encoding="utf-8") as handle:
        report = json.load(handle)
    required = {
        "schema", "status", "frame_range", "sampled_frames", "cache_checks",
        "pose_action_inventory", "named_pose_coverage", "pose_coverage_complete",
        "garment_aggregate", "frame_checks", "pin_weight_checks", "issues",
        "warnings", "tearing_detection", "continuous_collision_detection",
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
    print("CLOTH_INTEGRITY_REPORT_VALID status=%s frames=%d issues=%d" % (
        report["status"], len(report["frame_checks"]), len(report["issues"])))

if __name__ == "__main__":
    main()

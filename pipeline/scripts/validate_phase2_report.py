"""Validate Phase 2 Blender worker output and its declared morph/module contract."""
import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("Usage: validate_phase2_report.py report.json")
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_face = {
    "ForgeFace_jaw_width", "ForgeFace_jaw_height", "ForgeFace_cheek_fullness",
    "ForgeFace_eye_scale", "ForgeFace_eye_spacing", "ForgeFace_nose_width",
    "ForgeFace_nose_length", "ForgeFace_mouth_width", "ForgeFace_brow_depth",
    "ForgeFace_chin_projection"
}
expected_body = {
    "ForgeBody_height", "ForgeBody_shoulder_width", "ForgeBody_torso_ratio",
    "ForgeBody_arm_length", "ForgeBody_leg_length", "ForgeBody_muscle", "ForgeBody_mass"
}
face = set(report.get("face_morph_targets", []))
body = set(report.get("body_morph_targets", []))
if face != expected_face:
    raise SystemExit("Phase 2 face morph target set mismatch")
if body != expected_body:
    raise SystemExit("Phase 2 body morph target set mismatch")
if report.get("module_count") != len(report.get("modules", [])):
    raise SystemExit("Phase 2 module count mismatch")
if report.get("profile_validation") != "strict_ranges_and_catalog_slots":
    raise SystemExit("Phase 2 profile validation was not applied")
if report.get("status") != "phase2_generated":
    raise SystemExit("Phase 2 worker status invalid")
print("PHASE2_REPORT_VALID")

"""Fail-closed validator for native Unity/Unreal asset certification reports."""
import argparse, json, os, re, sys

REQUIRED_CLIPS = {"walk", "run", "jump", "combat"}
REQUIRED_IMPORT_CHECKS = {"model", "materials", "textures", "skeleton", "animations"}
DEFAULT_LIMITS = {"min_fps": 30.0, "p95_frame_ms": 33.34, "peak_memory_mb": 4096.0, "draw_calls": 250, "triangles": 150000}

def validate_report(report, root="."):
    failures = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]
    def require(ok, message):
        if not ok: failures.append(message)
    require(report.get("schema_version") == "1.0", "schema_version must be 1.0")
    require(report.get("engine") in {"unity", "unreal"}, "engine must be unity or unreal")
    require(bool(str(report.get("engine_version", "")).strip()), "engine_version is required")
    require(bool(report.get("asset_id")), "asset_id is required")
    require(report.get("is_synthetic_fixture") is False, "synthetic fixtures cannot be certified")
    imported = report.get("import", {})
    require(imported.get("status") == "passed", "engine import did not pass")
    require(REQUIRED_IMPORT_CHECKS.issubset(set(imported.get("checks", []))), "import checks must include model, materials, textures, skeleton and animations")
    require(imported.get("missing_materials", 1) == 0, "missing materials must be zero")
    require(imported.get("missing_textures", 1) == 0, "missing textures must be zero")
    clips = report.get("animation", {}).get("clips", [])
    passed = {c.get("name") for c in clips if c.get("status") == "passed" and c.get("frames_evaluated", 0) > 0}
    require(REQUIRED_CLIPS.issubset(passed), "walk, run, jump and combat clips must each pass with evaluated frames")
    collision = report.get("collision", {})
    require(collision.get("status") == "passed", "collision validation must pass")
    require(collision.get("body_penetrations", -1) == 0, "body penetrations must be zero")
    require(collision.get("self_intersections", -1) == 0, "self intersections must be zero")
    require(collision.get("pose_samples", 0) >= 12, "at least 12 collision pose samples are required")
    perf = report.get("performance", {})
    limits = dict(DEFAULT_LIMITS); limits.update(report.get("budgets", {}))
    require(perf.get("sample_count", 0) >= 300, "at least 300 performance samples are required")
    for metric in ("min_fps", "p95_frame_ms", "peak_memory_mb", "draw_calls", "triangles"):
        value = perf.get(metric)
        require(isinstance(value, (int, float)) and value >= 0, f"performance.{metric} must be a non-negative number")
        if isinstance(value, (int, float)):
            if metric == "min_fps": require(value >= limits[metric], f"{metric} is below budget {limits[metric]}")
            else: require(value <= limits[metric], f"{metric} exceeds budget {limits[metric]}")
    relative = report.get("evidence", {}).get("file")
    require(isinstance(relative, str) and bool(relative), "engine evidence file is required")
    if isinstance(relative, str) and relative:
        base = os.path.realpath(root); path = os.path.realpath(os.path.join(base, relative))
        if os.path.commonpath([base, path]) != base or not os.path.isfile(path) or os.path.getsize(path) == 0:
            failures.append("engine evidence file is missing, empty or outside asset root")
    return failures

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("report"); p.add_argument("--root",default="."); p.add_argument("--require-engine",choices=("unity","unreal")); a=p.parse_args()
    try:
        with open(a.report,encoding="utf-8") as f: report=json.load(f)
        failures=validate_report(report,a.root)
        if a.require_engine and report.get("engine") != a.require_engine: failures.append("report engine does not match required engine "+a.require_engine)
        if failures: raise ValueError("; ".join(failures))
        print(json.dumps({"status":"passed","engine":report["engine"],"engine_version":report["engine_version"],"asset_id":report["asset_id"],"certification_scope":"reported-native-engine-import-animation-collision-performance"},indent=2))
    except (OSError,json.JSONDecodeError,TypeError,ValueError,KeyError) as exc:
        print("ENGINE_CERTIFICATION_BLOCKED: "+str(exc),file=sys.stderr); raise SystemExit(1)
if __name__=="__main__": main()

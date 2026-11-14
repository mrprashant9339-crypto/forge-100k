"""Validate a Forge production asset package and enforce release gates.

Usage: python validate_production_package.py package.json --root ./assets
"""
import argparse, hashlib, json, os, re, sys

def safe_file(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("file path must be a non-empty string")
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, relative))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("package path escapes asset root: " + relative)
    if not os.path.isfile(path):
        raise ValueError("missing package file: " + relative)
    return path

def verify_sha256(path, expected):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError("SHA-256 mismatch for " + path)
    return actual

def release_gates(data):
    failures = []
    if data.get("geometry", {}).get("retopology_review") != "approved":
        failures.append("artist-approved retopology is missing")
    if data.get("geometry", {}).get("uv_review") != "approved":
        failures.append("UV review is missing")
    if data.get("materials", {}).get("bake_review") != "approved":
        failures.append("PBR bake review is missing")
    if data.get("rigging", {}).get("required") and data.get("rigging", {}).get("review") != "approved":
        failures.append("rigging review is missing")
    if data.get("animation", {}).get("required") and data.get("animation", {}).get("review") != "approved":
        failures.append("animation review is missing")
    artist = data.get("reviews", {}).get("artist", {})
    if artist.get("status") != "approved" or not artist.get("reviewer") or not artist.get("reviewed_at") or not artist.get("evidence"):
        failures.append("signed artist approval evidence is missing")
    engines = data.get("reviews", {}).get("engines", [])
    passed = {e.get("name") for e in engines if e.get("status") == "passed" and e.get("version") and e.get("evidence")}
    targets = set(data.get("target_engines", []))
    if not targets or not targets.issubset(passed):
        failures.append("versioned import evidence is incomplete for declared target engines")
    return failures

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    with open(args.manifest, encoding="utf-8") as stream:
        data = json.load(stream)
    root = os.path.realpath(args.root)
    source = safe_file(root, data["source"]["file"])
    safe_file(root, data["geometry"]["glb"])
    safe_file(root, data["materials"]["pbr_manifest"])
    for field in ("lod_files",):
        for item in data["geometry"].get(field, []):
            safe_file(root, item)
    for item in data["materials"].get("texture_files", []):
        safe_file(root, item)
    for item in data.get("animation", {}).get("clips", []):
        safe_file(root, item)
    verify_sha256(source, data["source"]["sha256"])
    failures = release_gates(data)
    if data["release_status"] == "game_ready" and failures:
        raise SystemExit("RELEASE BLOCKED: " + "; ".join(failures))
    if data["release_status"] == "game_ready":
        print("GAME_READY_PACKAGE_VALID")
    else:
        print("PACKAGE_FILES_AND_PROVENANCE_VALID")
        print("RELEASE_GATES_OPEN: " + ("; ".join(failures) if failures else "none"))
    print(json.dumps({"asset_id": data["asset_id"], "release_status": data["release_status"],
                      "artist_approved": data["reviews"]["artist"]["status"] == "approved",
                      "engine_certified": not failures, "open_gates": failures}, indent=2))

if __name__ == "__main__":
    main()

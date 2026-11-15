"""Validate a Forge production asset package and enforce release gates.

Usage: python validate_production_package.py package.json --root ./assets
Requires jsonschema (pinned in the repository CI workflow).
"""
import argparse
import hashlib
import json
import os
import sys

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:
    raise SystemExit("Missing dependency: install jsonschema>=4.25,<5") from exc

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "production-asset.schema.json")


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


def validate_schema(data):
    with open(SCHEMA_PATH, encoding="utf-8") as stream:
        schema = json.load(stream)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda error: list(map(str, error.absolute_path)))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            details.append(location + ": " + error.message)
        raise ValueError("production package schema validation failed: " + "; ".join(details))


def package_files(data):
    paths = [
        data["source"]["file"],
        data["geometry"]["glb"],
        data["materials"]["pbr_manifest"],
    ]
    paths.extend(data["geometry"].get("lod_files", []))
    paths.extend(data["materials"].get("texture_files", []))
    paths.extend(data.get("animation", {}).get("clips", []))
    artist = data.get("reviews", {}).get("artist", {})
    if artist.get("status") == "approved":
        paths.append(artist.get("evidence"))
    for engine in data.get("reviews", {}).get("engines", []):
        if engine.get("status") == "passed":
            paths.append(engine.get("evidence"))
    return paths


def release_gates(data):
    failures = []
    if data["geometry"]["retopology_review"] != "approved":
        failures.append("artist-approved retopology is missing")
    if data["geometry"]["uv_review"] != "approved":
        failures.append("UV review is missing")
    if data["materials"]["bake_review"] != "approved":
        failures.append("PBR bake review is missing")
    if data["rigging"]["required"] and data["rigging"]["review"] != "approved":
        failures.append("rigging review is missing")
    if data["animation"]["required"] and data["animation"]["review"] != "approved":
        failures.append("animation review is missing")
    artist = data["reviews"]["artist"]
    if artist["status"] != "approved" or not artist.get("reviewer") or not artist.get("reviewed_at") or not artist.get("evidence"):
        failures.append("signed artist approval evidence is missing")
    engines = data["reviews"]["engines"]
    passed = {e["name"] for e in engines if e["status"] == "passed" and e.get("version") and e.get("evidence")}
    targets = set(data["target_engines"])
    if not targets.issubset(passed):
        failures.append("versioned import evidence is incomplete for declared target engines")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        with open(args.manifest, encoding="utf-8") as stream:
            data = json.load(stream)
        validate_schema(data)
        root = os.path.realpath(args.root)
        for relative in package_files(data):
            safe_file(root, relative)
        verify_sha256(safe_file(root, data["source"]["file"]), data["source"]["sha256"])
        failures = release_gates(data)
        if data["release_status"] == "game_ready" and failures:
            raise ValueError("RELEASE BLOCKED: " + "; ".join(failures))
        if data["release_status"] == "game_ready":
            print("GAME_READY_PACKAGE_VALID")
        else:
            print("PACKAGE_FILES_AND_PROVENANCE_VALID")
            print("RELEASE_GATES_OPEN: " + ("; ".join(failures) if failures else "none"))
        print(json.dumps({
            "asset_id": data["asset_id"],
            "release_status": data["release_status"],
            "artist_approved": data["reviews"]["artist"]["status"] == "approved",
            "engine_certified": not failures,
            "open_gates": failures,
        }, indent=2))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print("PACKAGE_INVALID: " + str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

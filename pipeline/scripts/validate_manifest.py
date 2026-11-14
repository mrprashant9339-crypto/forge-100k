#!/usr/bin/env python3
"""Validate a Forge 100K batch manifest and enforce unique asset IDs."""
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator, RefResolver

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_manifest.py path/to/manifest.json")
    manifest_path=Path(sys.argv[1]).resolve()
    root=Path(__file__).resolve().parents[1]
    manifest_schema=json.loads((root/"schemas"/"batch-manifest.schema.json").read_text())
    job_schema=json.loads((root/"schemas"/"asset-job.schema.json").read_text())
    resolver=RefResolver.from_schema(manifest_schema, store={
        "asset-job.schema.json":job_schema,
        job_schema.get("$id","asset-job.schema.json"):job_schema
    })
    manifest=json.loads(manifest_path.read_text())
    errors=sorted(Draft202012Validator(manifest_schema,resolver=resolver).iter_errors(manifest),
                  key=lambda error:list(error.path))
    if errors:
        for error in errors:
            location=".".join(str(part) for part in error.path) or "<root>"
            print("FAIL:",location,error.message)
        raise SystemExit(1)
    ids=[job["asset_id"] for job in manifest["jobs"]]
    if len(ids)!=len(set(ids)):
        raise SystemExit("FAIL: duplicate asset_id values in batch")
    seeds=[job["seed"] for job in manifest["jobs"]]
    if len(seeds)!=len(set(seeds)):
        raise SystemExit("FAIL: duplicate seed values in batch")
    print(json.dumps({"status":"pass","batch_id":manifest["batch_id"],
        "jobs":len(ids),"unique_asset_ids":len(set(ids)),
        "unique_seeds":len(set(seeds))},indent=2))

if __name__=="__main__":
    main()

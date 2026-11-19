#!/usr/bin/env python3
"""Supabase-backed Forge 100K blockout generation worker.

Only the trusted worker receives SUPABASE_SERVICE_ROLE_KEY. Never ship it to the
browser. The worker currently accepts the 'character' job type and produces
original procedural blockout GLBs, not production/game-ready characters.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "pipeline"
BLENDER = os.environ.get("BLENDER_BIN", "blender")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
POLL_SECONDS = max(2, int(os.environ.get("WORKER_POLL_SECONDS", "8")))
WORKER_ID = os.environ.get("WORKER_ID", socket.gethostname())[:120]
BUCKET = "forge-private-uploads"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ASSET_ID_RE = re.compile(r"^FG-[A-Z]{3}-[0-9]{6}$")


class WorkerError(RuntimeError):
    pass


def request_json(method: str, url: str, payload: Any = None, *, extra_headers: dict | None = None):
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise WorkerError(f"Supabase HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise WorkerError(f"Supabase connection error: {exc.reason}") from exc


def rpc(name: str, payload: dict):
    return request_json("POST", f"{SUPABASE_URL}/rest/v1/rpc/{name}", payload)


def claim_job():
    rows = rpc("claim_next_generation_job", {"p_worker_id": WORKER_ID})
    if isinstance(rows, dict):
        return rows
    return rows[0] if isinstance(rows, list) and rows else None


def heartbeat(job_id: str):
    result = rpc("heartbeat_generation_job", {"p_job_id": job_id, "p_worker_id": WORKER_ID})
    if result is not True:
        raise WorkerError("Worker lease was lost; refusing to publish output")


def fail_job(job_id: str, error_code: str):
    try:
        rpc("fail_generation_job", {
            "p_job_id": job_id,
            "p_worker_id": WORKER_ID,
            "p_error_code": error_code[:100],
        })
    except Exception as exc:
        print(f"Could not report failed job {job_id}: {exc}", flush=True)


def safe_job_spec(job: dict) -> dict:
    if job.get("job_type") != "character":
        raise WorkerError("unsupported_job_type")
    request = job.get("request")
    if not isinstance(request, dict) or not isinstance(request.get("asset"), dict):
        raise WorkerError("invalid_job_request")
    asset = request["asset"]
    asset_id = asset.get("asset_id")
    if not isinstance(asset_id, str) or not ASSET_ID_RE.fullmatch(asset_id):
        raise WorkerError("invalid_asset_id")
    if asset.get("quality_tier") != "blockout":
        raise WorkerError("worker_only_supports_blockout")
    if asset.get("target") != "glTF2":
        raise WorkerError("worker_only_supports_gltf2")
    provenance = asset.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("kind") != "original_procedural":
        raise WorkerError("unverified_asset_provenance")
    return asset


def upload_object(storage_path: str, data: bytes):
    if len(data) > MAX_UPLOAD_BYTES:
        raise WorkerError("generated_glb_exceeds_upload_limit")
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in storage_path.split("/"))
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{encoded}"
    req = urllib.request.Request(url, data=data, headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "model/gltf-binary",
        "x-upsert": "true",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise WorkerError(f"Storage upload failed ({exc.code}): {detail}") from exc


def insert_asset(job: dict, asset: dict, glb_path: Path) -> str:
    data = glb_path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise WorkerError("generated_glb_header_invalid")
    digest = hashlib.sha256(data).hexdigest()
    user_id = str(job["user_id"])
    job_id = str(job["id"])
    storage_path = f"{user_id}/{job_id}/{asset['asset_id']}.glb"
    upload_object(storage_path, data)

    slug = f"{asset['asset_id'].lower()}-{job_id[:8]}"
    catalog_rows = request_json("POST", f"{SUPABASE_URL}/rest/v1/asset_catalog?on_conflict=slug", [{
        "slug": slug,
        "owner_id": user_id,
        "title": asset["archetype"].replace("-", " ").title(),
        "description": "Original procedural Forge 100K blockout. Requires artist review before production use.",
        "category": asset["species"],
        "visibility": "pending_review",
        "metadata": {
            "asset_id": asset["asset_id"],
            "quality_tier": "blockout",
            "provenance": asset["provenance"],
            "pipeline": "forge-100k-generation-worker",
            "release_status": "draft",
        },
    }], extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"})
    if not isinstance(catalog_rows, list) or not catalog_rows:
        raise WorkerError("asset_catalog_insert_failed")
    asset_uuid = catalog_rows[0]["id"]

    version_rows = request_json("POST", f"{SUPABASE_URL}/rest/v1/asset_versions?on_conflict=asset_id,version", [{
        "asset_id": asset_uuid,
        "owner_id": user_id,
        "version": 1,
        "storage_path": storage_path,
        "sha256": digest,
        "mime_type": "model/gltf-binary",
        "byte_size": len(data),
        "validation_status": "passed",
        "validation_report": {
            "status": "pass",
            "validator": "pipeline/scripts/validate_glb.py",
            "scope": "container-and-structure-only",
            "quality_tier": "blockout",
        },
    }], extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"})
    if not isinstance(version_rows, list) or not version_rows:
        raise WorkerError("asset_version_insert_failed")
    return asset_uuid


def run_blender_with_heartbeat(job_id: str, command: list[str], timeout: int):
    process = subprocess.Popen(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stop = threading.Event()
    lease_errors = []

    def keep_lease_alive():
        while not stop.wait(60):
            try:
                heartbeat(job_id)
            except Exception as exc:
                lease_errors.append(exc)
                process.terminate()
                return

    keeper = threading.Thread(target=keep_lease_alive, name=f"lease-{job_id[:8]}", daemon=True)
    keeper.start()
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise WorkerError("blender_generation_timeout")
    finally:
        stop.set()
        keeper.join(timeout=5)

    if lease_errors:
        raise WorkerError("worker_lease_lost")
    if process.returncode:
        detail = (stderr or stdout or "")[-1200:]
        raise WorkerError("blender_generation_failed: " + detail)
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def process_job(job: dict):
    job_id = str(job["id"])
    heartbeat(job_id)
    asset = safe_job_spec(job)
    with tempfile.TemporaryDirectory(prefix=f"forge-{job_id[:8]}-") as tmp:
        workspace = Path(tmp)
        manifest_path = workspace / "pipeline" / "manifests" / "job.json"
        manifest_path.parent.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0.0",
            "batch_id": f"job-{job_id}",
            "output_dir": "artifacts",
            "jobs": [asset],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        validation = subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(PIPELINE / "scripts" / "validate_manifest.py"), str(manifest_path)],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        if validation.returncode:
            raise WorkerError("manifest_validation_failed")
        heartbeat(job_id)
        result = run_blender_with_heartbeat(
            job_id,
            [BLENDER, "--background", "--python", str(PIPELINE / "blender" / "generate_batch.py"), "--", str(manifest_path)],
            timeout=int(os.environ.get("BLENDER_JOB_TIMEOUT", "900")),
        )
        glb_path = workspace / "artifacts" / f"{asset['asset_id']}.glb"
        if not glb_path.is_file():
            raise WorkerError("generated_glb_missing")
        checked = subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(PIPELINE / "scripts" / "validate_glb.py"), str(glb_path)],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        if checked.returncode:
            raise WorkerError("generated_glb_validation_failed")
        heartbeat(job_id)
        asset_uuid = insert_asset(job, asset, glb_path)
        completed = rpc("complete_generation_job", {
            "p_job_id": job_id,
            "p_worker_id": WORKER_ID,
            "p_result_asset_id": asset_uuid,
        })
        if completed is not True:
            raise WorkerError("job_completion_rejected")
        print(json.dumps({
            "event": "job_succeeded",
            "job_id": job_id,
            "asset_id": asset["asset_id"],
            "catalog_asset_id": asset_uuid,
            "quality_tier": "blockout",
        }), flush=True)


def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    print(json.dumps({"event": "worker_started", "worker_id": WORKER_ID}), flush=True)
    while True:
        job = None
        try:
            job = claim_job()
            if job is None:
                time.sleep(POLL_SECONDS)
                continue
            print(json.dumps({"event": "job_claimed", "job_id": job.get("id"), "attempt": job.get("attempt_count")}), flush=True)
            process_job(job)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(json.dumps({"event": "job_error", "job_id": (job or {}).get("id"), "error": str(exc)[:300]}), flush=True)
            if job and job.get("id"):
                fail_job(str(job["id"]), re.sub(r"[^a-zA-Z0-9_-]", "_", str(exc))[:100] or "worker_error")
            time.sleep(1)


if __name__ == "__main__":
    main()

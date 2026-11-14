import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942

def make_glb(path):
    doc = {
        "asset": {"version": "2.0", "generator": "Forge validator test"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [{"componentType": 5126, "count": 3, "type": "VEC3"}]
    }
    raw = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((4 - len(raw) % 4) % 4)
    chunk = struct.pack("<II", len(raw), JSON_CHUNK) + raw
    total = 12 + len(chunk)
    path.write_bytes(struct.pack("<III", MAGIC, 2, total) + chunk)

def main():
    validator = Path(__file__).resolve().parents[1] / "scripts" / "validate_glb.py"
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "valid.glb"
        make_glb(good)
        result = subprocess.run([sys.executable, str(validator), str(good)], capture_output=True, text=True)
        if result.returncode != 0 or '"status": "pass"' not in result.stdout:
            raise SystemExit("Valid GLB fixture rejected: " + result.stdout + result.stderr)
        bad = Path(tmp) / "invalid.glb"
        bad.write_bytes(b"not-a-glb")
        result = subprocess.run([sys.executable, str(validator), str(bad)], capture_output=True, text=True)
        if result.returncode == 0:
            raise SystemExit("Invalid GLB fixture unexpectedly passed")
    print("GLB validator tests passed")

if __name__ == "__main__":
    main()

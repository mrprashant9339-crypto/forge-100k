#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    config=json.loads((ROOT/"pipeline/catalog/character-dimensions.json").read_text())
    total=1
    for values in config["dimensions"].values(): total*=len(values)
    assert total==100000,total
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable,str(ROOT/"pipeline/scripts/build_character_catalog.py"),"--output",tmp,"--batch-size","777"],check=True,capture_output=True,text=True)
        root=Path(tmp); report=json.loads((root/"catalog-report.json").read_text())
        assert report["written"]==100000 and report["batch_count"]==129
        lines=(root/"presets.jsonl").read_text().splitlines()
        assert len(lines)==100000
        first=json.loads(lines[0]); last=json.loads(lines[-1])
        assert first["asset_id"]=="FG-HUM-000001" and last["asset_id"]=="FG-HUM-100000"
        assert len({json.loads(line)["preset_sha256"] for line in lines})==100000
        batch=json.loads((root/"queue"/"batch-000000.json").read_text())
        assert batch["count"]==777 and batch["execution_policy"]["retry_limit"]==3
    print("100K deterministic preset catalogue and bounded queue batching passed.")
if __name__=="__main__": main()

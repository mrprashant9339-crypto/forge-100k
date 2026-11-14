"""Validate the exported facial morph target pack."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    worker=root/"blender"/"facial_morph_pack.py"
    validator=root/"scripts"/"validate_glb.py"
    source=Path(sys.argv[1]).resolve()
    out=Path(sys.argv[2]).resolve()
    report=out.with_suffix(".json")
    subprocess.run(["blender","--background","--python",str(worker),"--",str(source),str(out),str(report)],check=True)
    subprocess.run([sys.executable,str(validator),"--require-morphs",str(out)],check=True)
    data=json.loads(report.read_text())
    assert data["target_count"]==11,data
    assert len(data["expression_targets"])==6 and len(data["viseme_targets"])==5,data
    print("Facial morph pack integration test passed")
if __name__=="__main__": main()

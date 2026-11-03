"""Run all five real models. This is CPU integration QA on the executing machine."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
summary = []
for name in ("classification", "detection", "pose", "gesture", "segmentation"):
    image = root / "media" / ("right_hands.jpg" if name == "gesture" else "grace_hopper.jpg")
    command = [sys.executable, str(root / "ai" / "run_demo.py"), name, "--image", str(image), "--runs", "3", "--output", str(root / "evidence" / "host-ai")]
    if name == "gesture":
        command += ["--crop", "360", "0", "720", "360"]
    run = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = root / "evidence" / ("smoke-" + name + ".log")
    log.parent.mkdir(exist_ok=True)
    log.write_bytes(run.stdout)
    summary.append({"demo": name, "exit_code": run.returncode, "scope": "preparation computer CPU, not QB560D"})
    print(name + ": " + ("PASS" if run.returncode == 0 else "FAIL; " + str(log)))
(root / "evidence" / "ai-smoke-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
if any(row["exit_code"] != 0 for row in summary):
    sys.exit(1)

"""Repeat the five static AI demos on the single selected ADB target."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import os
import getpass
from adb_login import resolve_adb
from target_layout import DEFAULT_REMOTE, validate_remote

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--adb")
p.add_argument("--serial")
p.add_argument("--transport-id")
p.add_argument('--remote', default=DEFAULT_REMOTE, type=validate_remote)
p.add_argument("--repeat", type=int, choices=[1, 2, 3], default=3)
a = p.parse_args()
a.adb = resolve_adb(a.adb)
child_env = os.environ.copy()
if not child_env.get("QB560D_ADB_PASSWORD"):
    child_env["QB560D_ADB_PASSWORD"] = getpass.getpass("Senha Linux da caixa para root: ")
rows = []
for repetition in range(1, a.repeat + 1):
    for name in ("classification", "detection", "pose", "gesture", "segmentation"):
        image = "media/right_hands.jpg" if name == "gesture" else "media/grace_hopper.jpg"
        command = [sys.executable, str(root / "host" / "adb_lab.py"), "--adb", a.adb, '--remote', a.remote, "--timeout", "90", "run", "ai", name, "--image", image, "--runs", "20"]
        if a.serial:
            command[4:4] = ["--serial", a.serial]
        if a.transport_id:
            command[4:4] = ["--transport-id", a.transport_id]
        if name == "gesture":
            command += ["--crop", "360", "0", "720", "360"]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=150, env=child_env)
        result_dirs = [d for d in (root / "evidence").iterdir() if d.is_dir() and (d / "result.json").is_file()]
        receipt = max(result_dirs, key=lambda d: d.name) if result_dirs else None
        row = {"demo": name, "repetition": repetition, "exit_code": result.returncode,
               "receipt": receipt.name if receipt else None, "scope": "physical QB560D-EU CPU, 20 invokes after 3 warmups"}
        rows.append(row)
        print("Repeat %d %s: %s" % (repetition, name, "PASS" if result.returncode == 0 else "FAIL"), flush=True)
        if result.returncode:
            sys.stdout.buffer.write(result.stdout)
summary = {"at_host_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "runs": rows}
(root / "evidence" / "target-ai-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
sys.exit(1 if any(r["exit_code"] for r in rows) else 0)

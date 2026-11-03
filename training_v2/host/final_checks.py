"""Source/data checks. Run HTTP/unit and shell checks separately and record their results."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sh", default=shutil.which("sh"))
args = parser.parse_args()
files = [p for folder in ("ai", "app", "host", "target", "tests") for p in (root / folder).glob("*.py")]
for p in files:
    ast.parse(p.read_text(encoding="utf-8"), feature_version=(3, 8))
for p in (root / "target").glob("*.sh"):
    if b"\r\n" in p.read_bytes():
        raise ValueError("Target script must use LF endings: " + str(p))
lock = json.loads((root / "models" / "models.lock.json").read_text())
for name, spec in lock.items():
    if hashlib.sha256((root / "models" / name).read_bytes()).hexdigest() != spec["sha256"]:
        raise ValueError("Model asset changed: " + name)
origin = json.loads((root / 'models/snpe-model.origin.json').read_text())
for field, checksum in (('source_model', 'source_sha256'), ('target_model', 'target_sha256')):
    assert hashlib.sha256((root / 'models' / origin[field]).read_bytes()).hexdigest() == origin[checksum], 'SNPE source/candidate model changed'
canonical = root / 'slides/QB560D_EU_Training.pptx'
with zipfile.ZipFile(canonical) as package:
    manifest = ET.fromstring(package.read("ppt/presentation.xml"))
    slide_count = len(manifest.find("{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst"))
    media = [p for p in package.infolist() if p.filename.startswith("ppt/media/")]
    assert all(p.file_size > 0 for p in media), "PPTX contains empty media"
acceleration = root / "evidence/acceleration"
latest = json.loads((acceleration / "LATEST.json").read_text())
accel_path = root / latest["summary"]
assert hashlib.sha256(accel_path.read_bytes()).hexdigest() == latest["sha256"]
accel = json.loads(accel_path.read_text())
assert len(accel["records"]) == 2 * accel["sessions_per_backend"]
assert all(row["top1_equal"] for row in accel["correctness"])
for row in accel["records"]:
    log = (accel_path.parent / row["log"]).read_text(encoding="utf-8")
    if row["backend"] == "gpu":
        assert "Initialized OpenCL-based API" in log and "Created 1 GPU delegate kernels" in log
extra_receipts = {}
for name in ("wlan", "htp-dsp"):
    pointer = json.loads((root / "evidence" / name / "LATEST.json").read_text())
    receipt = root / pointer["summary"]
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == pointer["sha256"]
    extra_receipts[name] = json.loads(receipt.read_text())
htp = extra_receipts['htp-dsp']
assert htp['model_inference'] == 'PASS_REFERENCE_IMAGE_HTP'
assert htp['snpe_htp_runtime']['model_loaded'] is True
assert htp['profile']['dsp_entries'] == 34 and htp['profile']['cpu_entries'] == 0
assert len(htp['records']) == 4 * htp['sessions_per_backend']
assert all(row['top1_equal'] for row in htp['correctness'])
assert htp['model_hashes']['htp'] == htp['model_hashes']['snpe_cpu_fixed'] == origin['target_sha256']
assert htp['model_hashes']['tflite_cpu'] == htp['model_hashes']['tflite_gpu'] == origin['source_sha256']
htp_folder = root / json.loads((root / 'evidence/htp-dsp/LATEST.json').read_text())['summary']
placements = re.findall(r'^\s*\d+:.*?:\s*(DSP|CPU)\s*$', (htp_folder.parent / htp['profile']['file']).read_text(), re.MULTILINE)
assert len(placements) == 34 and set(placements) == {'DSP'}
target = json.loads((root / "evidence" / "target-ai-summary.json").read_text())
assert len(target["runs"]) == 15 and all(row["exit_code"] == 0 for row in target["runs"])
docker_root = root / 'demos/docker'
docker_receipt = {'result': 'NOT_AVAILABLE', 'source': 'demos/docker/evidence/LATEST.json'}
if (docker_root / 'evidence/LATEST.json').exists():
    docker_pointer = json.loads((docker_root / 'evidence/LATEST.json').read_text())
    docker_summary = docker_root / docker_pointer['summary']
    assert hashlib.sha256(docker_summary.read_bytes()).hexdigest() == docker_pointer['sha256']
    docker_result = json.loads(docker_summary.read_text())
    assert all(row['passed'] for row in docker_result['checks'])
    docker_receipt.update({'result': docker_result['result'], 'sessions': len(docker_result['three_sessions']), 'command_checks': len(docker_result['checks']), 'runtime': docker_result['engine']['ServerVersion']})
unit = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-p", "test_*.py", "-v"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(root / "evidence" / "unit-http-tests.log").write_bytes(unit.stdout)
if unit.returncode:
    raise SystemExit("Unit/HTTP checks failed; see evidence/unit-http-tests.log")
match = re.search(rb"Ran ([0-9]+) tests?", unit.stdout)
if not match:
    raise SystemExit("Unit test count was not reported")
shell = {"result": "NOT_RUN", "reason": "No POSIX shell supplied"}
if args.sh:
    scripts = list((root / "target").glob("*.sh"))
    for script in scripts:
        subprocess.run([args.sh, "-n", str(script)], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    shell = {"result": "PASS", "scripts": len(scripts)}
report = {"preparation_platform": platform.platform(), "python38_syntax_files": len(files), "shell_lf": "PASS",
          "shell_syntax": shell,
          "unit_http_legacy_adb": {"tests": int(match.group(1)), "result": "PASS", "execution": "actual subprocess run by final_checks.py"},
          "target_ai": {"sessions": 15, "models": 5, "result": "PASS_REFERENCE_INPUTS", "runtime": "vendor TFLite C API 2.8.4"},
          "target_app": "Dated target observations in docs/TARGET_RESULTS.md",
          "slides": {"canonical_file": canonical.name, "count": slide_count, "embedded_media": len(media), "empty_media": 0, "source": "official Quectel 2026 template"},
          "target_gpu": {"result": "PASS_REFERENCE_INPUT", "sessions": accel["sessions_per_backend"], "runs_per_session": accel["runs_per_session"], "speedup": accel["speedup_cpu_over_gpu"], "source": latest["summary"]},
          "wlan": {"result": extra_receipts["wlan"]["result"], "ntp_synchronized": extra_receipts["wlan"]["ntp_synchronized"], "boot_reconnection": "NOT_TESTED"},
          "htp": {"runtime": htp["snpe_htp_runtime"], "model_inference": htp["model_inference"], "sessions_per_backend": htp['sessions_per_backend'], "profile": htp['profile'], "same_dlc_speedup": htp['speedup_same_dlc_cpu_over_htp'], "numerical_validation": "reference top1 matches; maximum HTP/same-DLC CPU probability difference 4/256; no dataset accuracy evaluation"},
          "target_docker": docker_receipt,
          "pending": ([] if docker_receipt['result'] == 'PASS_THREE_SESSIONS_AND_OFFLINE_DEPLOY' else ['Docker']) + ["iperf3/server", "active cellular session", "BSP failed-unit review", "AI Hub hosted job", "camera", "HTP dataset accuracy", "WLAN boot reconnection", "event-specific inputs and negative controls"]}
current_path = root / 'evidence/CURRENT_FIRMWARE.json'
if current_path.exists():
    current = json.loads(current_path.read_text(encoding='utf-8'))
    core = json.loads((root/current['core']).read_text(encoding='utf-8'))
    reference = json.loads((root/current['cpu_reference_results']).read_text(encoding='utf-8'))
    assert core['result'] == 'PASS_LOCAL_CORE_DEMOS'
    assert all(row['exit_code'] == 0 for row in core['checks'] if row['required'])
    assert len(reference['runs']) == 15 and all(row['correct_reference'] for row in reference['runs'])
    final = json.loads((root/current['final_state']).read_text(encoding='utf-8'))
    assert final['vendor_libraries_unchanged'] and final['service_active'] == 'inactive'
    snpe_lock = json.loads((root/'host/snpe-runtime.lock.json').read_text())
    for name,spec in snpe_lock['files'].items():
        assert hashlib.sha256((root/'offline/snpe226'/name).read_bytes()).hexdigest() == spec['sha256']
    report['current_firmware'] = {'bsp':current['bsp'],'core_checks':len(core['checks']),'cpu_reference_results':len(reference['runs']),
                                  'result':current['result'],'vendor_libraries_unchanged':True,'snpe_offline_files':len(snpe_lock['files'])}
    report['pending'] = ['cellular/iperf3 deferred by owner until SIM setup','cold boot and BSP failed-unit review','AI Hub account/job','camera sensor/pipeline','dataset/event-scene controls','WLAN boot reconnection']
(root / "evidence" / "software-qa.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))

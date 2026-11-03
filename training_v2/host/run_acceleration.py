"""Run alternating CPU/GPU sessions on the connected QB560D, preserving evidence."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shlex
import statistics
import subprocess
import sys

import numpy as np
from adb_lab import ROOT, marked_command, remote_exit_status, select_device
from adb_login import resolve_adb, run_shell, transfer
from target_layout import DEFAULT_REMOTE, validate_remote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--transport-id")
    parser.add_argument('--remote', default=DEFAULT_REMOTE, type=validate_remote)
    parser.add_argument("--sessions", type=int, default=3)
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=10)
    a = parser.parse_args()
    if not 1 <= a.sessions <= 10 or not 1 <= a.runs <= 1000 or not 0 <= a.warmup <= 100:
        parser.error("Invalid session/run/warmup count")
    a.adb = resolve_adb(a.adb)
    base = [a.adb, *select_device(a.adb, a.serial, a.transport_id)]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    local = ROOT / "evidence" / "acceleration" / stamp
    local.mkdir(parents=True, exist_ok=False)
    remote = a.remote
    records = []
    for session in range(a.sessions):
        # Reverse order every other session to reduce a fixed ordering bias.
        for backend in (("cpu", "gpu") if session % 2 == 0 else ("gpu", "cpu")):
            output = "evidence/acceleration/" + stamp + "/session_%d_%s" % (session + 1, backend)
            args = ["sh", "target/ai.sh", "classification", "--image", "media/grace_hopper.jpg",
                    "--backend", backend, "--vendor-c-api", "--threads", "2", "--runs", str(a.runs),
                    "--warmup", str(a.warmup), "--output", output]
            command = "cd " + remote + " && " + " ".join(shlex.quote(v) for v in args)
            result = run_shell(base, marked_command(command), timeout=180)
            log = result.stdout.decode("utf-8", errors="replace").replace("\r", "")
            logfile = local / ("session_%d_%s.log" % (session + 1, backend))
            logfile.write_text(log, encoding="utf-8")
            status = remote_exit_status(result.returncode, result.stdout)
            if status:
                raise RuntimeError("Target failed; see " + str(logfile))
            if backend == "gpu" and not all(s in log for s in ("Initialized OpenCL-based API", "Created 1 GPU delegate kernels")):
                raise RuntimeError("Expected GPU execution evidence is missing; refusing CPU fallback result")
            records.append({"session": session + 1, "backend": backend, "log": logfile.name})
            print("Session", session + 1, backend, "OK", flush=True)
    transfer(base, "pull", remote + "/evidence/acceleration/" + stamp, str(local / "target"), stdout=subprocess.PIPE)
    by_backend = {"cpu": [], "gpu": []}
    arrays = {}
    for record in records:
        folder = local / "target" / ("session_%d_%s" % (record["session"], record["backend"])) / "classification"
        files = list(folder.glob("*.json"))
        if len(files) != 1:
            raise RuntimeError("Expected exactly one result in " + str(folder))
        data = json.loads(files[0].read_text())
        by_backend[record["backend"]].append(data)
        arrays[(record["session"], record["backend"])] = np.load(files[0].with_suffix(".outputs.npz"))["output_0"]
        record.update({"result": files[0].relative_to(local).as_posix(), "median_ms": data["inference_ms_median"], "p95_ms": data["inference_ms_p95"], "top1": data["top3"][0]})
    hashes = {(r["model_sha256"], r["image_sha256"], r["runtime_version"]) for rows in by_backend.values() for r in rows}
    if len(hashes) != 1:
        raise RuntimeError("Model/input/runtime mismatch")
    cpu = statistics.median(r["inference_ms_median"] for r in by_backend["cpu"])
    gpu = statistics.median(r["inference_ms_median"] for r in by_backend["gpu"])
    diffs = [{"session": i, "max_abs_probability_difference": float(np.max(np.abs(arrays[(i, "cpu")] - arrays[(i, "gpu")]))),
              "top1_equal": bool(np.argmax(arrays[(i, "cpu")]) == np.argmax(arrays[(i, "gpu")]))} for i in range(1, a.sessions + 1)]
    model_hash, image_hash, runtime_version = next(iter(hashes))
    summary = {"recorded_at_host_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "target_clock_warning": "Target clock is not synchronized; timestamps use host UTC",
               "demo": "MobileNet V1 uint8 image classification", "model_sha256": model_hash, "image_sha256": image_hash,
               "runtime_version": runtime_version, "sessions_per_backend": a.sessions, "runs_per_session": a.runs, "warmup_per_session": a.warmup,
               "cpu_threads": 2, "cpu_median_of_session_medians_ms": cpu, "gpu_median_of_session_medians_ms": gpu,
               "speedup_cpu_over_gpu": cpu / gpu, "latency_reduction_percent": (1 - gpu / cpu) * 100,
               "timing_scope": "TFLite InterpreterInvoke only; includes delegate boundary conversion for uint8, excludes image decode/preprocess/output copy/render",
               "gpu_evidence": "BSP logs: Initialized OpenCL-based API; Created 1 GPU delegate kernels. One GPU partition confirmed; per-operator coverage not exposed by this C API.",
               "htp_dsp_status": "Not executed; GPU result does not establish HTP/DSP execution",
               "correctness": diffs, "records": records}
    (local / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (ROOT / "evidence" / "acceleration" / "LATEST.json").write_text(json.dumps({"summary": (local / "summary.json").relative_to(ROOT).as_posix(), "sha256": hashlib.sha256((local / "summary.json").read_bytes()).hexdigest()}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cpu_ms": cpu, "gpu_ms": gpu, "speedup": cpu / gpu, "correctness": diffs, "summary": str(local / "summary.json")}, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()

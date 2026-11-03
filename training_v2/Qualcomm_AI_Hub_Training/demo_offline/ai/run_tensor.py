"""Validate the tiny AI Hub TFLite artifact on the actual BSP, using known tensors."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
import numpy as np
from c_api_backend import Interpreter


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--backend", choices=["cpu", "gpu"], default="cpu")
    p.add_argument("--runs", type=int, default=50)
    p.add_argument("--warmup", type=int, default=10)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if not 1 <= a.runs <= 1000 or not 0 <= a.warmup <= 100:
        p.error("Invalid timing count")
    source = np.load(a.input, allow_pickle=False)
    expected = np.load(a.expected, allow_pickle=False)
    interpreter = Interpreter(a.model, num_threads=2, backend=a.backend)
    interpreter.allocate_tensors()
    inputs, outputs = interpreter.get_input_details(), interpreter.get_output_details()
    if len(inputs) != 1 or len(outputs) != 1 or inputs[0]["dtype"] != np.float32 or outputs[0]["dtype"] != np.float32:
        raise ValueError("This example requires exactly one float32 input and output")
    if source.shape != (1, 3, 32, 32) or expected.shape != (1, 4):
        raise ValueError("Use the reviewed tiny model input and expected tensor")
    layout = "NCHW"
    if list(inputs[0]["shape"]) == [1, 32, 32, 3]:
        source = source.transpose(0, 2, 3, 1)
        layout = "NHWC (transposed from source NCHW)"
    interpreter.set_tensor(inputs[0]["index"], np.ascontiguousarray(source))
    for _ in range(a.warmup):
        interpreter.invoke()
    timings = []
    for _ in range(a.runs):
        started = time.perf_counter()
        interpreter.invoke()
        timings.append((time.perf_counter() - started) * 1000)
    actual = interpreter.get_tensor(outputs[0]["index"])
    if actual.shape != expected.shape:
        raise ValueError("Output shape differs from the reference")
    passed = bool(np.allclose(actual, expected, atol=1e-4, rtol=1e-3))
    result = {"result": "PASS" if passed else "NUMERICAL_MISMATCH", "backend": a.backend,
              "runtime_version": interpreter.lib.TfLiteVersion().decode(), "input_layout": layout,
              "model_sha256": hashlib.sha256(Path(a.model).read_bytes()).hexdigest(),
              "input_sha256": hashlib.sha256(Path(a.input).read_bytes()).hexdigest(),
              "expected_sha256": hashlib.sha256(Path(a.expected).read_bytes()).hexdigest(),
              "max_abs_error": float(np.max(np.abs(actual - expected))), "atol": 1e-4, "rtol": 1e-3,
              "actual": actual.tolist(), "expected": expected.tolist(),
              "warmup": a.warmup, "runs": a.runs, "median_invoke_ms": statistics.median(timings),
              "p95_invoke_ms": float(np.percentile(timings, 95)),
              "timing_scope": "invoke only, excluding set_tensor/get_tensor/preprocessing"}
    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

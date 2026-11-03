"""D2-04. Compile/profile an ONNX model on an explicitly chosen hosted device."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def main():
    # The SDK prints Unicode progress symbols, including when output is redirected.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--device", required=True, help="Exact name returned by qai-hub list-devices")
    p.add_argument("--runtime", choices=["tflite", "onnx"], default="tflite")
    p.add_argument("--compute-unit", choices=["cpu", "gpu", "npu"], default="gpu")
    p.add_argument("--input", help="Optional .npy float32 input; otherwise profile uses random data")
    p.add_argument("--input-name", default="image")
    p.add_argument("--expected", help="Optional expected .npy output for the one-output tiny example")
    p.add_argument("--output", default="evidence/workbench")
    a = p.parse_args()
    import qai_hub as hub
    model = Path(a.model)
    if not model.is_file():
        p.error("Supply an ONNX model whose input/output contract you have validated")
    if a.expected and not a.input:
        p.error("--expected requires --input")
    for name in (a.input, a.expected):
        if name and not Path(name).is_file():
            p.error("Input/reference file does not exist: " + name)
    dest = Path(a.output)
    dest.mkdir(parents=True, exist_ok=True)
    if (dest / "jobs.json").exists():
        p.error("Output already has job records. Use a new output directory to preserve evidence.")
    device = hub.Device(a.device)
    client = hub.Client()
    options = "--target_runtime " + a.runtime + " --compute_unit " + a.compute_unit
    compile_job = client.submit_compile_job(model=str(model), device=device, options=options)
    receipt = {"device": a.device, "location": "Qualcomm-hosted device; NOT the local QB560D", "compile_options": options,
               "source_sha256": hashlib.sha256(model.read_bytes()).hexdigest(), "compile_job": {"id": compile_job.job_id, "url": compile_job.url}}
    def save_receipt():
        (dest / "jobs.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    save_receipt()
    print("COMPILE_JOB: " + compile_job.url, flush=True)
    if not compile_job.wait().success:
        raise RuntimeError("Compile failed; inspect " + compile_job.url)
    print("COMPILE_PASS", flush=True)
    target = compile_job.get_target_model()
    if target is None:
        raise RuntimeError("Compile did not produce a model. Review the job in Workbench.")
    inputs = None
    if a.input:
        import numpy as np
        value = np.load(a.input, allow_pickle=False)
        if value.dtype != np.float32:
            p.error("Example input must be float32")
        inputs = {a.input_name: [value]}
        receipt["input_sha256"] = hashlib.sha256(Path(a.input).read_bytes()).hexdigest()
    # qai-hub 0.57: profile=True replaces deprecated submit_profile_job().
    profile_job = client.submit_inference_job(model=target, device=device, inputs=inputs,
                                               options="--compute_unit " + a.compute_unit, profile=True)
    receipt["inference_profile_job"] = {"id": profile_job.job_id, "url": profile_job.url}
    save_receipt()
    print("INFERENCE_PROFILE_JOB: " + profile_job.url, flush=True)
    if not profile_job.wait().success:
        raise RuntimeError("Inference/profile failed; inspect " + profile_job.url)
    print("INFERENCE_PROFILE_PASS", flush=True)
    profile = profile_job.download_profile()
    asset = dest / ("model." + a.runtime)
    target.download(str(asset))
    receipt["target_sha256"] = hashlib.sha256(asset.read_bytes()).hexdigest()
    if inputs:
        dataset = profile_job.get_output_dataset()
        if dataset is None:
            raise RuntimeError("Inference returned no output dataset")
        outputs = dataset.download()
        import numpy as np
        np.savez_compressed(dest / "hosted_outputs.npz", **{name + "_" + str(i): value for name, values in outputs.items() for i, value in enumerate(values)})
        if a.expected:
            values = [value for batches in outputs.values() for value in batches]
            expected = np.load(a.expected, allow_pickle=False)
            if len(values) != 1 or values[0].shape != expected.shape:
                raise ValueError("Expected one output with the same shape as the reference")
            receipt["correctness"] = {"pass": bool(np.allclose(values[0], expected, rtol=1e-3, atol=1e-4)),
                                      "max_abs_error": float(np.max(np.abs(values[0] - expected))), "atol": 1e-4, "rtol": 1e-3}
            save_receipt()
            print("CORRECTNESS: " + json.dumps(receipt["correctness"]), flush=True)
            if not receipt["correctness"]["pass"]:
                raise RuntimeError("Hosted output differs from expected; see jobs.json")
    save_receipt()
    (dest / "profile.json").write_text(json.dumps(profile, indent=2, default=str), encoding="utf-8")
    (dest / "scope.txt").write_text("Device: " + a.device + "\nExecution location: Qualcomm-hosted device, not local QB560D-EU.\n", encoding="utf-8")
    print("RESULT: HOSTED_COMPILE_PROFILE_COMPLETE. Local deployment still requires BSP/runtime validation.")


if __name__ == "__main__":
    main()

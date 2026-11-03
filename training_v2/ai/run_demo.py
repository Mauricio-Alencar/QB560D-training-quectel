"""Five demos: CPU/GPU, plus an explicit Hexagon DSP attempt requiring profile review."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import platform
import statistics
import time

import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
POSE_EDGES = [(0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
HAND_EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def interpreter_type():
    for module in ("tflite_runtime.interpreter", "ai_edge_litert.interpreter"):
        try:
            return importlib.import_module(module).Interpreter, module
        except ImportError:
            pass
    try:
        import tensorflow as tf
        return tf.lite.Interpreter, "tensorflow.lite"
    except ImportError as exc:
        if Path("/usr/lib/libtensorflowlite_c.so").is_file():
            from c_api_backend import Interpreter
            return Interpreter, "vendor_tflite_c_api"
        raise RuntimeError("No TFLite interpreter installed. See docs/TARGET_SETUP.md") from exc


def prepare_input(canvas, profile, detail):
    pixels = np.asarray(canvas, dtype=np.float32)
    if profile["input_kind"] == "raw":
        if not np.issubdtype(detail["dtype"], np.integer):
            raise ValueError("This profile expects integer RGB pixels. Inspect the new model before changing it.")
        tensor = pixels.astype(detail["dtype"])
    else:
        tensor = (pixels - profile.get("mean", 0.0)) / profile.get("std", 1.0)
        if np.issubdtype(detail["dtype"], np.integer):
            scale, zero = detail["quantization"]
            if scale <= 0:
                raise ValueError("Unsupported quantization: per-tensor scale required")
            limits = np.iinfo(detail["dtype"])
            tensor = np.clip(np.rint(tensor / scale + zero), limits.min, limits.max)
        tensor = tensor.astype(detail["dtype"])
    return tensor[np.newaxis]


def dequantize(data, detail):
    if np.issubdtype(data.dtype, np.integer):
        scale, zero = detail.get("quantization", (0.0, 0))
        if scale > 0:
            return (data.astype(np.float32) - zero) * scale
    return data.astype(np.float32)


def finger_state(points):
    """Conservative open-hand / closed-fist rule for a palm-facing, aligned crop."""
    points = np.asarray(points)
    wrist = points[0, :2]
    extended = []
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        extended.append(bool(np.linalg.norm(points[tip, :2] - wrist) > 1.2 * np.linalg.norm(points[pip, :2] - wrist)))
    count = sum(extended)
    return {"gesture": "open_hand" if count == 4 else "closed_fist" if count == 0 else "other", "extended_fingers_excluding_thumb": count}


def postprocess(task, tensors, profile, labels, threshold):
    def out(key):
        return tensors[profile["outputs"][key]]
    if task == "classification":
        scores = out("scores").reshape(-1)
        top = np.argsort(scores)[::-1][:3]
        return {"top3": [{"class_id": int(i), "label": labels[i] if i < len(labels) else "class_" + str(i), "score": float(scores[i])} for i in top]}
    if task == "detection":
        boxes, scores, classes = out("boxes").reshape(-1, 4), out("scores").reshape(-1), out("classes").reshape(-1)
        count = min(int(out("count").reshape(-1)[0]), len(scores), len(boxes), len(classes))
        detections = []
        for i in range(count):
            if scores[i] < threshold:
                continue
            cls = int(round(float(classes[i])))
            label_index = cls + profile.get("label_offset", 0)
            detections.append({"class_id": cls, "label": labels[label_index] if 0 <= label_index < len(labels) else "class_" + str(cls), "score": float(scores[i]), "box_yxyx": np.clip(boxes[i], 0, 1).tolist()})
        return {"detections": detections}
    if task == "pose":
        heatmaps, offsets = out("heatmaps")[0], out("offsets")[0]
        if heatmaps.ndim != 3 or heatmaps.shape[-1] != 17 or offsets.shape != heatmaps.shape[:2] + (34,):
            raise ValueError("Expected PoseNet NHWC heatmaps with 17 joints and 34 offsets")
        height, width = heatmaps.shape[:2]
        input_w, input_h = profile["size"]
        points = []
        for joint in range(17):
            y, x = np.unravel_index(np.argmax(heatmaps[:, :, joint]), (height, width))
            score = float(1.0 / (1.0 + np.exp(-np.clip(heatmaps[y, x, joint], -80, 80))))
            py = (y * (input_h - 1) / (height - 1) + offsets[y, x, joint]) / input_h
            px = (x * (input_w - 1) / (width - 1) + offsets[y, x, joint + 17]) / input_w
            points.append([float(py), float(px), score])
        return {"keypoints_yxs": points, "visible_keypoints": sum(point[2] >= threshold for point in points), "decoder": "single_person_heatmap_argmax"}
    if task == "gesture":
        points = out("landmarks").reshape(21, 3) / 224.0
        presence = float(out("presence").reshape(-1)[0])
        result = {"presence": presence, "landmarks_xyz": points.tolist()}
        result.update(finger_state(points) if presence >= threshold else {"gesture": "no_hand"})
        return result
    if task == "segmentation":
        logits = out("mask")
        if logits.shape != (1, 257, 257, 21):
            raise ValueError("Expected DeepLabV3 [1,257,257,21]")
        mask = np.argmax(logits[0], axis=-1)
        ids, counts = np.unique(mask, return_counts=True)
        labels = profile["class_labels"]
        return {"foreground_fraction": float((mask != 0).mean()), "class_fractions": {labels[int(i)]: float(n / mask.size) for i, n in zip(ids, counts)}}
    raise ValueError("Unknown task: " + task)


def annotate(canvas, result, task, tensors, profile, threshold):
    canvas = canvas.copy()
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    if task == "classification":
        draw.rectangle((4, 4, w - 4, 49), fill="white")
        for i, row in enumerate(result["top3"]):
            draw.text((8, 6 + 14 * i), row["label"] + " %.3f" % row["score"], fill="black")
    if task == "detection":
        for row in result["detections"]:
            y0, x0, y1, x1 = row["box_yxyx"]
            draw.rectangle((x0 * w, y0 * h, x1 * w, y1 * h), outline="red", width=2)
            draw.text((x0 * w, max(0, y0 * h - 12)), row["label"], fill="red")
    if task in ("pose", "gesture"):
        if task == "gesture" and result["gesture"] == "no_hand":
            return canvas
        if task == "pose":
            points = [(x * w, y * h, score) for y, x, score in result["keypoints_yxs"]]
            edges = POSE_EDGES
        else:
            points = [(x * w, y * h, 1.0) for x, y, _ in result["landmarks_xyz"]]
            edges = HAND_EDGES
        for a, b in edges:
            if points[a][2] >= threshold and points[b][2] >= threshold:
                draw.line((points[a][:2], points[b][:2]), fill="red", width=2)
        for x, y, score in points:
            if score >= threshold:
                draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="yellow")
    if task == "segmentation":
        mask = np.argmax(tensors[profile["outputs"]["mask"]][0], axis=-1)
        overlay = np.zeros((h, w, 4), dtype=np.uint8)
        for class_id in np.unique(mask):
            if class_id:
                overlay[mask == class_id] = [(int(class_id) * 67) % 256, (int(class_id) * 101) % 256, (int(class_id) * 137) % 256, 110]
        canvas = Image.alpha_composite(canvas.convert("RGBA"), Image.fromarray(overlay)).convert("RGB")
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", choices=["classification", "detection", "pose", "gesture", "segmentation"])
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", help="Override only after reviewing tensor contract")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--backend", choices=["cpu", "gpu", "dsp"], default="cpu")
    parser.add_argument("--vendor-c-api", action="store_true", help="Use the same installed C runtime for a CPU/GPU comparison")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", default="evidence/ai")
    a = parser.parse_args()
    if not (1 <= a.runs <= 1000 and 0 <= a.warmup <= 100 and 1 <= a.threads <= 8 and 0 <= a.threshold <= 1):
        parser.error("Invalid run count, thread count or threshold")
    profile = json.loads((ROOT / "ai" / "profiles.json").read_text())[a.demo]
    model = Path(a.model) if a.model else ROOT / "models" / profile["model"]
    if a.backend != "cpu" or a.vendor_c_api:
        from c_api_backend import Interpreter
        runtime = "vendor.tflite_c_api"
        interpreter = Interpreter(model_path=str(model), num_threads=a.threads, backend=a.backend)
    else:
        cls, runtime = interpreter_type()
        interpreter = cls(model_path=str(model), num_threads=a.threads)
    interpreter.allocate_tensors()
    inputs, outputs = interpreter.get_input_details(), interpreter.get_output_details()
    details = {"inputs": [{"name": d["name"], "shape": d["shape"].tolist(), "dtype": str(d["dtype"]), "quantization": list(d["quantization"])} for d in inputs],
               "outputs": [{"slot": i, "name": d["name"], "shape": d["shape"].tolist(), "dtype": str(d["dtype"]), "quantization": list(d["quantization"])} for i, d in enumerate(outputs)]}
    print(json.dumps(details, indent=2))
    if a.inspect:
        return
    width, height = profile["size"]
    if len(inputs) != 1 or list(inputs[0]["shape"]) != [1, height, width, 3]:
        raise ValueError("Input shape differs from the reviewed profile")
    original = ImageOps.exif_transpose(Image.open(a.image)).convert("RGB")
    if a.crop:
        left, top, right, bottom = a.crop
        if not (0 <= left < right <= original.width and 0 <= top < bottom <= original.height):
            parser.error("Crop must lie inside the input image")
        original = original.crop(tuple(a.crop))
    # Deliberate stretch-resize baseline. Output image uses model coordinates.
    # Gesture input must already be a square, upright crop of one hand.
    if a.demo == "gesture" and original.width != original.height:
        raise ValueError("Gesture demo requires a square, upright hand crop")
    canvas = original.resize((width, height), Image.Resampling.BILINEAR)
    interpreter.set_tensor(inputs[0]["index"], prepare_input(canvas, profile, inputs[0]))
    for _ in range(a.warmup):
        interpreter.invoke()
    timings = []
    for _ in range(a.runs):
        start = time.perf_counter()
        interpreter.invoke()
        timings.append((time.perf_counter() - start) * 1000)
    tensors = [dequantize(interpreter.get_tensor(d["index"]), d) for d in outputs]
    labels_path = ROOT / "models" / profile.get("labels", "__none__")
    labels = labels_path.read_text(encoding="utf-8").splitlines() if labels_path.is_file() else []
    result = postprocess(a.demo, tensors, profile, labels, a.threshold)
    result.update({"demo_id": profile["demo_id"], "backend": a.backend.upper(), "runtime": runtime,
                   "platform": platform.platform(), "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                   "image_sha256": hashlib.sha256(Path(a.image).read_bytes()).hexdigest(),
                   "runs": a.runs, "warmup": a.warmup, "threads": a.threads, "crop": a.crop,
                   "inference_ms_median": statistics.median(timings), "inference_ms_p95": float(np.percentile(timings, 95)),
                   "timing_scope": "interpreter.invoke only; excludes decode, preprocessing and rendering", "tensor_contract": details})
    if a.backend == "gpu":
        result["delegate"] = "TfLiteGpuDelegateV2 (installed BSP); inspect stderr for delegated partition coverage"
    if a.backend == "dsp":
        result["backend"] = "DSP_REQUESTED"
        result["delegate"] = "TfLiteHexagonDelegate (installed BSP); graph profile/debug enabled; inspect DSP execution evidence"
        result["execution_confirmation"] = "Requires DSP graph profile review; delegate creation alone does not verify offload"
    if hasattr(interpreter, "lib"):
        result["runtime_version"] = interpreter.lib.TfLiteVersion().decode()
    dest = Path(a.output) / a.demo
    dest.mkdir(parents=True, exist_ok=True)
    stamp = str(time.time_ns())
    (dest / (stamp + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    np.savez_compressed(dest / (stamp + ".outputs.npz"), **{"output_%d" % i: value for i, value in enumerate(tensors)})
    rendered = annotate(canvas, result, a.demo, tensors, profile, a.threshold)
    scale = 768.0 / max(rendered.size)
    rendered.resize((round(rendered.width * scale), round(rendered.height * scale))).save(dest / (stamp + ".png"))
    print(json.dumps(result, indent=2))
    print("RESULT: INFERENCE_EXECUTED (check visual correctness before acceptance)")


if __name__ == "__main__":
    main()

"""Rebuild a candidate DLC from the original TFLite; never overwrite the published model.

Run on Windows with Python 3.8 and the dependencies listed in docs/HTP_DSP.md.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def validate_onnx(folder):
    import numpy as np
    import onnxruntime as ort
    import tensorflow as tf
    from PIL import Image, ImageOps
    pixels = np.asarray(ImageOps.exif_transpose(Image.open(ROOT / 'media/grace_hopper.jpg')).convert('RGB').resize((224, 224), Image.Resampling.BILINEAR), dtype=np.uint8)[None]
    interpreter = tf.lite.Interpreter(model_path=str(ROOT / 'models/mobilenet_v1.tflite'), num_threads=2)
    interpreter.allocate_tensors()
    interpreter.set_tensor(interpreter.get_input_details()[0]['index'], pixels)
    interpreter.invoke()
    expected = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])
    rows = []
    for name in ('mobilenet_v1.onnx', 'mobilenet_v1_scalar.onnx'):
        session = ort.InferenceSession(str(folder / name), providers=['CPUExecutionProvider'])
        actual = session.run(None, {session.get_inputs()[0].name: pixels})[0]
        if not np.array_equal(expected, actual):
            raise ValueError('ONNX differs from source TFLite under the conversion reference runtime')
        rows.append({'file': name, 'source_tflite_tf213_exact_output_match': True, 'top1': int(np.argmax(actual)), 'top1_score': float(actual.max()) / 256})
    report = {'tensorflow': tf.__version__, 'onnxruntime': ort.__version__, 'scope': 'supplied image only; the old target TFLite 2.8.4 has separately measured rounding differences', 'records': rows}
    (folder / 'onnx-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.build/snpe-conversion-rebuilt')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--sdk-root', type=Path, default=ROOT / '.build/sdk-public-2.26/qairt/2.26.0.240828')
    args = parser.parse_args()
    args.sdk_root = args.sdk_root.resolve()
    folder = args.output.resolve()
    if args.verify_only:
        validate_onnx(folder)
        return
    folder.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'models/mobilenet_v1.tflite'
    origin = json.loads((ROOT / 'models/snpe-model.origin.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != origin['source_sha256']:
        raise ValueError('Source TFLite hash mismatch')
    subprocess.run([sys.executable, '-m', 'tf2onnx.convert', '--tflite', str(source), '--opset', '13', '--output', str(folder / 'mobilenet_v1.onnx')], check=True)
    import onnx
    from onnx import numpy_helper
    model = onnx.load(str(folder / 'mobilenet_v1.onnx'))
    tensors = {value.name: value for value in model.graph.initializer}
    changed = []
    for node in model.graph.node:
        if node.op_type == 'DequantizeLinear' and node.input[0] in tensors and node.input[1] in tensors:
            if len(tensors[node.input[0]].dims) == 1 and numpy_helper.to_array(tensors[node.input[1]]).size == 1 and not any(a.name == 'axis' for a in node.attribute):
                node.attribute.append(onnx.helper.make_attribute('axis', 0))
                changed.append(node.name)
    onnx.checker.check_model(model)
    onnx.save(onnx.shape_inference.infer_shapes(model), str(folder / 'mobilenet_v1_scalar.onnx'))
    (folder / 'axis-metadata.json').write_text(json.dumps(changed, indent=2), encoding='utf-8')
    validate_onnx(folder)
    env = os.environ.copy()
    env['QB560D_SNPE_SDK_ROOT'] = str(args.sdk_root.resolve())
    subprocess.run([sys.executable, str(Path(__file__).with_name('snpe_converter_entry.py')), 'snpe-onnx-to-dlc', '--input_network', str(folder / 'mobilenet_v1_scalar.onnx'), '--input_layout', 'input', 'NHWC', '--input_dtype', 'input', 'float32', '--output_path', str(folder / 'mobilenet_v1_float_io.dlc'), '-n', '--strict'], env=env, check=True)
    import numpy as np
    from PIL import Image, ImageOps
    (folder / 'calibration').mkdir()
    names = []
    for image_name in ('grace_hopper', 'right_hands'):
        pixels = np.asarray(ImageOps.exif_transpose(Image.open(ROOT / ('media/' + image_name + '.jpg'))).convert('RGB').resize((224, 224), Image.Resampling.BILINEAR), dtype=np.float32)
        name = 'calibration/' + image_name + '_norm.raw'
        ((pixels - 128.0) / 128.0).astype('<f4').tofile(folder / name)
        names.append(name)
    (folder / 'calibration_normalized.txt').write_text('\n'.join(names) + '\n', encoding='utf-8')
    env['PATH'] = str(args.sdk_root / 'lib/x86_64-windows-msvc') + os.pathsep + env.get('PATH', '')
    subprocess.run([str(args.sdk_root / 'bin/x86_64-windows-msvc/snpe-dlc-quant.exe'), '--input_dlc', 'mobilenet_v1_float_io.dlc', '--input_list', 'calibration_normalized.txt', '--output_dlc', 'mobilenet_v1_preserved_int8.dlc', '--weights_bitwidth', '8', '--act_bitwidth', '8', '--bias_bitwidth', '32', '--override_params'], cwd=str(folder), env=env, check=True)
    print('Candidate saved; validate its CPU-fixed and HTP results before publishing:', folder)


if __name__ == '__main__':
    main()

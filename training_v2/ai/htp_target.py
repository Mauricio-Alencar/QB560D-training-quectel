"""Eleven offline controls: prepare, execute HTP, decode and render on the target."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageOps, __version__ as pillow_version
from run_demo import annotate, postprocess

PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = Path('/opt/qairt-isolated/2.51.40.260930')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def inside(relative):
    path = (PACKAGE / relative).resolve()
    if PACKAGE not in path.parents:
        raise ValueError('Package path outside the bundle: ' + str(relative))
    return path


def verify_package():
    manifest = json.loads((PACKAGE / 'MANIFEST.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        if sha(inside(name)) != digest:
            raise ValueError('Changed or incomplete offline file: ' + name)
    return manifest


def environment(runtime):
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = str(runtime / 'lib') + ':/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu'
    env['ADSP_LIBRARY_PATH'] = str(runtime / 'dsp') + ';/usr/lib/rfsa/adsp;/dsp;/usr/lib'
    return env


def runtime_snapshot(runtime):
    return {str(p): sha(p) for sub in ('bin', 'lib', 'dsp')
            for p in sorted((runtime / sub).rglob('*')) if p.is_file()}


def check(runtime, manifest):
    if platform.machine().lower() not in ('aarch64', 'arm64'):
        raise RuntimeError('Run this offline bundle on the ARM64 target')
    for relative in ('bin/qnn-net-run', 'bin/qnn-profile-viewer', 'lib/libQnnHtp.so', 'lib/libQnnModelDlc.so'):
        if not (runtime / relative).is_file():
            raise RuntimeError('Missing prepared QAIRT runtime file: ' + str(runtime / relative))
    if not (runtime / 'dsp').is_dir():
        raise RuntimeError('Missing HTP DSP libraries')
    version = subprocess.check_output([str(runtime / 'bin/qnn-net-run'), '--version'],
                                     env=environment(runtime), stderr=subprocess.STDOUT, timeout=30).decode(errors='replace')
    if manifest['runtime_version'] not in version:
        raise RuntimeError('Runtime version differs from reviewed ' + manifest['runtime_version'])
    return dict(result='TARGET_HTP_READY', runtime=str(runtime), version=version.strip(),
                python=platform.python_version(), numpy=np.__version__, pillow=pillow_version,
                cases=len(manifest['cases']), package_files_verified=len(manifest['files']),
                inference_backend='HTP only', cpu_reference='Saved TFLite CPU results; no CPU inference in this runner')


def prepare(spec, model, assets, dest):
    canvas = ImageOps.exif_transpose(Image.open(inside('media/controls/' + spec['image']))).convert('RGB')
    crop = spec.get('crop')
    if crop:
        l, t, r, b = crop
        if not (0 <= l < r <= canvas.width and 0 <= t < b <= canvas.height):
            raise ValueError('Crop outside the selected image')
        canvas = canvas.crop(tuple(crop))
    if spec['task'] == 'gesture' and canvas.width != canvas.height:
        raise ValueError('Gesture needs the reviewed square crop')
    profile = assets['profiles'][spec['task']]
    canvas = canvas.resize(tuple(profile['size']), Image.Resampling.BILINEAR)
    pixels = np.asarray(canvas, dtype=np.float32)
    contract = assets['contracts']['models'][spec['task']]['inputs'][0]
    scale, zero = contract['quantization']
    if model.get('input_mode') == 'pixels_float32':
        tensor = pixels
    else:
        tensor = (pixels - zero) * scale if scale else (pixels - profile.get('mean', 0)) / profile.get('std', 1)
    tensor = tensor[None].astype('<f4')
    tensor.tofile(dest / 'input.raw')
    canvas.save(dest / 'input.png')
    if sha(dest / 'input.raw') != spec['prepared_tensor_sha256']:
        raise ValueError('Target preprocessing differs from the reviewed input; inspect Python/Pillow versions')
    return canvas


def read_outputs(folder, specs):
    files = list((folder / 'Result_0').rglob('*.raw'))
    outputs, used = [], set()
    for spec in specs:
        count = int(np.prod(spec['shape']))
        safe = re.sub(r'[^A-Za-z0-9_.-]', '_', spec['name'])
        matches = [p for p in files if p not in used and p.stat().st_size == count * 4
                   and p.stem in (spec['name'], safe, spec['name'].replace('/', '_').replace(':', '_'))]
        if not matches:
            matches = [p for p in files if p not in used and p.stat().st_size == count * 4]
        if len(matches) != 1:
            raise ValueError('Ambiguous/missing QNN output: ' + spec['name'])
        used.add(matches[0])
        array = np.fromfile(matches[0], dtype='<f4').reshape(spec['shape'])
        if not np.isfinite(array).all():
            raise ValueError('Non-finite QNN output: ' + spec['name'])
        outputs.append(array)
    return outputs


def iou(a, b):
    y0, x0, y1, x1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, y1-y0) * max(0, x1-x0)
    area = lambda r: max(0, r[2]-r[0]) * max(0, r[3]-r[1])
    return float(intersection / max(area(a)+area(b)-intersection, 1e-12))


def detection_decode(tensors, contracts):
    options = contracts['models']['detection']['nms_options']
    anchors = np.load(inside('assets/ssd_anchors.npy'), allow_pickle=False)
    enc = tensors[0].reshape(-1, 4)
    scores = tensors[1].reshape(len(enc), -1)[:, 1:]
    classes, best = np.argmax(scores, axis=1), np.max(scores, axis=1)
    cy = enc[:, 0] / options['y_scale'] * anchors[:, 2] + anchors[:, 0]
    cx = enc[:, 1] / options['x_scale'] * anchors[:, 3] + anchors[:, 1]
    h = np.exp(np.clip(enc[:, 2] / options['h_scale'], -50, 50)) * anchors[:, 2]
    w = np.exp(np.clip(enc[:, 3] / options['w_scale'], -50, 50)) * anchors[:, 3]
    boxes = np.stack([cy-h/2, cx-w/2, cy+h/2, cx+w/2], axis=1)
    selected = []
    for index in np.argsort(best, kind='stable')[::-1]:
        if best[index] < options['nms_score_threshold']:
            break
        if any(iou(boxes[index], boxes[other]) > options['nms_iou_threshold'] for other in selected):
            continue
        selected.append(int(index))
        if len(selected) >= options['max_detections']:
            break
    return [boxes[selected][None], classes[selected][None].astype(np.float32),
            best[selected][None], np.array([len(selected)], dtype=np.float32)]


def profile(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('Msg Timestamp,'))
    rows = [{k.strip(): v.strip() for k, v in row.items()} for row in csv.DictReader(lines[start:])]
    return dict(
        accelerator_events=sum(r.get('Message') == 'EXECUTE' and 'qnn accelerator' in r.get('Event Identifier', '').lower()
                               and float(r.get('Time') or 0) > 0 for r in rows),
        positive_cycle_events=sum(r.get('Unit of Measurement') == 'CYCLES' and float(r.get('Time') or 0) > 0 for r in rows),
        execute_us=[float(r['Time']) for r in rows if r.get('Message') == 'EXECUTE'
                    and r.get('Timing Source') == 'NETRUN' and r.get('Event Level') == 'ROOT'])


def compare(spec, result, reference, tensors):
    task, expected = spec['task'], spec['expected']
    if task == 'classification':
        ok = result['top3'][0]['class_id'] == reference['top3'][0]['class_id']
        ok &= expected in result['top3'][0]['label'].lower() and expected in reference['top3'][0]['label'].lower()
        return dict(passed=bool(ok), criterion='Same top-1 as saved original CPU and expected cheeseburger')
    if task == 'gesture':
        return dict(passed=result['gesture'] == reference['gesture'] == expected,
                    criterion='Same gesture/presence as saved original CPU and expected label')
    if task == 'detection':
        a = [d for d in result['detections'] if d['label'] == 'person']
        b = [d for d in reference['detections'] if d['label'] == 'person']
        if expected == 'no_person':
            return dict(passed=not a and not b, criterion='No person >=0.5 in HTP or saved CPU reference')
        overlap = max([iou(x['box_yxyx'], y['box_yxyx']) for x in a for y in b] or [0])
        return dict(passed=bool(a and b and overlap >= 0.7 and len(a) <= len(b)+1
                               and len(result['detections']) <= len(reference['detections'])+2),
                    person_box_iou=overlap, criterion='Person IoU >=0.7 versus saved CPU, bounded extra detections')
    if task == 'pose':
        a, b = np.asarray(result['keypoints_yxs']), np.asarray(reference['keypoints_yxs'])
        visible = (a[:, 2] >= 0.5) & (b[:, 2] >= 0.5)
        error = float(np.median(np.linalg.norm(a[visible, :2]-b[visible, :2], axis=1))) if visible.any() else 1.
        ok = result['visible_keypoints'] >= min(5, reference['visible_keypoints']) and error <= 0.12
        if expected == 'full_body':
            ok &= min(result['visible_keypoints'], reference['visible_keypoints']) >= 12
        return dict(passed=bool(ok), median_visible_joint_distance=error,
                    criterion='Visible joint displacement <=0.12; full_body needs >=12 visible points in both')
    a = np.argmax(tensors[0][0], axis=-1) == 15
    b = np.load(inside('references/' + spec['id'] + '.npz'), allow_pickle=False)['person_mask']
    if expected == 'no_person':
        return dict(passed=bool(max(float(a.mean()), float(b.mean())) <= .01),
                    actual_person_fraction=float(a.mean()), criterion='Person fraction <=1% in HTP and saved CPU')
    overlap = float((a & b).sum() / max(1, (a | b).sum()))
    return dict(passed=bool(a.any() and b.any() and overlap >= .70), person_mask_iou=overlap,
                criterion='Person-mask IoU >=0.70 versus saved original CPU')


def command(argv, env, log, timeout=180):
    with log.open('wb') as stream:
        proc = subprocess.run([str(x) for x in argv], env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('QNN command failed, exit %d; see %s. No CPU retry.' % (proc.returncode, log))


def run_case(spec, assets, runtime, dest, runs):
    dest.mkdir()
    model = assets['models'][spec['task']]
    reference = json.loads(inside('references/' + spec['id'] + '.json').read_text(encoding='utf-8'))
    canvas = prepare(spec, model, assets, dest)
    input_list = dest / 'input_list.txt'
    input_list.write_text(model['input_name'] + ':=' + str(dest / 'input.raw') + '\n', encoding='utf-8')
    output, env = dest / 'qnn', environment(runtime)
    argv = [runtime / 'bin/qnn-net-run', '--model', runtime / 'lib/libQnnModelDlc.so',
            '--dlc_path', inside(model['dlc']), '--backend', runtime / 'lib/libQnnHtp.so',
            '--input_list', input_list, '--output_dir', output, '--profiling_level', 'detailed',
            '--log_level', 'info', '--num_inferences', str(runs), '--keep_num_outputs', str(runs)]
    save(dest / 'command.json', dict(argv=[str(x) for x in argv], backend='HTP', cpu_fallback=False))
    command(argv, env, dest / 'inference.log')
    command([runtime / 'bin/qnn-profile-viewer', '--input_log', output / 'qnn-profiling-data_0.log',
             '--output', output / 'profile.csv'], env, dest / 'profile.log', 60)
    placement = profile(output / 'profile.csv')
    if not placement['accelerator_events'] or not placement['positive_cycle_events']:
        raise RuntimeError('No positive HTP accelerator execution evidence')
    tensors = read_outputs(output, model['outputs'])
    if spec['task'] == 'detection':
        tensors = detection_decode(tensors, assets['contracts'])
    task_profile = assets['profiles'][spec['task']]
    labels = inside('labels/' + task_profile['labels']).read_text(encoding='utf-8').splitlines() if 'labels' in task_profile else []
    result = postprocess(spec['task'], tensors, task_profile, labels, .5)
    comparison = compare(spec, result, reference, tensors)
    result.update(dict(case=spec['id'], task=spec['task'], backend='htp', runtime='QAIRT/QNN 2.51.40.260930',
                       model_sha256=sha(inside(model['dlc'])), source_image_sha256=sha(inside('media/controls/'+spec['image'])),
                       prepared_tensor_sha256=sha(dest / 'input.raw'), profile=placement,
                       comparison_to_saved_cpu=comparison, passed=bool(comparison['passed']),
                       execution_location='All preparation, CNN inference, decoding, NMS/rules and rendering on target',
                       cpu_reference='Saved original TFLite CPU output; no live CPU inference',
                       scope='Functional controls on reviewed images. No dataset accuracy or latency benchmark.'))
    save(dest / 'result.json', result)
    np.savez_compressed(dest / 'outputs.npz', **{'output_%d' % i: t for i, t in enumerate(tensors)})
    image = annotate(canvas, result, spec['task'], tensors, task_profile, .5)
    ratio = 768 / max(image.size)
    image = image.resize((round(image.width*ratio), round(image.height*ratio)))
    banner = Image.new('RGB', (image.width, image.height+40), 'white')
    banner.paste(image, (0, 0))
    ImageDraw.Draw(banner).text((8, image.height+12), spec['id']+' / TARGET HTP', fill='black')
    banner.save(dest / 'prediction.png')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', type=Path, default=DEFAULT_RUNTIME)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('list')
    sub.add_parser('check')
    one = sub.add_parser('run')
    one.add_argument('case')
    for parser in (one, sub.add_parser('run-all')):
        parser.add_argument('--runs', type=int, default=3)
        parser.add_argument('--output', type=Path)
    a = p.parse_args()
    manifest = verify_package()
    if a.action == 'list':
        for spec in manifest['cases']:
            print(spec['id'], spec['task'], spec['image'])
        return
    ready = check(a.runtime, manifest)
    if a.action == 'check':
        print(json.dumps(ready, indent=2))
        return
    if not 1 <= a.runs <= 20:
        p.error('--runs must be 1..20')
    cases = [s for s in manifest['cases'] if a.action == 'run-all' or s['id'] == a.case]
    if not cases:
        p.error('Unknown case. Use: sh run.sh list')
    dest = (a.output or PACKAGE / 'runs' / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:5])).resolve()
    dest.mkdir(parents=True, exist_ok=False)
    assets = {name: json.loads(inside('assets/' + filename).read_text(encoding='utf-8'))
              for name, filename in [('models', 'models.json'), ('contracts', 'source-contracts.json'), ('profiles', 'profiles.json')]}
    before = runtime_snapshot(a.runtime)
    records = []
    for spec in cases:
        try:
            result = run_case(spec, assets, a.runtime, dest / spec['id'], a.runs)
            row = dict(case=spec['id'], passed=result['passed'], profile=result['profile'],
                       comparison=result['comparison_to_saved_cpu'], result=str(dest / spec['id'] / 'result.json'))
        except Exception as exc:
            row = dict(case=spec['id'], passed=False, error=type(exc).__name__+': '+str(exc))
            save(dest / spec['id'] / 'failure.json', row)
        records.append(row)
        print(spec['id'], 'PASS' if row['passed'] else 'FAILED', flush=True)
    after = runtime_snapshot(a.runtime)
    unchanged = before == after
    integrity = dict(passed=unchanged, files_checked=len(before), changed=[k for k in set(before)|set(after) if before.get(k) != after.get(k)])
    save(dest / 'runtime-integrity.json', integrity)
    passed = all(r['passed'] for r in records) and unchanged
    summary = dict(status='PASS_TARGET_HTP_CONTROLS' if passed else 'FAILED_TARGET_HTP_CONTROLS',
                   location='target only; no ADB/host calls', cpu_reference='Bundled saved TFLite CPU outputs',
                   fresh_cpu_inferences=0, gpu_inferences=0, cases=len(records), records=records,
                   runtime_integrity=integrity, environment=ready, evidence=str(dest))
    save(dest / 'summary.json', summary)
    print(summary['status'], '\nEVIDENCE', dest, flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        raise SystemExit(1)

"""Compare TFLite CPU/GPU and the same INT8 DLC on SNPE CPU-fixed/HTP."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import sys
import numpy as np
from adb_lab import ROOT, marked_command, remote_exit_status, select_device
from adb_login import resolve_adb, run_shell, transfer
from target_layout import DEFAULT_REMOTE, validate_remote
from snpe_paths import pinned_sdk_root


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', default='adb')
    p.add_argument("--serial")
    p.add_argument("--transport-id")
    p.add_argument('--remote', default=DEFAULT_REMOTE, type=validate_remote)
    p.add_argument('--sdk-root', type=Path, default=pinned_sdk_root(), help='Pinned offline runtime and host profile decoder')
    p.add_argument('--sessions', type=int, default=3)
    p.add_argument('--runs', type=int, default=50)
    p.add_argument('--warmup', type=int, default=10)
    a = p.parse_args()
    if not 1 <= a.sessions <= 10 or not 1 <= a.runs <= 1000 or not 0 <= a.warmup <= 100:
        p.error('Invalid timing count')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    local = ROOT / 'evidence/htp-dsp' / stamp
    local.mkdir(parents=True, exist_ok=False)
    remote = a.remote
    relative = 'evidence/htp-comparison/' + stamp
    a.adb = resolve_adb(a.adb)
    base = [a.adb, *select_device(a.adb, a.serial, a.transport_id)]
    configs = ['tflite_cpu', 'tflite_gpu', 'snpe_cpu_fixed', 'htp']
    records = []

    def execute(args, name):
        command = 'cd ' + remote + ' && ' + ' '.join(shlex.quote(v) for v in args)
        response = run_shell(base, marked_command(command), timeout=180)
        log = response.stdout.decode('utf-8', errors='replace').replace('\r', '')
        (local / (name + '.log')).write_text(log, encoding='utf-8')
        if remote_exit_status(response.returncode, response.stdout):
            raise RuntimeError('Target failed; see ' + str(local / (name + '.log')))
        return log

    for session in range(a.sessions):
        order = configs if session % 2 == 0 else list(reversed(configs))
        for backend in order:
            name = 'session_%d_%s' % (session + 1, backend)
            args = ['sh', 'target/ai.sh']
            if backend.startswith('tflite_'):
                args += ['classification', '--image', 'media/grace_hopper.jpg', '--backend', backend.split('_')[1], '--vendor-c-api', '--threads', '2']
            else:
                args += ['snpe', '--sdk-root', 'runtime/qairt226-ubuntu', '--model', 'models/mobilenet_v1_snpe_int8.dlc',
                         '--image', 'media/grace_hopper.jpg', '--backend', 'cpu' if backend == 'snpe_cpu_fixed' else 'dsp',
                         '--input-mode', 'normalized', '--profiling', 'off']
                if backend == 'snpe_cpu_fixed':
                    args += ['--cpu-fixed-point']
            args += ['--runs', str(a.runs), '--warmup', str(a.warmup), '--output', relative + '/' + name]
            log = execute(args, name)
            if backend == 'tflite_gpu' and not all(v in log for v in ('Initialized OpenCL-based API', 'Created 1 GPU delegate kernels')):
                raise RuntimeError('GPU evidence is missing')
            records.append({'session': session + 1, 'backend': backend, 'name': name})
            print(name, 'PASS', flush=True)
    profile_args = ['sh', 'target/ai.sh', 'snpe', '--sdk-root', 'runtime/qairt226-ubuntu', '--model', 'models/mobilenet_v1_snpe_int8.dlc',
                    '--image', 'media/grace_hopper.jpg', '--backend', 'dsp', '--input-mode', 'normalized', '--runs', '1', '--warmup', '0',
                    '--profiling', 'detailed', '--output', relative + '/profile_htp']
    execute(profile_args, 'profile_htp')
    transfer(base, 'pull', remote + '/' + relative, str(local / 'target'), stdout=subprocess.PIPE)
    by_backend = {name: [] for name in configs}
    vectors = {}
    hashes = {}
    for record in records:
        folder = local / 'target' / record['name']
        if record['backend'].startswith('tflite_'):
            folder /= 'classification'
        files = list(folder.glob('*.json'))
        if len(files) != 1:
            raise RuntimeError('Expected exactly one receipt per session')
        report = json.loads(files[0].read_text())
        by_backend[record['backend']].append(report)
        arrays = list(folder.glob('*.npz'))
        if len(arrays) != 1:
            raise RuntimeError('Expected output tensor archive')
        with np.load(arrays[0], allow_pickle=False) as data:
            values = data[data.files[0]].reshape(-1)
        if values.size != 1001 or not np.isfinite(values).all():
            raise RuntimeError('Invalid classification output')
        vectors[(record['session'], record['backend'])] = values
        hashes.setdefault(record['backend'], set()).add(report['model_sha256'])
        record.update({'result': files[0].relative_to(local).as_posix(), 'median_ms': report['inference_ms_median'],
                       'p95_ms': report['inference_ms_p95'], 'top1': report['top3'][0]})
    assert hashes['tflite_cpu'] == hashes['tflite_gpu']
    assert hashes['snpe_cpu_fixed'] == hashes['htp']
    assert all(len(values) == 1 for values in hashes.values())
    assert len({r['image_sha256'] for reports in by_backend.values() for r in reports}) == 1
    assert all(r['runtime_order'] == ['dsp'] and r['cpu_retry'] is False for r in by_backend['htp'])
    correctness = []
    for session in range(1, a.sessions + 1):
        reference = vectors[(session, 'tflite_cpu')]
        control = vectors[(session, 'snpe_cpu_fixed')]
        for backend in configs[1:]:
            output = vectors[(session, backend)]
            top1_equal = bool(np.argmax(reference) == np.argmax(output))
            if not top1_equal:
                raise RuntimeError('Top-1 changed; inspect output before accepting the demo')
            correctness.append({'session': session, 'backend': backend, 'top1_equal': top1_equal,
                                'max_abs_vs_tflite_cpu': float(np.max(np.abs(output - reference))),
                                'mean_abs_vs_tflite_cpu': float(np.mean(np.abs(output - reference))),
                                'max_abs_vs_same_dlc_cpu': float(np.max(np.abs(output - control)))})
    medians = {backend: statistics.median(r['inference_ms_median'] for r in reports) for backend, reports in by_backend.items()}
    sdk = a.sdk_root
    decoder = sdk / 'bin/x86_64-windows-msvc/snpe-diagview.exe'
    env = dict(__import__('os').environ)
    env['PATH'] = str(sdk / 'lib/x86_64-windows-msvc') + __import__('os').pathsep + env.get('PATH', '')
    profile = local / 'target/profile_htp/SNPEDiag_0.log'
    response = subprocess.run([str(decoder), '--input_log', str(profile), '--output', str(local / 'htp-profile.csv')], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    decoded = response.stdout.decode('utf-8', errors='replace').replace('\r', '')
    (local / 'htp-profile.txt').write_text(decoded, encoding='utf-8')
    placements = re.findall(r'^\s*\d+:.*?:\s*(DSP|CPU)\s*$', decoded, re.MULTILINE)
    if not placements or any(item != 'DSP' for item in placements):
        raise RuntimeError('Profile does not confirm exclusively DSP graph entries')
    summary = {'recorded_at_host_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'model_inference': 'PASS_REFERENCE_IMAGE_HTP',
               'source_model': 'MobileNet V1 from the original reviewed TFLite; converted to a separate INT8 DLC',
               'model_hashes': {key: sorted(values)[0] for key, values in hashes.items()},
               'snpe_htp_runtime': {'result': 'INFERENCE_EXECUTED_DSP_PROFILE_CONFIRMED', 'version': by_backend['htp'][0]['runtime_version'], 'model_loaded': True},
               'sessions_per_backend': a.sessions, 'runs_per_session': a.runs, 'warmup_per_session': a.warmup,
               'median_of_session_medians_ms': medians,
               'speedup_same_dlc_cpu_over_htp': medians['snpe_cpu_fixed'] / medians['htp'],
               'latency_ratio_tflite_cpu_over_htp': medians['tflite_cpu'] / medians['htp'],
               'timing_scope': 'invoke/ExecuteITensors only; excludes preprocessing, output copies, rendering, compilation and ADB',
               'cpu_thread_policy': {'tflite_cpu': '2 threads', 'snpe_cpu_fixed': 'SNPE runtime default'},
               'profile': {'dsp_entries': placements.count('DSP'), 'cpu_entries': placements.count('CPU'), 'includes_input_output_entries': True,
                           'file': 'htp-profile.txt', 'timing_sessions_profiling': 'off; detailed placement collected in a separate run'},
               'correctness': correctness, 'accuracy_scope': 'Top-1 agreement on the supplied image; full numerical differences reported. Not a dataset accuracy benchmark. DLC quantization/runtime differ from the TFLite baselines.',
               'records': records}
    path = local / 'summary.json'
    path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'evidence/htp-dsp/LATEST.json').write_text(json.dumps({'summary': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'median_ms': medians, 'same_dlc_speedup': summary['speedup_same_dlc_cpu_over_htp'], 'profile': summary['profile'], 'summary': str(path)}, indent=2))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()

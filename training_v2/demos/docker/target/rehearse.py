"""D2-03: target integration checks with saved results, no Internet required for runs."""
import datetime as dt
import errno
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path('/opt/qb560d-docker-demo')
IMAGE = 'qb560d-telemetry:1.0.0'
NAME = 'qb560d-docker-demo'
OFFLINE_NAME = 'qb560d-docker-offline'
OUT = ROOT / 'evidence' / ('rehearsal-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(parents=True, exist_ok=False)
checks = []


def command(args, label, expect=0):
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    text = result.stdout.decode('utf-8', errors='replace')
    (OUT / (label + '.log')).write_text(text, encoding='utf-8')
    passed = result.returncode == expect if expect == 0 else result.returncode != 0
    checks.append({'test': label, 'command': args, 'exit_code': result.returncode, 'expected': 'zero' if expect == 0 else 'nonzero', 'passed': passed})
    if not passed:
        raise RuntimeError(label + ': ' + text[-2000:])
    return text


def docker(args, label, expect=0):
    return command(['sh', str(ROOT / 'target/docker.sh')] + args, label, expect)


def remove(name, label):
    probe = subprocess.run(['sh', str(ROOT / 'target/docker.sh'), 'container', 'inspect', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if probe.returncode:
        return
    info = json.loads(probe.stdout)[0]
    if info['Config'].get('Labels', {}).get('com.quectel.training.demo') != 'qb560d-docker':
        raise RuntimeError('Refusing to remove an unrelated container: ' + name)
    docker(['container', 'rm', '-f', name], label)


def start(name, version, network, label):
    return docker(['run', '-d', '--pull', 'never', '--name', name, '--network', network, '--read-only',
                   '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                   '--pids-limit', '64', '--memory', '128m', '-e', 'APP_VERSION=' + version, IMAGE], label)


def http(path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8081' + path, timeout=3) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, None


def healthy(name, label):
    for _ in range(20):
        info = json.loads(docker(['inspect', name], label))[0]
        if info['State'].get('Health', {}).get('Status') == 'healthy':
            return info
        time.sleep(1)
    raise RuntimeError('Healthcheck did not become healthy')


report = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'result': 'FAIL', 'checks': checks,
          'scope': 'one QB560D/BSP; host-network and network-none HTTP app; bridge/NAT, GPU/HTP in containers and cold boot not tested'}
try:
    report['engine'] = json.loads(docker(['info', '--format', '{{json .}}'], 'engine-info'))
    before = json.loads(docker(['image', 'inspect', IMAGE], 'image-before'))[0]
    assert before['Os'] == 'linux' and before['Architecture'] == 'arm64'
    report['image_id'] = before['Id']
    report['image_size_bytes'] = before['Size']
    report['routes_before'] = command(['ip', '-4', 'route', 'show'], 'routes-before')
    for name in (NAME, OFFLINE_NAME):
        probe = subprocess.run(['sh', str(ROOT / 'target/docker.sh'), 'container', 'inspect', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if probe.returncode == 0:
            raise RuntimeError('Container already exists; inspect/clean it explicitly: ' + name)
    observations = []
    for index in range(1, 4):
        prefix = 'session-' + str(index)
        start(NAME, '1.0.0', 'host', prefix + '-start')
        info = healthy(NAME, prefix + '-healthcheck')
        assert info['HostConfig']['ReadonlyRootfs'] and info['HostConfig']['Memory'] == 134217728
        assert info['HostConfig']['PidsLimit'] == 64 and info['Config']['User'] == '65534:65534'
        assert http('/health')[0] == 200 and http('/missing')[0] == 404
        status, telemetry = http('/telemetry')
        assert status == 200 and telemetry['machine'] == 'aarch64' and telemetry['version'] == '1.0.0'
        observations.append(telemetry)
        docker(['logs', NAME], prefix + '-logs')
        docker(['exec', NAME, 'python3', '-c', 'import os; assert os.getuid()==65534; p="/tmp/demo-check"; open(p,"w").write("ok"); print(open(p).read()); print(open("/proc/self/status").read())'], prefix + '-user-tmp-security')
        docker(['exec', '--user', '0', NAME, 'python3', '-c', 'import errno\ntry:\n open("/app/readonly-check","w").write("must fail")\nexcept OSError as e:\n assert e.errno==errno.EROFS, e\n print("PASS: EROFS")\nelse:\n raise RuntimeError("root filesystem writable")'], prefix + '-readonly-root')
        docker(['stop', '--time', '5', NAME], prefix + '-stop')
        try:
            http('/health')
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        else:
            raise RuntimeError('Endpoint still available after stop')
        remove(NAME, prefix + '-remove')
    report['three_sessions'] = observations
    for version in ('1.0.1', '1.0.0'):
        label = 'update-' + version.replace('.', '-')
        start(NAME, version, 'host', label + '-start')
        healthy(NAME, label + '-healthcheck')
        assert http('/telemetry')[1]['version'] == version
        remove(NAME, label + '-remove')
    report['update_rollback'] = 'PASS: configuration APP_VERSION 1.0.0 -> 1.0.1 -> 1.0.0; same immutable image'
    archive = ROOT / 'offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz'
    report['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    command(['sha256sum', '-c', str(ROOT / 'offline/image.sha256')], 'archive-checksum')
    docker(['image', 'rm', IMAGE], 'offline-remove-image')
    docker(['run', '--pull', 'never', '--network', 'none', '--name', OFFLINE_NAME, IMAGE], 'offline-missing-image-rejected', expect=1)
    docker(['load', '-i', str(archive)], 'offline-load')
    after = json.loads(docker(['image', 'inspect', IMAGE], 'image-after-load'))[0]
    assert after['Id'] == before['Id']
    start(OFFLINE_NAME, '1.0.0', 'none', 'offline-start-network-none')
    info = healthy(OFFLINE_NAME, 'offline-healthcheck')
    assert info['HostConfig']['NetworkMode'] == 'none'
    payload = docker(['exec', OFFLINE_NAME, 'python3', '-c', 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8081/telemetry",timeout=2).read().decode())'], 'offline-internal-http')
    assert json.loads(payload)['version'] == '1.0.0'
    report['offline'] = 'PASS: image absent -> --pull never refused -> tar.gz load restores same image ID -> healthy HTTP app with --network none'
    remove(OFFLINE_NAME, 'offline-remove')
    command(['systemctl', 'restart', 'qb560d-docker-demo.service'], 'engine-restart')
    for _ in range(20):
        probe = subprocess.run(['sh', str(ROOT / 'target/docker.sh'), 'info'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if probe.returncode == 0:
            break
        time.sleep(1)
    assert probe.returncode == 0
    assert json.loads(docker(['image', 'inspect', IMAGE], 'image-after-engine-restart'))[0]['Id'] == before['Id']
    report['routes_after'] = command(['ip', '-4', 'route', 'show'], 'routes-after')
    assert report['routes_before'] == report['routes_after']
    report['unit_enabled_state'] = command(['systemctl', 'is-enabled', 'qb560d-docker-demo.service'], 'unit-autostart-disabled', expect=1).strip()
    report['result'] = 'PASS_THREE_SESSIONS_AND_OFFLINE_DEPLOY'
except Exception as exc:
    report['error'] = repr(exc)
    raise
finally:
    for name in (NAME, OFFLINE_NAME):
        remove(name, 'final-cleanup-' + name)
    report['completed_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    (OUT / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': report['result'], 'checks': len(checks), 'summary': str(OUT / 'summary.json'), 'error': report.get('error')}, indent=2))

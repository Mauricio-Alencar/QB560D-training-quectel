"""D2-01: foreground HTTP contract, 404 and endpoint removal after stopping."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
url = 'http://127.0.0.1:8080'
probe = socket.socket()
probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    probe.bind(('127.0.0.1', 8080))
finally:
    probe.close()
process = subprocess.Popen([sys.executable, str(root / 'app/telemetry.py'), '--host', '127.0.0.1', '--port', '8080'])
result = {}
try:
    for attempt in range(30):
        if process.poll() is not None:
            raise RuntimeError('The demo process exited before becoming healthy')
        try:
            with urllib.request.urlopen(url + '/health', timeout=1) as response:
                result['health'] = {'http':response.status, 'body':json.load(response)}
            break
        except urllib.error.URLError:
            time.sleep(0.1)
    else:
        raise RuntimeError('Foreground application did not become healthy')
    assert result['health']['http'] == 200 and result['health']['body']['status'] == 'ok'
    with urllib.request.urlopen(url + '/telemetry', timeout=2) as response:
        result['telemetry'] = {'http':response.status, 'body':json.load(response)}
    assert result['telemetry']['http'] == 200
    assert result['telemetry']['body']['version'] == '1.0.0'
    assert result['telemetry']['body']['machine'] == 'aarch64'
    try:
        urllib.request.urlopen(url + '/missing', timeout=2)
        raise AssertionError('Unknown endpoint unexpectedly succeeded')
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
        result['missing'] = 404
finally:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
try:
    urllib.request.urlopen(url + '/health', timeout=1)
    raise AssertionError('Endpoint still responds after stopping the foreground demo')
except urllib.error.URLError:
    result['stopped_endpoint'] = 'unavailable as expected'
print(json.dumps({'result':'PASS_FOREGROUND_HTTP_LIFECYCLE', **result}, indent=2))

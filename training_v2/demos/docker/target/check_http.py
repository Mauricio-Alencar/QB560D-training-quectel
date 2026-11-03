"""Verify the demo's documented HTTP contract."""
import json
import os
import urllib.error
import urllib.request

observed = {}
for path in ('/health', '/telemetry', '/missing'):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8081' + path, timeout=3) as response:
            status, body = response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        status, body = exc.code, None
    assert status == (404 if path == '/missing' else 200), (path, status)
    if path == '/telemetry':
        assert body['machine'] == 'aarch64' and body['version'] == os.environ.get('EXPECTED_VERSION', '1.0.0'), body
    observed[path] = {'http': status, 'body': body}
print(json.dumps(observed, indent=2))

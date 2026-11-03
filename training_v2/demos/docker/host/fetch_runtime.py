"""Cache official ARM64 Docker static binaries and Buildx for the lab."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'QB560D-Training-Docker'})
        with urllib.request.urlopen(request, timeout=60) as response, path.with_suffix(path.suffix + '.part').open('wb') as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
        path.with_suffix(path.suffix + '.part').replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lock_path = ROOT / 'offline/runtime.lock.json'
    previous = json.loads(lock_path.read_text()) if lock_path.exists() else None
    version = '29.9.2'
    if previous:
        buildx_version = previous['buildx_version']
    else:
        with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/docker/buildx/releases/latest', headers={'User-Agent': 'QB560D-Training-Docker'}), timeout=30) as response:
            buildx_version = json.load(response)['tag_name']
    urls = {
        'docker-' + version + '.tgz': 'https://download.docker.com/linux/static/stable/aarch64/docker-' + version + '.tgz',
        'buildx-' + buildx_version + '.linux-arm64': 'https://github.com/docker/buildx/releases/download/' + buildx_version + '/buildx-' + buildx_version + '.linux-arm64',
    }
    files = {}
    for name, url in urls.items():
        path = ROOT / 'offline/runtime' / name
        digest = fetch(url, path)
        if previous and previous['files'][name]['sha256'] != digest:
            raise ValueError('Cached official artifact hash mismatch: ' + name)
        files[name] = {'url': url, 'sha256': digest, 'bytes': path.stat().st_size}
        print(name, path.stat().st_size, digest, flush=True)
    lock = {'docker_version': version, 'buildx_version': buildx_version, 'architecture': 'aarch64 / linux-arm64', 'hash_scope': 'HTTPS source, local SHA256 pin; not a separate vendor signature', 'files': files}
    lock_path.write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

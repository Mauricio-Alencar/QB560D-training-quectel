"""Read selected members of an official public SDK ZIP via bounded HTTP ranges."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import urllib.request
import zipfile
import zlib


class RemoteFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        request = urllib.request.Request(url, headers={'Range': 'bytes=0-7'})
        with urllib.request.urlopen(request, timeout=45) as response:
            self.size = int(response.headers['Content-Range'].split('/')[-1])
            response.read(8)
        self.position = 0
        self.cache = []

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position

    def read(self, count=-1):
        count = self.size - self.position if count < 0 else min(count, self.size - self.position)
        if count > 256 * 1024 * 1024:
            raise ValueError('Refusing unbounded SDK download')
        if count <= 0:
            return b''
        start = self.position
        self.position += count
        for offset, data in self.cache:
            if offset <= start and start + count <= offset + len(data):
                return data[start - offset:start - offset + count]
        fetch_start = (start // (1024 * 1024)) * (1024 * 1024)
        fetch_end = min(self.size, max(start + count, fetch_start + 1024 * 1024))
        request = urllib.request.Request(self.url, headers={'Range': 'bytes=%d-%d' % (fetch_start, fetch_end - 1)})
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 206:
                raise ValueError('Server ignored Range; refusing full SDK download')
            data = response.read(fetch_end - fetch_start + 1)
        if len(data) != fetch_end - fetch_start:
            raise ValueError('Truncated or oversized range response')
        if len(data) < 16 * 1024 * 1024:
            self.cache.append((fetch_start, data))
            self.cache = self.cache[-40:]
        return data[start - fetch_start:start - fetch_start + count]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', default='2.26.0.240828')
    p.add_argument('--extract-pattern', action='append', default=[])
    p.add_argument('--dest', default=str(Path(__file__).resolve().parents[1] / '.build/sdk-public-2.26'))
    p.add_argument('--mode', choices=['demo', 'conversion'], default='demo')
    a = p.parse_args()
    if a.version != '2.26.0.240828':
        p.error('Only the reviewed release 2.26.0.240828 is pinned by this demo')
    lock = json.loads(Path(__file__).with_name('snpe-runtime.lock.json').read_text())
    prefix = 'qairt/' + a.version + '/'
    a.extract_pattern += ['^' + re.escape(prefix + name) + '$' for name in lock['files']]
    if a.mode == 'conversion':
        a.extract_pattern += [r'/bin/x86_64-windows-msvc/(snpe-onnx-to-dlc|snpe-dlc-info|snpe-dlc-quant\.exe)$', r'/lib/python/qti/(?:__init__\.py|aisw/(?:__init__\.py|(?:converters|dlc_utils)/.*(?:\.py|windows-x86_64/.*38\.pyd)))$']
    url = 'https://softwarecenter.qualcomm.com/api/download/software/qualcomm_neural_processing_sdk/v' + a.version + '.zip'
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    receipts = []
    with zipfile.ZipFile(RemoteFile(url)) as archive:
        entries = [{'name': info.filename, 'bytes': info.file_size, 'compressed': info.compress_size} for info in archive.infolist()]
        (dest / 'index.json').write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')
        for info in archive.infolist():
            if not info.is_dir() and any(re.search(pattern, info.filename) for pattern in a.extract_pattern):
                target = dest / info.filename
                if dest.resolve() not in target.resolve().parents:
                    raise ValueError('Unsafe SDK ZIP member')
                io_target = Path('\\\\?\\' + str(target.resolve())) if os.name == 'nt' else target
                payload = io_target.read_bytes() if io_target.exists() else b''
                if len(payload) != info.file_size or zlib.crc32(payload) != info.CRC:
                    payload = archive.read(info)
                    io_target.parent.mkdir(parents=True, exist_ok=True)
                    io_target.write_bytes(payload)
                relative = info.filename[len(prefix):] if info.filename.startswith(prefix) else ''
                expected = lock['files'].get(relative)
                if expected and hashlib.sha256(payload).hexdigest() != expected['sha256']:
                    raise ValueError('Pinned SDK SHA-256 mismatch: ' + relative)
                receipts.append({'member': info.filename, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
                if len(receipts) % 50 == 0 or not info.filename.endswith('.py'):
                    print('Extracted', len(receipts), info.filename, len(payload), flush=True)
    (dest / 'receipt.json').write_text(json.dumps({'official_public_url': url, 'extracted': receipts}, indent=2) + '\n', encoding='utf-8')
    missing = set(lock['files']) - {row['member'][len(prefix):] for row in receipts}
    if missing:
        raise ValueError('Required members absent: ' + str(sorted(missing)))
    print('Indexed', len(entries), 'entries; extracted', len(receipts))


if __name__ == '__main__':
    main()

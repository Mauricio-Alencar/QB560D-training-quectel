"""Validate the offline cache and stage this demo after authenticated root login."""
import argparse
import hashlib
import json
import shlex
from adb_control import ROOT, add_connection_arguments, record, session_from_args

REMOTE = '/opt/qb560d-docker-demo'


def verify_asset(source, digest, size, label):
    if not source.is_file():
        raise ValueError('Missing offline ' + label + ': ' + str(source) +
                         '; extract the complete training release, not only demos/docker')
    with source.open('rb') as stream:
        pointer = stream.read(128).startswith(b'version https://git-lfs.github.com/spec/v1')
    if pointer:
        raise ValueError('Git LFS pointer instead of offline ' + label +
                         '; download the complete training release or run git lfs pull in the clone')
    if size is not None and source.stat().st_size != size:
        raise ValueError('Incomplete/changed offline ' + label + ': expected ' + str(size) +
                         ' bytes, found ' + str(source.stat().st_size) +
                         '; download and fully extract the complete training release again')
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError('Checksum mismatch for offline ' + label +
                         '; download and fully extract the complete training release again; keep the reviewed lock unchanged')


def verify_local():
    runtime = json.loads((ROOT / 'offline/runtime.lock.json').read_text(encoding='utf-8'))
    checksums = []
    for name, spec in runtime['files'].items():
        source = ROOT / 'offline/runtime' / name
        verify_asset(source, spec['sha256'], spec.get('bytes'), 'runtime ' + name)
        checksums.append(spec['sha256'] + '  offline/runtime/' + name)
    (ROOT / 'offline/runtime.sha256').write_bytes(('\n'.join(checksums) + '\n').encode())
    image = json.loads((ROOT / 'offline/image.lock.json').read_text(encoding='utf-8'))
    archive = ROOT / image['archive']
    verify_asset(archive, image['archive_sha256'], image.get('archive_bytes'), 'image')
    if image['os'] != 'linux' or image['architecture'] != 'arm64':
        raise ValueError('The reviewed image must be linux/arm64')
    return image


def stage(session):
    image = verify_local()
    code = "import os,pathlib\np=pathlib.Path(" + repr(REMOTE) + ")\n"
    code += "assert os.path.realpath(str(p))==str(p), 'Remote path is a symlink'\n"
    code += "if p.exists():\n assert p.is_dir() and (p/'.owner').read_text().strip()=='qb560d-training-docker-v1', 'Unrecognized existing target folder'\n"
    code += "else:\n p.mkdir(); (p/'.owner').write_text('qb560d-training-docker-v1\\n')\n"
    code += "(p/'evidence').mkdir(exist_ok=True)\nprint('OWNED_TARGET_DIRECTORY_READY')"
    status, _, _ = record(session, 'python3 -c ' + shlex.quote(code), 'stage-directory', 30)
    if status:
        raise RuntimeError('Target folder was refused; inspect it before retrying')
    for name in ('app', 'target', 'config', 'offline'):
        session.transfer('push', ROOT / name, REMOTE + '/')
    print('Staged offline resources at', REMOTE)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_connection_arguments(parser)
    args = parser.parse_args()
    verify_local()
    with session_from_args(args) as session:
        stage(session)


if __name__ == '__main__':
    main()

"""Stage the pinned Ubuntu/HTP v68 runtime privately, without replacing BSP files."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
from adb_lab import ROOT, marked_command, remote_exit_status, select_device
from adb_login import resolve_adb, run_shell, transfer
from target_layout import DEFAULT_REMOTE, validate_remote
from snpe_paths import pinned_sdk_root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument("--serial")
    parser.add_argument("--transport-id")
    parser.add_argument('--remote', default=DEFAULT_REMOTE, type=validate_remote)
    parser.add_argument('--sdk-root', type=Path, default=pinned_sdk_root())
    parser.add_argument('--check-only', action='store_true', help='Validate local files without ADB')
    args = parser.parse_args()
    lock = json.loads((Path(__file__).parent / 'snpe-runtime.lock.json').read_text())
    for member, spec in lock['files'].items():
        path = args.sdk_root / member
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError('Missing/changed SDK member; run fetch_snpe_sdk.py: ' + member)
    if args.check_only:
        print('PASS: all pinned SDK demo files')
        return
    args.adb = resolve_adb(args.adb)
    base = [args.adb, *select_device(args.adb, args.serial, args.transport_id)]
    remote = args.remote + '/runtime/qairt226-ubuntu'
    members = [name for name in lock['files'] if name.startswith('lib/aarch64-ubuntu-') or name.startswith('lib/hexagon-v68/')]
    dirs = sorted({str(Path(name).parent).replace('\\', '/') for name in members})
    command = 'mkdir -p ' + ' '.join(shlex.quote(remote + '/' + name) for name in dirs)
    result = run_shell(base, marked_command(command), timeout=30)
    if remote_exit_status(result.returncode, result.stdout):
        raise RuntimeError(result.stdout.decode(errors='replace'))
    for name in members:
        transfer(base, 'push', str(args.sdk_root / name), remote + '/' + name)
    # sha256sum is available in the reviewed BSP. Verify every staged file.
    command = 'cd ' + shlex.quote(remote) + ' && sha256sum ' + ' '.join(shlex.quote(name) for name in members)
    result = run_shell(base, marked_command(command), timeout=30)
    text = result.stdout.decode(errors='replace').replace('\r', '')
    if remote_exit_status(result.returncode, result.stdout):
        raise RuntimeError(text)
    for name in members:
        if lock['files'][name]['sha256'] + '  ' + name not in text:
            raise RuntimeError('Staged hash verification failed: ' + name)
    print('PASS: four matching runtime libraries staged at ' + remote)


if __name__ == '__main__':
    main()

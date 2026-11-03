"""Record authenticated ADB commands; all package paths are relative to this script."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'host'))
from adb_transport import AdbSession, AuthenticationError, select_device

ROOT = Path(__file__).resolve().parents[1]


def add_connection_arguments(parser):
    parser.add_argument('--adb', help='ADB executable; default is the bundled Windows client, then PATH')
    parser.add_argument('--serial', help='Unique ADB serial, when available')
    parser.add_argument('--transport-id', help='Select a listed ADB transport when serials repeat')
    parser.add_argument('--user', default='root', help='Linux login user; root is required')


def session_from_args(args):
    return AdbSession(adb=args.adb, serial=args.serial, transport_id=args.transport_id, user=args.user)


def device(adb=None, serial=None, transport_id=None):
    return select_device(adb, serial, transport_id)[0]


def record(session, command, label, timeout=90):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', label):
        raise ValueError('Invalid evidence label')
    dest = ROOT / 'evidence' / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + label)
    dest.mkdir(parents=True, exist_ok=False)
    timed_out = False
    try:
        result = session.run(command, timeout)
        data, code = result.stdout, result.returncode
    except TimeoutError:
        data, code, timed_out = b'Authenticated command timed out; inspect target before retrying.\n', 124, True
    (dest / 'output.log').write_bytes(data)
    receipt = {'command': session.redact(command.encode()).decode(), 'exit_code': code, 'timed_out': timed_out,
               'identity': session.identity, 'authentication': session.auth, 'host_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    (dest / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(data.decode('utf-8', errors='replace')[-9000:])
    print('Evidence:', dest)
    return code, data, dest


def run(adb, command, label, timeout=90, session=None):
    if session is not None:
        return record(session, command, label, timeout)[0]
    with AdbSession(adb=adb) as connection:
        return record(connection, command, label, timeout)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_connection_arguments(parser)
    sub = parser.add_subparsers(dest='action', required=True)
    execute = sub.add_parser('run')
    execute.add_argument('--command', required=True)
    execute.add_argument('--label', required=True)
    execute.add_argument('--timeout', type=int, default=90)
    sub.add_parser('login', help='Authenticate and prove uid=0 without changing the target')
    for name in ('push', 'pull'):
        transfer = sub.add_parser(name)
        transfer.add_argument('source')
        transfer.add_argument('destination')
    args = parser.parse_args()
    with session_from_args(args) as session:
        if args.action == 'run':
            return record(session, args.command, args.label, args.timeout)[0]
        if args.action == 'login':
            print(json.dumps({'identity': session.identity, 'authentication': session.auth}, indent=2))
            return 0
        session.transfer(args.action, args.source, args.destination)
        return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (AuthenticationError, ValueError, FileNotFoundError, ConnectionError, TimeoutError) as exc:
        print('ERROR:', str(exc), file=sys.stderr)
        sys.exit(1)

"""Collect evidence and the reviewed image from the explicitly selected box."""
import argparse
import datetime as dt
import hashlib
import json
from adb_control import ROOT, add_connection_arguments, session_from_args


def collect(session):
    remote = '/opt/qb560d-docker-demo'
    dest = ROOT / 'evidence/collected' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    dest.mkdir(parents=True, exist_ok=False)
    session.transfer('pull', remote + '/evidence', dest / 'target')
    expected = json.loads((ROOT / 'offline/image.lock.json').read_text(encoding='utf-8'))
    archive = ROOT / expected['archive']
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        session.transfer('pull', remote + '/' + expected['archive'], archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected['archive_sha256']:
        raise ValueError('Host image archive differs from the reviewed offline image')
    summaries = sorted((dest / 'target').glob('rehearsal-*/summary.json'))
    if summaries:
        summary = summaries[-1]
        report = json.loads(summary.read_text(encoding='utf-8'))
        if report['result'] == 'PASS_THREE_SESSIONS_AND_OFFLINE_DEPLOY':
            (ROOT / 'evidence/LATEST.json').write_text(json.dumps({'summary': summary.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(summary.read_bytes()).hexdigest()}, indent=2) + '\n', encoding='utf-8')
    (dest / 'connection.json').write_text(json.dumps({'identity':session.identity, 'authentication':session.auth},indent=2)+'\n',encoding='utf-8')
    print('Collected target evidence at', dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_connection_arguments(parser)
    args = parser.parse_args()
    with session_from_args(args) as session:
        collect(session)


if __name__ == '__main__':
    main()

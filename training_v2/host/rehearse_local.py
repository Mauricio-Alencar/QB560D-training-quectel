"""Repeat the local Day 1/2 core demos. Cellular, iperf and hosted jobs are separate."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import sys
import uuid
from adb_login import AdbSession
from target_layout import DEFAULT_REMOTE, validate_remote

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb')
    parser.add_argument('--serial')
    parser.add_argument('--transport-id')
    parser.add_argument('--remote', default=DEFAULT_REMOTE, type=validate_remote)
    parser.add_argument('--repeat', type=int, choices=[1,2,3], default=3)
    parser.add_argument('--unit-label', default='QB560D-EU')
    args = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    dest = ROOT / 'evidence/regression' / stamp
    dest.mkdir(parents=True)
    remote_output = 'evidence/rv-' + uuid.uuid4().hex[:12]
    report = {'host_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'unit_label':args.unit_label,
              'remote':args.remote, 'result':'FAIL', 'checks':[], 'excluded':['cellular','iperf3','cold boot','hosted AI Hub job','camera','GPU/HTP use their comparison runners']}
    with AdbSession(args.adb, args.serial, args.transport_id) as session:
        report.update(identity=session.identity, authentication=session.auth)

        def run(label, command, timeout=90, required=True):
            response = session.run('cd ' + shlex.quote(args.remote) + ' && ' + command, timeout=timeout)
            logfile = dest / (label + '.log')
            logfile.write_bytes(response.stdout)
            row = {'label':label,'exit_code':response.returncode,'log':logfile.name,'required':required}
            report['checks'].append(row)
            (dest / 'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(label + ': ' + ('PASS' if not response.returncode else 'FAIL'), flush=True)
            return response

        try:
            response = run('D1-01-inventory','sh target/preflight.sh')
            if response.returncode:
                raise RuntimeError('Stage the training payload or run provision_target first')
            run('D1-02-boot-observation','uptime; systemctl --failed --no-pager; journalctl -b -p err -n 30 --no-pager; dmesg | tail -n 40',required=False)
            run('D1-03-logger','sh target/diagnostics.sh')
            run('D2-00-model-hashes','sh target/ai.sh verify')
            run('D2-00-private-Pillow','sh target/ai.sh prepare')
            run('D2-00-model-contracts','sh target/ai.sh inspect',timeout=120)
            run('D2-01-native-C','sh target/application.sh compile')
            for repetition in range(1,args.repeat+1):
                run('D2-01-http-%d'%repetition,'python3 target/rehearse_application.py')
                run('D2-02-systemd-%d'%repetition,'sh target/application.sh rehearse-service')
                for index, name in enumerate(('classification','detection','pose','gesture','segmentation'),5):
                    image = 'media/right_hands.jpg' if name == 'gesture' else 'media/grace_hopper.jpg'
                    argv = ['sh','target/ai.sh',name,'--image',image,'--runs','20','--warmup','3','--threads','2','--output',remote_output+'/'+str(repetition)]
                    if name == 'gesture':
                        argv += ['--crop','360','0','720','360']
                    run('D2-%02d-%s-%d'%(index,name,repetition),' '.join(shlex.quote(value) for value in argv),timeout=120)
            session.transfer('pull',args.remote+'/'+remote_output,dest/'ai')
            report['ai_outputs'] = 'ai/'
            report['result'] = 'PASS_LOCAL_CORE_DEMOS' if all(not row['exit_code'] for row in report['checks'] if row['required']) else 'FAIL_LOCAL_CORE_DEMOS'
        finally:
            (dest / 'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print('Evidence:',dest,flush=True)
    return 0 if report['result'] == 'PASS_LOCAL_CORE_DEMOS' else 1


if __name__ == '__main__':
    sys.exit(main())

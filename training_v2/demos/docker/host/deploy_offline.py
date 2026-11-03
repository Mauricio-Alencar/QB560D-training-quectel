"""Classroom deployment: verify, login, inspect, install, load and test without downloads."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import sys
from adb_control import ROOT, add_connection_arguments, record, session_from_args
from collect import collect
from stage import REMOTE, stage, verify_local


def platform_probe(session):
    code = """import datetime,json,os,platform,shutil,subprocess
tools=['sh','base64','python3','tar','gzip','sha256sum','systemctl','mount','iptables']
result={'uid':os.getuid(),'architecture':platform.machine(),'kernel':platform.release(),'kernel_build':platform.version(),'glibc':subprocess.check_output(['getconf','GNU_LIBC_VERSION'],text=True).strip(),'os_release':open('/etc/os-release').read(),'target_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'free_bytes_opt':shutil.disk_usage('/opt').free,'tools':{name:shutil.which(name) for name in tools},'docker_demo_already_present':os.path.isdir('/opt/qb560d-docker-demo')}
print(json.dumps(result))
assert result['uid']==0 and result['architecture']=='aarch64','Root on an ARM64 target is required'
assert result['kernel']=='5.4.219-perf','Unexpected kernel; validate the BSP before using the classroom image'
assert result['free_bytes_opt']>=2*1024**3,'Keep at least 2 GiB free on /opt for the classroom package'
assert all(result['tools'].values()),'Required BSP tool missing'
assert 'VERSION_ID="20.04"' in result['os_release'],'This package was validated with Ubuntu20.04'
"""
    status, data, _ = record(session, 'python3 -c ' + shlex.quote(code), 'classroom-platform-probe', 30)
    if status:
        raise RuntimeError('Target preflight failed; inspect the saved platform evidence')
    return json.loads(data.decode('utf-8').strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_connection_arguments(parser)
    parser.add_argument('--unit-label', default='classroom-box', help='Physical label of the selected student box')
    parser.add_argument('--validate-only', action='store_true', help='Check local offline files; do not use ADB')
    parser.add_argument('--stop-after-test', action='store_true', help='Remove the demo container after successful tests')
    args = parser.parse_args()
    image = verify_local()
    if args.validate_only:
        print(json.dumps({'result':'PASS_LOCAL_OFFLINE_CACHE','root':str(ROOT),'image':image['image'],'archive_sha256':image['archive_sha256']},indent=2))
        return 0
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    summary_path = ROOT / 'evidence' / ('deployment-' + stamp + '.json')
    summary = {'result':'FAIL','host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'unit_label':args.unit_label,
               'image_id':image['image_id'],'archive_sha256':image['archive_sha256'],'network_downloads':'NONE; only cached local files and ADB'}
    try:
        with session_from_args(args) as session:
            summary['identity'] = session.identity
            summary['authentication'] = session.auth
            summary['platform'] = platform_probe(session)
            stage(session)
            steps = [
                ('install-offline-runtime','sh ' + REMOTE + '/target/install.sh',120),
                ('load-offline-image','sh ' + REMOTE + '/target/demo.sh load',180),
            ]
            for label, command, timeout in steps:
                if record(session, command, label, timeout)[0]:
                    raise RuntimeError('Deployment step failed: ' + label)
            # An existing running container is reused only when owned and using the reviewed image.
            code = """import json,subprocess
d=['sh','/opt/qb560d-docker-demo/target/docker.sh']
name='qb560d-docker-demo'
p=subprocess.run(d+['container','inspect',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if p.returncode:
 print('CREATE')
else:
 c=json.loads(p.stdout)[0]
 assert c['Config'].get('Labels',{}).get('com.quectel.training.demo')=='qb560d-docker','Unrelated container; inspect manually'
 assert c['Image']==""" + repr(image['image_id']) + """,'Existing container uses another image'
 if c['State']['Running']:
  print('REUSE')
 else:
  subprocess.run(['sh','/opt/qb560d-docker-demo/target/demo.sh','stop'],check=True)
  print('CREATE')
"""
            status, data, _ = record(session, 'python3 -c ' + shlex.quote(code), 'owned-container-check', 30)
            if status:
                raise RuntimeError('Existing target container was refused; no replacement was attempted')
            reused = data.decode().strip().endswith('REUSE')
            if not reused and record(session, 'sh ' + REMOTE + '/target/demo.sh run', 'run-classroom-demo', 60)[0]:
                raise RuntimeError('Demo did not start healthy')
            status, output, _ = record(session, 'sh ' + REMOTE + '/target/demo.sh check', 'classroom-http-tests', 30)
            if status:
                raise RuntimeError('Classroom HTTP acceptance failed')
            summary['http'] = json.loads(output.decode().strip())
            summary['deployment'] = 'REUSED_REVIEWED_CONTAINER' if reused else 'CREATED_REVIEWED_CONTAINER'
            if args.stop_after_test:
                if record(session, 'sh ' + REMOTE + '/target/demo.sh stop', 'classroom-stop', 30)[0]:
                    raise RuntimeError('Container cleanup failed')
            summary['final_container_state'] = 'removed' if args.stop_after_test else 'running'
            summary['collected_evidence'] = str(collect(session).relative_to(ROOT))
            summary['result'] = 'PASS_AUTHENTICATED_OFFLINE_CLASSROOM_DEPLOY'
    except Exception as exc:
        summary['error'] = str(exc)
        raise
    finally:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('Deployment record:', summary_path)
    print(json.dumps(summary,indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('ERROR:',str(exc),file=sys.stderr)
        sys.exit(1)

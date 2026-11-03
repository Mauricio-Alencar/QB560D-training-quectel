"""Collect the current firmware inventory over ADB; no target files are installed."""
import argparse,datetime as dt,json,sys
from pathlib import Path
from adb_session import Session
ROOT=Path(__file__).resolve().parent
def collect(session,evidence):
    session.run('id\nuname -a\ncat /etc/os-release\ncommand -v python3\npython3 --version',evidence,'initial')
    output=session.python((ROOT/'inventory_target.py').read_text(encoding='utf-8'),evidence,'inventory',timeout=180)
    report=json.loads(next(line[len('INVENTORY_JSON='):] for line in output.splitlines() if line.startswith('INVENTORY_JSON=')))
    report['host_utc']=dt.datetime.now(dt.timezone.utc).isoformat();report['adb_identity']=session.identity
    (evidence/'inventory.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (ROOT/'LATEST.json').write_text(json.dumps(dict(evidence=__import__('os').path.relpath(evidence.resolve(),ROOT),inventory=__import__('os').path.relpath((evidence/'inventory.json').resolve(),ROOT)),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(os=report['os_release'],kernel=report['identity']['kernel'],python=report['identity']['python'],snpe=report['snpe_api_versions'],qnn=report['runtime_versions'],evidence=str(evidence.resolve())),indent=2))
    return report
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--adb',default=None);p.add_argument('--serial');p.add_argument('--user',default='root');p.add_argument('--evidence',type=Path);a=p.parse_args()
    evidence=a.evidence or ROOT/'evidence'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');evidence.mkdir(parents=True,exist_ok=False)
    with Session(a.adb,a.serial,a.user) as session:collect(session,evidence)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(1)

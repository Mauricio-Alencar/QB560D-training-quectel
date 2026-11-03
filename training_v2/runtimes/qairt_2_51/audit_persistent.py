"""Read-only audit of the persistent target, demo files and original BSP hashes."""
import json,sys
from pathlib import Path
from update_qairt import Adb,DEFAULT_REMOTE,ROOT,environment,require_owner,snapshot,write_json
sys.path.insert(0,str(ROOT.parents[1]/'demos/hand_gesture'))
from gesture_demo import check_demo
def main():
    evidence=ROOT/'evidence/persistent-20261101/final-audit';adb=Adb(None)
    require_owner(adb,DEFAULT_REMOTE,evidence);check_demo(adb,DEFAULT_REMOTE,evidence)
    final=snapshot(adb,evidence,'originals-final')
    adb.shell(environment(DEFAULT_REMOTE)+' '+DEFAULT_REMOTE+'/bin/qnn-net-run --version',evidence,'runtime-version')
    code="import os,json,hashlib,subprocess\nfrom pathlib import Path\np="+repr(DEFAULT_REMOTE)+"\nowner=json.load(open(p+'/ownership.json'))\n"
    code+="hashes={f:hashlib.sha256(open(f,'rb').read()).hexdigest() if os.path.isfile(f) else None for f in owner['original_hashes']}\nassert hashes==owner['original_hashes']\nprocesses=[]\n"
    code+="for f in Path('/proc').glob('[0-9]*/cmdline'):\n try:\n  args=f.read_bytes().split(b'\\0')\n  if any(a.decode(errors='replace')==p+'/bin/qnn-net-run' for a in args):processes.append(f.parent.name)\n except OSError:pass\n"
    code+="result={'runtime':p,'mount':subprocess.check_output(['findmnt','-T',p,'-no','TARGET,SOURCE,FSTYPE,OPTIONS'],text=True).strip(),'originals_unchanged':True,'active_qnn_processes':processes,'legacy_tmp_exists':os.path.lexists('/tmp/update-qiart-251-mobilenet-validation'),'runtime_and_demo_checksums':'PASS','target_bytes':sum(f.stat().st_size for f in Path(p).rglob('*') if f.is_file()),'reboot_tested':False}\nassert not result['legacy_tmp_exists'] and not processes\nprint('AUDIT='+json.dumps(result))"
    output=adb.python(code,evidence,'persistent-filesystem-and-processes')
    record=json.loads(next(l[6:] for l in output.splitlines() if l.startswith('AUDIT=')));write_json(evidence/'audit.json',record)
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()

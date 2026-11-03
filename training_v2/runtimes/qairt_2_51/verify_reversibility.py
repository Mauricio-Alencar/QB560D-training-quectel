"""Exercise removal only on a tiny disposable owned directory, never the validated model tree."""
import datetime as dt,hashlib,json,subprocess,sys
from pathlib import Path
from update_qairt import ROOT,VERSION,Adb,snapshot,validate_remote,write_json
stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
remote=validate_remote("/tmp/update-qiart-251-cleanup-probe-"+stamp)
evidence=ROOT/"evidence"/"reversibility"/stamp
adb=Adb(None)
before=snapshot(adb,evidence,"before-cleanup-probe")
payload=(ROOT/"cleanup_target.py").read_text(encoding="utf-8")
owner=dict(package="update_QIART",version=VERSION,remote=remote,purpose="Disposable removal check only")
create="import os,json,hashlib\np="+repr(remote)+"\nassert not os.path.lexists(p)\nassert os.path.realpath(p)==p\nos.mkdir(p)\n"
create+="open(p+'/cleanup_target.py','w').write("+repr(payload)+")\n"
create+="json.dump("+repr(owner)+",open(p+'/ownership.json','w'))\n"
create+="json.dump([{'path':'cleanup_target.py','sha256':hashlib.sha256(open(p+'/cleanup_target.py','rb').read()).hexdigest()}],open(p+'/files.json','w'))\nprint('DISPOSABLE_PROBE_CREATED')"
adb.python(create,evidence,"create-disposable-probe")
subprocess.run([sys.executable,str(ROOT/"update_qairt.py"),"remove","--remote",remote,"--evidence",str(evidence)],check=True)
adb.python("import os\nassert not os.path.lexists("+repr(remote)+")\nprint('DISPOSABLE_PROBE_REMOVED')",evidence,"confirm-removal")
after=snapshot(adb,evidence,"after-cleanup-probe")
assert before["original_hashes"]==after["original_hashes"]
write_json(evidence/"result.json",dict(status="PASS",removed_only=remote,main_validation_directory_removed=False,originals_unchanged=True))
print("REVERSIBILITY_PASS",evidence)


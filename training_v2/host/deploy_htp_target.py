"""One-time authenticated copy/install of the offline target-only HTP bundle."""
import argparse
import getpass
import hashlib
from pathlib import Path
import shlex

from adb_login import resolve_adb
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'provision_target'))
from adb_session import Session

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/opt/qb560d-ai-htp251'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb');p.add_argument('--serial')
    p.add_argument('--archive',type=Path,default=ROOT/'offline/htp-controls-target.tar.gz')
    a=p.parse_args();digest=hashlib.sha256(a.archive.read_bytes()).hexdigest()
    record=a.archive.with_name(a.archive.name+'.sha256').read_text(encoding='ascii').split()[0]
    if digest!=record:raise ValueError('Archive differs from its SHA-256 file')
    evidence=ROOT/'evidence/vision-controls/target-deploy'/digest[:12];evidence.mkdir(parents=True,exist_ok=True)
    password=getpass.getpass('Target root password (not saved): ')
    with Session(resolve_adb(a.adb),a.serial,password=password) as s:
        guard="from pathlib import Path\nimport json\np=Path("+repr(REMOTE)+")\nassert p.resolve()==p\nr=Path('/opt/qairt-isolated/2.51.40.260930/bin/qnn-net-run')\nassert r.is_file(), 'Prepare the isolated QAIRT runtime first; see provision_target/README.txt'\nowner={'package':'qb560d-ai-htp251-v1'}\nif p.exists():\n assert (p/'.owner.json').is_file() and json.loads((p/'.owner.json').read_text())==owner,'Foreign HTP directory'\nelse:\n p.mkdir();(p/'.owner.json').write_text(json.dumps(owner))\nprint('RECOGNIZED_HTP_DIRECTORY')"
        s.python(guard,evidence,'target-guard')
        remote=REMOTE+'/htp-controls-target.tar.gz';s.push(a.archive,remote)
        install="""import hashlib,json,tarfile
from pathlib import Path,PurePosixPath
root=Path(%r);archive=root/'htp-controls-target.tar.gz';digest=%r
assert root.resolve()==root,'Refusing a target symlink'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest,'Transfer hash mismatch'
dest=root/'htp-controls'
if dest.exists():
 assert not dest.is_symlink() and (dest/'.bundle-sha256').is_file() and json.loads((dest/'MANIFEST.json').read_text()).get('package')=='qb560d-htp-controls-target-v1','Foreign target directory'
 old=(dest/'.bundle-sha256').read_text().strip()
 assert len(old)==64 and all(c in '0123456789abcdef' for c in old)
 if old==digest:print('SAME_OFFLINE_BUNDLE_ALREADY_INSTALLED')
 else:
  previous=root/('htp-controls.previous-'+old[:12]);assert not previous.exists(),'Previous backup already exists'
  dest.rename(previous);print('PREVIOUS_BUNDLE_AND_RESULTS_PRESERVED',previous)
if not dest.exists():
 with tarfile.open(archive,'r:gz') as tar:
  members=tar.getmembers()
  for member in members:
   name=PurePosixPath(member.name)
   assert not name.is_absolute() and '..' not in name.parts and name.parts[0]=='htp-controls' and member.isfile(),'Unsafe archive member'
  tar.extractall(str(root),members=members)
 (dest/'.bundle-sha256').write_text(digest+'\\n')
 print('OFFLINE_TARGET_BUNDLE_INSTALLED')
""" % (REMOTE,digest)
        s.python(install,evidence,'install')
        s.run('sh '+shlex.quote(REMOTE+'/htp-controls/run.sh')+' check',evidence,'native-preflight',60)
    print('TARGET_BUNDLE_READY:',REMOTE+'/htp-controls')
    print('Shell command: cd '+REMOTE+'/htp-controls && sh run.sh run-all')


if __name__=='__main__':
    main()

"""Install only into the bootstrap-owned /opt trees. Called by provision.py apply."""
import hashlib,io,json,os,platform,shutil,stat,subprocess,sys,tarfile,time,zipfile
from pathlib import Path
WORK=Path('/opt/qb560d-workshop');LAB=Path('/opt/qb560d-training-payload');QROOT=Path('/opt/qairt-isolated/2.51.40.260930')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(args,**kw):subprocess.run(list(map(str,args)),check=True,**kw)
def owned(path):
    assert path.resolve()==path and json.loads((path/'.provision-owner.json').read_text())['package']=='qb560d-workshop-bootstrap-v1'
def write(path,text):
    data=text.encode();path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,'Existing file differs: '+str(path)
    else:path.write_bytes(data)
def source_files():
    rows=json.loads((WORK/'downloads/files.json').read_text())
    for row in rows:
        p=WORK/'downloads'/row['name'];assert p.resolve().parent==WORK/'downloads';assert sha(p)==row['sha256'],'Download hash mismatch'
    return rows
def extract_wheel(path,dest):
    with zipfile.ZipFile(path) as z:
        for item in z.infolist():
            p=(dest/item.filename).resolve();assert dest in p.parents and '\\' not in item.filename
            assert not stat.S_ISLNK(item.external_attr>>16),'Unexpected wheel symlink'
        z.extractall(dest)
def python_deps():
    owned(LAB);rows=source_files();wheels=[r for r in rows if r['name'].endswith('.whl')]
    assert len(wheels)==2 and platform.machine()=='aarch64' and sys.version_info[:2]==(3,8)
    identity=hashlib.sha256(json.dumps(wheels,sort_keys=True).encode()).hexdigest()[:16]
    dest=LAB/('.python-deps-'+identity);marker=dest/'provision.json'
    if marker.exists():assert json.loads(marker.read_text())==wheels
    else:
        assert not dest.exists(),'Incomplete private dependency directory exists: '+str(dest)
        dest.mkdir()
        for row in wheels:
            extract_wheel(WORK/'downloads'/row['name'],dest)
        marker.write_text(json.dumps(wheels,indent=2))
    alias=LAB/'.python-deps'
    if alias.exists() or alias.is_symlink():assert alias.is_symlink() and alias.resolve()==dest
    else:alias.symlink_to(dest.name,target_is_directory=True)
    env=os.environ.copy();env['PYTHONPATH']=str(dest)
    run([sys.executable,'-c',"import numpy,PIL,json;assert numpy.__version__=='1.24.4';assert PIL.__version__=='10.4.0';print(json.dumps({'numpy':numpy.__version__,'Pillow':PIL.__version__}))"],env=env)
def ss_binary(deb):
    raw=deb.read_bytes();assert raw.startswith(b'!<arch>\n');pos=8;data=None
    while pos<len(raw):
        header=raw[pos:pos+60];size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
        if name.startswith('data.tar'):data=raw[pos+60:pos+60+size]
        pos+=60+size+(size%2)
    assert data
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        body=archive.extractfile('./bin/ss').read();license=archive.extractfile('./usr/share/doc/iproute2/copyright').read()
    assert body[:6]==b'\x7fELF\x02\x01' and int.from_bytes(body[18:20],'little')==183
    dest=WORK/'tools/ss-5.5.0';dest.mkdir(parents=True,exist_ok=True)
    for name,contents in [('ss',body),('copyright',license)]:
        path=dest/name
        if path.exists():assert path.read_bytes()==contents
        else:path.write_bytes(contents)
    (dest/'ss').chmod(0o755)
    linked=subprocess.check_output(['ldd',str(dest/'ss')],stderr=subprocess.STDOUT,text=True)
    print(linked);assert 'not found' not in linked
    run([dest/'ss','-V'])
def normalize_build_times(source):
    # Some BSPs restore a stale clock even after date -s. Keep the release
    # archive/hash intact and adjust metadata only in our private build copy.
    source=Path(source)
    assert source==WORK/'build/iperf-3.22' and source.resolve()==source
    entries=[(p,p.lstat()) for p in [source]+list(source.rglob('*'))]
    for path,info in entries:
        assert stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),'Unexpected build entry: '+str(path)
        assert path==source or source in path.resolve().parents,'Build path outside source tree'
    ceiling=time.time_ns()-60*1_000_000_000
    shift=max(0,max(info.st_mtime_ns for _,info in entries)-ceiling)
    if shift:
        for path,info in entries:
            os.utime(path,ns=(info.st_atime_ns,info.st_mtime_ns-shift))
    print('BUILD_TIMESTAMPS_OK: '+str(len(entries))+' entries; shifted_ns='+str(shift),flush=True)

def network_tools():
    source_files();ss_binary(WORK/'downloads/iproute2_5.5.0-1ubuntu1_arm64.deb')
    prefix=WORK/'tools/iperf3-3.22';binary=prefix/'bin/iperf3';archive=WORK/'downloads/iperf-3.22.tar.gz'
    if not binary.exists():
        build=WORK/'build';build.mkdir(exist_ok=True);source=build/'iperf-3.22'
        if not source.exists():
            with tarfile.open(archive) as t:
                for item in t.getmembers():
                    p=(build/item.name).resolve();assert build in p.parents and (item.name=='iperf-3.22' or item.name.startswith('iperf-3.22/'))
                    assert item.isfile() or item.isdir(),'Unexpected source link'
                t.extractall(build)
        normalize_build_times(source)
        env=os.environ.copy();(WORK/'tmp').mkdir(exist_ok=True);env['TMPDIR']=str(WORK/'tmp')
        run(['./configure','--prefix='+str(prefix),'--disable-shared','--enable-static','--without-openssl'],cwd=source,env=env)
        run(['make','-j2'],cwd=source,env=env);run(['make','install'],cwd=source,env=env)
        (prefix/'source.sha256').write_text(sha(archive)+'\n')
    assert (prefix/'source.sha256').read_text().strip()==sha(archive)
    version=subprocess.check_output([str(binary),'--version'],stderr=subprocess.STDOUT,text=True)
    assert 'iperf 3.22' in version
    assert '--bind-dev' in subprocess.check_output([str(binary),'--help'],stderr=subprocess.STDOUT,text=True)
    print(version)
def wrappers():
    directory=WORK/'bin';directory.mkdir(exist_ok=True)
    commands={'iperf3':'exec '+str(WORK/'tools/iperf3-3.22/bin/iperf3')+' "$@"','ss':'exec '+str(WORK/'tools/ss-5.5.0/ss')+' "$@"','docker':'exec sh /opt/qb560d-docker-demo/target/docker.sh "$@"'}
    for name in ['qnn-net-run','snpe-net-run','qnn-platform-validator','qnn-profile-viewer']:
        commands[name]='exec env LD_LIBRARY_PATH="'+str(QROOT)+'/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu" ADSP_LIBRARY_PATH="'+str(QROOT)+'/dsp;/usr/lib/rfsa/adsp;/dsp;/usr/lib" '+str(QROOT/'bin'/name)+' "$@"'
    for name,command in commands.items():
        p=directory/name;write(p,'#!/bin/sh\n'+command+'\n');p.chmod(0o755)
    write(WORK/'env.sh','export PATH="/opt/qb560d-workshop/bin:$PATH"\nexport QAIRT_ROOT=/opt/qairt-isolated/2.51.40.260930\nexport QB560D_LAB=/opt/qb560d-training-payload\n')
if __name__=='__main__':
    if not __debug__:raise RuntimeError('Do not run the target installer with Python optimization (-O)')
    assert os.geteuid()==0;owned(WORK)
    action=sys.argv[1]
    if action=='python':python_deps()
    elif action=='network':network_tools()
    elif action=='wrappers':wrappers()
    else:raise ValueError('Unknown installation step')

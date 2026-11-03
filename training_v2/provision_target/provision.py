"""Reproducible host-driven preparation. Default action plans only; apply installs."""
import argparse,datetime as dt,hashlib,importlib,io,json,os,shlex,subprocess,sys,tarfile,urllib.request,uuid
from pathlib import Path
from adb_session import Session,RuntimeAdapter
from inspect_device import collect
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;WORK='/opt/qb560d-workshop';LAB='/opt/qb560d-training-payload';DOCKER='/opt/qb560d-docker-demo';QROOT='/opt/qairt-isolated/2.51.40.260930'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,obj):Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def local_reference(value):
    path=Path(value)
    return path if path.is_absolute() else ROOT/path

def latest():return local_reference(read(ROOT/'LATEST.json')['inventory'])
def stamp():return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
def rows(folder):return [p for p in Path(folder).rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix!='.pyc']
def fingerprint(inv):
    return dict(os=inv['os_release'].get('VERSION_ID'),arch=inv['identity']['architecture'],glibc=inv['identity']['glibc'],python_minor=inv['identity']['python'].split()[0].rsplit('.',1)[0],bsp=inv['build_files'].get('/etc/build_version'),kernel=inv['identity']['kernel'],vendor_hashes={r['path']:r['sha256'] for r in inv['ai_libraries'] if r['path'].startswith('/usr/') and 'sha256' in r})
def modules():
    sys.path.insert(0,str(REPO/'runtimes/qairt_2_51'));q=importlib.import_module('update_qairt')
    sys.path.insert(0,str(REPO/'demos/hand_gesture'));h=importlib.import_module('gesture_demo');return q,h
def prepare(offline):
    q,h=modules()
    if offline:q.download(True)
    else:q.download(False)
    if offline:h.check_assets()
    else:subprocess.run([sys.executable,str(REPO/'demos/hand_gesture/download_gesture.py')],check=True)
    subprocess.run([sys.executable,str(REPO/'ai/fetch_models.py'),'--verify'],check=True)
    if not offline:subprocess.run([sys.executable,str(REPO/'demos/docker/host/fetch_runtime.py')],check=True)
    for row in read(ROOT/'sources.lock.json'):
        p=ROOT/'cache'/row['name']
        if not p.exists():
            if offline:raise RuntimeError('Offline cache missing: '+str(p))
            req=urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0 QB560D-training'})
            with urllib.request.urlopen(req,timeout=90) as response:data=response.read(40*1024*1024)
            assert hashlib.sha256(data).hexdigest()==row['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        assert sha(p)==row['sha256'],'Download hash mismatch: '+str(p)
    files=[]
    def add(path,component):files.append(dict(path=Path(path).relative_to(REPO).as_posix(),component=component,sha256=sha(path),bytes=Path(path).stat().st_size))
    for row in q.check_lock()['files']:add(REPO/'runtimes/qairt_2_51'/row['path'],'qairt')
    for component,names in [('docker',['app','target','config','offline']),('training',['target','config','app','ai','models','media','wheelhouse'])]:
        base=(REPO/'demos/docker' if component=='docker' else REPO)
        for name in names:
            for p in rows(base/name):add(p,component)
    lock=read(REPO/'demos/docker/offline/runtime.lock.json')
    for name,spec in lock['files'].items():assert sha(REPO/'demos/docker/offline/runtime'/name)==spec['sha256']
    image=read(REPO/'demos/docker/offline/image.lock.json');image_path=REPO/'demos/docker/offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz'
    assert image_path.is_file(),'Offline container image is missing from the training package'
    assert sha(image_path)=='cd0c23929d9b698a1e824d1f735cad94112c9eeef6e9e1b60648e13ccc638550'
    for p in rows(REPO/'demos/hand_gesture/assets'):add(p,'gesture')
    for row in read(ROOT/'sources.lock.json'):add(ROOT/'cache'/row['name'],'network-and-python')
    add(REPO/'wheelhouse/pillow-10.4.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl','network-and-python')
    for folder in [ROOT,REPO/'runtimes/qairt_2_51',REPO/'demos/hand_gesture']:
        for p in folder.glob('*.py'):add(p,'installer')
    for p in [ROOT/'sources.lock.json',REPO/'runtimes/qairt_2_51/versions.lock.json',REPO/'demos/hand_gesture/assets.lock.json']:
        add(p,'installer-metadata')
    for p in [REPO/'host/adb_transport.py',REPO/'host/provision_session.py',ROOT/'setup_host.ps1',REPO/'runtimes/qairt_2_51/requirements-host.txt']:
        add(p,'host-support')
    save(ROOT/'bundle-manifest.json',dict(schema=1,files=files,total_bytes=sum(r['bytes'] for r in files)))
    print('HOST_ONLY_PREPARED: '+str(len(files))+' locked files; '+str(sum(r['bytes'] for r in files))+' bytes')
def plan(inventory,output):
    inv=read(inventory);fp=fingerprint(inv)
    blockers=[]
    if inv['os_release'].get('ID')!='ubuntu' or fp['os']!='20.04' or fp['arch']!='aarch64' or fp['python_minor']!='3.8' or fp['glibc']!=['glibc','2.31']:blockers.append('This prepared profile requires Ubuntu 20.04 / AArch64 / Python 3.8 / glibc 2.31')
    if inv['identity']['uid']!=0:blockers.append('Root session required for /opt and the Docker unit')
    for tool in ['python3','sh','base64','tar','gzip','gcc','make','systemctl','sha256sum','findmnt']:
        if not inv['tools'].get(tool,{}).get('path'):blockers.append('Missing base firmware prerequisite: '+tool)
    for name,paths in inv.get('system_libraries_for_ss',{}).items():
        if not paths:blockers.append('ss requires existing firmware library: '+name)
    if 'system_libraries_for_ss' not in inv:blockers.append('Refresh inventory to check ss runtime libraries')
    headers=inv.get('compiler_headers',{})
    if not headers.get('/usr/include/stdio.h') or not headers.get('/usr/include/pthread.h') or not (headers.get('/usr/include/sys/socket.h') or headers.get('/usr/include/aarch64-linux-gnu/sys/socket.h')):blockers.append('C development headers required for the iperf3 native build')
    if 'noexec' in inv['mounts']['/opt']['output']:blockers.append('/opt is mounted noexec')
    manifest=ROOT/'bundle-manifest.json'
    result=dict(schema=1,status='READY_TO_REVIEW' if not blockers else 'BLOCKED',installation_executed=False,inventory=Path(os.path.relpath(Path(inventory).resolve(),ROOT)).as_posix(),inventory_sha256=sha(inventory),firmware_fingerprint=fp,bundle_manifest_sha256=sha(manifest) if manifest.exists() else None,blockers=blockers,steps=[dict(component='network tools',software=['iperf3 3.22 (native build, OpenSSL auth disabled)','ss from Ubuntu iproute2 5.5.0-1ubuntu1 ARM64'],destination=WORK,why='iperf3 --bind-dev for D1-06; optional socket diagnostics',method='Host downloads, ADB transfer, build iperf3 with existing gcc/make, extract only ss without dpkg install'),dict(component='native AI demos',software=['NumPy 1.24.4 CP38 ARM64','Pillow 10.4.0 CP38 ARM64','five models, images and training source'],destination=LAB,why='Private modules satisfy target requirements; retain system NumPy 1.17.4 and TFLite C API 2.8.4',method='Extract pinned wheels into a private PYTHONPATH; no target pip'),dict(component='Docker workshop',software=['Docker Engine/CLI 29.9.2','containerd 2.4.2','runc 1.5.2','Buildx v0.38.1','qb560d-telemetry:1.0.0 Linux ARM64 image'],destination=DOCKER,why='D2-03 build and offline deploy',method='Existing static-runtime package, private daemon/socket/data and its own systemd unit; no autostart at boot'),dict(component='QAIRT workshop',software=['QAIRT/QNN/SNPE 2.51.40.260930230134 ARM64','HTP v68 stubs/skeletons','MobileNet V2 w8a8','MediaPipe three-DLC hand gesture model'],destination=QROOT,why='Current AI Hub / QNN CPU and HTP workflow',method='Existing isolated updater through authenticated ADB adapter; per-process library paths')],existing_reused=['Ubuntu, kernel, glibc, Python, gcc/g++, make, systemd/journald, curl, ip/ping, GStreamer/V4L2, TFLite C API, FastRPC/OpenCL'],not_required_on_target=['pip/venv','PyTorch','TensorFlow Python','ONNX Runtime','OpenCV Python','Git','CMake','Docker Compose'],validation=['private NumPy/Pillow import and five-model contract inspection','iperf3 --version/--bind-dev and short loopback-only client/server test','ss -V and ss -lnt','Docker daemon, image load, one HTTP demo cycle then stop container','MobileNet CPU/HTP plus seven hand gesture photos on HTP','before/after vendor-library hashes'],scope='Preparation plan for this measured BSP. No OS upgrade, package database repair, modem/WLAN/route change, global library replacement or automatic reboot.')
    result['bundle_prepared']=manifest.exists()
    result['clock_step']='Do not change the system clock. Normalize future timestamps only in the private /opt/qb560d-workshop/build/iperf-3.22 source copy, preserving relative file times and the downloaded archive hash.'
    result['new_firmware_installation_validation']='NOT_RUN: this task collects evidence and prepares the plan/cache only'
    save(output,result);print(json.dumps(result,indent=2));return result
def check_bundle(plan_record):
    path=ROOT/'bundle-manifest.json';assert path.exists(),'Run prepare first'
    assert sha(path)==plan_record['bundle_manifest_sha256'],'Bundle changed; regenerate and review the plan'
    for row in read(path)['files']:assert sha(REPO/row['path'])==row['sha256'],'Host file changed: '+row['path']
def own(session,dest,evidence,adopt_docker=False):
    code="import os,json\nfrom pathlib import Path\np=Path("+repr(dest)+")\nassert p.resolve()==p\nm=p/'.provision-owner.json'\nowner={'package':'qb560d-workshop-bootstrap-v1'}\n"
    code+="if p.exists():\n assert (m.is_file() and json.load(open(m))==owner)"+(" or (p/'.owner').read_text().strip()=='qb560d-training-docker-v1'" if adopt_docker else '')+", 'Foreign /opt directory'\nelse:p.mkdir(parents=True)\nm.write_text(json.dumps(owner))\nprint('OWNED '+str(p))"
    session.python(code,evidence,'own-'+Path(dest).name)
def stage_files(session,base,dest,files,evidence):
    # Refuse changed existing source files, but allow untracked runtime data/results.
    specs=[dict(path=p.relative_to(base).as_posix(),sha256=sha(p)) for p in files]
    code="import os,hashlib\nfrom pathlib import Path\np=Path("+repr(dest)+")\nrows="+repr(specs)+"\nfor r in rows:\n f=p/r['path']\n assert str(f.resolve()).startswith(str(p)+'/')\n assert not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256'], 'Target file differs: '+str(f)\nprint('TARGET_SOURCE_GUARD_OK')"
    session.python(code,evidence,'guard-'+Path(dest).name)
    # Archive only manifest-listed files. Never upload __pycache__, evidence or host tools.
    expected={r['path']:r['sha256'] for r in read(ROOT/'bundle-manifest.json')['files']}
    archive=ROOT/'cache'/('payload-'+Path(dest).name+'.tar')
    with tarfile.open(archive,'w') as t:
        for p in files:
            contents=p.read_bytes();assert hashlib.sha256(contents).hexdigest()==expected[p.relative_to(REPO).as_posix()]
            info=tarfile.TarInfo(p.relative_to(base).as_posix());info.size=len(contents);info.mode=0o644;t.addfile(info,io.BytesIO(contents))
    remote=WORK+'/downloads/'+archive.name;session.push(archive,remote)
    code="import hashlib,tarfile\nfrom pathlib import Path\np=Path("+repr(dest)+");archive=Path("+repr(remote)+")\nassert hashlib.sha256(archive.read_bytes()).hexdigest()=="+repr(sha(archive))+"\nwith tarfile.open(archive) as t:\n for item in t.getmembers():\n  f=(p/item.name).resolve();assert p in f.parents and item.isfile()\n t.extractall(p)\nprint('PAYLOAD_EXTRACTED')"
    session.python(code,evidence,'extract-'+Path(dest).name)
def apply(a):
    rec=read(a.plan);assert rec['status']=='READY_TO_REVIEW' and not rec['blockers'],'Plan has blockers';check_bundle(rec)
    evidence=ROOT/'evidence'/(stamp()+'-apply');evidence.mkdir(parents=True)
    with Session(a.adb,a.serial,a.user) as session:
        fresh=collect(session,evidence/'before');assert fingerprint(fresh)==rec['firmware_fingerprint'],'Different firmware baseline; create a fresh plan'
        q,h=modules();adapter=RuntimeAdapter(session)
        own(session,WORK,evidence);own(session,LAB,evidence)
        code="from pathlib import Path\np=Path("+repr(WORK)+")\nassert __import__('shutil').disk_usage(p).free>1500*1024*1024\n(p/'downloads').mkdir(exist_ok=True)\nprint('SPACE_OK')";session.python(code,evidence,'space')
        assets=read(ROOT/'sources.lock.json');wheel=REPO/'wheelhouse/pillow-10.4.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl'
        for row in assets:session.push(ROOT/'cache'/row['name'],WORK+'/downloads/'+row['name'])
        session.push(wheel,WORK+'/downloads/'+wheel.name);assets.append(dict(name=wheel.name,sha256=sha(wheel)))
        save(evidence/'files.json',assets);session.push(evidence/'files.json',WORK+'/downloads/files.json');session.push(ROOT/'target_install.py',WORK+'/target_install.py')
        native=[p for name in ['target','config','app','ai','models','media','wheelhouse'] for p in rows(REPO/name)]
        stage_files(session,REPO,LAB,native,evidence)
        session.run('python3 '+WORK+'/target_install.py python',evidence,'install-python',120)
        session.run('python3 '+WORK+'/target_install.py network',evidence,'install-network',600)
        own(session,DOCKER,evidence,True)
        docker_files=[p for name in ['target','config','app','offline'] for p in rows(REPO/'demos/docker'/name)]
        stage_files(session,REPO/'demos/docker',DOCKER,docker_files,evidence)
        session.run("printf 'qb560d-training-docker-v1\\n' > "+DOCKER+'/.owner\nsh '+DOCKER+'/target/install.sh',evidence,'install-docker',180)
        _,status=session.run('test -d '+QROOT,evidence,'qairt-directory-status',10,False)
        if status:q.stage(adapter,QROOT,evidence/'qairt-stage')
        else:q.require_owner(adapter,QROOT,evidence/'qairt-existing')
        h.deploy(adapter,QROOT,evidence/'gesture-deploy')
        session.run('python3 '+WORK+'/target_install.py wrappers',evidence,'install-wrappers',30)
        verify(session,evidence/'verification')
        final=collect(session,evidence/'after');assert fingerprint(final)==rec['firmware_fingerprint'],'Vendor baseline changed'
        save(evidence/'result.json',dict(status='INSTALL_AND_VALIDATION_PASSED',before_fingerprint=fingerprint(fresh),after_fingerprint=fingerprint(final)))
    print('INSTALL_AND_VALIDATION_PASSED: '+str(evidence))
def verify(session,evidence):
    evidence.mkdir(parents=True,exist_ok=True);q,h=modules();adapter=RuntimeAdapter(session)
    required=[WORK+'/env.sh',WORK+'/bin/iperf3',WORK+'/tools/iperf3-3.22/bin/iperf3',WORK+'/bin/ss',DOCKER+'/target/docker.sh',LAB+'/target/ai.sh',QROOT+'/bin/qnn-net-run']
    command='missing=0\nfor file in '+' '.join(shlex.quote(p) for p in required)+'; do\n if [ ! -f "$file" ]; then printf "MISSING: %s\\n" "$file"; missing=1; fi\ndone\n[ "$missing" -eq 0 ]'
    output,status=session.run(command,evidence,'installation-prerequisites',30,False)
    if status:raise RuntimeError('Installation incomplete. '+output.strip()+'\nRun prepare, plan, then apply to complete the installation; verify only checks an installed target.')
    session.run('. '+WORK+'/env.sh\niperf3 --version\niperf3 --help | grep -- --bind-dev\nss -V\nss -lnt',evidence,'network-versions',30)
    # Loopback only, with automatic server stop. No cellular traffic is generated.
    session.run('. '+WORK+'/env.sh\niperf3 -s -1 -B 127.0.0.1 -p 45201 > '+WORK+'/iperf-loopback-server.log 2>&1 &\nprovision_pid=$!\ntrap \'kill "$provision_pid" 2>/dev/null || :\' EXIT\nsleep 1\niperf3 -c 127.0.0.1 -p 45201 -t 1 -J\nwait "$provision_pid"',evidence,'iperf-loopback',20)
    session.run('cd '+LAB+'\nsh target/ai.sh verify\nsh target/ai.sh inspect',evidence,'native-ai-contracts',120)
    session.run('cd '+DOCKER+'\nsh target/docker.sh info\ntrap \'sh target/demo.sh stop\' EXIT\nsh target/demo.sh load\nsh target/demo.sh run\nsh target/demo.sh check',evidence,'docker-offline-http',180)
    q.test(adapter,QROOT,evidence/'mobilenet',5)
    # Keep deep classifier log paths below Windows MAX_PATH in the workshop's
    # long OneDrive root. A unique suffix also prevents target run collisions.
    results=[];run_id=uuid.uuid4().hex[:8]
    for index,(name,label) in enumerate(h.SAMPLES.items(),1):
        results.append(h.run(adapter,QROOT,'htp',h.ROOT/'assets/images'/name,evidence/('g%02d-%s'%(index,run_id)),label))
    save(evidence/'gestures.json',results);assert all(r['passed'] for r in results),'Gesture labels differ on this firmware'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['inspect','prepare','plan','apply','verify','run'],nargs='?',default='plan');p.add_argument('--adb',default=None);p.add_argument('--serial');p.add_argument('--user',default='root');p.add_argument('--offline',action='store_true');p.add_argument('--inventory',type=Path);p.add_argument('--plan',type=Path,default=ROOT/'plan.json');p.add_argument('--command');a=p.parse_args()
    if a.action=='prepare':prepare(a.offline)
    elif a.action=='plan':plan(a.inventory or latest(),a.plan)
    elif a.action=='apply':apply(a)
    else:
        evidence=ROOT/'evidence'/(stamp()+'-'+a.action);evidence.mkdir(parents=True)
        with Session(a.adb,a.serial,a.user) as session:
            if a.action=='inspect':collect(session,evidence)
            elif a.action=='verify':verify(session,evidence)
            else:
                if not a.command:raise ValueError('run requires --command')
                output,_=session.run(a.command,evidence,'run',120);print(output)
if __name__=='__main__':
    if not __debug__:raise RuntimeError('Do not run the bootstrap with Python optimization (-O)')
    try:main()
    except Exception as error:print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

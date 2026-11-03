"""Read-only target inventory. Runs with the firmware's existing Python 3."""
import ctypes,datetime,glob,hashlib,importlib.util,json,mmap,os,platform,re,shutil,subprocess,sys
from pathlib import Path
def read(path,limit=16384):
    try:return Path(path).read_bytes()[:limit].replace(b'\0',b'').decode(errors='replace').strip()
    except OSError:return None
def cmd(args,timeout=8):
    try:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        return dict(exit_code=p.returncode,output=p.stdout.decode(errors='replace')[:24000],truncated=len(p.stdout)>24000)
    except (OSError,subprocess.TimeoutExpired) as e:return dict(exit_code=None,output=str(e))
def module(name):
    code="import importlib,json;m=importlib.import_module("+repr(name)+");print(json.dumps({'version':getattr(m,'__version__',getattr(m,'VERSION',None)),'file':getattr(m,'__file__',None)}))"
    result=cmd([sys.executable,'-c',code],10)
    if result['exit_code']==0:
        try:return dict(available=True,**json.loads(result['output'].splitlines()[-1]))
        except ValueError:pass
    return dict(available=False,error=result['output'][-700:])
tools={}
versions={'python3':['--version'],'gcc':['--version'],'g++':['--version'],'make':['--version'],'cmake':['--version'],'curl':['--version'],'git':['--version'],'iperf3':['--version'],'docker':['--version'],'dockerd':['--version'],'containerd':['--version'],'runc':['--version'],'systemctl':['--version'],'gst-launch-1.0':['--version'],'v4l2-ctl':['--version'],'apt-get':['--version'],'dpkg':['--version'],'tar':['--version'],'unzip':['-v'],'ip':['-Version'],'ss':['-V']}
for name in ['sh','bash','base64','timeout','sha256sum','findmnt','dpkg-deb','logger','journalctl','ping','ldconfig','lsb_release','pip3','python3','gcc','g++','make','cmake','curl','wget','git','iperf3','docker','dockerd','containerd','runc','qnn-net-run','snpe-net-run','qnn-platform-validator','qnn-profile-viewer','systemctl','gst-launch-1.0','v4l2-ctl','apt-get','dpkg','tar','gzip','xz','unzip','ip','ss']:
    p=shutil.which(name);tools[name]=dict(path=p)
    if p and name in versions:tools[name]['version']=cmd([p]+versions[name])
osrelease=read('/etc/os-release');fields={}
for line in (osrelease or '').splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);fields[k]=v.strip('"\'')
libraries=[];executables=[];seen=set()
for root in ['/usr/lib','/usr/lib64','/opt','/vendor/lib64','/lib/aarch64-linux-gnu']:
    if not os.path.isdir(root):continue
    for folder,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in ['site-packages','node_modules','.git','results','evidence','runs']]
        if len(Path(folder).relative_to(root).parts)>=6:dirs[:]=[]
        for name in files:
            p=Path(folder)/name
            if name in ['qnn-net-run','snpe-net-run','qnn-platform-validator','qnn-profile-viewer']:executables.append(str(p))
            if not (name.startswith(('libSNPE','libQnn','libSnpe','libtensorflowlite','libOpenCL','libxdsprpc','libadsprpc')) and '.so' in name):continue
            resolved=str(p.resolve())
            if resolved in seen:continue
            seen.add(resolved)
            try:
                item=dict(path=str(p),realpath=resolved,bytes=p.stat().st_size)
                with p.open('rb') as f:
                    with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
                        item['embedded_versions']=sorted({x.decode() for x in re.findall(rb'(?<![0-9])(?:[12]\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{6,18})(?![0-9])',data)})[:20]
                if name in ['libSNPE.so','libQnnCpu.so','libQnnHtp.so','libQnnSystem.so','libtensorflowlite_c.so']:item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                libraries.append(item)
            except (OSError,ValueError) as e:libraries.append(dict(path=str(p),error=str(e)))
executables=list(dict.fromkeys(executables+[v['path'] for k,v in tools.items() if k in ['qnn-net-run','snpe-net-run'] and v['path']]))
runtime_versions=[]
for exe in executables:
    if Path(exe).name not in ['qnn-net-run','snpe-net-run']:continue
    dirs=[str(Path(exe).parents[1]/'lib'),str(Path(exe).parent),'/usr/lib','/usr/lib/aarch64-linux-gnu']
    for p in Path(exe).parents[1].glob('lib/aarch64*'):dirs.insert(0,str(p))
    env=os.environ.copy();env['LD_LIBRARY_PATH']=':'.join(dirs)
    try:
        p=subprocess.run([exe,'--version'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
        runtime_versions.append(dict(executable=exe,exit_code=p.returncode,output=p.stdout.decode(errors='replace')[:3000]))
    except (OSError,subprocess.TimeoutExpired) as e:runtime_versions.append(dict(executable=exe,error=str(e)))
snpe=[]
for row in libraries:
    if Path(row['path']).name!='libSNPE.so':continue
    code="import ctypes as c,json;l=c.CDLL("+repr(row['path'])+");l.Snpe_Util_GetLibraryVersion.restype=c.c_void_p;l.Snpe_DlVersion_ToString.argtypes=[c.c_void_p];l.Snpe_DlVersion_ToString.restype=c.c_char_p;l.Snpe_DlVersion_Delete.argtypes=[c.c_void_p];v=l.Snpe_Util_GetLibraryVersion();print(l.Snpe_DlVersion_ToString(v).decode());l.Snpe_DlVersion_Delete(v)"
    snpe.append(dict(path=row['path'],probe=cmd([sys.executable,'-c',code],10)))
tflite=cmd([sys.executable,'-c',"import ctypes as c;l=c.CDLL('/usr/lib/libtensorflowlite_c.so');l.TfLiteVersion.restype=c.c_char_p;print(l.TfLiteVersion().decode())"],10)
packages=cmd(['dpkg-query','-W','-f=${binary:Package}\t${Version}\t${db:Status-Abbrev}\n'])
modules={name:module(name) for name in ['numpy','PIL','tflite_runtime','ai_edge_litert','tensorflow','cv2','onnxruntime']}
docker=dict(system_client=tools['docker'],system_version=cmd(['docker','version'],8) if tools['docker']['path'] else None,private_installed=Path('/opt/qb560d-docker-demo/runtime/docker/dockerd').exists(),private_service=cmd(['systemctl','is-active','qb560d-docker-demo.service'],5),system_service=cmd(['systemctl','is-active','docker.service'],5))
mounts={p:cmd(['findmnt','-T',p,'-no','TARGET,SOURCE,FSTYPE,OPTIONS'],5) for p in ['/','/opt','/data','/tmp'] if Path(p).exists()}
devices=sorted(set(sum([glob.glob(p) for p in ['/dev/fastrpc*','/dev/adsprpc*','/dev/video*','/dev/dma_heap/*','/dev/dri/*']],[])))
build={p:read(p) for pattern in ['/etc/*version*','/etc/*release*','/etc/*build*'] for p in glob.glob(pattern) if Path(p).is_file() and Path(p).stat().st_size<16384}
system_libs={n:sorted(set(glob.glob('/lib/aarch64-linux-gnu/'+n)+glob.glob('/usr/lib/aarch64-linux-gnu/'+n)+glob.glob('/lib/'+n)+glob.glob('/usr/lib/'+n))) for n in ['libselinux.so.1','libmnl.so.0','libbsd.so.0','libcap.so.2','libc.so.6','ld-linux-aarch64.so.1']}
result=dict(schema=1,at_target_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity=dict(uid=os.getuid(),user=cmd(['id']),hostname=platform.node(),architecture=platform.machine(),kernel=platform.release(),uname=cmd(['uname','-a']),glibc=platform.libc_ver(),python=sys.version,boot_id=read('/proc/sys/kernel/random/boot_id'),soc_model=read('/proc/device-tree/model')),os_release=fields,os_release_raw=osrelease,lsb_release_raw=read('/etc/lsb-release'),build_files=build,tools=tools,python_modules=modules,ai_libraries=libraries,ai_executables=executables,runtime_versions=runtime_versions,snpe_api_versions=snpe,tflite_c_api_version=tflite,docker=docker,packages=packages,dpkg_audit=cmd(['dpkg','--audit'],10),mounts=mounts,filesystems=read('/proc/filesystems'),cgroups=read('/proc/cgroups'),cgroup_mount=read('/proc/self/cgroup'),devices=devices,system_libraries_for_ss=system_libs,compiler_headers={p:Path(p).is_file() for p in ['/usr/include/stdio.h','/usr/include/pthread.h','/usr/include/sys/socket.h','/usr/include/aarch64-linux-gnu/sys/socket.h']},space=cmd(['df','-h','/','/opt']),opt_entries=sorted(p.name for p in Path('/opt').iterdir()) if Path('/opt').exists() else [],network_tools_only=True)
print('INVENTORY_JSON='+json.dumps(result))

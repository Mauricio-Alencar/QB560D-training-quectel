"""Prepare and validate QAIRT in an owned directory. Never replaces BSP files.
Default action is plan. Python stdlib for download/staging; NumPy/Pillow for image preparation.
"""
import argparse, base64, datetime as dt, hashlib, json, os, re, shlex, shutil, subprocess, sys, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
AUTH_HELPERS=ROOT.parents[1]/'host'
sys.path.insert(0,str(AUTH_HELPERS))
from adb_transport import local_path, resolve_adb, run_shell, transfer
VERSION="2.51.40.260930"
SDK_URL=f"https://softwarecenter.qualcomm.com/api/download/software/sdks/Qualcomm_AI_Runtime_Community/All/{VERSION}/v{VERSION}.zip"
SDK=ROOT/"cache"/"sdk"/"qairt"/VERSION
MODEL=ROOT/"assets"/"model"/"mobilenet_v2-qnn_dlc-w8a8"
BIN_NAMES=["qnn-net-run","qnn-platform-validator","qnn-profile-viewer","snpe-net-run"]
LIB_NAMES=["libSNPE.so","libSnpeHtpV68Stub.so","libSnpeHtpV68CalculatorStub.so","libQnnCpu.so","libQnnHtp.so","libQnnSystem.so","libQnnHtpV68Stub.so","libQnnHtpV68CalculatorStub.so","libQnnHtpPrepare.so","libQnnHtpNetRunExtensions.so","libQnnModelDlc.so","libQnnIr.so","libcalculator.so"]
DSP_NAMES=["libSnpeHtpV68Skel.so","libQnnHtpV68Skel.so","libQnnHtpV68.so","libCalculator_skel.so"]
ORIGINALS=["/usr/lib/libSNPE.so","/usr/lib/aarch64-linux-gnu/snpe-2.12/lib/aarch64_Linux/libSNPE.so","/usr/lib/aarch64-linux-gnu/snpe-2.12/lib/aarch64_Linux/libSnpeHtpV68Stub.so","/usr/lib/aarch64-linux-gnu/snpe-2.12/lib/aarch64_Linux/hexagon-v68/unsigned/libSnpeHtpV68Skel.so"]
DEFAULT_REMOTE=f"/opt/qairt-isolated/{VERSION}"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,obj):
    path=local_path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
def selected():
    for group,names in (("bin/aarch64-ubuntu-gcc9.4",BIN_NAMES),("lib/aarch64-ubuntu-gcc9.4",LIB_NAMES),("lib/hexagon-v68/unsigned",DSP_NAMES)):
        for name in names:yield SDK/group/name
    for name in ("LICENSE.pdf","QAIRT_ReleaseNotes.txt","sdk.yaml"):yield SDK/name
def check_lock():
    lock=json.loads((ROOT/"versions.lock.json").read_text(encoding="utf-8"))
    for row in lock["files"]:
        path=ROOT/row["path"]
        if not path.is_file() or sha(path)!=row["sha256"]:raise ValueError("Missing or changed locked file: "+row["path"])
    return lock
def validate_remote(value):
    allowed=(re.fullmatch(r"/tmp/update-qiart-251-[A-Za-z0-9_-]{4,80}",value) or value==f"/opt/qairt-isolated/{VERSION}")
    if not allowed:raise ValueError("Use /tmp/update-qiart-251-<name> or /opt/qairt-isolated/"+VERSION)
    return value
class Adb:
    def __init__(self,exe,serial=None,transport_id=None):
        exe=resolve_adb(exe)
        output=subprocess.check_output([exe,"devices","-l"],text=True,timeout=15)
        rows=[line.split() for line in output.splitlines()[1:] if len(line.split())>1 and line.split()[1]=="device"]
        if serial:rows=[r for r in rows if r[0]==serial]
        if transport_id is not None:rows=[r for r in rows if "transport_id:"+str(transport_id) in r]
        if len(rows)!=1:raise ValueError("Expected one authorized device; use --serial when needed")
        transport=next((v.split(":",1)[1] for v in rows[0] if v.startswith("transport_id:")),None)
        self.base=[exe,"-t",transport] if transport else [exe,"-s",rows[0][0]]
        self.identity=" ".join(rows[0])
    def shell(self,command,evidence,name,timeout=150,allow_failure=False):
        evidence=local_path(evidence)
        marked=command+"\nqa251_rc=$?\nprintf '\\n__QA251_EXIT__=%s\\n' \"$qa251_rc\"\nexit \"$qa251_rc\""
        try:
            r=run_shell(self.base,"sh -c "+shlex.quote(marked),timeout=timeout)
            output=r.stdout.decode(errors="replace").replace("\r\r\n","\n").replace("\r\n","\n")
            markers=re.findall(r"(?m)^__QA251_EXIT__=(\d+)",output)
            status=int(markers[-1]) if markers else -1
        except (subprocess.TimeoutExpired,TimeoutError) as e:
            output=(getattr(e,"stdout",None) or b"").decode(errors="replace");status=124
        evidence.mkdir(parents=True,exist_ok=True)
        (evidence/(name+".log")).write_text(output,encoding="utf-8")
        write_json(evidence/(name+".json"),dict(command=command,exit_code=status,at_utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        if name.startswith("profile-"):print("Profile extracted:",evidence/(name+".log"),flush=True)
        else:print(output,flush=True)
        if status and not allow_failure:raise RuntimeError(f"{name}: remote exit {status}; see {evidence}")
        return output,status
    def python(self,code,evidence,name):
        encoded=base64.b64encode(code.encode()).decode()
        return self.shell("echo "+encoded+" | base64 -d | /usr/bin/python3",evidence,name)[0]
    def push(self,source,destination):
        transfer(self.base,"push",str(source),destination,timeout=120)
    def pull(self,source,destination):
        Path(destination).mkdir(parents=True,exist_ok=True)
        transfer(self.base,"pull",source,str(destination),timeout=120)
def snapshot(adb,evidence,name):
    code="import hashlib,json,os,platform,subprocess\npaths="+repr(ORIGINALS)+"\n"
    code+="hashes={p:hashlib.sha256(open(p,'rb').read()).hexdigest() if os.path.isfile(p) else None for p in paths}\n"
    code+="print('SNAPSHOT='+json.dumps({'original_hashes':hashes,'architecture':platform.machine(),'kernel':platform.release(),'glibc':platform.libc_ver(),'os_release':open('/etc/os-release').read()}))\n"
    output=adb.python(code,evidence,name)
    result=json.loads(next(line[9:] for line in output.splitlines() if line.startswith("SNAPSHOT=")))
    write_json(evidence/(name+"-data.json"),result)
    return result
def require_owner(adb,remote,evidence):
    code="import json,os\np="+repr(remote)+"\n"
    code+="assert os.path.realpath(p)==p, 'Unexpected remote symlink'\no=json.load(open(p+'/ownership.json'))\n"
    code+="assert o['package']=='update_QIART' and o['version']=="+repr(VERSION)+" and o['remote']==p, 'Ownership mismatch'\n"
    code+="import hashlib\nfor row in json.load(open(p+'/files.json')):\n f=os.path.realpath(p+'/'+row['path'])\n assert f.startswith(p+'/'), 'Unsafe manifest path'\n assert hashlib.sha256(open(f,'rb').read()).hexdigest()==row['sha256'], 'Target checksum mismatch: '+row['path']\nprint('OWNERSHIP_AND_CHECKSUMS_OK')"
    adb.python(code,evidence,"ownership-check")
def environment(remote):
    return "env LD_LIBRARY_PATH="+shlex.quote(remote+"/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu")+" ADSP_LIBRARY_PATH="+shlex.quote(remote+"/dsp;/usr/lib/rfsa/adsp;/dsp;/usr/lib")
def download(offline):
    if not offline:
        import sdk_download
        patterns=["/bin/aarch64-ubuntu-gcc9\\.4/("+ "|".join(map(re.escape,BIN_NAMES))+")$",
                  "/lib/aarch64-ubuntu-gcc9\\.4/("+ "|".join(map(re.escape,LIB_NAMES))+")$",
                  "/lib/hexagon-v68/unsigned/("+ "|".join(map(re.escape,DSP_NAMES))+")$",
                  "/(LICENSE\\.pdf|QAIRT_ReleaseNotes\\.txt|sdk\\.yaml)$"]
        subprocess.run([sys.executable,str(ROOT/"sdk_download.py"),"--url",SDK_URL,"--dest",str(ROOT/"cache"/"sdk"),*sum((["--pattern",p] for p in patterns),[])],check=True)
        subprocess.run([sys.executable,str(ROOT/"download_assets.py")],check=True)
    check_lock()
    subprocess.run([sys.executable,str(ROOT/"prepare_input.py")],check=True)
    print("Host cache verified. No target files changed.")
def stage(adb,remote,evidence):
    check_lock()
    if (evidence/"before-stage.log").exists():raise ValueError("Use a new --evidence folder to preserve the previous staging record")
    fresh="import os,shutil\np="+repr(remote)+"\nassert not os.path.lexists(p), 'Target folder already exists; choose a new --remote'\nassert os.path.realpath(p)==p, 'Unexpected parent symlink'\nparent=os.path.dirname(p)\nwhile not os.path.exists(parent):parent=os.path.dirname(parent)\nassert shutil.disk_usage(parent).free>300*1024*1024, 'Need at least 300 MiB free on the destination filesystem'\nprint('FRESH_TARGET_PATH_OK')"
    adb.python(fresh,evidence,"fresh-target-check")
    before=snapshot(adb,evidence,"before-stage")
    if before["architecture"]!="aarch64":raise ValueError("This bundle is for AArch64 Linux")
    if not re.search(r'^ID=\"?ubuntu\"?$',before["os_release"],re.M):raise ValueError("This bundle was validated for Ubuntu targets")
    if tuple(map(int,before["glibc"][1].split('.')[:2]))<(2,31):raise ValueError("This bundle requires the validated glibc 2.31 baseline or newer")
    payload=ROOT/"cache"/"payload"
    for name in ("bin","lib","dsp","model","input"): (payload/name).mkdir(parents=True,exist_ok=True)
    for folder,names,sub in (("bin/aarch64-ubuntu-gcc9.4",BIN_NAMES,"bin"),("lib/aarch64-ubuntu-gcc9.4",LIB_NAMES,"lib"),("lib/hexagon-v68/unsigned",DSP_NAMES,"dsp")):
        for name in names:shutil.copy2(SDK/folder/name,payload/sub/name)
    for name in ("mobilenet_v2.dlc","metadata.json","labels.txt"):shutil.copy2(MODEL/name,payload/"model"/name)
    shutil.copy2(ROOT/"assets"/"dog_float32_nhwc.raw",payload/"input"/"dog.raw")
    (payload/"input"/"input_list.txt").write_text(remote+"/input/dog.raw\n",encoding="utf-8")
    for source in ("probe_runtime.py","cleanup_target.py"):
        shutil.copy2(ROOT/source,payload/source)
    owner=dict(package="update_QIART",version=VERSION,remote=remote,created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),original_hashes=before["original_hashes"])
    write_json(payload/"ownership.json",owner)
    write_json(payload/"files.json",[dict(path=p.relative_to(payload).as_posix(),sha256=sha(p)) for p in payload.rglob("*") if p.is_file() and p.name!="files.json"])
    # Only a fresh directory may be created. No reuse/overwrite of a different target tree.
    create="import os\np="+repr(remote)+"\nassert not os.path.lexists(p), 'Target folder already exists; choose a new --remote'\nassert os.path.realpath(p)==p, 'Unexpected parent symlink'\nos.makedirs(p,exist_ok=False)\nprint('CREATED '+p)"
    adb.python(create,evidence,"create-isolated-target")
    adb.push(str(payload)+"/.",remote+"/")
    adb.shell("chmod 700 "+remote+"/bin/*\n"+environment(remote)+" "+remote+"/bin/qnn-net-run --version",evidence,"staged-runtime-version")
    after=snapshot(adb,evidence,"after-stage")
    if before["original_hashes"]!=after["original_hashes"]:raise RuntimeError("Original runtime hashes changed during staging")
    write_json(evidence/"stage-result.json",dict(remote=remote,version=VERSION,originals_unchanged=True,device=adb.identity))
def test(adb,remote,evidence,runs):
    evidence=local_path(evidence)
    check_lock();require_owner(adb,remote,evidence)
    if (evidence/"mobilenet-cpu.log").exists():raise ValueError("Use a new --evidence folder to preserve the previous attempt")
    before=snapshot(adb,evidence,"before-test")
    result_id=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    remote_output=remote+"/results/"+result_id
    env=environment(remote)
    failure=None
    try:
        for backend in ("cpu","htp"):
            lib="libQnnCpu.so" if backend=="cpu" else "libQnnHtp.so"
            command="cd "+shlex.quote(remote)+"\n"+env+" /usr/bin/timeout 120s "+remote+"/bin/qnn-net-run --model "+remote+"/lib/libQnnModelDlc.so --dlc_path "+remote+"/model/mobilenet_v2.dlc --backend "+remote+"/lib/"+lib+" --input_list "+remote+"/input/input_list.txt --output_dir "+remote_output+"/"+backend+" --profiling_level detailed --log_level info --num_inferences "+str(runs)+" --keep_num_outputs "+str(runs)
            adb.shell(command,evidence,"mobilenet-"+backend,timeout=140)
        from collect_profiles import collect
        collect(adb,remote,remote_output,evidence)
    except Exception as error:failure=error
    finally:
        collection_error=None
        try:adb.pull(remote_output,evidence/"target")
        except Exception as error:collection_error=str(error)
        after=snapshot(adb,evidence,"after-test")
        unchanged=before["original_hashes"]==after["original_hashes"]
        write_json(evidence/"test-run.json",dict(remote=remote,remote_output=remote_output,result_id=result_id,version=VERSION,runs=runs,originals_unchanged=unchanged,device=adb.identity,execution_pass=failure is None,error=str(failure) if failure else None,collection_error=collection_error))
        if not unchanged:raise RuntimeError("Original runtime hashes changed during test")
    if failure:raise failure
    if collection_error:raise RuntimeError("Could not collect target outputs: "+collection_error)
    subprocess.run([sys.executable,str(ROOT/"analyze_results.py"),"--evidence",str(evidence)],check=True)
    print("Results collected:",evidence)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",nargs="?",default="plan",choices=["plan","download","inspect","stage","test","remove"])
    p.add_argument("--adb",help="Bundled classroom ADB or PATH by default")
    p.add_argument("--serial")
    p.add_argument("--transport-id")
    p.add_argument("--remote",default=DEFAULT_REMOTE)
    p.add_argument("--offline",action="store_true")
    p.add_argument("--runs",type=int,default=5)
    p.add_argument("--evidence",type=Path)
    a=p.parse_args()
    remote=validate_remote(a.remote)
    evidence=a.evidence or ROOT/"evidence"/dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if a.action=="plan":
        print(json.dumps(dict(version=VERSION,source=SDK_URL,target_directory=remote,default_is_read_only=True,changes_system_libraries=False,changes_global_path=False,actions=["download: host only","inspect: target read only","stage: create NEW isolated target folder","test: execute MobileNet CPU/HTP in owned folder","remove: delete only owned isolated folder"]),indent=2));return
    if a.action=="download":download(a.offline);return
    adb=Adb(a.adb,a.serial,a.transport_id)
    if a.action=="inspect":snapshot(adb,evidence,"inspect")
    elif a.action=="stage":stage(adb,remote,evidence)
    elif a.action=="test":
        if not 1<=a.runs<=100:raise ValueError("--runs must be 1..100")
        test(adb,remote,evidence,a.runs)
    else:
        require_owner(adb,remote,evidence)
        adb.shell("/usr/bin/python3 "+remote+"/cleanup_target.py "+shlex.quote(remote),evidence,"remove-isolated-target")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("ERROR:",e,file=sys.stderr);sys.exit(1)


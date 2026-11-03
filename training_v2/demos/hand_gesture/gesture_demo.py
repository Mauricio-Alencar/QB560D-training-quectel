"""Still-image workshop: host geometry, three real QNN DLC graphs on the target."""
import argparse,csv,datetime as dt,io,json,re,shlex,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'runtimes/qairt_2_51'))
sys.path.insert(0,str(ROOT.parents[1]/'host'))
from update_qairt import Adb,DEFAULT_REMOTE,VERSION,environment,require_owner,sha,snapshot,write_json
from adb_transport import local_path
from geometry import LABELS,letterbox,palm_roi,hand_crop,map_landmarks,features64,annotate
MODELS=ROOT/'assets/models/mediapipe_hand_gesture-qnn_dlc-w8a8'
SAMPLES={'closed_fist.jpg':'Closed_Fist','full_open_palm.png':'Open_Palm','pointing_up.jpg':'Pointing_Up','thumbs_down.jpg':'Thumb_Down','thumbs_up.jpg':'Thumb_Up','test_victory.jpg':'Victory','iloveyou.jpg':'ILoveYou'}

def check_assets():
    lock=json.loads((ROOT/'assets.lock.json').read_text(encoding='utf-8'))
    for row in lock:
        if sha(ROOT/'assets'/row['path'])!=row['sha256']:raise ValueError('Changed asset: '+row['path'])
    import zipfile
    with zipfile.ZipFile(ROOT/'assets/gesture-qnn_dlc-w8a8.zip') as z:
        for item in z.infolist():
            if not item.is_dir() and (ROOT/'assets/models'/item.filename).read_bytes()!=z.read(item):raise ValueError('Changed DLC bundle member')

def deploy(adb,remote,evidence):
    require_owner(adb,remote,evidence);check_assets()
    target=remote+'/demos/hand_gesture'
    files=[*MODELS.glob('*'),*(p for p in (ROOT/'assets/images').iterdir() if p.suffix.lower() in ('.jpg','.png'))]
    rows=[dict(path=('models/' if p.parent==MODELS else 'images/')+p.name,sha256=sha(p)) for p in files]
    manifest=dict(package='update_QIART-hand-gesture',runtime_version=VERSION,files=rows)
    code="import os,json,hashlib\np="+repr(target)+"\nm="+repr(manifest)+"\nassert os.path.realpath(p)==p\nif os.path.exists(p):\n old=json.load(open(p+'/ownership.json'))\n assert old['package']==m['package'] and old['runtime_version']==m['runtime_version']\n for r in old['files']:\n  assert r in m['files'], 'Different demo already installed'\n  assert hashlib.sha256(open(p+'/'+r['path'],'rb').read()).hexdigest()==r['sha256']\n print('ALREADY_DEPLOYED' if old==m else 'NEW_DEPLOY')\nelse:\n os.makedirs(p+'/models');os.makedirs(p+'/images');print('NEW_DEPLOY')"
    output=adb.python(code,evidence,'demo-deploy-check')
    if 'NEW_DEPLOY' in output:
        for p,r in zip(files,rows):adb.push(p,target+'/'+r['path'])
        owner=evidence/'ownership.json';write_json(owner,manifest);adb.push(owner,target+'/ownership.json')
    print('Demo installed at '+target,flush=True)

def check_demo(adb,remote,evidence):
    target=remote+'/demos/hand_gesture'
    code="import os,json,hashlib\np="+repr(target)+"\nassert os.path.realpath(p)==p\nm=json.load(open(p+'/ownership.json'))\nassert m['package']=='update_QIART-hand-gesture' and m['runtime_version']=="+repr(VERSION)+"\nfor r in m['files']:\n f=os.path.realpath(p+'/'+r['path'])\n assert f.startswith(p+'/')\n assert hashlib.sha256(open(f,'rb').read()).hexdigest()==r['sha256']\nprint('DEMO_FILES_VERIFIED')"
    adb.python(code,evidence,'demo-files-check')

def profile_summary(path):
    lines=path.read_text(encoding='utf-8-sig').splitlines()
    start=next(i for i,l in enumerate(lines) if l.startswith('Msg Timestamp,'))
    rows=[{k.strip():v.strip() for k,v in row.items()} for row in csv.DictReader(io.StringIO('\n'.join(lines[start:])))]
    execute=[r for r in rows if r['Message']=='EXECUTE']
    root=[float(r['Time']) for r in execute if r['Timing Source']=='NETRUN' and r['Event Level']=='ROOT']
    accelerator=[r for r in execute if 'qnn accelerator' in r['Event Identifier'].lower() and float(r['Time'])>0]
    cycles=[r for r in rows if r['Unit of Measurement']=='CYCLES' and float(r['Time'])>0]
    return dict(execute_us=root,accelerator_events=len(accelerator),positive_cycle_events=len(cycles))

class Runner:
    def __init__(self,adb,remote,backend,evidence):
        self.adb,self.remote,self.backend,self.evidence=adb,remote,backend,evidence
        self.metadata=json.loads((MODELS/'metadata.json').read_text())['model_files'];self.stages=[]
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,160}',evidence.name):raise ValueError('Unsafe run identifier')
        self.job=remote+'/demos/hand_gesture/runs/'+evidence.name
        adb.python("import os\np="+repr(self.job)+"\nassert not os.path.lexists(p)\nos.makedirs(p)",evidence,'new-run')
    def graph(self,name,inputs):
        spec=self.metadata[name+'.dlc'];folder=self.evidence/name;folder.mkdir(parents=True)
        remote_stage=self.job+'/'+name
        self.adb.shell('mkdir '+shlex.quote(remote_stage),folder,'mkdir')
        entries=[]
        for key,inp in inputs.items():
            values=np.asarray(inp,dtype='<f4')
            if list(values.shape)!=spec['inputs'][key]['shape'] or not np.isfinite(values).all():raise ValueError('Input contract mismatch: '+key)
            path=folder/(key+'.raw');values.tofile(path);dest=remote_stage+'/'+path.name
            self.adb.push(path,dest);entries.append(key+':='+dest)
        input_list=folder/'input_list.txt';input_list.write_text(' '.join(entries)+'\n',encoding='utf-8');self.adb.push(input_list,remote_stage+'/input_list.txt')
        env=environment(self.remote);lib='libQnnHtp.so' if self.backend=='htp' else 'libQnnCpu.so'
        args=[self.remote+'/bin/qnn-net-run','--model',self.remote+'/lib/libQnnModelDlc.so','--dlc_path',self.remote+'/demos/hand_gesture/models/'+name+'.dlc','--backend',self.remote+'/lib/'+lib,'--input_list',remote_stage+'/input_list.txt','--output_dir',remote_stage+'/output','--profiling_level','detailed','--log_level','info','--num_inferences','1','--keep_num_outputs','1']
        self.adb.shell(env+' /usr/bin/timeout 120s '+shlex.join(args),folder,'inference',timeout=140)
        self.adb.shell(env+' '+self.remote+'/bin/qnn-profile-viewer --input_log '+remote_stage+'/output/qnn-profiling-data_0.log --output '+remote_stage+'/output/profile.csv',folder,'profile-'+name,timeout=40)
        self.adb.pull(remote_stage+'/output',folder)
        outputs={}
        for key,out in spec['outputs'].items():
            value=np.fromfile(folder/'output/Result_0'/(key+'.raw'),dtype='<f4').reshape(out['shape'])
            if not np.isfinite(value).all():raise ValueError('Non-finite output: '+key)
            outputs[key]=value
        profile=profile_summary(folder/'output/profile.csv')
        if self.backend=='htp' and not profile['positive_cycle_events']:raise RuntimeError('No HTP cycle evidence: '+name)
        self.stages.append(dict(graph=name,backend=lib,profile=profile,model_sha256=sha(MODELS/(name+'.dlc'))))
        return outputs

def run(adb,remote,backend,image_path,evidence,expected=None,palm_threshold=0.75):
    evidence=local_path(evidence)
    image=ImageOps.exif_transpose(Image.open(image_path)).convert('RGB');runner=Runner(adb,remote,backend,evidence)
    tensor,scale,pad=letterbox(image);palm=runner.graph('palm_detector',{'image':tensor})
    corners,details=palm_roi(palm['box_coords'],palm['box_scores'],scale,pad,palm_threshold)
    details['palm_threshold']=palm_threshold
    points=None;label='No_hand';confidence=0.0;probabilities={}
    if corners is not None:
        tensor,inverse,crop=hand_crop(image,corners);crop.save(evidence/'hand_crop.png')
        hand=runner.graph('hand_landmark_detector',{'image':tensor});details['landmark_score']=float(hand['scores'].item());details['handedness']=float(hand['lr'].item())
        if details['landmark_score']>=0.2:
            points=map_landmarks(hand['landmarks'],inverse)
            result=runner.graph('canned_gesture_classifier',{'hand':features64(points,details['handedness']),'mirrored_hand':features64(points,details['handedness'],True)})
            scores=result['Identity'].ravel();idx=int(np.argmax(scores));label=LABELS[idx];confidence=float(scores[idx]);probabilities=dict(zip(LABELS,map(float,scores)))
    annotate(image,points,label,confidence,corners).save(evidence/'prediction.png')
    record=dict(runtime_version=VERSION,runtime=remote,target_run=runner.job,backend=backend,image=str(image_path.resolve()),image_sha256=sha(image_path),prediction=label,confidence=confidence,expected=expected,passed=label==expected if expected else None,probabilities=probabilities,details=details,stages=runner.stages,scope='Three DLC graphs execute on target. Image transforms, ROI and feature assembly execute on host. Single hand, still image.')
    write_json(evidence/'result.json',record);print('PREDICTION '+json.dumps(record),flush=True);return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','deploy','run','test-all'],nargs='?',default='plan');p.add_argument('--adb');p.add_argument('--serial');p.add_argument('--transport-id');p.add_argument('--runtime',default=DEFAULT_REMOTE,choices=[DEFAULT_REMOTE]);p.add_argument('--image',type=Path);p.add_argument('--backend',choices=['cpu','htp','both'],default='htp');p.add_argument('--evidence',type=Path)
    p.add_argument('--palm-threshold',type=float,default=0.75)
    a=p.parse_args()
    if not 0<a.palm_threshold<=1:raise ValueError('Threshold must be in (0,1]')
    if a.action=='plan':print('Runtime: '+a.runtime+'\nModel: MediaPipe-Hand-Gesture-Recognition, QNN DLC w8a8 v0.65.0\nActions: deploy, run --image PATH --backend htp, test-all');return
    check_assets();adb=Adb(a.adb,a.serial,a.transport_id);stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');evidence=local_path(a.evidence or ROOT/'evidence'/stamp);evidence.mkdir(parents=True,exist_ok=True)
    if (evidence/'before-test.log').exists():raise ValueError('Evidence directory already used')
    require_owner(adb,a.runtime,evidence);before=snapshot(adb,evidence,'before-test')
    try:
        if a.action=='deploy':deploy(adb,a.runtime,evidence)
        elif a.action=='run':
            check_demo(adb,a.runtime,evidence)
            if not a.image:raise ValueError('--image is required')
            if a.backend=='both':raise ValueError('run requires cpu or htp')
            stem=re.sub(r'[^A-Za-z0-9._-]','_',a.image.stem)[:80]
            run(adb,a.runtime,a.backend,a.image,evidence/(stamp+'-'+a.backend+'-'+stem),palm_threshold=a.palm_threshold)
        else:
            check_demo(adb,a.runtime,evidence)
            records=[]
            for backend in (('cpu','htp') if a.backend=='both' else (a.backend,)):
                for name,expected in SAMPLES.items():records.append(run(adb,a.runtime,backend,ROOT/'assets/images'/name,evidence/(stamp+'-'+backend+'-'+Path(name).stem),expected,a.palm_threshold))
            write_json(evidence/'summary.json',dict(tested=len(records),passed=sum(bool(r['passed']) for r in records),results=records))
            if not all(r['passed'] for r in records):raise RuntimeError('Some sample labels differ. Inspect summary.json')
    finally:
        after=snapshot(adb,evidence,'after-test');unchanged=before['original_hashes']==after['original_hashes'];write_json(evidence/'system-integrity.json',dict(originals_unchanged=unchanged,before=before['original_hashes'],after=after['original_hashes']))
        if not unchanged:raise RuntimeError('Original system hashes changed')
if __name__=='__main__':
    try:main()
    except Exception as error:print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)

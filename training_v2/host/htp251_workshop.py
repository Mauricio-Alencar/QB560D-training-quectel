"""Isolated five-demo QAIRT 2.51 workshop. Original runtimes/models are read-only."""
import argparse,csv,datetime as dt,getpass,hashlib,json,os,re,shlex,sys,traceback,uuid
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT;PACKAGE=ROOT/'htp251'
REMOTE='/opt/qb560d-ai-htp251';RUNTIME='/opt/qairt-isolated/2.51.40.260930';LAB='/opt/qb560d-training-payload'
sys.path.insert(0,str(REPO/'provision_target'));from adb_session import Session
sys.path.insert(0,str(ROOT/'ai'));from run_demo import postprocess,annotate
PROFILES=json.loads((ROOT/'ai/profiles.json').read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def stamp():return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def snapshot(session,evidence,label):
    code="import hashlib,json\nfrom pathlib import Path\nrequired="+repr([RUNTIME+'/bin',RUNTIME+'/lib',RUNTIME+'/dsp',LAB+'/models'])+"\noptional="+repr([LAB+'/runtime/qairt226-ubuntu',RUNTIME+'/model',RUNTIME+'/demos/hand_gesture/models'])+"\npaths=[Path('/usr/lib/libSNPE.so'),Path('/usr/lib/libtensorflowlite_c.so')];absent={}\nfor root in required+optional:\n p=Path(root)\n if not p.is_dir():\n  assert root in optional, 'Required original tree missing: '+root\n  absent[root]='NOT_INSTALLED';continue\n paths += [f for f in p.rglob('*') if f.is_file()]\nrows={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))};rows.update(absent)\nprint(json.dumps(rows))"
    raw=session.python(code,evidence,label);rows=json.loads(raw);save(evidence/(label+'-hashes.json'),rows);return rows
def own(session,evidence):
    code="import json\nfrom pathlib import Path\np=Path("+repr(REMOTE)+")\nassert p.resolve()==p\nm=p/'.owner.json'\nowner={'package':'qb560d-ai-htp251-v1'}\nif p.exists():\n assert m.is_file() and json.loads(m.read_text())==owner, 'Foreign directory'\nelse:\n p.mkdir();m.write_text(json.dumps(owner))\n(p/'models').mkdir(exist_ok=True);(p/'runs').mkdir(exist_ok=True)\nprint('OWNED_ISOLATED_DEMO_DIRECTORY')"
    session.python(code,evidence,'owned-directory')
def stage(session,task,model,evidence):
    path=PACKAGE/model['dlc'];assert sha(path)==model['dlc_sha256'],'Changed DLC: '+str(path)
    assert PACKAGE.resolve() in path.resolve().parents,'Model path outside the isolated package'
    assert sha(ROOT/'models'/model['source_model'])==model['source_sha256'],'Original source model changed'
    remote=REMOTE+'/models/'+task+'-'+model['dlc_sha256'][:16]+'.dlc'
    code="from pathlib import Path\nimport hashlib\np=Path("+repr(remote)+")\nif p.exists():\n assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(model['dlc_sha256'])+"\n print('ALREADY_STAGED')\nelse:print('NEEDS_UPLOAD')"
    if 'NEEDS_UPLOAD' in session.python(code,evidence,'model-status-'+task):session.push(path,remote)
    code="from pathlib import Path\nimport hashlib\np=Path("+repr(remote)+")\nassert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(model['dlc_sha256'])+"\nprint('MODEL_HASH_OK')"
    session.python(code,evidence,'model-hash-'+task);return remote
def prepare_image(task,image,crop=None,input_mode=None):
    canvas=ImageOps.exif_transpose(Image.open(image)).convert('RGB')
    if crop:
        l,t,r,b=crop
        if not (0<=l<r<=canvas.width and 0<=t<b<=canvas.height):raise ValueError('Crop outside image')
        canvas=canvas.crop(tuple(crop))
    if task=='gesture' and canvas.width!=canvas.height:raise ValueError('Gesture requires an aligned square hand crop; use --crop')
    canvas=canvas.resize(tuple(PROFILES[task]['size']),Image.Resampling.BILINEAR)
    pixels=np.asarray(canvas,dtype=np.float32);contract=json.loads((PACKAGE/'source-contracts.json').read_text())['models'][task]['inputs'][0]
    scale,zero=contract['quantization']
    tensor=pixels if input_mode=='pixels_float32' else ((pixels-zero)*scale if scale else (pixels-PROFILES[task].get('mean',0))/PROFILES[task].get('std',1))
    return canvas,tensor[None].astype('<f4')
def read_outputs(folder,specs):
    files=list((folder/'Result_0').rglob('*.raw'));outputs=[];used=set()
    for spec in specs:
        count=int(np.prod(spec['shape']));safe=re.sub(r'[^A-Za-z0-9_.-]','_',spec['name'])
        matches=[p for p in files if p not in used and p.stat().st_size==count*4 and p.stem in [spec['name'],safe,spec['name'].replace('/','_').replace(':','_')]]
        if not matches:matches=[p for p in files if p not in used and p.stat().st_size==count*4]
        if len(matches)!=1:raise ValueError('Ambiguous/missing output '+spec['name']+': '+str([str(p) for p in files]))
        path=matches[0];used.add(path);array=np.fromfile(path,dtype='<f4').reshape(spec['shape']);assert np.isfinite(array).all();outputs.append(array)
    return outputs
def detection_decode(tensors,threshold=0.5):
    contract=json.loads((PACKAGE/'source-contracts.json').read_text())['models']['detection'];options=contract['nms_options'];anchors=np.load(PACKAGE/'ssd_anchors.npy')
    enc=tensors[0].reshape(-1,4);scores=tensors[1].reshape(len(enc),-1)[:,1:];classes=np.argmax(scores,axis=1);best=np.max(scores,axis=1)
    cy=enc[:,0]/options['y_scale']*anchors[:,2]+anchors[:,0];cx=enc[:,1]/options['x_scale']*anchors[:,3]+anchors[:,1]
    h=np.exp(np.clip(enc[:,2]/options['h_scale'],-50,50))*anchors[:,2];w=np.exp(np.clip(enc[:,3]/options['w_scale'],-50,50))*anchors[:,3]
    boxes=np.stack([cy-h/2,cx-w/2,cy+h/2,cx+w/2],axis=1);selected=[]
    for index in np.argsort(best,kind='stable')[::-1]:
        if best[index]<options['nms_score_threshold']:break
        if any(iou(boxes[index],boxes[other])>options['nms_iou_threshold'] for other in selected):continue
        selected.append(int(index))
        if len(selected)>=options['max_detections']:break
    return [boxes[selected][None],classes[selected][None].astype(np.float32),best[selected][None],np.array([len(selected)],dtype=np.float32)]
def iou(a,b):
    y0=max(a[0],b[0]);x0=max(a[1],b[1]);y1=min(a[2],b[2]);x1=min(a[3],b[3]);intersection=max(0,y1-y0)*max(0,x1-x0);area=lambda r:max(0,r[2]-r[0])*max(0,r[3]-r[1]);return float(intersection/max(area(a)+area(b)-intersection,1e-12))
def profile(path):
    lines=path.read_text(encoding='utf-8-sig').splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('Msg Timestamp,'));rows=[{k.strip():v.strip() for k,v in r.items()} for r in csv.DictReader(lines[start:])]
    return dict(accelerator_events=sum(r.get('Message')=='EXECUTE' and 'qnn accelerator' in r.get('Event Identifier','').lower() and float(r.get('Time') or 0)>0 for r in rows),positive_cycle_events=sum(r.get('Unit of Measurement')=='CYCLES' and float(r.get('Time') or 0)>0 for r in rows),execute_us=[float(r['Time']) for r in rows if r.get('Message')=='EXECUTE' and r.get('Timing Source')=='NETRUN' and r.get('Event Level')=='ROOT'])
def semantic(task,result,reference,tensors,ref_tensors):
    if task=='classification':return dict(passed=result['top3'][0]['class_id']==reference['top3'][0]['class_id'],criterion='same top-1 as original TFLite CPU')
    if task=='gesture':return dict(passed=result['gesture']==reference['gesture'],criterion='same gesture/presence result as original TFLite CPU')
    if task=='detection':
        expected=[d for d in reference['detections'] if d['label']=='person'];actual=[d for d in result['detections'] if d['label']=='person'];overlap=max([iou(a['box_yxyx'],b['box_yxyx']) for a in actual for b in expected] or [0]);return dict(passed=bool(actual and expected and overlap>=0.7 and len(actual)<=len(expected)+1 and len(result['detections'])<=len(reference['detections'])+2),person_box_iou=overlap,criterion='reference person IoU >= 0.7 with bounded extra detections/person duplicates')
    if task=='pose':
        a=np.asarray(result['keypoints_yxs']);b=np.asarray(reference['keypoints_yxs']);visible=(a[:,2]>=0.5)&(b[:,2]>=0.5);error=float(np.median(np.linalg.norm(a[visible,:2]-b[visible,:2],axis=1))) if visible.any() else 1.;return dict(passed=result['visible_keypoints']>=min(5,reference['visible_keypoints']) and error<=0.12,median_visible_joint_distance=error,criterion='visible reference joints retained, median normalized joint displacement <= 0.12')
    a=np.argmax(tensors[0][0],axis=-1)==15;b=np.argmax(ref_tensors[0][0],axis=-1)==15;overlap=float((a&b).sum()/max(1,(a|b).sum()));return dict(passed=bool(a.any() and b.any() and overlap>=0.70),person_mask_iou=overlap,criterion='person mask IoU >= 0.70 against original TFLite CPU')
def render(task,canvas,result,tensors,backend,path):
    rendered=annotate(canvas,result,task,tensors,PROFILES[task],0.5);ratio=768/max(rendered.size);rendered=rendered.resize((round(rendered.width*ratio),round(rendered.height*ratio)))
    banner=Image.new('RGB',(rendered.width,rendered.height+55),'white');banner.paste(rendered,(0,0));draw=ImageDraw.Draw(banner)
    try:font=ImageFont.truetype('arial.ttf',19)
    except OSError:font=ImageFont.load_default()
    label=task+' / QAIRT 2.51 '+backend.upper()
    if task=='gesture':label+=' / '+result['gesture']
    draw.text((10,rendered.height+15),label,fill='black',font=font);banner.save(path)
def run_case(session,task,model,remote_model,image,crop,case,runs,cpu_control=False,quality_check=None):
    case.mkdir(parents=True,exist_ok=True);canvas,tensor=prepare_image(task,image,crop,model.get('input_mode'));canvas.save(case/'input.png');tensor.tofile(case/'input.raw')
    job=REMOTE+'/runs/r'+uuid.uuid4().hex[:14];session.run('mkdir '+shlex.quote(job),case,'run-directory');session.push(case/'input.png',job+'/input.png');session.push(case/'input.raw',job+'/input.raw')
    (case/'input_list.txt').write_text(model['input_name']+':='+job+'/input.raw\n',encoding='utf-8');session.push(case/'input_list.txt',job+'/input_list.txt')
    command=shlex.join(['sh',LAB+'/target/ai.sh',task,'--image',job+'/input.png','--output',job+'/reference','--runs','1','--warmup','0','--vendor-c-api'])
    session.run(command,case,'original-tflite-cpu',120);session.pull(job+'/reference',case)
    ref_files=list((case/'reference'/task).glob('*.json'));assert len(ref_files)==1;reference=json.loads(ref_files[0].read_text());assert reference['model_sha256']==model['source_sha256'],'Target reference model differs from the reviewed source';npz=np.load(next((case/'reference'/task).glob('*.npz')));ref_tensors=[npz[k] for k in sorted(npz.files)]
    records=[]
    for backend in (['htp','cpu'] if cpu_control else ['htp']):
        evidence=case/backend;evidence.mkdir();lib='libQnnHtp.so' if backend=='htp' else 'libQnnCpu.so';output=job+'/'+backend
        env='env LD_LIBRARY_PATH='+shlex.quote(RUNTIME+'/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu')+' ADSP_LIBRARY_PATH='+shlex.quote(RUNTIME+'/dsp;/usr/lib/rfsa/adsp;/dsp;/usr/lib')
        args=[RUNTIME+'/bin/qnn-net-run','--model',RUNTIME+'/lib/libQnnModelDlc.so','--dlc_path',remote_model,'--backend',RUNTIME+'/lib/'+lib,'--input_list',job+'/input_list.txt','--output_dir',output,'--profiling_level','detailed','--log_level','info','--num_inferences',str(runs),'--keep_num_outputs',str(runs)]
        _,status=session.run(env+' /usr/bin/timeout 180s '+shlex.join(args),evidence,'inference',200,False)
        if status:
            failed=dict(task=task,backend=backend,passed=False,exit_code=status,error='Graph/inference failed; inspect inference.log. No CPU fallback was requested.')
            save(evidence/'result.json',failed);records.append(failed);print(task,backend,'EXECUTION_FAILED',status,flush=True);continue
        session.run(env+' '+shlex.join([RUNTIME+'/bin/qnn-profile-viewer','--input_log',output+'/qnn-profiling-data_0.log','--output',output+'/profile.csv']),evidence,'profile',60);session.pull(output,evidence)
        folder=evidence/backend;tensors=read_outputs(folder,model['outputs']);placement=profile(folder/'profile.csv')
        if backend=='htp' and not (placement['positive_cycle_events'] and placement['accelerator_events']):raise RuntimeError('No positive HTP execution evidence')
        if task=='detection':tensors=detection_decode(tensors)
        labels=(ROOT/'models'/PROFILES[task]['labels']).read_text(encoding='utf-8').splitlines() if 'labels' in PROFILES[task] else []
        result=postprocess(task,tensors,PROFILES[task],labels,0.5);comparison=(quality_check or semantic)(task,result,reference,tensors,ref_tensors)
        result.update(dict(task=task,backend=backend,runtime='QAIRT/QNN 2.51.40.260930',model_sha256=model['dlc_sha256'],input_image_sha256=sha(case/'input.png'),profile=placement,comparison_to_original_tflite_cpu=comparison,passed=bool(comparison['passed']),scope='CNN graph executes on target. Image preparation, output decoding, NMS/rules and rendering execute on host. Reference images, not dataset accuracy.'))
        save(evidence/'result.json',result);np.savez_compressed(evidence/'outputs.npz',**{'output_%d'%i:t for i,t in enumerate(tensors)});render(task,canvas,result,tensors,backend,evidence/'prediction.png');records.append(result)
        print(task,backend,'PASS' if result['passed'] else 'QUALITY_CHECK_FAILED',flush=True)
    return dict(task=task,passed=any(r['backend']=='htp' and r['passed'] for r in records),acceptance='HTP execution/profile and semantic comparison against original TFLite CPU; QNN CPU is an additional separately reported control.',results=records,case=str(case))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['inspect','deploy','run','test-all']);p.add_argument('task',nargs='?',choices=list(PROFILES));p.add_argument('--adb',default=str(REPO/'tools/platform-tools/adb.exe'));p.add_argument('--serial');p.add_argument('--image',type=Path);p.add_argument('--crop',type=int,nargs=4);p.add_argument('--runs',type=int,default=3);p.add_argument('--evidence',type=Path);p.add_argument('--qnn-cpu-control',action='store_true',help='Additional diagnostic; original TFLite CPU is always the quality reference');a=p.parse_args()
    if not 1<=a.runs<=20:p.error('--runs must be 1..20')
    evidence=a.evidence or PACKAGE/'evidence'/(stamp()+'-'+uuid.uuid4().hex[:5]);evidence.mkdir(parents=True,exist_ok=False);rows=[]
    password=getpass.getpass('Target root password (not saved): ')
    with Session(a.adb,a.serial,'root',password=password) as session:
        before=snapshot(session,evidence,'before')
        try:
            if a.action=='inspect':print('READ_ONLY_RUNTIME_SNAPSHOT:',len(before),'files');return
            models=json.loads((PACKAGE/'models.json').read_text())['models'];own(session,evidence)
            env='env LD_LIBRARY_PATH='+shlex.quote(RUNTIME+'/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu')
            version,_=session.run(env+' '+RUNTIME+'/bin/qnn-net-run --version',evidence,'runtime-version');assert '2.51.40.260930' in version
            tasks=list(PROFILES) if a.action in ['test-all','deploy'] else [a.task]
            if any(task not in PROFILES for task in tasks):raise ValueError('Choose a demo task for run')
            for task in tasks:
                try:
                    remote_model=stage(session,task,models[task],evidence)
                    if a.action=='deploy':continue
                    image=a.image if a.image else PACKAGE/(task+'.input.png');rows.append(run_case(session,task,models[task],remote_model,image,a.crop,evidence/task,a.runs,a.qnn_cpu_control))
                except Exception as error:traceback.print_exc();rows.append(dict(task=task,passed=False,error=str(error)));print(task,'FAILED:',str(error),flush=True)
        finally:
            after=snapshot(session,evidence,'after');unchanged=before==after;save(evidence/'runtime-integrity.json',dict(passed=unchanged,files_checked=len(before),changed=[path for path in before if before[path]!=after.get(path)]));assert unchanged,'Original runtimes/models changed during test'
    status='MODELS_DEPLOYED_NOT_TESTED' if a.action=='deploy' and not rows else ('PASS_ALL_MIGRATED_HTP_DEMOS' if a.action=='test-all' and len(rows)==5 and all(r['passed'] for r in rows) else ('PASS_HTP_DEMO' if a.action=='run' and rows and all(r['passed'] for r in rows) else 'FAILED_DEMOS'))
    summary=dict(status=status,runtime=RUNTIME,isolated_demo_root=REMOTE,original_runtimes_unchanged=True,results=rows,evidence=str(evidence.resolve()));save(evidence/'summary.json',summary);save(PACKAGE/'LATEST.json',dict(evidence=str(evidence.resolve()),status=summary['status']));print(summary['status'],str(evidence),flush=True)
    if rows:
        from publish_htp251_results import publish
        publish(summary)
    if any(not r['passed'] for r in rows):sys.exit(1)
if __name__=='__main__':main()

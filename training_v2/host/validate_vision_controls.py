"""Additional real-image controls, independent of the original approved gallery."""
import argparse, datetime as dt, getpass, hashlib, json, shlex, sys, uuid
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from htp251_workshop import (ROOT,REPO,PACKAGE,REMOTE,LAB,Session,save,sha,snapshot,own,stage,run_case,semantic,PROFILES)
from benchmark_htp251 import run_tflite

MEDIA=ROOT/'media/controls'
CASES=[
    dict(id='burger-classification',task='classification',image='burger.jpg',expected='cheeseburger'),
    dict(id='full-body-detection',task='detection',image='pose.jpg',expected='person'),
    dict(id='no-person-detection',task='detection',image='cat.jpg',expected='no_person'),
    dict(id='full-body-pose',task='pose',image='pose.jpg',expected='full_body'),
    dict(id='standing-full-body-pose',task='pose',image='male_full_height_hands.jpg',expected='full_body'),
    dict(id='occluded-pose',task='pose',image='pose_lower_body_occluded.png',expected='occluded'),
    dict(id='closed-fist',task='gesture',image='fist.jpg',crop=[52,42,310,300],expected='closed_fist'),
    dict(id='no-hand',task='gesture',image='burger.jpg',crop=[77,0,402,325],expected='no_hand'),
    dict(id='person-segmentation',task='segmentation',image='pose.jpg',expected='person'),
    dict(id='standing-boundary-segmentation',task='segmentation',image='male_full_height_hands.jpg',expected='person'),
    dict(id='no-person-segmentation',task='segmentation',image='cat.jpg',expected='no_person'),
]

def quality(spec):
    def compare(task,result,reference,tensors,ref_tensors):
        expected=spec['expected']
        if expected=='no_person' and task=='detection':
            a=[x for x in result['detections'] if x['label']=='person'];b=[x for x in reference['detections'] if x['label']=='person']
            return dict(passed=not a and not b,criterion='No person at score >=0.5 in CPU and evaluated backend',actual_person_count=len(a),reference_person_count=len(b))
        if expected=='no_person' and task=='segmentation':
            a=float(result['class_fractions'].get('person',0));b=float(reference['class_fractions'].get('person',0))
            return dict(passed=max(a,b)<=0.01,criterion='Person-labelled fraction <=1% in CPU and evaluated backend; other VOC classes are allowed',actual_person_fraction=a,reference_person_fraction=b)
        check=semantic(task,result,reference,tensors,ref_tensors)
        if task=='classification':check['passed'] &= expected in result['top3'][0]['label'].lower() and expected in reference['top3'][0]['label'].lower()
        if task=='gesture':check['passed'] &= result['gesture']==expected and reference['gesture']==expected
        if expected=='full_body':check['passed'] &= min(result['visible_keypoints'],reference['visible_keypoints'])>=12;check['minimum_visible_keypoints']=12
        if expected=='occluded':check['scope']='Synthetic lower-body occlusion: inspect visible upper-body points; hidden-joint guesses are not ground truth.'
        return check
    return compare

def prepare():
    original=MEDIA/'pose.jpg'
    canvas=Image.open(original).convert('RGB')
    ImageDraw.Draw(canvas).rectangle((300,390,740,666),fill=(127,127,127))
    canvas.save(MEDIA/'pose_lower_body_occluded.png')
    sources=json.loads((MEDIA/'sources.json').read_text())
    sources=[r for r in sources if r['path']!='pose_lower_body_occluded.png']
    sources.append(dict(path='pose_lower_body_occluded.png',derived_from='pose.jpg',source_sha256=sha(original),sha256=sha(MEDIA/'pose_lower_body_occluded.png'),operation='Test-fixture occlusion rectangle RGB127 at x300,y390,x740,y666; original unchanged',scope='Synthetic control, not an independent photograph'))
    save(MEDIA/'sources.json',sources)
    save(MEDIA/'cases.json',dict(cases=CASES,scope='Prepared public reference controls; no event-specific photos were supplied. No dataset accuracy claim.'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run']);p.add_argument('--adb',default=str(REPO/'tools/platform-tools/adb.exe'));p.add_argument('--output',type=Path);p.add_argument('--case',action='append',choices=[x['id'] for x in CASES]);p.add_argument('--backend',choices=['all','htp'],default='all',help='all: CPU reference + HTP + GPU; htp: HTP with the separate CPU correctness reference, without a GPU run');a=p.parse_args()
    if a.action=='prepare':prepare();print('CONTROLS_PREPARED');return
    dest=a.output or ROOT/'evidence/vision-controls'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:5]);dest.mkdir(parents=True,exist_ok=False)
    models=json.loads((PACKAGE/'models.json').read_text())['models'];records=[]
    password=getpass.getpass('Target root password (not saved): ')
    with Session(a.adb,password=password) as session:
        before=snapshot(session,dest,'before')
        try:
            own(session,dest)
            for spec in CASES:
                if a.case and spec['id'] not in a.case:continue
                task=spec['task'];case=dest/spec['id'];model=models[task];remote_model=stage(session,task,model,dest)
                row={'case':spec,'image_sha256':sha(MEDIA/spec['image']),'passed':False}
                try:
                    check=quality(spec)
                    htp=run_case(session,task,model,remote_model,MEDIA/spec['image'],spec.get('crop'),case,3,quality_check=check)
                    from benchmark_htp251 import tensors
                    refdir=case/'reference'/task
                    cpu,ref_arrays=tensors(refdir)
                    gpu=None
                    if a.backend=='all':
                        # GPU receives the exact prepared canvas used for CPU/HTP.
                        job=REMOTE+'/runs/c'+uuid.uuid4().hex[:14]
                        session.run('mkdir '+shlex.quote(job),case,'gpu-directory');session.push(case/'input.png',job+'/input.png')
                        gpu,arrays=run_tflite(session,task,'gpu',job,case/'gpu',3,1)
                        if gpu['passed']:
                            gpu['correctness']=check(task,gpu['result'],cpu,arrays,ref_arrays)
                            gpu['passed'] &= bool(gpu['correctness']['passed'])
                    row.update(htp=htp,gpu=gpu,cpu=cpu,requested_backend=a.backend,passed=bool(htp['passed'] and (gpu is None or gpu['passed'])))
                except Exception as e:
                    row['error']=type(e).__name__+': '+str(e)
                    print(spec['id'],'ERROR',row['error'],flush=True)
                records.append(row);save(dest/'summary.json',dict(status='IN_PROGRESS',records=records))
                print(spec['id'],'PASS' if row['passed'] else 'REVIEW_REQUIRED',flush=True)
        finally:
            after=snapshot(session,dest,'after');unchanged=before==after;save(dest/'runtime-integrity.json',dict(passed=unchanged,files_checked=len(before),changed=[key for key in before if before[key]!=after.get(key)]))
    passed_status='PASS_HTP_REFERENCE_CONTROLS' if a.backend=='htp' else 'PASS_REFERENCE_CONTROLS'
    scope='Functional HTP controls with a separate TFLite CPU correctness reference;3 HTP invocations per case. No GPU invocation. No CPU fallback for the HTP graph.' if a.backend=='htp' else 'Functional CPU/OpenCL GPU/HTP controls on selected public images;3 HTP invocations,3 GPU invokes after1warmup.'
    summary=dict(status=passed_status if records and all(r['passed'] for r in records) and unchanged else 'REVIEW_REQUIRED',requested_backend=a.backend,records=records,original_runtimes_unchanged=unchanged,scope=scope+' Not a latency benchmark or dataset accuracy evaluation.')
    save(dest/'summary.json',summary);print(summary['status'],dest,flush=True)
    if summary['status']!=passed_status:raise SystemExit(1)

if __name__=='__main__':main()

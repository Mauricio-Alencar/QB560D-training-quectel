"""Compare existing TFLite CPU/GPU pipelines with the isolated QAIRT 2.51 HTP DLCs."""
import argparse,csv,datetime as dt,getpass,json,shlex,statistics,sys,uuid
from pathlib import Path
import numpy as np
from htp251_workshop import (ROOT,REPO,PACKAGE,REMOTE,RUNTIME,LAB,PROFILES,Session,
    save,sha,snapshot,own,stage,prepare_image,read_outputs,detection_decode,postprocess,semantic)

def client_samples(path,warmup,runs):
    """Only QnnGraph_execute call times, never INIT/FINALIZE or accelerator-only time."""
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines()
    start=next(i for i,line in enumerate(lines) if line.startswith('Msg Timestamp,'))
    rows=[{k.strip():v.strip() for k,v in row.items()} for row in csv.DictReader(lines[start:])]
    records=[row for row in rows if row.get('Message')=='EXECUTE' and row.get('Timing Source')=='NETRUN' and row.get('Event Level')=='ROOT']
    assert len(records)==warmup+runs,('Incorrect QNN execute sample count',len(records),warmup+runs)
    assert all(row['Unit of Measurement']=='US' for row in records),'Unexpected timing unit'
    values=[float(row['Time'])/1000 for row in records]
    assert all(np.isfinite(v) and v>0 for v in values),'Invalid execute samples'
    return values[warmup:],values[:warmup]

def tensors(folder):
    files=list(folder.glob('*.json'));assert len(files)==1
    report=json.loads(files[0].read_text());data=np.load(next(folder.glob('*.npz')))
    arrays=[data[k] for k in sorted(data.files)]
    assert all(np.isfinite(a).all() for a in arrays)
    return report,arrays

def run_tflite(session,task,backend,job,folder,runs,warmup):
    remote=job+'/'+folder.name
    args=['sh',LAB+'/target/ai.sh',task,'--image',job+'/input.png','--output',remote,'--backend',backend,'--vendor-c-api','--threads','2','--runs',str(runs),'--warmup',str(warmup)]
    log,status=session.run('/usr/bin/timeout 240s '+shlex.join(args),folder,'inference',260,False)
    if status:return {'backend':backend,'passed':False,'exit_code':status,'error':'TFLite invocation failed'},None
    if backend=='gpu' and not ('Initialized OpenCL-based API' in log and 'GPU delegate kernels' in log):
        return {'backend':backend,'passed':False,'error':'GPU partition evidence absent; refusing to report CPU fallback as GPU'},None
    session.pull(remote,folder);report,arrays=tensors(folder/folder.name/task)
    assert report['runtime_version']=='2.8.4' and report['backend']==backend.upper()
    result={'backend':backend,'passed':True,'runtime':'TFLite BSP 2.8.4','median_ms':report['inference_ms_median'],'p95_ms':report['inference_ms_p95'],'model_sha256':report['model_sha256'],'image_sha256':report['image_sha256'],'result':report}
    if backend=='gpu':result['coverage']='GPU delegate partition confirmed; residual CPU operators may remain, see log. No fully-GPU graph claim.'
    return result,arrays

def run_htp(session,task,model,remote_model,job,folder,runs,warmup):
    remote=job+'/'+folder.name
    env='env LD_LIBRARY_PATH='+shlex.quote(RUNTIME+'/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu')+' ADSP_LIBRARY_PATH='+shlex.quote(RUNTIME+'/dsp;/usr/lib/rfsa/adsp;/dsp;/usr/lib')
    args=[RUNTIME+'/bin/qnn-net-run','--model',RUNTIME+'/lib/libQnnModelDlc.so','--dlc_path',remote_model,'--backend',RUNTIME+'/lib/libQnnHtp.so','--input_list',job+'/input_list.txt','--output_dir',remote,'--profiling_level','client','--perf_profile','default','--log_level','info','--num_inferences',str(runs+warmup),'--keep_num_outputs','1']
    _,status=session.run(env+' /usr/bin/timeout 240s '+shlex.join(args),folder,'inference',260,False)
    if status:return {'backend':'htp','passed':False,'exit_code':status,'error':'HTP invocation failed'},None
    session.run(env+' '+shlex.join([RUNTIME+'/bin/qnn-profile-viewer','--input_log',remote+'/qnn-profiling-data_0.log','--output',remote+'/profile.csv']),folder,'profile',60)
    session.pull(remote,folder);output=folder/folder.name
    measured,discarded=client_samples(output/'profile.csv',warmup,runs)
    arrays=read_outputs(output,model['outputs'])
    if task=='detection':arrays=detection_decode(arrays)
    labels=(ROOT/'models'/PROFILES[task]['labels']).read_text(encoding='utf-8').splitlines() if 'labels' in PROFILES[task] else []
    report=postprocess(task,arrays,PROFILES[task],labels,0.5)
    return {'backend':'htp','passed':True,'runtime':'QAIRT/QNN 2.51.40.260930','median_ms':statistics.median(measured),'p95_ms':float(np.percentile(measured,95)),'model_sha256':model['dlc_sha256'],'samples_ms':measured,'discarded_warmup_ms':discarded,'result':report},arrays

def metadata(session,evidence,label):
    code="import json,os\nfrom pathlib import Path\nrows={}\nfor p in Path('/sys/class/thermal').glob('thermal_zone*/temp'):\n try: rows[str(p)]=int(p.read_text())\n except (OSError,ValueError):pass\nprint(json.dumps({'loadavg':os.getloadavg(),'thermal_raw_millicelsius':rows}))"
    session.python(code,evidence,label)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb',default=str(REPO/'tools/platform-tools/adb.exe'));p.add_argument('--serial')
    p.add_argument('--sessions',type=int,default=3);p.add_argument('--runs',type=int,default=50);p.add_argument('--warmup',type=int,default=10)
    p.add_argument('--task',action='append',choices=list(PROFILES));p.add_argument('--evidence',type=Path)
    a=p.parse_args()
    if not 1<=a.sessions<=10 or not 1<=a.runs<=1000 or not 0<=a.warmup<=100:p.error('Invalid session/run/warmup count')
    tasks=a.task or list(PROFILES);local=a.evidence or PACKAGE/'benchmarks'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:5]);local.mkdir(parents=True,exist_ok=False)
    password=getpass.getpass('Target root password (not saved): ')
    models=json.loads((PACKAGE/'models.json').read_text())['models'];records=[];references={}
    with Session(a.adb,a.serial,password=password) as session:
        before=snapshot(session,local,'before')
        try:
            own(session,local);metadata(session,local,'conditions-before')
            version,_=session.run('env LD_LIBRARY_PATH='+RUNTIME+'/lib '+RUNTIME+'/bin/qnn-net-run --version',local,'runtime-version');assert '2.51.40.260930' in version
            for task in tasks:
                model=models[task];remote_model=stage(session,task,model,local)
                case=local/task;case.mkdir();canvas,tensor=prepare_image(task,PACKAGE/(task+'.input.png'),input_mode=model.get('input_mode'));canvas.save(case/'input.png');tensor.tofile(case/'input.raw')
                job=REMOTE+'/runs/b'+uuid.uuid4().hex[:14];session.run('mkdir '+shlex.quote(job),case,'run-directory');session.push(case/'input.png',job+'/input.png');session.push(case/'input.raw',job+'/input.raw');(case/'input_list.txt').write_text(model['input_name']+':='+job+'/input.raw\n');session.push(case/'input_list.txt',job+'/input_list.txt')
                for number in range(1,a.sessions+1):
                    order=['cpu','gpu','htp'];offset=(number-1)%3;order=order[offset:]+order[:offset]
                    for backend in order:
                        folder=case/('s%d_%s'%(number,backend));folder.mkdir()
                        result,arrays=(run_htp(session,task,model,remote_model,job,folder,a.runs,a.warmup) if backend=='htp' else run_tflite(session,task,backend,job,folder,a.runs,a.warmup))
                        result.update(task=task,session=number,runs=a.runs,warmup=a.warmup,input_png_sha256=sha(case/'input.png'))
                        if result['passed']:
                            if backend!='htp':assert result['model_sha256']==model['source_sha256'] and result['image_sha256']==sha(case/'input.png')
                            if backend=='cpu' and task not in references:references[task]=(result['result'],arrays)
                            reference,ref_arrays=references[task]
                            result['comparison_to_tflite_cpu']=semantic(task,result['result'],reference,arrays,ref_arrays);result['passed']=bool(result['comparison_to_tflite_cpu']['passed'])
                        save(folder/'record.json',result);records.append(result);print(task,number,backend,'PASS' if result['passed'] else 'FAIL',result.get('median_ms'),flush=True)
                metadata(session,case,'conditions-after')
        finally:
            after=snapshot(session,local,'after');unchanged=before==after;save(local/'runtime-integrity.json',{'passed':unchanged,'files_checked':len(before),'changed':[key for key in before if before[key]!=after.get(key)]});assert unchanged,'Original runtime/model changes detected'
    table=[]
    for task in tasks:
        values={}
        for backend in ['cpu','gpu','htp']:
            rows=[r for r in records if r['task']==task and r['backend']==backend];passed=len(rows)==a.sessions and all(r['passed'] for r in rows)
            values[backend]={'passed':passed,'median_of_session_medians_ms':statistics.median(r['median_ms'] for r in rows) if passed else None,'session_medians_ms':[r.get('median_ms') for r in rows],'session_p95_ms':[r.get('p95_ms') for r in rows]}
        table.append({'task':task,'backends':values,'latency_ratio_cpu_over_htp':values['cpu']['median_of_session_medians_ms']/values['htp']['median_of_session_medians_ms'] if values['cpu']['passed'] and values['htp']['passed'] else None,'latency_ratio_gpu_over_htp':values['gpu']['median_of_session_medians_ms']/values['htp']['median_of_session_medians_ms'] if values['gpu']['passed'] and values['htp']['passed'] else None})
    summary={'status':'PASS_COMPARATIVE_TIMING' if all(r['passed'] for r in records) and len(records)==len(tasks)*a.sessions*3 else 'PARTIAL_COMPARATIVE_TIMING','recorded_at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sessions_per_backend':a.sessions,'measured_runs_per_session':a.runs,'discarded_warmup_per_session':a.warmup,'table':table,'records':records,'original_runtimes_unchanged':True,'evidence':str(local.resolve()),'method':{'cpu_gpu_runtime':'Installed TFLite C API 2.8.4; CPU 2 threads; GPU delegate OpenCL partition, residual CPU ops possible','htp_runtime':'QAIRT/QNN 2.51.40.260930; libQnnHtp.so only; perf_profile default; profiling client; discard first warmup executions','scope':'TFLite InterpreterInvoke and QNN NETRUN ROOT EXECUTE; excludes model loading/compile, input preprocessing, host postprocess/NMS, rendering and ADB. TFLite SSD includes built-in detection postprocess/NMS; QNN SSD graph excludes host NMS. Converted/quantized artifacts differ; pipeline latency ratios, not pure hardware speedups or FPS.','order':'Rotate CPU/GPU/HTP order each session; no global governors/services/settings changed','placement_evidence':'Detailed HTP functional profiles: htp251/evidence/20261101T195905Z-ffc9e, matching current DLC hashes. Timing uses client profiling to avoid detailed per-op overhead.','reference_scope':'Same prepared PNG per task, semantic checks against original TFLite CPU; selected images, not dataset accuracy'}}
    save(local/'summary.json',summary);save(PACKAGE/'BENCHMARK_LATEST.json',{'summary':str((local/'summary.json').resolve()),'status':summary['status']});print(json.dumps({'status':summary['status'],'table':table,'evidence':str(local)},indent=2))
    if summary['status']!='PASS_COMPARATIVE_TIMING':sys.exit(1)

if __name__=='__main__':main()

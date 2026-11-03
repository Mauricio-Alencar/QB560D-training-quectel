"""Compare hosted and physical QB560D results for the same tiny TFLite artifact."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import numpy as np


def read_result(path, backend):
    log=Path(path).read_text(encoding='utf-8')
    decoder=json.JSONDecoder()
    candidates=[]
    for m in re.finditer(r'(?m)^\{',log):
        try:value,_=decoder.raw_decode(log[m.start():])
        except json.JSONDecodeError:continue
        if isinstance(value,dict) and value.get('backend')==backend and 'model_sha256' in value:candidates.append(value)
    assert len(candidates)==1,'Expected one '+backend+' result in '+str(path)
    result=candidates[0]
    assert result['result']=='PASS' and re.search(r'(?m)^__QB560D_EXIT__=0\s*$',log),'Target command did not pass'
    return result,log


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',required=True)
    p.add_argument('--cpu-log',required=True)
    p.add_argument('--gpu-log')
    a=p.parse_args()
    run=Path(a.run_dir).resolve();root=Path(__file__).resolve().parents[2]
    jobs=json.loads((run/'jobs.json').read_text(encoding='utf-8'))
    reviewed=json.loads((run/'hosted-review.json').read_text(encoding='utf-8'))
    digest=hashlib.sha256((run/'model.tflite').read_bytes()).hexdigest()
    assert digest==jobs['target_sha256']==reviewed['artifact_sha256']
    sample=root/'models/workbench_input.npy';reference=root/'models/workbench_expected.npy'
    expected=np.load(reference,allow_pickle=False)
    results={};proof={}
    for backend,path in [('cpu',a.cpu_log),('gpu',a.gpu_log)]:
        if not path:continue
        result,log=read_result(path,backend)
        assert result['model_sha256']==digest,'Different target artifact'
        assert result['input_sha256']==hashlib.sha256(sample.read_bytes()).hexdigest()
        assert result['expected_sha256']==hashlib.sha256(reference.read_bytes()).hexdigest()
        actual=np.asarray(result['actual']);assert actual.shape==expected.shape==(1,4)
        assert np.isfinite(actual).all() and np.allclose(actual,expected,atol=1e-4,rtol=1e-3)
        if backend=='gpu':
            proof={'opencl_initialized':'Initialized OpenCL-based API' in log,
                   'gpu_delegate_kernels':bool(re.search(r'Created [1-9][0-9]* GPU delegate kernels?',log))}
            assert all(proof.values()),'GPU output passed, but OpenCL/delegate log evidence is missing'
        results[backend]=result
        (run/('target-'+backend+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    report={'at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'result':'HOSTED_AND_TARGET_CPU_GPU_PASS' if a.gpu_log else 'HOSTED_AND_TARGET_CPU_PASS_GPU_PENDING',
            'artifact_sha256':digest,'hosted':reviewed,'target':results,'local_gpu_log_evidence':proof,
            'timing_note':'Hosted estimate/raw samples and local invoke medians use different environments/procedures. No cross-device speedup is claimed.',
            'scope':'One deterministic synthetic input. Not semantic classification or dataset accuracy. One local session/backend,10 warmups and50 invokes.',
            'recorded_contingency':'PENDING_RECORDING_OF_APPROVED_FLOW'}
    if a.gpu_log:
        report['max_abs_local_gpu_vs_cpu']=float(np.max(np.abs(np.asarray(results['gpu']['actual'])-np.asarray(results['cpu']['actual']))))
        report['max_abs_local_gpu_vs_hosted_gpu']=float(np.max(np.abs(np.asarray(results['gpu']['actual'])-np.asarray(reviewed['actual']))))
    (run/'deployment-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('result','artifact_sha256','local_gpu_log_evidence')},indent=2))
    for backend,result in results.items():
        print(backend+': max_abs_error='+str(result['max_abs_error'])+', median_invoke_ms='+str(result['median_invoke_ms']))


if __name__=='__main__':
    main()

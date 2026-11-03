"""Review a completed tiny-model run without contacting the service or using credentials."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    run=Path(a.run_dir).resolve()
    jobs=json.loads((run/'jobs.json').read_text(encoding='utf-8'))
    profile=json.loads((run/'profile.json').read_text(encoding='utf-8'))
    model=run/'model.tflite'
    digest=hashlib.sha256(model.read_bytes()).hexdigest()
    assert digest==jobs['target_sha256'],'Downloaded model hash differs from job receipt'
    assert model.read_bytes()[4:8]==b'TFL3','Expected a TensorFlow Lite FlatBuffer'
    expected_path=root/'models/workbench_expected.npy'
    expected=np.load(expected_path,allow_pickle=False)
    with np.load(run/'hosted_outputs.npz',allow_pickle=False) as archive:
        assert len(archive.files)==1,'Expected exactly one output'
        actual=archive[archive.files[0]]
    assert actual.shape==expected.shape==(1,4)
    assert np.isfinite(actual).all() and np.isfinite(expected).all()
    passed=bool(np.allclose(actual,expected,atol=1e-4,rtol=1e-3))
    error=float(np.max(np.abs(actual-expected)))
    assert passed and jobs['correctness']['pass'],'Hosted output failed reference comparison'
    assert abs(error-jobs['correctness']['max_abs_error'])<1e-12,'Receipt comparison differs'
    units=Counter(e['compute_unit'] for e in profile['execution_detail'])
    times=profile['execution_summary']['all_inference_times']
    report={'at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'result':'HOSTED_ARTIFACT_AND_REFERENCE_PASS_LOCAL_DEPLOY_PENDING',
            'device':jobs['device'],'compile_job':jobs['compile_job'],
            'inference_profile_job':jobs['inference_profile_job'],
            'artifact_bytes':model.stat().st_size,'artifact_sha256':digest,
            'actual':actual.tolist(),'expected':expected.tolist(),
            'max_abs_error':error,'atol':1e-4,'rtol':1e-3,
            'profile_compute_units':dict(units),'profile_entry_count':len(profile['execution_detail']),
            'estimated_inference_us':profile['execution_summary']['estimated_inference_time'],
            'sample_count':len(times),'sample_median_us':float(np.median(times)),
            'sample_min_us':min(times),'sample_max_us':max(times),
            'timing_scope':'Qualcomm-hosted kit only. Estimated field and raw-sample median are distinct; neither is local QB560D latency.',
            'compute_scope':'Four listed graph entries on GPU, zero CPU entries. Does not claim all application/preprocessing work avoids CPU.',
            'local_deploy':'PENDING_TARGET_COMPATIBILITY_AND_OUTPUT_CHECKS',
            'profile_units_source':'https://workbench.aihub.qualcomm.com/docs/hub/jobs.html'}
    (run/'hosted-review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()

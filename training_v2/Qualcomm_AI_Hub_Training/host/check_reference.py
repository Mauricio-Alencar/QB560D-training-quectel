"""Validate the supplied synthetic model and expected output without cloud access."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import numpy as np
import onnx
from onnx.reference import ReferenceEvaluator

root=Path(__file__).resolve().parents[2]
paths=[root/'models'/name for name in
       ('workbench_demo.onnx','workbench_input.npy','workbench_expected.npy')]
model=onnx.load(str(paths[0]));onnx.checker.check_model(model)
sample=np.load(paths[1],allow_pickle=False)
expected=np.load(paths[2],allow_pickle=False)
assert sample.shape==(1,3,32,32) and sample.dtype==np.float32
assert expected.shape==(1,4) and expected.dtype==np.float32
actual=ReferenceEvaluator(model).run(None,{'image':sample})[0]
assert np.allclose(actual,expected,atol=1e-6,rtol=1e-5)
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
dest=root/'Qualcomm_AI_Hub_Training/evidence'/('preparation-'+stamp);dest.mkdir(parents=True,exist_ok=False)
report={'at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'result':'HOST_REFERENCE_PASS_CLOUD_NOT_RUN',
        'input_shape':list(sample.shape),'output_shape':list(actual.shape),'actual':actual.tolist(),
        'expected':expected.tolist(),'max_abs_error':float(np.max(np.abs(actual-expected))),
        'atol':1e-6,'rtol':1e-5,'files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'scope':'Local ONNX ReferenceEvaluator versus independent NumPy reference. No hosted job or QB560D artifact execution claimed.'}
(dest/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))

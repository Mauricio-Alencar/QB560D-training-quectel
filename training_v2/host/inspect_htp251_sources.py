"""Inspect original TFLite contracts without changing any model (conversion host)."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.lite.python import schema_py_generated as schema
from flatbuffers import flexbuffers
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'htp251';DEST.mkdir(exist_ok=True)
profiles=json.loads((ROOT/'ai/profiles.json').read_text());records={}
def detail(d):return dict(name=d['name'],shape=d['shape'].tolist(),dtype=str(d['dtype']),quantization=list(d['quantization']))
for task,profile in profiles.items():
    source=ROOT/'models'/profile['model'];interpreter=tf.lite.Interpreter(model_path=str(source),experimental_preserve_all_tensors=True);interpreter.allocate_tensors()
    record=dict(source_model=profile['model'],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),inputs=[detail(d) for d in interpreter.get_input_details()],outputs=[detail(d) for d in interpreter.get_output_details()])
    ops=interpreter._get_ops_details();record['operators']=sorted(set(o['op_name'] for o in ops))
    if task=='detection':
        op=next(o for o in ops if 'Detection_PostProcess' in o['op_name']);details={d['index']:d for d in interpreter.get_tensor_details()}
        record['pre_nms_outputs']=[detail(details[int(index)]) for index in op['inputs'][:2]]
        anchor=interpreter.get_tensor(int(op['inputs'][2]));d=details[int(op['inputs'][2])];scale,zero=d['quantization']
        anchor=(anchor.astype(np.float32)-zero)*scale if scale else anchor.astype(np.float32)
        np.save(DEST/'ssd_anchors.npy',anchor)
        model=schema.Model.GetRootAsModel(source.read_bytes(),0);graph=model.Subgraphs(0)
        for i in range(graph.OperatorsLength()):
            operator=graph.Operators(i);code=model.OperatorCodes(operator.OpcodeIndex())
            if code.CustomCode() and b'Detection_PostProcess' in code.CustomCode():record['nms_options']=flexbuffers.Loads(bytes(operator.CustomOptionsAsNumpy()))
    records[task]=record
(DEST/'source-contracts.json').write_text(json.dumps(dict(tensorflow_inspection_version=tf.__version__,models=records),indent=2),encoding='utf-8')
print(json.dumps({k:dict(inputs=v['inputs'],outputs=v.get('pre_nms_outputs',v['outputs']),nms=v.get('nms_options')) for k,v in records.items()},indent=2))

"""Export the reviewed TFLite functions to ONNX; retain original files and contracts."""
import argparse,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import numpy as np
import onnx,onnxruntime as ort,tensorflow as tf,tf2onnx
from onnx import numpy_helper
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'htp251';CONTRACTS=json.loads((DEST/'source-contracts.json').read_text())['models'];PROFILES=json.loads((ROOT/'ai/profiles.json').read_text())
def io_path(p):return '\\\\?\\'+str(p.resolve()) if os.name=='nt' else str(p)
def canvas(path,task):
    image=ImageOps.exif_transpose(Image.open(io_path(path))).convert('RGB')
    if task=='gesture' and path.name=='right_hands.jpg':image=image.crop((360,0,720,360))
    return image.resize(tuple(PROFILES[task]['size']),Image.Resampling.BILINEAR)
parser=argparse.ArgumentParser();parser.add_argument('--tasks',nargs='+',choices=list(CONTRACTS),default=list(CONTRACTS));args=parser.parse_args()
records=json.loads((DEST/'export-results.json').read_text()) if (DEST/'export-results.json').is_file() else {}
for task,contract in CONTRACTS.items():
    if task not in args.tasks:continue
    try:
        folder=DEST/'models'/('detection_requant' if task=='detection' else task);folder.mkdir(parents=True,exist_ok=True)
        source=ROOT/'models'/contract['source_model'];assert hashlib.sha256(source.read_bytes()).hexdigest()==contract['source_sha256']
        outputs=contract.get('pre_nms_outputs') or [contract['outputs'][i] for i in sorted(set(PROFILES[task]['outputs'].values()))]
        print('EXPORT',task,'outputs:',[d['name'] for d in outputs],flush=True)
        if task=='detection':
            subprocess.run([sys.executable,'-m','tf2onnx.convert','--tflite',str(source),'--outputs',','.join(d['name'] for d in outputs),'--opset','13','--dequantize','--output',str(folder/'export.onnx')],check=True)
            model=onnx.load(str(folder/'export.onnx'))
        else:model,_=tf2onnx.convert.from_tflite(str(source),output_names=[d['name'] for d in outputs],opset=13,output_path=str(folder/'export.onnx'))
        # Recalibrate SSD as one floating-point CNN rather than retaining the
        # legacy Q/DQ output ranges that generated false-positive boxes on QNN.
        if task=='detection':
            constants={t.name:t for t in model.graph.initializer};fixed=[];removed_quantizers=[]
            for node in model.graph.node:
                if node.op_type=='DequantizeLinear' and node.input[0] in constants:
                    value=numpy_helper.to_array(constants[node.input[0]]).astype(np.float32);scale=numpy_helper.to_array(constants[node.input[1]]);zero=numpy_helper.to_array(constants[node.input[2]]) if len(node.input)>2 else 0
                    if np.asarray(scale).size>1:
                        axis=next((a.i for a in node.attribute if a.name=='axis'),1);shape=[1]*value.ndim;shape[axis]=scale.size;scale=scale.reshape(shape);zero=np.asarray(zero).reshape(shape)
                    model.graph.initializer.append(numpy_helper.from_array(((value-zero)*scale).astype(np.float32),node.output[0]));removed_quantizers.append(node.name);continue
                if node.op_type in ['QuantizeLinear','DequantizeLinear']:
                    fixed.append(onnx.helper.make_node('Identity',[node.input[0]],list(node.output),name=node.name+'_float'));removed_quantizers.append(node.name)
                else:fixed.append(node)
            del model.graph.node[:];model.graph.node.extend(fixed);del model.graph.value_info[:]
            for tensor in list(model.graph.input)+list(model.graph.output):tensor.type.tensor_type.elem_type=onnx.TensorProto.FLOAT
            (folder/'float-recalibration.json').write_text(json.dumps(dict(removed_activation_quantizers=removed_quantizers,reason='Fresh QAIRT 2.51 calibration after legacy Q/DQ ranges caused extra detections on the target'),indent=2))
        tensors={t.name:t for t in model.graph.initializer};changes=[]
        for node in model.graph.node:
            if node.op_type=='DequantizeLinear' and node.input[0] in tensors and node.input[1] in tensors and len(tensors[node.input[0]].dims)==1 and numpy_helper.to_array(tensors[node.input[1]]).size==1 and not any(a.name=='axis' for a in node.attribute):
                node.attribute.append(onnx.helper.make_attribute('axis',0));changes.append(node.name)
        onnx.checker.check_model(model);onnx.save(onnx.shape_inference.infer_shapes(model),str(folder/'model.onnx'))
        interpreter=tf.lite.Interpreter(model_path=str(source),experimental_preserve_all_tensors=task=='detection');interpreter.allocate_tensors();input_detail=interpreter.get_input_details()[0];details={d['name']:d for d in interpreter.get_tensor_details()}
        runtime=ort.InferenceSession(str(folder/'model.onnx'),providers=['CPUExecutionProvider'])
        samples=[ROOT/'media'/('right_hands.jpg' if task=='gesture' else 'grace_hopper.jpg'),ROOT/'media'/'right_hands.jpg']
        if task=='gesture':
            samples+=list((ROOT/'demos/hand_gesture/evidence/fw-20261101').rglob('hand_crop.png'))[:7]
        else:samples+=list((ROOT/'demos/hand_gesture/assets/images').glob('*.jpg'))[:3]
        cal=DEST/'calibration'/task;cal.mkdir(parents=True,exist_ok=True);validation=[];paths=[]
        for i,path in enumerate(samples):
            image=canvas(path,task);pixels=np.asarray(image,dtype=np.float32);profile=PROFILES[task]
            scale,zero=input_detail['quantization']
            if scale:
                native=pixels.astype(input_detail['dtype'])[None];real=(native.astype(np.float32)-zero)*scale
            else:
                real=((pixels-profile.get('mean',0))/profile.get('std',1))[None];native=real.astype(input_detail['dtype'])
            converter_input=native.astype(np.float32) if task=='detection' else real.astype(np.float32)
            name='calibration/'+task+'/%02d.raw'%i;converter_input.astype('<f4').tofile(DEST/name);paths.append(name)
            if i==0:image.save(DEST/(task+'.input.png'))
            if i<2:
                interpreter.set_tensor(input_detail['index'],native);interpreter.invoke();actual=runtime.run(None,{runtime.get_inputs()[0].name:converter_input if task=='detection' else native})
                errors=[]
                for out,value in zip(outputs,actual):
                    expected=interpreter.get_tensor(details[out['name']]['index'])
                    if task=='detection':
                        out_scale,out_zero=out['quantization'];expected=(expected.astype(np.float32)-out_zero)*out_scale
                    difference=np.abs(expected.astype(np.float64)-value.astype(np.float64));error=float(np.max(difference));errors.append(dict(name=out['name'],max_abs_error=error,mean_abs_error=float(difference.mean()),dtype=str(expected.dtype)))
                    limit=(2.0 if out['name']=='Squeeze' else 0.10) if task=='detection' else (4.0 if np.issubdtype(expected.dtype,np.integer) else 0.02)
                    assert error<=limit,(task,out['name'],error)
                    if task=='classification' and i==0:assert np.argmax(expected)==np.argmax(value),'Reference top-1 changed during export'
                validation.append(dict(image=str(path.relative_to(ROOT)),outputs=errors))
        (cal/'input_list.txt').write_text('\n'.join(paths)+'\n',encoding='utf-8')
        record=dict(status='ONNX_EXPORT_VALIDATED',input=contract['inputs'][0],outputs=outputs,source_model=contract['source_model'],source_sha256=contract['source_sha256'],onnx=(folder/'model.onnx').relative_to(DEST).as_posix(),onnx_sha256=hashlib.sha256((folder/'model.onnx').read_bytes()).hexdigest(),dequantized_before_fresh_calibration=task=='detection',axis_metadata_changes=changes,reference_validation=validation,calibration_samples=len(paths),calibration_list='calibration/'+task+'/input_list.txt',scope='Reference-image conversion checks; not dataset accuracy. SSD decoding/NMS runs on host after pre-NMS CNN outputs.' if task=='detection' else 'Reference-image conversion checks; not dataset accuracy.')
        record['input_mode']='pixels_float32' if task=='detection' else 'normalized_float32'
        records[task]=record;print('ONNX_OK',task,flush=True)
    except Exception as error:
        traceback.print_exc();records[task]=dict(status='EXPORT_FAILED',error=str(error));print('EXPORT_FAILED',task,str(error),flush=True)
(DEST/'export-results.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
sys.exit(1 if any(r['status']!='ONNX_EXPORT_VALIDATED' for r in records.values()) else 0)

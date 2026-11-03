"""Build separate QAIRT 2.51 DLCs from the reviewed ONNX exports (Windows/Python 3.12)."""
import argparse,hashlib,json,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'htp251';ENTRY=Path(__file__).with_name('qairt251_entry.py')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def invoke(tool,args,log):
    command=[sys.executable,'-X','utf8',str(ENTRY),tool]+list(map(str,args))
    with log.open('w',encoding='utf-8') as output:result=subprocess.run(command,cwd=DEST,stdout=output,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(tool+' failed: '+str(log))
    return command
def main():
    exports=json.loads((DEST/'export-results.json').read_text());p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tasks',nargs='+',choices=list(exports),default=list(exports));p.add_argument('--act-bits',type=int,choices=[8,16],default=16);a=p.parse_args()
    manifest=json.loads((DEST/'models.json').read_text()) if (DEST/'models.json').is_file() else dict(runtime_version='2.51.40.260930',models={},failures={})
    for task in a.tasks:
        try:
            export=exports[task];assert export['status']=='ONNX_EXPORT_VALIDATED';onnx=DEST/export['onnx'];folder=onnx.parent;input_name=export['input']['name'];assert sha(onnx)==export['onnx_sha256']
            arguments=['-i',onnx,'-o',folder/'model.float.dlc','--source_model_input_layout',input_name,'NHWC','--source_model_input_datatype',input_name,'float32','--onnx_skip_simplification','--onnx_disable_defer_loading']
            for spec in export['outputs']:
                if len(spec['shape']) in [3,4]:
                    layout='NHWC' if len(spec['shape'])==4 else 'NFC'
                    arguments+=['--source_model_output_layout',spec['name'],layout,'--desired_output_layout',spec['name'],layout]
            print('CONVERT',task,flush=True);conversion=invoke('qairt-converter',arguments,folder/'conversion.log')
            dlc=folder/('model.w8a'+str(a.act_bits)+'.dlc')
            print('QUANTIZE',task,flush=True);quantization=invoke('qairt-quantizer',['--input_dlc',folder/'model.float.dlc','--input_list',DEST/export['calibration_list'],'--output_dlc',dlc,'--weights_bitwidth','8','--act_bitwidth',str(a.act_bits),'--bias_bitwidth','32'],folder/('quantize-a'+str(a.act_bits)+'.log'))
            invoke('qairt-dlc-info',['-i',dlc,'--save',folder/'model-info.csv'],folder/'model-info.txt')
            record=dict(dlc=dlc.relative_to(DEST).as_posix(),dlc_sha256=sha(dlc),onnx_sha256=export['onnx_sha256'],input_name=input_name,outputs=export['outputs'],requested_precision='w8a'+str(a.act_bits),encoding_note='Source Q/DQ encodings retained when present; inspect model-info.csv for actual tensor types.',source_model=export['source_model'],source_sha256=export['source_sha256'],calibration_samples=export['calibration_samples'],conversion_command=conversion,quantization_command=quantization)
            record['input_mode']=export.get('input_mode','normalized_float32')
            manifest['models'][task]=record;manifest['failures'].pop(task,None);print('DLC_READY',task,record['dlc_sha256'],flush=True)
        except Exception as error:traceback.print_exc();manifest['failures'][task]=str(error);print('DLC_FAILED',task,str(error),flush=True)
        (DEST/'models.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if any(task not in manifest['models'] or task in manifest['failures'] for task in a.tasks):sys.exit(1)
if __name__=='__main__':main()

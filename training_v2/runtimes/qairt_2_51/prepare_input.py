"""Prepare the AI Hub ImageNet image contract without installing PyTorch."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parent
def main():
 assets=ROOT/'assets'
 metadata=json.loads((assets/'model/mobilenet_v2-qnn_dlc-w8a8/metadata.json').read_text())
 spec=metadata['model_files']['mobilenet_v2.dlc']['inputs']['image_tensor']
 if spec['shape']!=[1,224,224,3] or spec['value_range']!=[0.0,1.0]:raise ValueError('Unreviewed input contract')
 image=ImageOps.exif_transpose(Image.open(assets/'dog.jpg')).convert('RGB')
 w,h=image.size
 resized=(int(256*w/h),256) if w>=h else (256,int(256*h/w))
 image=image.resize(resized,Image.Resampling.BILINEAR)
 left=round((image.width-224)/2);top=round((image.height-224)/2)
 image=image.crop((left,top,left+224,top+224))
 array=(np.asarray(image,dtype=np.float32)/np.float32(255))[None]
 path=assets/'dog_float32_nhwc.raw';array.astype('<f4').tofile(path)
 image.save(assets/'dog_input_224.png')
 report={'shape':list(array.shape),'dtype':'little-endian float32','layout':'NHWC','range':[float(array.min()),float(array.max())],'resize_shorter_side':256,'center_crop':224,'normalization':'RGB / 255; ImageNet mean/std normalization is inside the AI Hub network','qnn_input_mode':'Float input file; qnn-net-run converts to the graph quantization','graph_input_quantization':spec['quantization_parameters'],'image_sha256':hashlib.sha256((assets/'dog.jpg').read_bytes()).hexdigest(),'tensor_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 (assets/'preprocessing.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()

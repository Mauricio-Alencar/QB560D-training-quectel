"""Download official MobileNet-v2 AI Hub DLC and a public ImageNet demo image."""
import hashlib, json, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ASSETS={
 'mobilenet_v2-qnn_dlc-w8a8.zip':'https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mobilenet_v2/releases/v0.65.0/mobilenet_v2-qnn_dlc-w8a8.zip',
 'dog.jpg':'https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg',
 'imagenet_classes.txt':'https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt',
 'aihub-model-source.py.txt':'https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/models/templates/imagenet_classifier/model.py',
 'aihub-preprocessing-source.py.txt':'https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/utils/image_processing.py',
 'model-card.md.txt':'https://huggingface.co/qualcomm/MobileNet-v2/raw/main/README.md',
}
def main():
 dest=ROOT/'assets';dest.mkdir(exist_ok=True)
 rows=[]
 for name,url in ASSETS.items():
  path=dest/name
  if not path.is_file():
   request=urllib.request.Request(url,headers={'User-Agent':'QB560D-QAIRT251-Validation/1.0'})
   with urllib.request.urlopen(request,timeout=45) as r:
    data=r.read(64*1024*1024+1)
   if len(data)>64*1024*1024:raise ValueError('Asset exceeded limit')
   path.write_bytes(data)
  data=path.read_bytes()
  rows.append(dict(name=name,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
  print(json.dumps(rows[-1]),flush=True)
 modeldir=dest/'model';modeldir.mkdir(exist_ok=True)
 with zipfile.ZipFile(dest/'mobilenet_v2-qnn_dlc-w8a8.zip') as z:
  for info in z.infolist():
   if info.is_dir():continue
   p=(modeldir/info.filename).resolve()
   if modeldir.resolve() not in p.parents:raise ValueError('Unsafe ZIP member')
   if info.file_size>64*1024*1024:raise ValueError('Model member exceeded limit')
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(info))
   print('MODEL_MEMBER',info.filename,info.file_size,flush=True)
 (dest/'sources.lock.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()

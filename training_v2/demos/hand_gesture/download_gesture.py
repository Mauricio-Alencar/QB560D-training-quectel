"""Download the official AI Hub hand gesture DLC bundle and primary-source samples."""
import hashlib,json,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
URLS={
"gesture-qnn_dlc-w8a8.zip":"https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-models/models/mediapipe_hand_gesture/releases/v0.65.0/mediapipe_hand_gesture-qnn_dlc-w8a8.zip",
"reference_app.py.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/models/mediapipe_hand_gesture/app.py",
"reference_model.py.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/models/mediapipe_hand_gesture/model.py",
"reference_mediapipe_app.py.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/models/templates/mediapipe/app.py",
"reference_mediapipe_utils.py.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/models/templates/mediapipe/utils.py",
"reference_hand_model.py.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/models/mediapipe_hand/model.py",
"reference_boxes.py.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/src/qai_hub_models/utils/bounding_box_processing.py",
"official_sample_notebook.ipynb.txt":"https://raw.githubusercontent.com/google-ai-edge/mediapipe-samples/main/examples/gesture_recognizer/python/gesture_recognizer.ipynb",
"model_card.md.txt":"https://huggingface.co/qualcomm/MediaPipe-Hand-Gesture-Recognition/raw/main/README.md",
"licenses/QAI_HUB_MODELS_LICENSE.txt":"https://raw.githubusercontent.com/qualcomm/ai-hub-models/main/LICENSE",
"licenses/MEDIAPIPE_LICENSE.txt":"https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/LICENSE",
"licenses/MODEL_LICENSE_POINTER.txt":"https://huggingface.co/qualcomm/MediaPipe-Hand-Gesture-Recognition/raw/main/LICENSE",
}
for name in ("thumbs_down.jpg","victory.jpg","thumbs_up.jpg","pointing_up.jpg"):
 URLS["images/"+name]="https://storage.googleapis.com/mediapipe-tasks/gesture_recognizer/"+name
for name in ('fist.jpg','fist.png','right_hands.jpg','victory.jpg'):
 URLS['images/test_'+name]='https://storage.googleapis.com/mediapipe-assets/'+name
URLS['images/iloveyou.jpg']='https://upload.wikimedia.org/wikipedia/commons/e/ec/ASL_ILY%40Side-PalmForward.jpg'
URLS['images/open_palm.jpg']='https://upload.wikimedia.org/wikipedia/commons/b/b4/Human_Palm.jpg'
URLS['images/full_open_palm.png']='https://upload.wikimedia.org/wikipedia/commons/d/d0/Right_Hand_Palm.png'
URLS['images/closed_fist.jpg']='https://upload.wikimedia.org/wikipedia/commons/7/7c/Closed_fist.jpg'
def main():
 assets=ROOT/"assets";assets.mkdir(parents=True,exist_ok=True);rows=[]
 pins=json.loads((ROOT/'assets.lock.json').read_text(encoding='utf-8'))
 expected={r['path']:r for r in pins}
 for name,url in URLS.items():
  if url!=expected[name]['url']:raise ValueError('Source URL differs from validated revision: '+name)
  path=assets/name;path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists():
   request=urllib.request.Request(url,headers={'User-Agent':'QB560D-training/1.0 (educational model validation)'})
   with urllib.request.urlopen(request,timeout=45) as r:data=r.read(64*1024*1024+1)
   if len(data)>64*1024*1024:raise ValueError("Asset too large")
   if hashlib.sha256(data).hexdigest()!=expected[name]['sha256']:raise ValueError('Downloaded asset differs from validated revision: '+name)
   path.write_bytes(data)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected[name]['sha256']:raise ValueError('Cached asset differs from validated revision: '+name)
  rows.append(dict(path=name,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
  print(name,path.stat().st_size,flush=True)
 with zipfile.ZipFile(assets/"gesture-qnn_dlc-w8a8.zip") as z:
  dest=(assets/"models").resolve()
  for i in z.infolist():
   if i.is_dir():continue
   path=(dest/i.filename).resolve()
   if dest not in path.parents:raise ValueError("Unsafe ZIP path")
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(i))
   print("MODEL_MEMBER",i.filename,i.file_size,flush=True)
 (assets/"sources.lock.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()


"""NumPy/Pillow adaptation of Qualcomm AI Hub MediaPipe hand preprocessing.
Reference implementation copyright Qualcomm Technologies, BSD-3-Clause.
Reference snapshots and URLs are preserved in assets/sources.lock.json.
Single-hand still-image workshop path; highest-scoring palm is selected.
"""
import math
import numpy as np
from PIL import Image,ImageOps,ImageDraw
LABELS=["None","Closed_Fist","Open_Palm","Pointing_Up","Thumb_Down","Thumb_Up","Victory","ILoveYou"]
EDGES=[(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(17,18),(18,19),(19,20),(0,17)]
def letterbox(image,size=256):
    image=ImageOps.exif_transpose(image).convert("RGB")
    w,h=image.size;scale=min(size/w,size/h)
    nw,nh=int(w*scale),int(h*scale)
    resized=image.resize((nw,nh),Image.Resampling.BILINEAR)
    px,py=(size-nw)//2,(size-nh)//2
    canvas=Image.new("RGB",(size,size));canvas.paste(resized,(px,py))
    return np.asarray(canvas,dtype=np.float32)[None]/np.float32(255),scale,np.array([px,py],dtype=np.float32)
def palm_roi(box_coords,box_scores,scale,pad,threshold=0.75):
    scores=box_scores.reshape(-1)
    index=int(np.argmax(scores));score=float(scores[index])
    if score<threshold:return None,dict(palm_score=score,reason="no_hand")
    # DLC includes anchor decode and sigmoid; coordinates are detector pixels, xyxy+7 keypoints.
    coords=box_coords.reshape(-1,9,2)[index].astype(np.float32)
    coords=(coords-pad)/scale
    lo,hi=coords[0],coords[1];keypoints=coords[2:]
    w,h=hi-lo
    if w<=0 or h<=0:return None,dict(palm_score=score,reason="invalid_box")
    vec=keypoints[2]-keypoints[0];length=float(np.linalg.norm(vec))
    if length<1e-5:return None,dict(palm_score=score,reason="invalid_rotation")
    center=(lo+hi)/2 + np.float32(0.5*w)*vec/length
    theta=float(np.arctan2(vec[1],vec[0])+math.pi/2)
    theta=(theta+math.pi)%(2*math.pi)-math.pi
    rotation=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]],dtype=np.float32)
    unit=np.array([[-1,-1],[-1,1],[1,-1],[1,1]],dtype=np.float32)
    corners=(unit*np.array([w,h],dtype=np.float32)*1.25)@rotation.T+center
    return corners,dict(palm_score=score,palm_box_xyxy=[*lo.tolist(),*hi.tolist()],roi_corners=corners.tolist(),rotation_radians=theta)
def hand_crop(image,corners,size=224):
    # Output-pixel -> original-image mapping, equivalent to inverse cv2 affine.
    inverse=np.column_stack(((corners[2]-corners[0])/(size-1),(corners[1]-corners[0])/(size-1),corners[0])).astype(np.float32)
    crop=image.transform((size,size),Image.Transform.AFFINE,tuple(inverse.reshape(-1)),Image.Resampling.BILINEAR,fillcolor=(0,0,0))
    return np.asarray(crop,dtype=np.float32)[None]/np.float32(255),inverse,crop
def map_landmarks(landmarks,inverse):
    points=landmarks.reshape(21,3).astype(np.float32).copy()
    points[:,:2]=points[:,:2]@inverse[:,:2].T+inverse[:,2]
    return points
def features64(points,handedness,mirror=False):
    points=points[None].astype(np.float32).copy();lr=np.array([[handedness]],dtype=np.float32)
    if mirror:points*=np.array([-1,1,1],dtype=np.float32);lr=1-lr
    center=points[:,[0,1,5,9,13,17],:].mean(axis=1,keepdims=True)
    normed=points-center
    scale=np.maximum(np.ptp(normed[:,:,0],axis=1),np.ptp(normed[:,:,1],axis=1)).reshape(-1,1,1)+np.float32(1e-5)
    return np.concatenate(((normed/scale).reshape(1,63),lr),axis=1).astype(np.float32)
def annotate(image,points,label,score,corners=None):
    out=image.copy();draw=ImageDraw.Draw(out)
    if corners is not None:
        c=[tuple(x) for x in corners]
        draw.line([c[0],c[1],c[3],c[2],c[0]],fill="yellow",width=2)
    if points is not None:
        for a,b in EDGES:draw.line([tuple(points[a,:2]),tuple(points[b,:2])],fill="lime",width=3)
        for x,y,z in points:draw.ellipse((x-3,y-3,x+3,y+3),fill="red")
    caption=f"{label}  {score:.3f}"
    draw.rectangle((0,0,min(out.width,340),30),fill="white")
    draw.text((6,7),caption,fill="black")
    return out


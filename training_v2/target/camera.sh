#!/bin/sh
# D2-10. Optional single-frame capture through an already validated BSP pipeline.
set -u
. "$(dirname -- "$0")/common.sh"
need gst-launch-1.0
need gst-inspect-1.0
need timeout
device=${1:-/dev/video0}
config() { printf 'CONFIG_REQUIRED: %s\n' "$*" >&2; exit 78; }
if [ "$device" = '--qmmf' ]; then
  sensor=${2:-0}
  case "$sensor" in ''|*[!0-9]*) fail 'Pass a numeric QMMF camera ID';; esac
  for plugin in qtiqmmfsrc identity videoconvert jpegenc filesink; do gst-inspect-1.0 "$plugin" >/dev/null 2>&1 || config "Missing plugin: $plugin"; done
else
  case "$device" in /dev/video*) :;; *) fail 'Pass a /dev/videoN node or --qmmf ID';; esac
  number=${device#/dev/video}
  case "$number" in ''|*[!0-9]*) fail 'Invalid V4L2 node';; esac
  [ -c "$device" ] || config 'Camera node absent; inspect the sensor and BSP camera source'
  need v4l2-ctl
  info=$(v4l2-ctl -d "$device" --all 2>&1) || config 'Cannot query the V4L2 node'
  printf '%s\n' "$info" | grep -q 'msm_vidc' && config 'This is a video codec node, not a camera sensor'
  printf '%s\n' "$info" | grep -q 'Video Capture' || config 'V4L2 node has no capture capability'
  for plugin in v4l2src videoconvert jpegenc filesink; do gst-inspect-1.0 "$plugin" >/dev/null 2>&1 || config "Missing plugin: $plugin"; done
fi
mkdir -p "$LAB_ROOT/media/captured" || exit 1
frame="$LAB_ROOT/media/captured/frame-$$.jpg"
if [ "$device" = '--qmmf' ]; then
  timeout -k 3s -s INT 15s gst-launch-1.0 -e qtiqmmfsrc camera="$sensor" ! 'video/x-raw,format=NV12,width=640,height=480,framerate=30/1' ! identity eos-after=2 ! videoconvert ! jpegenc ! filesink location="$frame" || fail 'QMMF capture failed or timed out. Check sensor availability, camera service and caps.'
else
  timeout -k 3s -s INT 15s gst-launch-1.0 -e v4l2src device="$device" num-buffers=1 ! videoconvert ! jpegenc ! filesink location="$frame" || fail 'V4L2 capture failed or timed out. Inspect caps and BSP camera source.'
fi
[ -s "$frame" ] || fail 'No frame written'
need python3
PYTHONPATH="$LAB_ROOT/.python-deps${PYTHONPATH:+:$PYTHONPATH}" python3 -c 'from PIL import Image; import sys; Image.open(sys.argv[1]).verify()' "$frame" || fail 'Captured output is not a valid image'
mv -- "$frame" "$LAB_ROOT/media/captured/frame.jpg" || exit 1
printf 'RESULT: CAMERA_FRAME_CAPTURED\n'

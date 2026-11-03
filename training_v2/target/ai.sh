#!/bin/sh
# Direct target AI entrypoint, including isolated Pillow and installed vendor C API.
set -u
. "$(dirname -- "$0")/common.sh"
python=${PYTHON:-python3}
need "$python"
export PYTHONPATH="$LAB_ROOT/.python-deps${PYTHONPATH:+:$PYTHONPATH}"
cd "$LAB_ROOT" || exit 1
action=${1:-inspect}
shift || :
case "$action" in
  prepare) exec "$python" target/unpack_pillow.py;;
  inspect) exec "$python" ai/inspect_models.py;;
  verify) exec "$python" ai/fetch_models.py --verify;;
  tensor) exec "$python" ai/run_tensor.py "$@";;
  snpe-probe) exec "$python" ai/probe_snpe.py "$@";;
  snpe) exec "$python" ai/run_snpe.py "$@";;
  classification|detection|pose|gesture|segmentation) exec "$python" ai/run_demo.py "$action" "$@";;
  *) fail 'Usage: ai.sh prepare|inspect|verify|tensor|snpe-probe|snpe|classification|detection|pose|gesture|segmentation';;
esac

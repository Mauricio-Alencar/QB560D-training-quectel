#!/bin/sh
set -eu
cd "$(dirname -- "$0")"
backend=${1:-cpu}
case "$backend" in cpu|gpu) ;; *) echo 'Use cpu or gpu' >&2; exit 78;; esac
export PYTHONPATH="/opt/qb560d-training-payload/.python-deps${PYTHONPATH:+:$PYTHONPATH}"
exec python3 ai/run_tensor.py --model models/aihub_tiny_6a569f3f9ea3.tflite --input models/workbench_input.npy --expected models/workbench_expected.npy --backend "$backend" --output "results/$backend.json"

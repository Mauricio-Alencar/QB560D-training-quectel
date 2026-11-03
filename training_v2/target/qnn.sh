#!/bin/sh
# D2-11. OPTIONAL existing-runtime demonstration. Installs no SDK.
# Usage: qnn.sh CONTEXT_BIN INPUT_LIST BACKEND_SO OUTPUT_DIR
set -u
. "$(dirname -- "$0")/common.sh"
need qnn-net-run
[ "$#" -eq 4 ] || fail 'Usage: qnn.sh CONTEXT_BIN INPUT_LIST BACKEND_SO OUTPUT_DIR'
[ -r "$1" ] && [ -r "$2" ] && [ -r "$3" ] || fail 'Context, input list or backend missing'
case "$3" in */libQnnHtp.so) :;; *) fail 'Pass the exact installed libQnnHtp.so path';; esac
qnn-net-run --help 2>&1 | grep -q -- '--retrieve_context' || { printf 'CONFIG_REQUIRED: inspect installed qnn-net-run version\n' >&2; exit 78; }
[ ! -e "$4" ] || fail 'Use a new output directory for each measurement'
# Runtime search paths and DSP firmware must already be configured by the BSP.
# A context binary must match this runtime/platform and its own raw input format.
qnn-net-run --retrieve_context "$1" --input_list "$2" --backend "$3" --output_dir "$4" --profiling_level basic || fail 'QNN execution failed'
printf 'RESULT: QNN_EXECUTED. Inspect profiling and numerical outputs before claiming HTP acceleration.\n'

#!/bin/sh
# Inside the offline bundle this file is run.sh, next to ai/ and MANIFEST.json.
set -eu
package=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="/opt/qb560d-training-payload/.python-deps${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python3}" "$package/ai/htp_target.py" "$@"

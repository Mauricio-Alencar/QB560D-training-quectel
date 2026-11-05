#!/bin/sh
set -eu
root=/opt/qb560d-docker-demo
[ "$(cat "$root/.owner")" = qb560d-training-docker-v1 ] || { echo 'Unrecognized lab directory'; exit 1; }
mkdir -p "$root/data/tmp"
export PATH="$root/runtime/docker:$PATH"
exec "$root/runtime/docker/dockerd" --config-file "$root/config/daemon.json"

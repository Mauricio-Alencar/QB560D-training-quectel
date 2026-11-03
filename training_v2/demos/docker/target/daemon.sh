#!/bin/sh
set -eu
root=/opt/qb560d-docker-demo
export PATH="$root/runtime/docker:$PATH"
exec "$root/runtime/docker/dockerd" --config-file "$root/config/daemon.json"

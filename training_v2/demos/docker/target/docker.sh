#!/bin/sh
set -eu
root=/opt/qb560d-docker-demo
export DOCKER_HOST=unix:///run/qb560d-docker-demo/docker.sock
export DOCKER_CONFIG="$root/client"
exec "$root/runtime/docker/docker" "$@"

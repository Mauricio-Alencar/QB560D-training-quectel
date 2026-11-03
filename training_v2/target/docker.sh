#!/bin/sh
# Compatibility entrypoint. Docker resources are canonical in demos/docker.
set -eu
root=/opt/qb560d-docker-demo
[ -f "$root/target/demo.sh" ] || { echo 'Stage/install demos/docker first; see demos/docker/README.md' >&2; exit 78; }
action=${1:-run}
case "$action" in
  check)
    sh "$root/target/docker.sh" info
    [ "$(sh "$root/target/docker.sh" image inspect qb560d-telemetry:1.0.0 --format '{{.Os}}/{{.Architecture}}')" = linux/arm64 ]
    ;;
  run|stop) exec sh "$root/target/demo.sh" "$action";;
  *) echo 'Usage: docker.sh check|run|stop' >&2; exit 1;;
esac

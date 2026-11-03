#!/bin/sh
set -eu
root=/opt/qb560d-docker-demo
[ "$(id -u)" = 0 ] || { echo 'Root is required'; exit 1; }
[ "$(cat "$root/.owner")" = qb560d-training-docker-v1 ] || { echo 'Unrecognized lab directory'; exit 1; }
[ "$(uname -m)" = aarch64 ] || { echo 'This runtime is ARM64 only'; exit 1; }
cd "$root"
sha256sum -c offline/runtime.sha256
mkdir -p runtime client/cli-plugins
if [ ! -x runtime/docker/dockerd ]; then tar -xzf offline/runtime/docker-29.9.2.tgz -C runtime; fi
cp offline/runtime/buildx-v0.38.1.linux-arm64 client/cli-plugins/docker-buildx
chmod 755 client/cli-plugins/docker-buildx
runtime/docker/dockerd --validate --config-file config/daemon.json
unit=/etc/systemd/system/qb560d-docker-demo.service
if [ -e "$unit" ]; then cmp -s "$unit" config/qb560d-docker-demo.service || { echo 'Existing unit differs; inspect it first'; exit 1; }; else cp config/qb560d-docker-demo.service "$unit"; fi
systemctl daemon-reload
systemctl start qb560d-docker-demo.service
attempt=0
while [ "$attempt" -lt 30 ]; do
  if sh target/docker.sh info > evidence/docker-info.txt 2>&1; then
    sh target/docker.sh version
    sh target/docker.sh buildx version
    echo 'RESULT: ENGINE_READY'
    exit 0
  fi
  attempt=$((attempt + 1)); sleep 1
done
journalctl -u qb560d-docker-demo.service -n 80 --no-pager
exit 1

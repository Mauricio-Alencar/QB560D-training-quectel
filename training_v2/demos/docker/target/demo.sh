#!/bin/sh
set -eu
root=/opt/qb560d-docker-demo
cd "$root"
image=${TRAINING_IMAGE:-qb560d-telemetry:1.0.0}
name=qb560d-docker-demo
d() { sh "$root/target/docker.sh" "$@"; }
case "${1:-status}" in
  run)
    [ "$(d image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/arm64 ] || { echo 'Image must be linux/arm64'; exit 1; }
    if d container inspect "$name" >/dev/null 2>&1; then echo 'Container exists; inspect it or use demo.sh stop'; exit 1; fi
    d run -d --pull never --name "$name" --network host --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
      --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 128m "$image"
    attempt=0
    while [ "$attempt" -lt 20 ]; do
      state=$(d inspect "$name" --format '{{.State.Health.Status}}')
      if [ "$state" = healthy ]; then python3 target/check_http.py; exit 0; fi
      attempt=$((attempt + 1)); sleep 1
    done
    d logs "$name"
    exit 1
    ;;
  check) python3 target/check_http.py;;
  logs) d logs "$name";;
  inspect) d inspect "$name";;
  status) d version; d ps -a; systemctl is-enabled qb560d-docker-demo.service || :;;
  stop)
    if ! d container inspect "$name" >/dev/null 2>&1; then echo 'Demo container already absent'; exit 0; fi
    [ "$(d inspect "$name" --format '{{index .Config.Labels "com.quectel.training.demo"}}')" = qb560d-docker ] || { echo 'Unrelated container; refusing removal'; exit 1; }
    d stop --time 5 "$name"
    d rm "$name"
    ;;
  load)
    sha256sum -c offline/image.sha256
    d load -i offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz
    [ "$(d image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/arm64 ]
    expected=$(python3 -c 'import json; print(json.load(open("offline/image.lock.json"))["image_id"])')
    [ "$(d image inspect "$image" --format '{{.Id}}')" = "$expected" ] || { echo 'Loaded image ID differs from the reviewed image'; exit 1; }
    ;;
  test) exec python3 target/rehearse.py;;
  *) echo 'Usage: demo.sh run|check|logs|inspect|status|stop|load|test'; exit 1;;
esac

#!/bin/sh
# D2-01 / D2-02. Direct target application deployment, no SDK or image build.
set -u
. "$(dirname -- "$0")/common.sh"
python=${PYTHON:-python3}
need "$python"
need curl
case "${1:-test}" in
  test)
    curl --fail --max-time 3 http://127.0.0.1:8080/health || fail 'Application health failed'
    curl --fail --max-time 3 http://127.0.0.1:8080/telemetry || fail 'Application telemetry failed'
    printf '\nRESULT: APPLICATION_HTTP_PASS\n'
    ;;
  install-service)
    need systemctl
    [ "$(id -u)" -eq 0 ] || fail 'Use the approved root shell for service installation'
    [ -x /usr/bin/python3 ] || fail 'Review ExecStart for the actual Python path'
    if [ -e /opt/qb560d-training ] || [ -e /etc/systemd/system/qb560d-training.service ]; then
      cmp -s "$LAB_ROOT/app/telemetry.py" /opt/qb560d-training/telemetry.py && \
        cmp -s "$LAB_ROOT/app/qb560d-training.service" /etc/systemd/system/qb560d-training.service || fail 'Existing training installation differs. Review it before updating.'
      printf 'Reusing the identical training installation\n'
    else
      mkdir -p /opt/qb560d-training || exit 1
      cp "$LAB_ROOT/app/telemetry.py" /opt/qb560d-training/telemetry.py || exit 1
      cp "$LAB_ROOT/app/qb560d-training.service" /etc/systemd/system/qb560d-training.service || exit 1
    fi
    systemctl daemon-reload || exit 1
    systemctl start qb560d-training.service || fail 'Inspect journalctl -u qb560d-training.service'
    # Do not enable at boot by default.
    attempt=0
    while [ "$attempt" -lt 10 ]; do
      curl --fail --max-time 2 http://127.0.0.1:8080/health && { printf '\nRESULT: SERVICE_HEALTH_PASS\n'; exit 0; }
      attempt=$((attempt + 1)); sleep 1
    done
    journalctl -u qb560d-training.service -n 30 --no-pager
    fail 'Service did not become healthy'
    ;;
  stop-service)
    need systemctl
    systemctl stop qb560d-training.service || exit 1
    printf 'RESULT: TRAINING_SERVICE_STOPPED\n'
    ;;
  rehearse-service)
    sh "$SCRIPT_DIR/application.sh" install-service || exit 1
    restore() {
      cp "$LAB_ROOT/app/qb560d-training.service" /etc/systemd/system/qb560d-training.service
      systemctl daemon-reload
      systemctl stop qb560d-training.service
    }
    trap restore 0 1 2 15
    sh "$SCRIPT_DIR/application.sh" test || exit 1
    sed 's/APP_VERSION=1.0.0/APP_VERSION=1.0.1/' "$LAB_ROOT/app/qb560d-training.service" > /etc/systemd/system/qb560d-training.service || exit 1
    systemctl daemon-reload && systemctl restart qb560d-training.service || exit 1
    sleep 1
    body=$(curl --fail --max-time 3 http://127.0.0.1:8080/telemetry) || fail 'Updated service not healthy'
    printf '%s\n' "$body" | "$python" -c 'import json,sys; assert json.load(sys.stdin)["version"] == "1.0.1"' || fail 'Updated version mismatch'
    cp "$LAB_ROOT/app/qb560d-training.service" /etc/systemd/system/qb560d-training.service || exit 1
    systemctl daemon-reload && systemctl restart qb560d-training.service || exit 1
    sleep 1
    body=$(curl --fail --max-time 3 http://127.0.0.1:8080/telemetry) || fail 'Rollback not healthy'
    printf '%s\n' "$body" | "$python" -c 'import json,sys; assert json.load(sys.stdin)["version"] == "1.0.0"' || fail 'Rollback version mismatch'
    printf 'RESULT: SERVICE_UPDATE_ROLLBACK_PASS (restored and stopped on exit)\n'
    ;;
  uninstall-service)
    need systemctl
    cmp -s "$LAB_ROOT/app/telemetry.py" /opt/qb560d-training/telemetry.py && \
      cmp -s "$LAB_ROOT/app/qb560d-training.service" /etc/systemd/system/qb560d-training.service || fail 'Files differ from this demo; review before removal'
    systemctl stop qb560d-training.service || exit 1
    rm -- /etc/systemd/system/qb560d-training.service /opt/qb560d-training/telemetry.py || exit 1
    rmdir /opt/qb560d-training || :
    systemctl daemon-reload || exit 1
    printf 'RESULT: TRAINING_SERVICE_REMOVED\n'
    ;;
  compile)
    need gcc
    mkdir -p "$LAB_ROOT/evidence/native" || exit 1
    gcc -Wall -Wextra -Werror -O2 "$LAB_ROOT/app/qb560d-hello.c" -o "$LAB_ROOT/evidence/native/qb560d-hello" || fail 'Native compilation failed'
    "$LAB_ROOT/evidence/native/qb560d-hello" || exit 1
    printf 'RESULT: NATIVE_COMPILE_PASS\n'
    ;;
  *) fail 'Usage: application.sh test|install-service|rehearse-service|stop-service|uninstall-service|compile';;
esac

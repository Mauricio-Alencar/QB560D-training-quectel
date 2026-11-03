#!/bin/sh
# D1-02 / D1-03. Inspect services and create one training log event.
set -u
. "$(dirname -- "$0")/common.sh"
need systemctl
need journalctl
printf 'Boot and system health\n'
uptime
systemctl --failed --no-pager
journalctl -b -p err -n 30 --no-pager
printf '\nRoot filesystem\n'
df -h /
mount
marker="qb560d-training-$(date +%s)-$$"
if command -v systemd-cat >/dev/null 2>&1; then
  # The BSP's /dev/log can be a different socket from journald's syslog socket.
  printf '%s\n' "$marker" | systemd-cat -t qb560d-training || fail 'Journal submission failed'
  printf 'LOG_TRANSPORT: systemd-cat\n'
else
  need logger
  logger -t qb560d-training "$marker" || fail 'logger failed'
  printf 'LOG_TRANSPORT: logger\n'
fi
attempt=0
while [ "$attempt" -lt 5 ]; do
  if journalctl -t qb560d-training -n 20 --no-pager 2>/dev/null | grep -F "$marker"; then
    printf 'RESULT: LOG_EVENT_FOUND\n'
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 1
done
fail 'Training event absent from journal. Check logger/journald routing and permissions.'

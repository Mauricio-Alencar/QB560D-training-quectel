#!/bin/sh
# Shared helpers. Deliberately no eval and no automatic package installation.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
LAB_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
if [ -r "$LAB_ROOT/config/lab.env" ]; then
  # This is a trusted, locally reviewed shell configuration file.
  . "$LAB_ROOT/config/lab.env"
fi
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || { printf 'CONFIG_REQUIRED: missing %s\n' "$1" >&2; exit 78; }; }
cell() {
  CELL_IF=${CELL_IF:-}
  case "$CELL_IF" in ''|*[!a-zA-Z0-9_.:-]*) fail 'Set CELL_IF to the observed cellular interface';; esac
  [ -d "/sys/class/net/$CELL_IF" ] || fail "Interface absent: $CELL_IF"
  need ip
}
counters() {
  printf 'RX='; cat "/sys/class/net/$CELL_IF/statistics/rx_bytes"
  printf 'TX='; cat "/sys/class/net/$CELL_IF/statistics/tx_bytes"
}

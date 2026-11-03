#!/bin/sh
# D1-06. Preserve failed benchmark exit status and raw JSON evidence.
set -u
. "$(dirname -- "$0")/common.sh"
cell
need iperf3
server=${IPERF_SERVER:-}
port=${IPERF_PORT:-5201}
duration=${SECONDS_PER_TEST:-10}
streams=${PARALLEL_STREAMS:-1}
case "$server" in ''|*[!0-9.]*) fail 'Set IPERF_SERVER to a numeric IPv4 address';; esac
for value in "$port" "$duration" "$streams"; do
  case "$value" in ''|*[!0-9]*) fail 'Port, duration and streams must be integers';; esac
done
[ "$port" -ge 1 ] && [ "$port" -le 65535 ] || fail 'Port must be 1..65535'
[ "$duration" -ge 1 ] && [ "$duration" -le 60 ] || fail 'Duration must be 1..60'
[ "$streams" -ge 1 ] && [ "$streams" -le 8 ] || fail 'Streams must be 1..8'
iperf3 --help 2>&1 | grep -q -- '--bind-dev' || { printf 'CONFIG_REQUIRED: iperf3 lacks --bind-dev\n' >&2; exit 78; }
out="$LAB_ROOT/evidence/iperf-$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$out" || fail 'Cannot create evidence directory'
printf 'SERVER=%s CELL_IF=%s OUTPUT=%s\n' "$server" "$CELL_IF" "$out"
printf 'BEFORE\n'; counters
result=0
iperf3 -4 -c "$server" -p "$port" --bind-dev "$CELL_IF" -t "$duration" -P "$streams" -J > "$out/uplink.json" 2> "$out/uplink.stderr" || result=1
cat "$out/uplink.json" "$out/uplink.stderr"
iperf3 -4 -c "$server" -p "$port" --bind-dev "$CELL_IF" -t "$duration" -P "$streams" -R -J > "$out/downlink.json" 2> "$out/downlink.stderr" || result=1
cat "$out/downlink.json" "$out/downlink.stderr"
printf 'AFTER\n'; counters
if [ "$result" -eq 0 ]; then printf 'RESULT: UL_DL_PASS\n'; else printf 'RESULT: UL_DL_FAIL\n'; fi
exit "$result"

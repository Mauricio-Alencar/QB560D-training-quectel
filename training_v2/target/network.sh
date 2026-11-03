#!/bin/sh
# D1-05. Interface-bound IPv4 probes, without editing routes.
set -u
. "$(dirname -- "$0")/common.sh"
cell
need curl
printf 'Interface and policy\n'
ip -d link show dev "$CELL_IF"
ip -4 addr show dev "$CELL_IF"
ip -4 route show table all
ip rule show
ip -4 route get "${PING_IP:-1.1.1.1}" || :
printf '\nBefore\n'; counters
result=0
icmp=SKIPPED_UNSUPPORTED
if command -v ping >/dev/null 2>&1 && ping -h 2>&1 | grep -q -- '-I'; then
  icmp=PASS
  ping -I "$CELL_IF" -c 5 -W 2 "${PING_IP:-1.1.1.1}" || { icmp=FAIL; result=1; }
else
  printf 'ICMP_SKIPPED: installed ping lacks interface binding (-I). No unbound fallback.\n'
fi
curl --noproxy '*' --interface "$CELL_IF" -4 --fail --connect-timeout 5 --max-time 20 \
  -o /dev/null -w 'HTTP=%{http_code} total_s=%{time_total}\n' "${HTTP_URL:-https://example.com/}" || result=1
printf '\nAfter\n'; counters
printf 'DNS_NOTE: curl may resolve through the system resolver. This is not an isolated cellular DNS test.\n'
printf 'ICMP_RESULT: %s\n' "$icmp"
if [ "$result" -ne 0 ]; then
  printf 'RESULT: NETWORK_FAIL\n'
elif [ "$icmp" = PASS ]; then
  printf 'RESULT: IP_AND_HTTP_PASS\n'
else
  printf 'RESULT: HTTP_PASS_ICMP_NOT_TESTED\n'
fi
exit "$result"

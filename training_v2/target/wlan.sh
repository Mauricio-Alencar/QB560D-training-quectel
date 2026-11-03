#!/bin/sh
# WLAN operations on an existing NetworkManager profile. Never prints secrets.
set -u
. "$(dirname -- "$0")/common.sh"
need nmcli
iface=${WLAN_IF:-wlan0}
profile=${WLAN_PROFILE:-qb560d-training-wlan}
case "${1:-status}" in
  status)
    nmcli --colors no -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS device show "$iface"
    ip -4 route show dev "$iface"
    if command -v iw >/dev/null 2>&1; then iw dev "$iface" link; fi
    ;;
  scan)
    nmcli --colors no -f SSID,CHAN,FREQ,SIGNAL,SECURITY device wifi list ifname "$iface"
    ;;
  up)
    nmcli --colors no --wait 45 connection up "$profile" ifname "$iface"
    ;;
  down)
    nmcli --colors no connection down "$profile"
    ;;
  check)
    need curl
    need getent
    nmcli --colors no -g GENERAL.STATE device show "$iface" | grep '^100 ' >/dev/null || fail 'WLAN is not connected'
    addresses=$(getent ahostsv4 example.com) || fail 'DNS resolution failed'
    printf '%s\n' "$addresses" | sed -n '1,2p'
    ip -4 route get 1.1.1.1 || fail 'No IPv4 route to the numeric probe endpoint'
    curl --interface "$iface" --fail --connect-timeout 8 --max-time 20 -sS -o /dev/null -w 'HTTPS_STATUS=%{http_code}\n' https://example.com || exit 1
    if command -v timedatectl >/dev/null 2>&1; then timedatectl show -p NTPSynchronized; fi
    ;;
  *) fail 'Usage: wlan.sh status|scan|up|down|check (configure credentials interactively with nmcli --ask)';;
esac

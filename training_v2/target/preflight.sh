#!/bin/sh
# D1-01 / D2-00. Inventory only. No radio or network configuration changes.
set -u
show() { printf '\n--- %s ---\n' "$1"; }
optional() { if command -v "$1" >/dev/null 2>&1; then "$@" 2>&1 || :; else printf 'NOT_INSTALLED: %s\n' "$1"; fi; }
show 'Identity'
date -u
id
uname -a
if [ -r /etc/build_version ]; then cat /etc/build_version; fi
optional getconf GNU_LIBC_VERSION
if [ -r /etc/os-release ]; then cat /etc/os-release; else printf 'NO_OS_RELEASE: inspect Android properties or BSP identity\n'; fi
if command -v getprop >/dev/null 2>&1; then getprop ro.build.version.release; getprop ro.product.model; fi
if [ -r /proc/device-tree/model ]; then tr -d '\000' < /proc/device-tree/model; printf '\n'; fi
optional uptime
show 'Resources'
optional free -m
optional df -h
optional mount
show 'Network'
optional ip -d link show
optional ip -4 addr show
optional ip -6 addr show
optional ip -4 route show table all
optional ip rule show
[ ! -r /etc/resolv.conf ] || cat /etc/resolv.conf
show 'Processes and services'
ps -ef 2>/dev/null || ps 2>/dev/null || :
optional systemctl --failed --no-pager
optional journalctl -b -p err -n 30 --no-pager
show 'Available tools'
for tool in sh ip ping curl iperf3 systemctl journalctl logger python3 gcc docker qlril-api-test qnn-net-run gst-launch-1.0 v4l2-ctl; do
  command -v "$tool" 2>/dev/null || printf 'NOT_INSTALLED: %s\n' "$tool"
done
show 'AI Python modules'
if command -v python3 >/dev/null 2>&1; then
  python3 -c 'import sys,importlib.util,json; print(sys.version); print(json.dumps({m:bool(importlib.util.find_spec(m)) for m in ["numpy","PIL","tflite_runtime","ai_edge_litert","tensorflow","onnxruntime","cv2"]}))' 2>&1 || :
fi
show 'Devices'
ls -l /dev/video* /dev/dma_heap/* /dev/fastrpc* /dev/adsprpc* /dev/mhi* 2>/dev/null || :
show 'Runtime library names in common paths'
for dir in /usr/lib /usr/lib64 /vendor/lib64 /opt/qcom; do
  [ ! -d "$dir" ] || find "$dir" -maxdepth 3 -type f \( -name 'libQnn*.so*' -o -name '*tensorflow*lite*.so*' -o -name '*onnxruntime*.so*' \) 2>/dev/null
done
printf '\nRESULT: INVENTORY_COLLECTED (not a hardware acceptance result)\n'

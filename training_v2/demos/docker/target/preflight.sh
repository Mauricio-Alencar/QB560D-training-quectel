#!/bin/sh
set -u
printf '\nPLATFORM\n'
id
uname -a
cat /etc/os-release
getconf GNU_LIBC_VERSION
date -u
printf '\nFILESYSTEMS\n'
df -h / /opt /tmp /var
cat /proc/filesystems
mount | sed -n '/ on \/ /p; / on \/opt /p; / on \/data /p; /cgroup/p'
printf '\nCGROUPS\n'
cat /proc/cgroups
cat /proc/self/cgroup
ls -ld /sys/fs/cgroup /sys/fs/cgroup/* 2>/dev/null
printf '\nTOOLS\n'
for tool in docker dockerd containerd runc apt-get dpkg curl tar gzip sha256sum iptables modprobe mount unshare; do command -v "$tool" || :; done
printf '\nPACKAGES\n'
dpkg --audit
dpkg-query -W -f='${Package} ${Version}\n' docker.io docker-ce containerd containerd.io runc iptables 2>/dev/null || :
printf '\nSERVICES\n'
systemctl is-active docker containerd || :
printf '\nSTORAGE\n'
ls -ld /opt /var/lib/docker /etc/docker 2>/dev/null || :
printf '\nKERNEL CONFIG\n'
if [ -r /proc/config.gz ]; then zcat /proc/config.gz | sed -n '/CONFIG_NAMESPACES=/p; /CONFIG_NET_NS=/p; /CONFIG_PID_NS=/p; /CONFIG_CGROUP/p; /CONFIG_SECCOMP/p; /CONFIG_OVERLAY_FS=/p; /CONFIG_VETH=/p; /CONFIG_BRIDGE=/p; /CONFIG_NETFILTER=/p'; fi
printf '\nLISTENERS\n'
if command -v ss >/dev/null; then ss -lnt; fi
printf '\nWLAN STATUS (not required for offline deployment)\n'
ip -4 address show dev wlan0 || :
if [ "${1:-}" = --online ]; then
  curl --interface wlan0 --fail --connect-timeout 8 --max-time 25 -I https://download.docker.com/
else
  printf 'OFFLINE_MODE: no Internet request made; use --online only for a separate WLAN check.\n'
fi

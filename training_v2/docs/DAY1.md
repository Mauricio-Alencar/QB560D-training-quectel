# Day 1 presenter runbook

Run all target commands from the package root. Use ADB for initial staging, then follow [SSH access](SSH.md) for manual target operation over the management LAN and USB-A peripheral testing. Use the installed RIL application interactively for cellular setup. Its default setup flow can install DNS/routes. The Linux probes do not automate modem bring-up.

Current lab root: `/opt/qb560d-training-payload`. Open `adb shell`, enter the Linux root login, then `cd` to this directory. The host helpers perform this login themselves. The later RIL inspection confirms the existing active cellular session. The owner supplied the successful 71/d activation. D1-06 later passed three cellular UL/DL pairs and a failed-endpoint control. NR/SA/NSA and teardown/reconnect remain unverified, outside the current closure queue by owner decision. The earlier local-only revalidation did not exercise cellular.

## D1-00 — Configuration and lab orientation, 20 min

Show the actual QB560D-EU and its connectors. State the confirmed QCM6490, Ubuntu 20.04.3 and cellular capability. Identify the management path and cellular data path separately. Record the unit label and running BSP/kernel during rehearsal. Do not quote unmeasured memory, NPU throughput or radio rates.

Pass: owner-confirmed platform and a usable ADB shell. Fallback: photograph and prior inventory from the same unit/build.

## D1-01 — Hardware/software discovery, 40 min

```sh
sh target/preflight.sh
```

Explain OS versus vendor BSP, kernel versus user space, installed storage versus free space, and logical versus physical network interfaces. The script lists available runtime tools and AI library names. It does not certify their functional compatibility.

Record: OS, kernel, aarch64 architecture, RAM, partitions, writable paths, Python version, interfaces, available tools and device nodes. Pass: inventory saved and understood. Missing optional tools are preparation tasks rather than automatic hardware faults.

## D1-02 — Boot and diagnostics, 40 min

One physical cold boot was captured and reviewed on 1 November 2026; see BOOT_WLAN.md for 13.94 s root shell/29.02s WLAN and measurement limits. Repeat the procedure per event box. Confirm the approved power sequence and console parameters before cycling power. Use ADB after boot, and a validated serial/Ethernet path if available. The public session can use a recording if power cycling risks disrupting the room.

```sh
uptime
systemctl --failed --no-pager
journalctl -b -p err -n 30 --no-pager
dmesg | tail -n 40
```

Record time from power-on to usable shell, kernel errors and service failures. Inspect an existing confirmed service with `systemctl status NAME` and `journalctl -u NAME`. Pass: useful shell, diagnosed errors and saved boot evidence. An empty failed-service list does not prove every peripheral works.

## D1-03 — Ubuntu runtime, filesystem and logs, 50 min

```sh
cat /etc/os-release
df -h /
mount
ls -ld /etc /usr /opt /var /tmp /data
sh target/diagnostics.sh
```

Explain transient `/tmp`, persistent application storage, executable paths, library paths, file permissions and systemd ownership. The logging script adds a uniquely tagged training event and polls for it in journald. It returns a failure if the event does not appear.

The script uses `systemd-cat` when available to submit directly to journald. On this BSP, `/dev/log` is a separate socket from `/run/systemd/journal/dev-log`, so a successful `logger` invocation alone does not prove that journald received the event. The script reports its transport and checks the actual marker.

Pass: root filesystem policy recorded and training event observed. Fallback: demonstrate the existing application log path if journald does not capture syslog, and record the image-specific behavior. The application implementation is the next day's lab.

## D1-08 — SSH control channel, within the Ubuntu/WLAN block

Follow [SSH.md](SSH.md) after the WLAN up/status/check steps and before disconnecting USB-C. Find the address of each box, compare its host-key fingerprint through trusted ADB, connect with Windows OpenSSH, verify `id -u` and firmware, and download `/etc/build_version` with SCP. Use about five minutes within D1-03/D1-07's existing 50 minutes; do not add a new agenda block.

Keep the WLAN connected while using it for SSH. The preceding WLAN disconnect/radio-off exercise must finish before establishing SSH, or be omitted. Existing host ADB helpers still require ADB; complete staging/transfers before removing the PC's USB-C cable. The manual documents the Type-A/Type-C exclusion. SSH login/SCP passed; USB-C removal, camera detection and HDMI comparison remain separate pending checks.

Pass: IP/box identity and host key verified, root shell usable over the LAN, and sample download matches the target. Use this shell for subsequent manual target commands. Fallback: recover ADB by reconnecting USB-C, recognizing that this can make USB-A unavailable again.

## D1-04 — Manual RIL bring-up and debug, 50 min

Follow [CELLULAR_RIL.md](CELLULAR_RIL.md) on the target. Open `/usr/bin/qlril-api-test` after Linux root login. Type menu numbers at the application's prompt, one at a time.

1. Use `0` for help, `4` for SIM slot, `21` for SIM readiness, `20` for operator and `29` for signal.
2. Use **`70`** to query data registration and reported RAT. Registered home/roaming states are 1/5. RAT14 is LTE,19 LTE_CA,20 NR. Record the actual result.
3. Query `73` before setup. If no session is active, use **`71`**, then **`d`** at its default/others prompt. Review status/interface/IP/DNS/gateway/MTU and route/DNS setup results. A different operator may need a different profile.
4. Query `73` again. Use `6` for AT debug. `AT`, `AT+CPIN?`, `AT+CEREG?`, `AT+COPS?`, `AT+CSQ` and `AT+QENG="servingcell"` worked on this firmware. Use `-1` to leave the AT submenu and another `-1` at the main menu to exit.

Teach registration and IP-session activation as separate states. The supplied owner run activated call0 on rmnet_data0. Live queries confirmed SIM ready, TIM, registered/RAT19 and an active call. The serving-cell query printed LTE. NR SA/NSA is not confirmed. Exiting the app left data active; option74 deactivates a call, but that cycle has not been tested here.

Timing: access/menu5min, SIM/operator/signal10min, registration/RAT10min, setup/list15min and AT/debug10min. Full menu, side effects and tested-versus-menu-only status are in the guide. Avoid changes to SIM locks, radio preference, RNDIS or resolver files during the basic lab.

Pass: student can explain70, create data with71/d when needed, confirm73 and map the returned interface to Linux. Retain the returned values for that box instead of copying example addresses. Event acceptance still requires repetitions and actual radio evidence for any 5G claim.

The [focused radio check](CELLULAR_RIL.md#5a-focused-check-is-this-session-actually-using-5g) sampled RIL and AT before/during/after two bounded cellular downloads. It observed LTE/LTE_CA, without confirmed NR. Use that section to reproduce the check manually and distinguish absent 5GS registration from inconclusive NSA evidence.

## D1-05 — RMNET, routing, IP reachability and DNS, 50 min

```sh
sh target/network.sh
```

Before running, set the observed interface and known reachable test endpoints in `config/lab.env`. Explain the default route, policy rules, source address and RX/TX counters. Compare the normal route lookup with traffic explicitly bound to the cellular interface.

The script uses `curl --noproxy '*' --interface` and records counters. When ping supports `-I`, it also performs bound ICMP and preserves failures. This BSP ping lacks `-I`, so the script reports ICMP skipped and HTTP-only success rather than claiming numeric ICMP acceptance. The manual guide shows the same short Linux checks. Its HTTP request may still resolve DNS using the system resolver. To isolate DNS over cellular, use an installed DNS tool supporting a specified source address/server and confirm packet capture/route behavior separately. Do not claim the supplied curl test isolates DNS.

Pass: HTTP succeeds through the selected data interface, counters move, and resolver limitations are understood. Record numeric ICMP as untested when the installed ping cannot bind. A successful unbound ping is only a general connectivity check. If ICMP is blocked by the operator, record that limitation and validate an agreed interface-bound TCP endpoint instead of declaring the radio broken.

Fallback: use a numeric application endpoint under team control to distinguish network reachability from DNS. Do not live-edit the management route.

## D1-06 — Cellular throughput and troubleshooting, 40 min

On the controlled server, allow the chosen TCP port and start `iperf3 -s -p 5201`. Set a numeric public IPv4 server address, port, duration and stream count in `config/lab.env`.

```sh
sh target/performance.sh
```

The script requires `iperf3 --bind-dev`, captures uplink and reverse/downlink JSON separately and preserves failures in its exit status. It limits duration to 1–60 seconds and parallel streams to 1–8. At 100 Mbps, a 10-second direction transfers about 125 MB before overhead; use an appropriate test SIM.

Record actual RAT evidence if available, RF/operator conditions, time, server, RTT/loss, UL/DL, counters and system load. No fixed minimum Mbps is promised by this package. Agree on an event baseline after measuring the real unit/site.

Fault walk-through: hardware/interface, session/IP, routing, numeric reachability, DNS, server/listener, then RF/load. A failed benchmark must remain a failed result even when the log file was saved successfully.

Pass: both directions succeed over the chosen interface and evidence includes counter changes and server conditions. Fallback: a clearly identified rehearsal recording from the same unit/build. Manual RIL debug is documented in CELLULAR_RIL.md. A later throughput rehearsal passed three cellular UL/DL pairs and the failed-endpoint control. Deactivate/reconnect was not exercised and is outside the current closure queue by owner decision. See evidence/iperf-public/20261101T195153557423Z-measure/RESULTADOS.txt.

## WLAN preparation and operation

The profile was recreated after reflash and revalidated on 1 November 2026: `wlan0`, `qb560d-training-wlan`, DHCP address `192.168.0.26/24` in this session, metric 600, DNS/HTTPS 200 and NTP. Review the [WLAN guide](WLAN.md) for scanning, interactive credential entry, DHCP, route selection, reconnection and the BSP dhcpcd ownership correction. Run `sh target/wlan.sh status` and `sh target/wlan.sh check` from the persistent lab.

Use this during platform/network preparation. Cellular tests must remain explicitly bound to the correct RMNET interface even when WLAN provides the default route. A later physical cold cycle passed: root shell 13.94 s, automatic WLAN connection 29.02 s from the operator marker, DHCP/DNS/HTTPS200 and later NTP synchronization. No manual WLAN activation was performed. See BOOT_WLAN.md.

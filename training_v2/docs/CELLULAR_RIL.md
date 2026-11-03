# Manual cellular bring-up and debug with qlril-api-test

Scope: D1-04 and D1-05, directly on the QB560D-EU running BSP **QDPA_Ubuntu20.04.003.51.303 V01**, Ubuntu 20.04.3. Inspected on 1 November 2026. Executable: **`/usr/bin/qlril-api-test`**. QLRIL library: **`202411060822`**. This lab uses the installed interactive application. No SDK build or automated modem bring-up is required.

**70 queries data registration. 71 sets up a data call.** A registered modem can still have no active IP session. Internet access alone does not identify NR5G, SA or NSA.

## 1. Open the target and the application

In PowerShell, from the extracted full training folder:

```powershell
$adb = (Resolve-Path 'tools/platform-tools/adb.exe').Path
& $adb devices -l
& $adb shell
```

The complete training package includes `tools/platform-tools/adb.exe`, relative to training_v2. With several devices, select the actual transport ID using `& $adb -t <ID> shell`. At the target's Linux login, enter `root` and the password supplied by the instructor. An authenticated shell in another window does not log in this one.

At the **target shell**, run:

```sh
id
command -v qlril-api-test
/usr/bin/qlril-api-test
```

Expect `uid=0`, `QLRIL_Init success`, library version and the menu. Enter the numbers below **inside the application**, at `Please input cmd index (-1: exit, 0: help):`. Typing `71` at a Linux shell produces `command not found`.

## 2. Check SIM and registration before activation

Enter each selection separately and read its response before continuing:

| Selection | Purpose | Observed on this box |
|---|---|---|
| `0` | Show full help/menu | Menu captured |
| `4` | Current SIM slot | Slot 1 |
| `21` | SIM/application readiness | Card present (1), USIM (2), application ready (5) |
| `20` | Operator | TIM, MCCMNC 72402 |
| `29` | Signal | LTE fields: signalStrength 23, rsrp 98, rsrq 13, rssnr 8, as printed |
| `37` | Automatic/manual network selection | 0, automatic |
| `38` | Baseband version | BP10.003(SG560DEUPAR60A02) |
| `75` | Preferred network setting | Raw value 11. This setting does not prove the serving RAT |
| **`70`** | **Current data registration and reported RAT** | **Registered (1), RAT 19 in the live query** |

For option 70, inspect `response[0]` (registration), `response[3]` (reported data radio technology) and the accompanying fields. In the RIL definition: registration 0 = not registered/not searching, 1 = home registered, 2 = searching, 3 = denied, 4 = unknown, 5 = roaming registered. A result other than 1 or 5 needs investigation before setup. The application's short example for state 2 omits the searching distinction.

RAT codes relevant here: **14 = LTE, 19 = LTE_CA, 20 = NR**. These codes come from `RIL_RadioTechnology`, not the preferred-network-type enumeration. The owner supplied RAT 14; the live read returned 19. An additional serving-cell AT query printed LTE. This evidence does not establish NR/SA/NSA, and an LTE anchor report alone does not exclude an NSA combination. Keep the 5G demonstration conditional on explicit serving-radio evidence at the event.

## 3. Activate data manually with 71

First enter **`73`** (`QLRIL_GetDataCallList`). If it already lists an active call with an interface/IP, use that session. Do not create repeated calls merely to repeat the demo.

When no call is active and the SIM/operator setup is ready, enter **`71`**. At this exact prompt:

```text
Input an character(d: default; o: others; -1: exit):
```

Enter **`d`** to use the application's default data-call configuration. The supplied owner session demonstrated this sequence successfully. The default is specific to the current SIM/BSP configuration; it does not guarantee a correct APN/authentication profile for every operator. The `o` branch is the alternative configuration path. Its field prompts were not exercised, so this guide does not invent APN values or input sequences. If the default fails, record the returned status and review the operator configuration with the instructor.

Expected evidence from the owner's successful setup:

```text
status:0, retry:-1, call_id:0, active:up
type:IP, ifname:rmnet_data0
addresses:100.65.195.62/30
dnses:189.40.198.90 189.40.198.91
gateways:100.65.195.61, mtu:1500
QLRIL_SetDNSByInterface success
QLRIL_SetRouteForIPV4V6 success
```

These addresses are examples from that session. Use the newly returned interface/IP on each training box. This sample's setup flow also installs DNS and routes, which can change the path used by WLAN/Ethernet traffic. Inspect the resulting configuration before continuing. The private cellular address does not imply public inbound reachability.

Enter **`73`** again to confirm the call. Record call ID, active state, interface, address, DNS, gateway and MTU. Enter **`-1`** at the main menu to exit the application. In the supplied session, data remained up after `QLRIL_Exit success`. Exiting the test application does not mean deactivating the data call. Option **74** explicitly deactivates a selected data call; its prompts/reconnect cycle were not tested in this inspection.

**Reorganization revalidation, 2 November 2026 UTC:** with no call initially listed, `71`/`d` printed `QLRIL_SetupDataCall failed with return:-4`. The following `73` nevertheless reported call 0 active on `rmnet_data0`; bound HTTPS and three cellular UL/DL pairs passed. Preserve both observations: this validates the resulting data path, not a successful return from the setup API. Do not repeat `71` while `73` already shows an active call. The meaning/cause of `-4` on this BSP remains unconfirmed; no APN, preferred-radio setting or teardown was changed to hide it. See the [post-reorganization validation](VALIDACAO_POS_REORGANIZACAO.md).

## 4. Inspect Linux and prove application traffic

Back at the target shell, use the interface returned by 71/73:

```sh
CELL_IF=rmnet_data0
ip -d link show dev "$CELL_IF"
ip -4 addr show dev "$CELL_IF"
ip -4 route show table all
ip rule show
ip -4 route get 1.1.1.1
cat /etc/resolv.conf
ip -s link show dev "$CELL_IF"
curl --noproxy '*' --interface "$CELL_IF" -4 --fail \
  --connect-timeout 5 --max-time 20 -o /dev/null \
  -w 'HTTP=%{http_code} remote=%{remote_ip} total_s=%{time_total}\n' \
  https://example.com/
ip -s link show dev "$CELL_IF"
```

The TCP connection uses the selected interface. DNS may still use the system resolver; this is not an isolated cellular DNS test. A successful unbound `ping google.com` proves general reachability, but cannot select the cellular path when several networks coexist. The BSP's BusyBox ping lacks `-I`; do not use an unsupported binding option or silently substitute an unbound ping. The optional `target/network.sh` now reports `ICMP_SKIPPED` and `HTTP_PASS_ICMP_NOT_TESTED` on that ping build. Configure `CELL_IF` in `config/lab.env` before using it.

The initial live kernel route showed `default via 100.65.195.62 dev rmnet_data0 metric 500`, while RIL listed gateway `100.65.195.61`. These are the observed outputs. Do not copy either address as a universal route or rewrite routes blindly. Retain both outputs when investigating BSP behavior.

Pass: ready SIM, registered data state, active call mapped to a Linux interface/IP, and successful interface-bound application traffic with RX/TX evidence. NR confirmation, throughput and repeated deactivate/reconnect are separate acceptance items. A later iperf3 rehearsal passed against an owner-authorized public server: three UL/DL pairs plus a local failed-endpoint control. See [measured results](../evidence/iperf-public/20261101T195153557423Z-measure/RESULTADOS.txt).

## 5. Send AT queries through menu 6

At the main RIL menu, enter **`6`**. The prompt changes to:

```text
Please input AT command(-1: exit):
```

Enter one command per prompt. These queries were executed on this firmware:

| AT query | Observed response | Debug use |
|---|---|---|
| `AT` | `OK` | Check AT request/response path |
| `AT+CPIN?` | `+CPIN: READY`, `OK` | SIM readiness |
| `AT+CEREG?` | `+CEREG: 0,1`, `OK` | EPS registration response |
| `AT+COPS?` | `+COPS: 0,0,"TIM TIM",7`, `OK` | Operator/current access response |
| `AT+CSQ` | `+CSQ: 23,99`, `OK` | Basic signal fields |
| `AT+QENG="servingcell"` | `"servingcell","NOCONN", "LTE", "FDD"` and RF fields, `OK` | Vendor serving-cell snapshot, LTE in this capture |

The last response included band 7, RSRP -102, RSRQ -12, RSSI -69 and SINR 12 as printed. The serial console wrapped its long line. Preserve the original field order and consult the matching vendor AT documentation before assigning unsupported meanings. `NOCONN` is the modem's printed state, not proof that the IP data call has failed. The named-query results describe this instant and can change.

Enter **`-1` once to leave the AT submenu** and return to the main menu. Enter **`-1` again at the main menu** to exit the application. For the basic lab use the queries above. Radio/APN changes, resets and SIM PIN/PUK entry require a deliberate separate procedure; wrong PIN/PUK attempts can consume the SIM retry budget.

## 5A. Focused check: is this session actually using 5G?

**Result on 1 November 2026: LTE/LTE_CA observed; 5G NR not confirmed.** This is the result of the radio queries in this observation window, including during cellular traffic. The module's 5G capability, Internet access and a network preference are different facts from the current serving radio.

| Check | Actual response | Interpretation |
|---|---|---|
| RIL `70`, four samples before/during/after traffic | Registration 1, RAT 19 in every sample | Registered, reported LTE_CA |
| Menu 6: `AT+QENG="servingcell"`, five samples | LTE/FDD, band 7, EARFCN 3150, PCI 364. No NR serving component appeared | LTE in all exposed snapshots. Three snapshots occurred during the downloads |
| `AT+COPS?` | `+COPS: 0,0,"TIM TIM",7` | Current operator/access response consistent with LTE |
| `AT+CEREG?` | `+CEREG: 0,1` | EPS registration reported active |
| `AT+C5GREG?`, three samples | `+C5GREG: 0,0` | No 5GS registration reported. The first 0 is the URC presentation setting, the second 0 is registration status |
| RIL `73` before/after | call 0, active up, rmnet_data0, 100.65.195.62/30 | Existing IP data call remained active |
| RIL `75` | Raw preferred-network value 11 | AOSP names 11 LTE_ONLY. Treat this as a configuration clue until the BSP-specific mapping is confirmed |
| `AT+QNWINFO`, `AT+QENDC`, `AT+QCAINFO`, `AT+QNWPREFCFG="mode_pref"` | `ERROR` on this application/BSP path | These attempted diagnostics supplied no usable result. An AT error does not prove lack of 5G capability or network coverage |

`C5GREG` concerns 5GS registration. **Its 0,0 response alone does not exclude LTE-anchored NSA.** For NSA, seek explicit valid NR serving-cell/component information alongside LTE. This check did not obtain it. The vendor reference shows NR5G-SA and LTE plus NR5G-NSA serving formats for other module families; command support and output on this smart-module BSP must be checked directly. The `NOCONN` label remained in QENG even during successful data transfers, so the guide does not use that label as an IP-connectivity verdict.

Two **2 MiB** downloads completed through `rmnet_data0`, each deliberately limited to 64 KiB/s: HTTP 200, source 100.65.195.62, 2097152 bytes, 31.860399 s and 31.860918 s. RX/TX increased on the same interface. Total application payload was 4 MiB. The rate limit creates a window for observation and prevents these times from being a throughput measurement. RIL 70 and QENG still reported LTE_CA/LTE in the sampled active window. This does not trace the bearer used for each byte or exclude a transient NR state between samples.

### Reproduce manually with two target shells

1. In the first authenticated root shell, run `/usr/bin/qlril-api-test`. Query 70 and 73. Query 75 if discussing the preferred network, then enter 6 for AT. Read each response separately.
2. At the AT prompt, send `AT+QENG="servingcell"`, `AT+COPS?`, `AT+CEREG?` and `AT+C5GREG?`, one command at a time. Record the entire QENG response, including any additional NR line. Mark an ERROR as unsupported/unavailable for that query path.
3. In a second authenticated root shell, run the bounded download below. It uses up to 2 MiB per run plus network overhead. Use the interface actually returned by 73.

```sh
CELL_IF=rmnet_data0
curl --noproxy '*' --interface "$CELL_IF" -4 --fail \
  --connect-timeout 5 --max-time 40 --limit-rate 64k \
  --max-filesize 2097152 -o /dev/null \
  -w 'HTTP=%{http_code} local=%{local_ip} bytes=%{size_download}\n' \
  'https://speed.cloudflare.com/__down?bytes=2097152'
```

4. While the second shell is downloading, repeat QENG and C5GREG in the first. To query RIL 70 during activity, use `-1` to return from AT to the main menu, query 70, then 6 to return to AT. Repeat once after the transfer. Confirm the session with 73 and exit the main menu with -1.
5. A positive NR observation needs explicit current NR evidence, such as a serving NR5G-SA result or an LTE/NR5G-NSA serving combination with valid NR fields. Keep registration, advertised capability and active serving information separate. A 5G icon or a preference value alone is insufficient.

The two host-UTC traffic windows were 19:28:20–19:28:52 and 19:29:54–19:30:26. The observed call/IP stayed the same. No 71 setup, 74 teardown, 76 preference change, APN change, radio reset or route change was performed. **Next checks if 5G is required:** confirm the vendor mapping for preferred value 11 and the intended NR-enabled configuration, SIM/operator provisioning and coverage at the event. The present evidence does not identify which of those conditions is responsible. Change radio settings only as a separate deliberate procedure using the matching BSP documentation.

Evidence: [condensed radio results](../evidence/ril/20261101-5g-verification/summary.json) and [timestamped RIL/AT responses](../evidence/ril/20261101-5g-verification/queries.txt). References: [AOSP RIL definitions](https://android.googlesource.com/device/generic/goldfish/+/bf3559a47ee8a4937035596a0a5c64273bbb0923/radio/ril/ril.h), Quectel [RG50xQ/RM5xxQ reference](https://www.quectel.com/content/uploads/2024/05/Quectel_RG50xQRM5xxQ_Series_AT_Commands_Manual_V1.2.pdf), sections 5.5/5.20/5.22, and [Cloudflare's endpoint documentation](https://github.com/cloudflare/speedtest). The Quectel manual covers another product family; the actual responses above are the acceptance evidence for this box.

## 6. Complete menu reference

Status legend: **live** = queried in this inspection, **owner** = successful execution in the supplied transcript, **menu** = present in help only, with no functional acceptance. Menu presence is not evidence that a feature works on this board. Names below reproduce the installed menu, including deprecated entries and `NEMA` spelling.

| Index | Installed function | Purpose / effect | Status |
|---|---|---|---|
| 0 | Help | Display menu | live |
| 1 / 2 / 3 | QLRIL_Init / QLRIL_Exit / QLRIL_GetVersion | Library lifecycle/version. Startup initialized and printed version, main-menu -1 exited; standalone 1/2/3 not selected | startup/exit live |
| 4 / 5 | QLRIL_GetSimCardSlotId / QLRIL_SetSimCardSlotId | Read slot / change slot | 4 live, 5 menu |
| 6 | QLRIL_SendAT | Interactive AT submenu | live |
| 7 | QLRIL_ResetQcrild | Reset RIL daemon, can interrupt data | menu |
| 8 / 9 | QLRIL_GetDefaultTimeout / QLRIL_SetDefaultTimeout | Read/change request timeout | menu |
| 10 / 11 | QLRIL_AddUnsolEventsListener / QLRIL_DelUnsolEventsListener | Add/remove unsolicited event listener | menu |
| 12 / 13 | QLRIL_RegisterUnsolEvents / QLRIL_UnregisterUnsolEvents | Subscribe/unsubscribe events | menu |
| 19 | QLRIL_GetIMSIForUSIM | Read subscriber identity, sensitive | menu |
| 20 / 21 | QLRIL_GetOperator / QLRIL_GetIccCardStatus | Operator and SIM/app status | live |
| 22 / 23 | QLRIL_SetRadioPower / QLRIL_SetScreenState | Change radio power/screen indication | menu |
| 24 | QLRIL_RequestShutdown | Shutdown request, deprecated | menu |
| 25 | QLRIL_GetDeviceIdentity | Device identifiers, sensitive | menu |
| 26 / 28 | QLRIL_GetIMSI / QLRIL_GetIMEI | Subscriber/device identities, deprecated | menu |
| 27 | QLRIL_GetIMSIForApp | App subscriber identity, sensitive | menu |
| 29 / 30 | QLRIL_GetSignalStrength / QLRIL_GetPhoneNumber | Signal / phone number if available | 29 live, 30 menu |
| 31 / 32 / 33 | QLRIL_SupplyIccPin / QLRIL_SupplyIccPuk / QLRIL_ChangeIccPin | Unlock/change SIM credentials, limited retries | menu |
| 34 / 35 | QLRIL_QueryFacilityLockForApp / QLRIL_SetFacilityLockForApp | Query/change SIM facility lock | menu |
| 36 | QLRIL_IccIOForApp | Low-level ICC I/O, request may write SIM | menu |
| 37 / 38 / 39 | QLRIL_GetNetworkSelectionMode / QLRIL_GetBasebandVersion / QLRIL_GetSimIccId | Selection mode, firmware, ICCID (sensitive) | 37/38 live, 39 menu |
| 140 | QLRIL_GetNITZTime | Network time query | menu |
| 40 / 41 / 42 | QLRIL_GetVoiceRegistrationState / QLRIL_GetVoiceRadioTechnology / QLRIL_GetImsRegistrationState | Voice RAT/registration and IMS registration | menu |
| 43 / 44 / 45 | QLRIL_Dial / QLRIL_AcceptCall / QLRIL_RejectCall | Place/accept/reject voice calls | menu |
| 46 / 54 | QLRIL_GetCurrentCalls / QLRIL_GetCurrentCallsByAtCmd | Query calls using RIL/AT | menu |
| 47 / 48 / 49 | QLRIL_HangupConnection / QLRIL_HangupWaitingOrBackground / QLRIL_HangupForegroundResumeBackground | End selected call groups | menu |
| 50 / 51 | QLRIL_GetMute / QLRIL_SetMute | Read/change mute | menu |
| 52 / 53 | QLRIL_SwitchWaitingOrHoldingAndActive / QLRIL_Conference | Swap calls / conference | menu |
| 56 / 57 | QLRIL_IMSServerState / QLRIL_IMSServerEnable | IMS server state/enable controls | menu |
| 58 / 59 | QLRIL_IMSSendImsRegistrationState / QLRIL_IMSSendRoamingRegistrationState | Send IMS/roaming state indications | menu |
| 60 / 61 | QLRIL_SendSms / QLRIL_SendSmsByPDU | Send SMS, may incur charges | menu |
| 62 / 63 | QLRIL_SendImsGsmSms / QLRIL_SendImsGsmSmsByPDU | Send IMS GSM SMS | menu |
| 70 | QLRIL_GetDataRegistrationState | Query registration and data RAT | live, owner |
| 71 | QLRIL_SetupDataCall | Activate session, default sample also sets DNS/routes | owner `d` |
| 72 | QLRIL_SetDataAllowed | Change allowed data state | menu |
| 73 | QLRIL_GetDataCallList | Query active calls and network parameters | live |
| 74 | QLRIL_DeactivateDataCall | Deactivate selected data call | menu |
| 75 / 76 | QLRIL_GetPreferredNetworkType / QLRIL_SetPreferredNetworkType | Read/change network preference | 75 live, 76 menu |
| 77 / 78 | QLRIL_AppendDNSForIPV4V6 / QLRIL_ClearResolvConfFile | Append DNS / clear resolver file, affects host resolution | menu |
| 79 / 80 | QLRIL_EnableRNDIS / QLRIL_DisableRNDIS | Change USB RNDIS network function | menu |
| 81 | QLRIL_IMSSendDataAllowedStatus | Send IMS data-allowed indication | menu |
| 82 / 83 | QLRIL_SetRouteForIPV6 / QLRIL_SetDNSByInterface | Modify IPv6 route / interface DNS | menu, 83 also appears in owner's setup flow |
| 90 / 91 / 92 | QLRIL_GNSS_CLIENT_OPEN / QLRIL_GNSS_NEMA_TYPE / QLRIL_GNSS_START_FIX | GNSS client/type/start, menu labeled **For Qrb** | menu, support unverified |
| 93 / 94 / 95 | QLRIL_GNSS_STOP_FIX / QLRIL_GNSS_CLIENT_CLOSE / QLRIL_GNSS_NEMA_GetLocation | GNSS stop/close/location, **For Qrb** | menu, support unverified |
| -1 | Exit | Leave current submenu or exit main application | live, owner |

Calls/SMS, GNSS, reset, slot switching, PIN/PUK, network preference changes and session teardown were not exercised. Do not portray this catalog as acceptance of those features. Mask IMSI, IMEI, ICCID, phone numbers and credentials before sharing logs.

## 7. Evidence and reproduction checklist

Owner evidence: initial 70 reported registered/RAT14, 71/d established call0 on rmnet_data0, route/DNS setup succeeded, app exit left the interface up, unbound ping returned 4/4 with 0% loss and average93.878ms. This establishes the supplied manual setup result, not a throughput benchmark.

Live inspection: same executable/library/BSP, read-only menu queries and six AT queries above, active call0 confirmed by73. The existing session was preserved. The later bound HTTPS returned HTTP200 with cellular source100.65.195.62,0.306503s and RX+6023/TX+1801bytes. The updated probe passed HTTP-only, and missing-interface/closed-endpoint controls returned nonzero. See [live evidence](../evidence/ril/20261101-manual/summary.json), [current firmware summary](../evidence/CURRENT_FIRMWARE.json) and [recorded results](TARGET_RESULTS.md). No fresh71 activation, deactivate/reconnect, NR SA/NSA confirmation or iperf3 measurement was performed in this inspection.

For each training box, record the label/BSP, library version, slot/readiness, operator,70 state/RAT,71 status when needed,73 call/interface/IP, Linux route/DNS and bound HTTP/counters. Repeat manually under the actual SIM/APN configuration. Keep the 50-minute D1-04 allocation: access/menu5min, SIM/operator/signal10min,70 interpretation10min,71/73/manual setup15min, AT debug/recap10min. D1-05 keeps its separate50minutes for Linux networking.

References: installed menu and actual device output are the board-specific sources. The [AOSP RIL header](https://android.googlesource.com/device/generic/goldfish/+/bf3559a47ee8a4937035596a0a5c64273bbb0923/radio/ril/ril.h) defines registration/RAT codes. The [Quectel QLRIL example](https://docs.quectel.com/zh/Quectel%20Pi/Quectel%20Pi%20M1_L1/%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97/%E5%AE%9A%E4%BD%8D/%E5%AE%9A%E4%BD%8D.html) illustrates the application's menu approach on another board; it does not certify that board's GNSS features on this QB560D-EU.

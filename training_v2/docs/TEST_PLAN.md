# Verification and acceptance

## Evidence levels

1. **Software QA on preparation computer:** syntax, HTTP behavior, preprocessing/decoding and actual CPU inference. This verifies source behavior on that machine.
2. **Target compatibility:** each required command/demo runs on the physical Ubuntu QB560D-EU, with actual runtime/model hashes and exit status.
3. **Event acceptance:** three consecutive runs on the event BSP/configuration, visual correctness, timing within the session budget, and an available fallback.

Never promote a host test to target acceptance. `docs/acceptance.csv` records actual target progress and pending cases. The five AI reference inputs passed three target executions and the systemd update/rollback lab passed. MobileNet V1 CPU/GPU/HTP is validated on the supplied reference image and included in the runtime block; dataset accuracy remains outside this acceptance. Manual RIL setup is documented using the owner activation and live queries. Fresh setup repetition, teardown/reconnect and NR confirmation were not exercised and are outside the current closure queue by owner decision. Camera remains optional. Read TARGET_RESULTS.md and STATUS.md for measured scope, agenda mapping and remaining controls.

Current revalidation: [CURRENT_FIRMWARE.json](../evidence/CURRENT_FIRMWARE.json). The earlier local rehearsal excluded cellular/iperf3. A later manual RIL inspection and bound HTTP passed separately. The subsequent iperf3 rehearsal also passed three cellular UL/DL pairs plus a failed-endpoint control; see evidence/iperf-public/20261101T195153557423Z-measure/RESULTADOS.txt. These tests are not included in `host/rehearse_local.py`. The local suite and GPU/HTP runners use authenticated ADB and the persistent /opt payload. One physical cold boot and automatic WLAN recovery subsequently passed; see BOOT_WLAN.md. Camera remains an explicit gate. The authenticated hosted AI Hub compile/inference/profile and local CPU/GPU deployment passed separately; the complete timed teaching rehearsal remains pending.

Focused NR assessment: [radio evidence](../evidence/ril/20261101-5g-verification/summary.json). Four RIL 70 and five QENG samples reported LTE_CA/LTE, including samples during two rate-limited 2 MiB downloads. C5GREG reported 0,0. This inspection completed with **NR not confirmed**; positive NR was not demonstrated and is outside the current closure queue by owner decision. ERROR responses from additional AT diagnostics are retained as limits, not radio state. Follow the manual two-shell procedure in CELLULAR_RIL.md.

## Local software checks

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/run_ai_smoke.py
python ai/fetch_models.py --verify
```

Unit/HTTP tests cover input quantization, output dequantization, detection label offsets and thresholding, pose offsets, hand-presence gating, finger rule, segmentation shape/argmax, safe archive member reading, HTTP 200/404 behavior and legacy ADB transport/return handling. Smoke tests execute all five real models on the preparation computer. Target reference tests are separate and record the physical unit's runtime and results.

POSIX shell scripts also require `sh -n` syntax validation. Rehearse the benchmark's failed-server case on the target: it must return nonzero and retain separate uplink/downlink evidence. This checks that saving a log does not conceal a network failure.

## Target test cases

| Demo | Positive case | Negative/recovery case | Acceptance evidence |
|---|---|---|---|
| D1-01 | Inventory over selected ADB serial | Disconnected or ambiguous ADB devices must fail selection | Inventory log, OS/kernel/arch |
| D1-02 | Cold boot and usable shell | Explain a known service/boot error without modifying production services | Boot log and measured access time |
| D1-03 | Tagged logger event in journal | Missing logger/journal routing returns failure/configuration work | Event tag and journal excerpt |
| D1-04 | Manual SIM/70/71d/73 workflow,6 AT queries, interface mapping | Interpret missing SIM/unregistered/failed call from responses without repeated activation | Owner setup trace and live RIL summary; NR/reconnect pending |
| D1-05 | Bound HTTP and counters; bound ICMP only when supported | Unreachable endpoint/nonexistent CELL_IF fails; unsupported ping-I is explicitly skipped | HTTP status, source IP, counters, routes, resolver note |
| D1-06 | UL and DL against controlled server | Closed server port/unreachable server must fail | Both JSON files, counters, conditions |
| D1-07 | WLAN DHCP, DNS, HTTPS and NTP | Reconnect after reboot; preserve cellular test interface binding | Profile/status/check evidence, no credentials |
| D1-08 | Verify LAN IP/host key; SSH root identity; SCP sample download | Unverified host key must not be bypassed; recover ADB if SSH is lost | Sanitized SSH summary; USB-C removal and peripheral continuity recorded separately |
| D2-01 | Health/telemetry and 404 | Process stop makes health unavailable | HTTP result and app version |
| D2-02 | Start/restart/version change/rollback/stop | Port conflict diagnosed using status/journal | Service log and version snapshots |
| D2-03 | ARM64 container health/logs/cleanup | Missing or wrong-architecture image rejected | Image ID, inspect, health and cleanup |
| D2-04 | Hosted compile/profile | Invalid model/job failure shown honestly | Job URLs, device, target artifact, profile |
| D2-05 | Reference top class and finite scores | Wrong/missing model input contract fails | CPU JSON, PNG, hashes |
| D2-06 | Person detection and plausible boxes | Control image reviewed for false positives | Labels, boxes, PNG and hashes |
| D2-07 | Visible joints align on person | Partial/occluded person limitations explained | PNG and confidences |
| D2-08 | Cropped open hand, later team-owned closed fist | Low presence produces no_hand; non-square input rejected | Crop, presence, rule result and PNG |
| D2-09 | Person/background boundary plausible | Empty/person-free scene inspected for false foreground | Overlay, fraction, PNG |
| D2-10 optional | Sensor captures valid JPEG | Missing node/plugin fails with explanation | Sensor identity and captured frame |
| D2-11 | Matched MobileNet V1 DLC executes on HTP | Wrong artifact/runtime fails and remains failed | DSP graph profiling, hashes and numerical comparison with CPU of the same DLC |
| D2-12 | Same TFLite on CPU and OpenCL GPU | Delegate failure remains failed without CPU retry | GPU log, output vectors, hashes and latency scope |

## Rehearsal record

Fill `acceptance.csv` for every repetition. Record actual target ID, OS/kernel, dependency versions, model/image hashes, date, operator/server conditions, command, exit status, visual judgement and file links. Keep raw identifiers and credentials out of presentation screenshots.

Do not impose invented Mbps/FPS thresholds. After the first real run, agree on minimum acceptable behavior with the team and record that threshold before the remaining repetitions. Measure end-to-end latency separately if the event claims it; the Python runner reports inference-call timing only.

## Slide synchronization

During development, slides use concepts, commands and explicitly labelled preparation-computer CPU reference outputs. Once a demo passes on target, replace its reference screenshot with the target artifact and keep the demo ID unchanged. Only add target latency/throughput numbers after the corresponding evidence exists. Freeze model hashes, runtime versions and slide revision together.

## Controles adicionais concluídos

[Onze controles públicos CPU/GPU/HTP](VISION_CONTROLS.md) foram executados e revisados, com galeria offline e limites visuais. As imagens de preparação foram selecionadas a pedido do proprietário; não há dependência de fotos particulares do evento. Cold boot/WLAN passaram em uma rodada física. Câmera e ensaio didático continuam separados.

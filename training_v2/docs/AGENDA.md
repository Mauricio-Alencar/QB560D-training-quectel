# QB560D-EU technical training agenda

Platform: QCM6490, Ubuntu 20.04.3 LTS and ADB. The cellular block includes manual qlril-api-test setup and debug, followed by Linux path checks. Five hours per day including a ten-minute break. Times are elapsed session time. Read [readiness and remaining work](STATUS.md) alongside this agenda. Boot and WLAN recovery passed one physical cycle: root 13.94 s/WLAN 29.02 s from the operator marker. See [measurement limits and reproduction](BOOT_WLAN.md).

Current rehearsal note (1 November 2026): the owner supplied successful71/d setup, and live RIL queries plus bound HTTP confirmed the active session. A later cellular iperf3 rehearsal passed three UL/DL pairs and a failed-endpoint control. NR SA/NSA and teardown/reconnect remain unverified and are outside the current closure queue by owner decision. See [manual RIL guide](CELLULAR_RIL.md). The local application/CPU/GPU/HTP/WLAN paths passed on the new firmware with root login. See TARGET_RESULTS.md for the camera and hosted-account limits. The time allocation below remains unchanged.

## Day 1: platform and cellular data path

| Time | Session | Demo IDs | Start slide | End slide | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| 00:00–00:20 | Platform and training goals | D1-00 | 1 | 5 | Recognize the confirmed configuration and lab boundaries |
| 00:20–01:00 | Yocto setup overview and platform discovery | D1-01 | 6 | 27 | Explain the conceptual setup, then collect the running platform inventory over ADB; no image build in this lab |
| 01:00–01:40 | Boot, access and diagnostics | D1-02 | 28 | 31 | Inspect boot and service health |
| 01:40–01:50 | Break |  | — | — |  |
| 01:50–02:40 | Ubuntu target environment, WLAN and SSH | D1-03, D1-07, D1-08 | 32 | 36 | Inspect filesystem/services/logs; reserve about 10 minutes for WLAN and 5 minutes for verified SSH/SCP and USB-A access preparation |
| 02:40–03:30 | Cellular session and data path | D1-04 | 37 | 38 | Operate RIL manually: SIM,70 registration,71/d setup,73 session,6 AT debug and interface mapping |
| 03:30–04:20 | RMNET, routing and DNS | D1-05 | 39 | 41 | Prove interface-bound traffic and distinguish resolver behavior |
| 04:20–05:00 | Performance and troubleshooting | D1-06 | 42 | 45 | Measure cellular RTT and UL/DL with recorded conditions |

## Day 2: target applications, containers and AI

| Time | Session | Demo IDs | Start slide | End slide | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| 00:00–00:40 | Application development and Yocto integration | D2-01 | 46 | 66 | Run the Python app and optionally compile native C; Yocto recipes/build commands are conceptual reference |
| 00:40–01:20 | Deployment, systemd concepts and operation | D2-02 | 67 | 78 | Start a systemd service, test health, inspect logs and stop it |
| 01:20–02:00 | Docker application deployment | D2-03 | 79 | 82 | Run an ARM64 image and inspect application isolation |
| 02:00–02:10 | Break |  | — | — |  |
| 02:10–02:50 | AI runtime, tensor contracts and CPU/GPU/HTP | D2-00, D2-11, D2-12 | 83 | 98 | Use 15 min for Edge AI concepts, workflow and contracts, run the validated MobileNet V1 comparison for 20 min and inspect profiling/limits for 5 min |
| 02:50–03:40 | Qualcomm AI Hub workflow | D2-04 | 99 | 105 | Demonstrate hosted compile/profile and separate it from local execution |
| 03:40–04:30 | Five vision demos | D2-05…D2-09 | 106 | 128 | Run classification, detection, pose, cropped-hand gesture and person segmentation |
| 04:30–05:00 | Final lab and Q&A | D2-10 optional | 129 | 133 | Inspect evidence, optionally capture one camera frame and review integration questions |

Five AI demos share a 50-minute block: classification 8 min, detection 10 min, pose 10 min, gesture 12 min and segmentation 10 min. MobileNet V1 GPU/HTP inference is already validated on the reference image; retain the static CPU path and saved target evidence as its contingency. The separate MobileNet V2/QAIRT 2.51 package is an optional extension or reserve example, not another time block. Camera remains optional. The first authenticated AI Hub compile/inference/profile and same-artifact local CPU/GPU run passed. A tested offline payload and 106-second replay of the validated logs are available in Qualcomm_AI_Hub_Training. The complete timed classroom rehearsal remains pending.

Current vision lesson selection: keep the existing 8/10/10/12/10-minute task split. Within the12-minute gesture slot, plan9minutes for the cropped-hand/closed-fist/no-hand controls and3minutes for the seven-gesture saved gallery. Download/deploy is preparation. MobileNet V2 remains reserve material. This is a proposed budget, not a completed timed teaching rehearsal.

## Presentation navigation

The main presentation contains **140 slides**, including the topic openers. The source slides retain the order defined by the presenter. Yocto remains conceptual, without build/setup labs.

The agenda tables are on slides **4** (Day 1), **5** (Day 2 overview) and **47** (Day 2 opening). Slide **107** details the five vision tasks. Start/end cells link to the current slide positions, including topic openers. Timing remains 300 minutes per day, including the break.

| Scope | First slide | Last slide | Navigation |
| --- | ---: | ---: | --- |
| Day 1 content | 1 | 45 | Agenda: 4 |
| Day 2 content | 46 | 133 | Agenda: 5 or 47 |
| Five vision demos and profile interpretation | 106 | 128 | Detailed map: 107 |
| Optional hand-gesture preparation | 134 | 139 | Download/deploy reference |
| Corporate closing | 140 | 140 | Thank you |

Slides **84–90** introduce Edge AI, deployment formats and the CPU/GPU/HTP routes inside the existing conceptual time budget. The shared vision controls are on **108–113**. The host HTP command list is on **111**, and target-only setup/commands are on **112–113**. Use prepared examples or one selected case during the short classroom slot. The existing 8/10/10/12/10-minute task split remains unchanged.

Slide **81** shows Docker HTTP requests and expected status codes. Slide **93** shows the model-inspection and hash-verification output. Slides **127–128** explain positive CYCLES rows and HTP execution profiling. Slide **130** shows the documented USB camera capture and CPU detection path. Capture and execution passed on the reference unit, with an empty detections array still requiring scene review. See [the camera evidence and reproduction guide](CAMERA_HDMI.md).

See the [complete numbered slide map](MAPA_SLIDES.txt). Numbers are one-based PowerPoint positions. Future manual insertions or reordering require refreshing the map and clickable agendas.

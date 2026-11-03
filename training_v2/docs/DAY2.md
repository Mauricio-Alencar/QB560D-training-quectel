# Day 2 presenter runbook

All local labs run on the QB560D-EU Ubuntu target. Start from the package root. Keep the validated runtime and models offline. Use the preparation computer for ADB/SSH, projection and, when needed, an AI Hub client environment. Yocto setup, cross-compilation and recipes are explained through conceptual slides. Participants do not execute a Yocto build or lab.

Use the [Day 1 SSH guide](SSH.md) for manual target commands and SCP downloads. Open two SSH terminals when a foreground app and a separate test client are required. Complete ADB staging before removing USB-C for USB-A camera testing; existing automated ADB runners retain their ADB transport.

Current root: `/opt/qb560d-training-payload`, prepared through `provision_target`. Authenticate root inside a manual `adb shell`, then enter this directory. Host runners authenticate automatically and default to this path. `python host/rehearse_local.py --repeat 3` from `training_v2` repeats the native/systemd/five-CPU-demo checks; GPU/HTP have separate comparison runners. See [current results](TARGET_RESULTS.md).

## D2-00 — Runtime inventory and AI concepts

Run `target/preflight.sh` and `sh target/ai.sh inspect`. Confirm Python ABI, actual interpreter, model shapes/dtypes and available CPU/runtime libraries. Explain CPU baseline, GPU delegation and QNN/HTP as separate execution paths. A library filename alone is insufficient evidence of acceleration.

The baseline demos explicitly record `backend: CPU`. XNNPACK is CPU acceleration. Do not relabel these results as NPU. The validated MobileNet V1 CPU/GPU/HTP comparison is covered in D2-11/12 within the 40-minute runtime block; camera remains optional.

## D2-01 — Application directly on target, 40 min

```sh
python3 app/telemetry.py --host 127.0.0.1 --port 8080
```

Keep it in the foreground and show its requests. In a second ADB shell:

```sh
cd /opt/qb560d-training-payload
sh target/application.sh test
curl --fail http://127.0.0.1:8080/telemetry
curl --fail http://127.0.0.1:8080/missing
```

The last request intentionally returns 404. Explain routing, JSON response, process lifetime and application version. Stop the foreground process with Ctrl+C and confirm `/health` fails. If target GCC already exists, optionally run `sh target/application.sh compile`, inspect architecture and execute the resulting native binary. This does not require an SDK.

Pass: health=200, telemetry contains version/machine/uptime, unknown route=404, and stopping the process makes the endpoint unavailable. Fallback: Python-only lab if GCC is absent.

## D2-02 — systemd deployment, 40 min

Confirm the foreground process from D2-01 has stopped and port 8080 is free. Review the service file with the team. From an approved root shell:

```sh
sh target/application.sh install-service
systemctl status qb560d-training.service --no-pager
journalctl -u qb560d-training.service -n 30 --no-pager
sh target/application.sh test
systemctl restart qb560d-training.service
sh target/application.sh test
sh target/application.sh stop-service
```

The installer reuses an identical training installation, refuses a differing one, and does not enable boot persistence. `sh target/application.sh rehearse-service` runs the full health/update/rollback exercise, restores APP_VERSION 1.0.0 and stops the service on exit. It passed on the connected unit. Show how process uptime resets after restarting and how the version changes in `/telemetry`.

Pass: service active, health succeeds after restart, version change/rollback visible, logs available, stop succeeds. Fallback: foreground execution and a unit/log recording from the same BSP if systemd is unavailable.

## D2-03 — Docker on the target, 40 min

Validated on 1 November 2026: Docker 29.9.2 ARM64 in the private `/opt/qb560d-docker-demo` installation, overlay2/ext4 and cgroup v1. The canonical sources, runtime, offline image, evidence and guide are together in [demos/docker](../demos/docker/README.md). Use that package for staging and installation.

On the target:

```sh
cd /opt/qb560d-docker-demo
systemctl start qb560d-docker-demo.service
sh target/demo.sh load
sh target/demo.sh run
sh target/demo.sh check
sh target/demo.sh logs
sh target/demo.sh stop
```

The app exposes `/health` and `/telemetry` on port 8081. Show the Dockerfile, immutable image, non-root user, read-only root, writable tmpfs and resource limits. The wrapper selects a private Unix socket. Host and network-none modes are validated; bridge/NAT and AI accelerator access in containers are separate exercises.

Three complete cycles passed. Tests included HTTP 200/404, UID 65534, EROFS, 128 MiB memory, 64 PIDs, configuration update/rollback, missing-image rejection with `--pull never`, load of the same image ID from the local archive and healthy execution with `--network none`. No global package-manager/BSP upgrade was required. The service is not enabled at boot.

Use the offline image and saved target logs as contingency. Use the [single presentation](../slides/QB560D_EU_Training.pptx) and the [Docker offline guide](../demos/docker/GUIA_ALUNO_OFFLINE.md). Suggested time: 5 min concepts, 10 min build/deployment files, 10 min endpoints, 10 min offline/isolation, 5 min questions.

## D2-04 — Qualcomm AI Hub Workbench, 50 min

Separate **hosted Qualcomm execution** from execution on this physical box. Show Models for model selection and Apps for reference applications. Use Workbench for compilation, profiling and numerical validation on a named hosted device. Select the device using the current account's device list; never assume a QCS6490 proxy or development kit is identical to this QB560D's software.

Before rehearsal, configure `qai-hub` using the official setup in a supported Python environment. Keep the API token outside scripts, slides and evidence. If the target's Python cannot run the current client, use Workbench in the browser or a preparation-machine environment. Local inference remains on the target.

```sh
qai-hub list-devices
python ai/workbench.py --model models/workbench_demo.onnx --device "EXACT HOSTED DEVICE NAME" --runtime tflite
```

`host/create_workbench_model.py` generates the small synthetic Conv/ReLU/GAP ONNX example after installing the `onnx` Python package in a preparation environment. Its purpose is to show compilation and profiling, not image recognition accuracy. The prepared ONNX file accompanies the package when generation has completed. For a product model, replace it with a reviewed model and its true preprocessing/validation dataset.

For the deterministic example, add `--input models/workbench_input.npy --expected models/workbench_expected.npy`. The script waits for compile and inference/profile jobs, downloads the artifact/profile and compares the single output with the saved reference. Without these arguments, it does not perform the reference comparison. Show the portal's actual job status and compute-unit summary. The earlier1 November check found no account. Later the account/API was configured,77 devices were listed, and compile j5q1v4l7g passed on Dragonwing RB3 Gen 2 Vision Kit (QCS6490, Qualcomm Linux1.6). Inference/profile j56mwo8vp then passed with max absolute error 4.0054e-05 and four GPU entries in the profile. The same 1992-byte TFLite passed on the local CPU with runtime 2.8.4 and max error 1.49e-08. The local GPU also passed with OpenCL/delegate log evidence, max error 2.98e-08 and median invoke 0.2543065ms. A separately packaged offline runner passed CPU/GPU. A 106-second captioned replay of the real logs is available, with no account credentials. The complete timed 50-minute teaching rehearsal remains a final-rehearsal task. See the accompanied guide for the next checks. This is independent of local QB560D firmware compatibility.

Pass: compile produces a deployable artifact and profile belongs to the selected hosted device; retain job links and profile. Local deployment remains a separate gate requiring matching runtime, input/output contract, correctness checks and target profiling. Fallback: job artifacts and screenshots captured during rehearsal. Account, queue and network availability remain external dependencies.

## D2-05 to D2-09 — Five static-image demos, 50 min total

The five original tasks also passed on QAIRT/QNN 2.51 HTP. The current host-driven HTP workflow is in [htp251/README.md](../htp251/README.md), with a [gallery of real target outputs](../htp251/results/index.html). From the training_v2 root, reuse `$py` and `$adb` from host setup:

```powershell
& $py host/htp251_workshop.py deploy --adb $adb
& $py host/htp251_workshop.py test-all --adb $adb
Invoke-Item htp251/results/index.html
```

Each CNN runs on HTP. Preprocessing, decoding, SSD NMS, gesture rules and rendering run on the host. The commands below retain the original TFLite CPU baseline for comparison. Both paths remain available; the new files live separately in `/opt/qb560d-ai-htp251`.

```sh
sh target/ai.sh verify
sh target/ai.sh classification --image media/grace_hopper.jpg
sh target/ai.sh detection --image media/grace_hopper.jpg
sh target/ai.sh pose --image media/grace_hopper.jpg
sh target/ai.sh gesture --image media/right_hands.jpg --crop 360 0 720 360
sh target/ai.sh segmentation --image media/grace_hopper.jpg
```

The TFLite CPU commands above create a JSON result and annotated PNG in `evidence/ai/<task>` on the target. Retrieve via ADB for projection. Output images use the resized model canvas, not original-image coordinates. Their `--runs`, `--warmup`, `--threads` and `--threshold` options are configurable. CPU default timing covers 20 calls after three warmups, measures `interpreter.invoke()` only, and reports median/p95 in milliseconds. It excludes image decode, preprocessing, annotation and transfer. The separate HTP 2.51 host runner uses three inferences with detailed profiles and saves its gallery under `htp251/results`; those measurements are not the CPU benchmark.

| ID | Model and visible result | Correctness check | Boundary |
|---|---|---|---|
| D2-05 | MobileNet V1, top-3 classes | The supplied portrait's reference top class is military uniform | Quantized uint8 input/output; labels include background |
| D2-06 | SSD MobileNet V1, boxes and labels | A person box overlaps the visible person; inspect unexpected detections | Label offset and box coordinate order matter |
| D2-07 | PoseNet, 17-joint topology | Visible head/shoulder joints align on the portrait; use a team-owned full-body photo for the event | Single-person argmax decoder; the portrait has only a partial body |
| D2-08 | Hand landmarks and a simple gesture rule | Supplied crop has high hand presence and reports open_hand | One square upright hand crop; no palm detector, tracking, thumb classification or general gesture vocabulary |
| D2-09 | DeepLabV3, class overlay | Person region follows the portrait; inspect face/body boundary | 21 Pascal VOC classes; no industrial custom-class claim |

For each task, also run a relevant negative/control image supplied by the team and inspect results. A successful invocation alone is not semantic correctness. A classifier always returns class scores even for irrelevant input. Gesture must return `no_hand` if presence is below threshold, and a blank scene may produce model-dependent false positives.

These five baseline weights come from TensorFlow/MediaPipe official assets. They are not represented as AI Hub exports. The AI Hub workflow is D2-04 and its generated artifact must receive its own profile before reuse with this runner. Do not substitute an exported model under an unchanged profile just because it has a `.tflite` extension.

## D2-10 — Optional camera frame

```sh
sh target/camera.sh /dev/video0 &&
sh target/ai.sh detection --image media/captured/frame.jpg
```

The script supports a V4L2 capture node or an explicit QMMF attempt, `sh target/camera.sh --qmmf 0`. Captures have a 15-second limit and successful output must decode as an image before becoming `frame.jpg`. In the initial inspection `/dev/video0` was absent; `/dev/video32` and `/dev/video33` were codecs. On 02 Nov 2026, after switching to SSH for USB-A operation, the UVC webcam enumerated at `/dev/video0` and produced a validated JPEG. CPU detection executed with no detections, median 35.613 ms; the photo still needs semantic review. A separate 640×480/25 fps live preview on HDMI completed and was visually confirmed. HDMI initially had no signal and recovered after restarting `init_display.service` and physically reconnecting HDMI; behavior after a new power-on is still untested. See [camera/HDMI reproduction and evidence](CAMERA_HDMI.md). QMMF was not retested with a MIPI sensor. The AI command above is capture-then-infer; the live preview does not run inference per video frame.

Pass: valid JPEG from the intended sensor and plausible inference result. Fallback: the five local-image demos.

## D2-11 — MobileNet on HTP v68, confirmed on this unit

Use the converted INT8 DLC from the original MobileNet TFLite, with the private SNPE 2.26 Ubuntu runtime. The ZIP includes the pinned runtime subset and Windows profile decoder in `offline/snpe226`. Run `python host/stage_snpe_runtime.py --check-only`, then `python host/stage_snpe_runtime.py` on the host. No SDK download or converter is needed for this replay. Full setup and reconstruction instructions: [HTP/DSP guide](HTP_DSP.md).

Inside `/opt/qb560d-training-payload` on the target:

```sh
sh target/ai.sh snpe --sdk-root runtime/qairt226-ubuntu --model models/mobilenet_v1_snpe_int8.dlc --image media/grace_hopper.jpg --backend cpu --cpu-fixed-point --input-mode normalized --warmup 10 --runs 50 --profiling off --output evidence/dlc-cpu-live-001
sh target/ai.sh snpe --sdk-root runtime/qairt226-ubuntu --model models/mobilenet_v1_snpe_int8.dlc --image media/grace_hopper.jpg --backend dsp --input-mode normalized --warmup 10 --runs 50 --profiling off --output evidence/dlc-htp-live-001
```

Use a new output directory for each run. From the host, `python host/run_htp_comparison.py` runs three alternating sessions for TFLite CPU/GPU and SNPE CPU-fixed/HTP, pulls outputs and decodes a separate detailed HTP profile.

Measured medians with the same DLC: CPU fixed point **6.748 ms**, HTP **1.130 ms**, ratio **5.97×**. Profile: 34 DSP entries, zero CPU entries, including graph input/output. Runtime order contains DSP only, unsigned PD; no CPU retry. Preprocessing and Python control still execute on CPU.

Top-1 agrees on the supplied image. The maximum probability difference is **4/256 versus CPU of the same DLC**, or 6/256 versus the original BSP TFLite CPU. This is a functional reference demo; dataset accuracy is not established. TFLite CPU uses two threads, SNPE CPU uses its runtime default. Measure inference separately from preparation/rendering.

The earlier TFLite Hexagon delegate failed at initialization. The working inference uses a complete matching 2.26 Ubuntu library set in a private directory; no firmware or BSP libraries were replaced. The current `/opt` payload persists. An explicit `/tmp` alternative needs restaging after reboot. The generic `target/qnn.sh` context-bin example remains conditional: it needs its own matched context artifact and input contract; the optional QAIRT 2.51 DLC examples use their own runners.

Pass: matching hashes, numerical comparison recorded and real DSP graph profiling. Use the CPU demos if this specific runtime path fails; do not relabel CPU fallback as HTP execution.

## D2-12 — MobileNet CPU/GPU comparison, confirmed on this target

Use the same classification model/input with the installed TFLite C runtime and its OpenCL GPU delegate:

```sh
sh target/ai.sh classification --image media/grace_hopper.jpg --backend cpu --vendor-c-api --threads 2 --warmup 10 --runs 50 --output evidence/demo-cpu
sh target/ai.sh classification --image media/grace_hopper.jpg --backend gpu --vendor-c-api --threads 2 --warmup 10 --runs 50 --output evidence/demo-gpu
```

On the preparation computer, from the `training_v2` directory, `python host/run_acceleration.py` repeats three alternating sessions and collects output arrays, logs, images and a comparison summary. Measured medians: CPU 25.41 ms, GPU 9.67 ms, speedup 2.63×. Top-1 matches; largest probability difference is 1/256. These are invoke-only timings, not end-to-end video FPS. One OpenCL GPU partition is confirmed in the runtime log. HTP/DSP execution is covered separately in D2-11 with the converted DLC and its CPU control.

The full Portuguese [AI Hub and deployment guide](../Qualcomm_AI_Hub_Training/GUIA_DEPLOY_AIBOX.md) provides the account setup, compile/inference/profile exercise, tiny ONNX reference and local TFLite deployment steps. The account/API is now configured; follow the [accompanied first-run guide](../Qualcomm_AI_Hub_Training/PASSO_A_PASSO_AIHUB.md) for the current hosted jobs, local deployment and recording.

## Optional QAIRT 2.51 / seven gestures extension

The manually added slides use the persistent runtime `/opt/qairt-isolated/2.51.40.260930`. Both the MobileNet V2 CPU/HTP test and all seven MediaPipe gesture labels passed again with the new login. The gesture run confirmed 21 graph executions with positive HTP cycles. From the complete workspace on the host:

```powershell
python runtimes/qairt_2_51/update_qairt.py test --runs 5
python demos/hand_gesture/gesture_demo.py test-all --backend htp
```

The ADB client is discovered through the Docker package; `--transport-id` selects a box when serials repeat. Logs and prediction images stay under each extension's `evidence` directory. Host image transforms/ROI handling are separate from the three target DLC graphs. Keep HTP as the validated gesture backend; the earlier CPU result for this w8a8 model was not accepted. This extension is separate from the single cropped-hand CPU baseline D2-08 and does not add time to the five-hour agenda automatically.

## Controles adicionais concluídos

[Onze controles públicos CPU/GPU/HTP](VISION_CONTROLS.md) foram executados e revisados, com galeria offline e limites visuais. As imagens de preparação foram selecionadas a pedido do proprietário; não há dependência de fotos particulares do evento. Cold boot/WLAN passaram em uma rodada física. Câmera e ensaio didático continuam separados.

Os 11 controles também passaram **inteiramente no target**, incluindo preparação e pós-processamento locais. Com o pacote instalado, no shell Linux: `cd /opt/qb560d-ai-htp251/htp-controls`, `sh run.sh check` e `sh run.sh run-all`; para uma entrada, `sh run.sh run closed-fist`. O modo local usa referências CPU já gravadas, sem executar CPU/GPU. O [guia de reprodução](VISION_CONTROLS.md) traz a cópia offline inicial, todos os comandos e a leitura dos resultados; os slides 112–113 mostram esse fluxo nesta revisão.

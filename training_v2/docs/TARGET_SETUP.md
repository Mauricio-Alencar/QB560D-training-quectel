# Target setup and rehearsal baseline

## Confirmed scope

QB560D-EU / QCM6490 / cellular 5G / Ubuntu 20.04.3 LTS. The owner supplied `/etc/os-release`. This identifies the distribution, but does not identify vendor BSP revision, kernel, Python ABI, glibc or installed AI libraries. Collect these using `target/preflight.sh` before installing anything.

All application development in this package runs directly on the target. No Yocto SDK, BSP rebuild or cross compiler is required. The cellular session is brought up manually with qlril-api-test before the Linux network checks.

Current measured BSP: `QDPA_Ubuntu20.04.003.51.303 V01`, kernel build 2 April 2026. The 1 November revalidation passed the native/CPU/GPU/HTP/WLAN paths with Linux root login. Cellular and iperf3 are deferred by the owner while the physical SIM setup is prepared. See [current results](TARGET_RESULTS.md).

For a newly flashed box, follow `provision_target/README.md` from the complete training tree first. The native payload is installed in `/opt/qb560d-training-payload`, private dependencies in its `.python-deps`, network wrappers in `/opt/qb560d-workshop/bin`, and QAIRT 2.51 in its separate owned directory. These tools do not appear in a plain global PATH. Use the environment file only for a lab that needs those wrappers: `. /opt/qb560d-workshop/env.sh`.

## Preparation order

After initial ADB staging and WLAN setup, complete [D1-08 SSH access](SSH.md). It covers the per-box IP, trusted host-key check, root login, SCP download and the USB-C-to-SSH transition required before testing USB-A peripherals. Keep ADB connected until SSH is verified. The manual ADB runners are not converted to SSH by this step.

### Validated path on this unit

The actual inventory found Python 3.8.10, NumPy, no pip, and `/usr/lib/libtensorflowlite_c.so` version 2.8.4. The package includes a small C API wrapper and the official Pillow 10.4.0 wheel for CPython 3.8/AArch64, with SHA256 in `wheelhouse/wheels.lock.json`.

On a fresh staging directory using the same ABI:

```sh
sh target/ai.sh prepare
sh target/ai.sh inspect
sh target/ai.sh verify
sh target/ai.sh classification --image media/grace_hopper.jpg
```

`prepare` expands Pillow only into `.python-deps` inside the lab directory. On repeat, it checks every wheel member and reuses identical content, including the private NumPy/Pillow directory created by the provisioner. It refuses modified or incomplete content. The shell entrypoint sets PYTHONPATH and falls back to the existing vendor C library when Python bindings are absent. Five models passed three reference executions on this path. No pip or SDK is required for it.

The observed `/data` mount has `noexec`, so do not put Python binary extensions or executables there. The default lab is now `/opt/qb560d-training-payload`, verified executable and persistent. The earlier `/tmp/qb560d-training` path is available with an explicit `--remote` argument and requires restaging after reboot.

### Other images or runtime environments

1. Run `host/adb_lab.py inventory`. Confirm `uname -m` is `aarch64`, root filesystem policy, available storage, user privileges and installed tools.
2. Confirm `python3 --version`, `ldd --version`, `python3 -m pip --version`, `systemctl --version`, `docker version`, and `iperf3 --version` where installed.
3. Stage runtime material via `host/adb_lab.py push`. Review `config/lab.env` on the target. This is a trusted shell file and must contain reviewed variable assignments only.
4. Reuse an existing BSP-supported AI runtime where possible. Check whether `tflite_runtime.interpreter`, `ai_edge_litert.interpreter` or `tensorflow.lite.Interpreter` imports successfully. The demo runner tries them in that order.
5. If dependencies are missing, use a virtual environment. Avoid modifying the vendor Python environment. Ubuntu 20.04 commonly uses Python 3.8, but measure the actual version.

Example, **only after package availability and the vendor image policy are confirmed**, during preparation rather than the public event:

```sh
python3 -m venv /opt/qb560d-venv
. /opt/qb560d-venv/bin/activate
python -m pip install -r ai/requirements-target.txt
python -m pip install --only-binary=:all: tflite-runtime==2.14.0
python ai/inspect_models.py
```

`/opt/qb560d-venv` is an example and requires appropriate permissions. `venv`/pip may not be installed. A tflite-runtime wheel must match **AArch64, Python ABI and glibc**. If no wheel matches, use the vendor-provided runtime/package. This package does not build a runtime or install a new Python version automatically. LiteRT 2.3.0 was used only for QA on the preparation computer, not selected as a mandatory target version.

For an offline rehearsal, obtain compatible wheels on a preparation machine, copy them to a reviewed wheelhouse and use `pip install --no-index --find-links /data/wheelhouse ...`. Do not copy a Windows environment or wheel to the ARM64 target.

## Application and service

The Python telemetry app uses the standard library. Test it in a shell before installing the service. The provided unit expects `/usr/bin/python3`, `/opt/qb560d-training/telemetry.py` and port 8080. It starts on demand and is not enabled at boot automatically.

Native C compilation is optional and uses target `gcc`. If it is missing, the Python application fully covers the direct deployment lab. Do not turn this into an SDK exercise.

## Docker

The D2-03 package is now validated and consolidated in [demos/docker](../demos/docker/README.md). It uses official Docker 29.9.2 ARM64 static binaries and Buildx v0.38.1 in `/opt/qb560d-docker-demo`, with its own daemon, socket, image storage and systemd unit. Package-manager control/list files were inconsistent on this BSP, so no Ubuntu package repair or global runtime replacement was performed.

Stage and install from that package, then run the reviewed offline image:

```sh
cd /opt/qb560d-docker-demo
systemctl start qb560d-docker-demo.service
sh target/demo.sh load
sh target/demo.sh run
sh target/demo.sh check
sh target/demo.sh stop
```

Use `sh target/docker.sh ...` within that directory to select the correct daemon. Do not assume a global `docker` command points to it. Three app cycles, security/resource checks, daemon restart and image reload/network-none execution passed. The archive and SHA-256 are in `demos/docker/offline`. Host/none networking is covered; bridge/NAT, Compose and GPU/HTP inside containers require separate validation. Static binary updates are manual; the unit is not enabled at boot.

## Camera and HTP

`camera.sh` is an optional V4L2/GStreamer single-frame path. Some BSPs use a vendor camera source or require explicit caps; a `/dev/videoN` node alone is insufficient evidence of capture support. Confirm the pipeline and sensor first.

`qnn.sh` uses only an **already installed** `qnn-net-run` and HTP backend. It requires a compatible context binary, the artifact-specific raw input list, BSP library paths and DSP firmware. It does not install QAIRT or a device SDK. Keep it optional until its outputs and profiling pass on this unit.

## ADB operational notes

Use a single authorized serial. `adb_lab.py` rejects ambiguous selection. Inventory does not require staging. Other scripts require `push` first. The host wrapper saves process exit status separately from log text.

The current firmware requests a Linux login inside `adb shell`. The host scripts prompt for the root password without echo and verify uid=0 before commands or transfers. The shared login helper is in `host/adb_transport.py` and the Windows ADB client is in `tools/platform-tools`; both accompany the complete training package. Credentials are not stored in the package.

This unit reports serial `?`. Transport IDs change after reconnecting, and multiple boxes may report the same serial. The wrapper selects a sole device automatically; use the current `--transport-id` with several boxes. It supports PTY-only legacy adbd, verifies the explicit remote exit marker and defaults to a 90-second command timeout. If a command times out, inspect the target process state before retrying. Do not assume the PTY carries a native remote exit status.

To access the local application from the preparation computer without changing target network configuration:

```sh
adb -s SERIAL forward tcp:8080 tcp:8080
adb -s SERIAL forward tcp:8081 tcp:8081
```

Then browse the local `/health` or `/telemetry` endpoints. Remove the forwards after rehearsal with `adb -s SERIAL forward --remove tcp:8080` and the corresponding 8081 command.

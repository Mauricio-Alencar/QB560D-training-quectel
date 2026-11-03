# D1-08 — SSH access and USB-A peripherals

Use this lab after WLAN setup in the Day 1 Ubuntu/WLAN block. Reserve about five minutes inside the existing 50-minute session. Use the same SSH terminal for the Day 2 application, systemd and vision commands.

## Why SSH is part of the lab

The QB560D user guide, section 4.10, states that USB Type-A Host and USB Type-C Device operation are mutually exclusive: connecting Type-C to the preparation PC as a USB device makes Type-A unavailable. Prepare the box through USB/ADB, establish and verify SSH over WLAN or Ethernet, then remove the PC's USB-C cable before testing a USB-A camera.

Keep the DC power supply connected. HDMI remains a separate diagnostic: this interface restriction does not establish that HDMI fails for the same reason.

## Requirements

- Target already provisioned in `/opt/qb560d-training-payload`.
- An approved WLAN profile, or a validated Ethernet connection, on a LAN reachable from the preparation PC. See [WLAN.md](WLAN.md) for creating the profile interactively.
- Windows OpenSSH Client (`ssh` and `scp`), or an equivalent SSH terminal.
- The target's Linux username and password supplied by the instructor. Enter the password at the prompt; do not put it in commands, slides or evidence.

On Windows PowerShell, confirm the client:

```powershell
Get-Command ssh, scp
```

If the client is missing, enable the Windows OpenSSH Client optional feature during host preparation. ADB remains available while the USB-C cable is connected.

## 1. Prepare the network while ADB is connected

From the full training workspace, reuse `$adb` from the host-prerequisites slide:

```powershell
& $adb devices -l
& $adb shell
```

Log in to Linux as `root`. In that **target shell**, activate the existing approved profile and read its actual address:

```sh
nmcli radio wifi on
nmcli --wait 45 connection up qb560d-training-wlan ifname wlan0
ip -4 addr show dev wlan0
```

Do not copy a previously observed IP to another box. DHCP can change it. This rehearsal used `192.168.0.26`; it is a recorded example, not the classroom configuration.

For Ethernet, use the address of the validated Ethernet interface instead. Keep the management LAN route and the RMNET data path distinct; SSH does not require a cellular connection.

While the trusted ADB shell is available, record the SSH host-key fingerprint:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

The fingerprint is public. Do not copy any file without the `.pub` suffix.

## 2. Connect from a second PowerShell window

Leave the ADB terminal open until SSH has passed:

```powershell
$boxIp = Read-Host 'IPv4 of this training box'
ssh "root@$boxIp"
```

For the first connection, compare the host-key algorithm and SHA256 fingerprint with the value obtained through ADB. Accept only the matching key, then enter the Linux password at the prompt.

Inside the **SSH target shell**:

```sh
id -u
hostname
cat /etc/build_version
cd /opt/qb560d-training-payload
sh target/preflight.sh
```

Expected: `id -u` prints `0`, the firmware belongs to the selected box, and the lab directory is available. If several boxes are in the room, keep a unit-label/IP record and confirm the identity before each exercise.

## 3. Transition from ADB to SSH

1. Finish staging and any ADB transfers or tests, including work in other chats.
2. Keep a working SSH terminal open and run `id -u` again.
3. Remove only the USB-C cable between the box and the preparation PC. Keep DC power, the USB-A camera and the HDMI cable connected.
4. In the SSH terminal, repeat `id -u`, then `lsusb` and `v4l2-ctl --list-devices`.
5. Select the camera's actual capture node from the new inventory before running the camera lab. `/dev/video32` and `/dev/video33` on the inspected BSP were codecs.

Update, 02 Nov 2026: the UVC webcam enumerated on USB-A while SSH was used for management. JPEG capture, CPU inference and live camera preview on HDMI completed. HDMI initially had no signal, then recovered after a graphics-service restart followed by physical HDMI reconnection, visually confirmed by the operator. This does not yet validate HDMI after a new power-on. See [the camera/HDMI guide and evidence](CAMERA_HDMI.md).

If SSH is unavailable, reconnect the PC's USB-C cable, recover the ADB shell and inspect the network and SSH service. Reconnecting USB-C can make USB-A unavailable again.

## 4. Use SSH during the demos

Commands documented as target commands run unchanged in the SSH shell:

```sh
cd /opt/qb560d-training-payload
sh target/diagnostics.sh
sh target/ai.sh inspect
sh target/ai.sh classification --image media/grace_hopper.jpg
```

For D2-01, open two SSH terminals: run the HTTP application in one and the endpoint tests in the other, as described in [DAY2.md](DAY2.md). D2-02 systemd commands use the same target shell. For Docker, change to `/opt/qb560d-docker-demo` and follow its guide.

For D2-10, follow the camera instructions only after identifying a real capture device. A successful SSH login does not establish camera or display compatibility.

The `host/adb_lab.py` and other existing ADB runners still use ADB. This guide adds manual SSH operation; it does not silently change their transport. Stage with ADB before disconnecting USB-C, or use reviewed SSH/SCP commands.

Do not run `wlan down`, disable the Wi-Fi radio or change its profile while relying on that WLAN for SSH. Reconnect ADB or establish a different validated management path first. This is why the WLAN slide's disconnect/radio-off steps are optional recovery demonstrations before entering this SSH lab.

## 5. Retrieve files with SCP

Run these commands in **PowerShell on the preparation PC**, not inside SSH:

```powershell
New-Item -ItemType Directory -Force .\ssh-download | Out-Null
scp "root@${boxIp}:/etc/build_version" .\ssh-download\
Get-Content .\ssh-download\build_version
```

The braces in `${boxIp}` separate the variable from the SCP colon. This download passed in the rehearsal, using the Windows client's default SCP/SFTP behavior.

To retrieve a known result file, replace `/etc/build_version` with its actual absolute target path. For example, after a camera capture has produced and verified that file:

```powershell
scp "root@${boxIp}:/opt/qb560d-training-payload/media/captured/frame.jpg" .\ssh-download\
```

Do not claim the example camera file exists until capture succeeds. Consult the corresponding demo's output directory for JSONs and annotated images. This rehearsal validated download; SCP upload was not part of this acceptance.

## Troubleshooting

| Observation | Check |
|---|---|
| WLAN unavailable | Wi-Fi radio state, saved profile, AP availability and the WLAN guide |
| SSH connection timeout | Current box IP, LAN reachability, client isolation, route and port 22 |
| Connection refused | SSH listener/socket/service on the target |
| Authentication denied | Correct box, instructor-provided user/password and effective SSH policy |
| Host-key mismatch | Verify the current key through trusted ADB; do not bypass the warning |
| SSH drops after WLAN down | Recover ADB and reactivate the approved profile |
| Camera absent while ADB works over USB-C | Apply the documented USB-A/USB-C transition above |

On this firmware, `ssh.socket` was active and accepted the LAN connection even though `ssh.service`/`sshd.service` were not active before the connection. Socket activation means an inactive service alone is not proof that SSH is unavailable. The measured `sshd_config` contained `ListenAddress 127.0.0.1`, but the active socket listened on port 22 and the LAN login passed. Do not rewrite SSH configuration based on one grep result; inspect the actual listener/socket and test the connection first.

## Acceptance and evidence

- Passed on 1 November 2026: WLAN activation, pinned-host-key SSH root login (`uid=0`) at the observed address, remote diagnostic commands and a 55-byte `/etc/build_version` download by SCP.
- BSP: QDPA_Ubuntu20.04.003.51.303 V01; kernel 5.4.219-perf.
- Pending: physical USB-C removal, continued SSH access after removal, USB-A camera enumeration/capture and the HDMI comparison. Cold-boot WLAN recovery remains its own checklist item.
- Sanitized record: [SSH summary](../evidence/ssh/20261101-manual/summary.json).
- Source: Quectel QB560D Series 5G Edge Computing Box User Guide V1.7, sections 4.2/4.3 and 4.10. The original PDF remains in the full workspace's `doc` folder.

Pass for this control-channel lab: the student finds the box IP, verifies the host key, logs in, proves target identity/root access and retrieves the sample file. Record the later USB/peripheral result separately.

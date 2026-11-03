"""ADB staging and evidence collection. Python stdlib only, on Windows or Linux."""
import argparse
import datetime as dt
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
from adb_login import resolve_adb, run_shell, transfer
from target_layout import DEFAULT_REMOTE, validate_remote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {"preflight", "diagnostics", "network", "performance", "docker", "camera", "qnn", "application", "ai", "wlan"}


def invoke(argv, **kwargs):
    return subprocess.run(argv, check=True, **kwargs)


def select_device(adb, serial, transport_id=None):
    data = subprocess.check_output([adb, "devices", "-l"], text=True, timeout=15)
    devices = [line.split() for line in data.splitlines()[1:] if len(line.split()) >= 2 and line.split()[1] == "device"]
    if serial:
        devices = [row for row in devices if row[0] == serial]
        if not devices:
            raise ValueError("Requested serial is not online/authorized")
    if transport_id is not None:
        devices = [row for row in devices if "transport_id:" + str(transport_id) in row]
    if len(devices) != 1:
        raise ValueError(f"Expected one authorized ADB device, found {len(devices)}. Use --serial.")
    row = devices[0]
    transport = next((v.split(":", 1)[1] for v in row if v.startswith("transport_id:")), None)
    return ["-t", transport] if transport else ["-s", row[0]]


def remote_exit_status(local_status, output):
    if local_status:
        return local_status
    markers = re.findall(rb"(?:^|\n)__QB560D_EXIT__=([0-9]+)\r*(?:\n|$)", output)
    return int(markers[-1]) if markers else 1


def marked_command(command):
    # Legacy adbd provides PTY only and does not transport a remote exit status.
    # Send an explicit command, without waiting for stdin EOF at a pseudo-terminal.
    return "sh -c " + shlex.quote(command + "\nqb_rc=$?\nprintf '\\n__QB560D_EXIT__=%s\\n' \"$qb_rc\"\nexit \"$qb_rc\"")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adb", help="ADB executable; bundled classroom client or PATH by default")
    p.add_argument("--serial")
    p.add_argument("--transport-id", help="Select an ADB transport when serial ? repeats")
    p.add_argument("--remote", default=DEFAULT_REMOTE)
    p.add_argument("--timeout", type=int, default=90, help="Maximum seconds per inventory/lab run")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("inventory")
    sub.add_parser("push")
    sub.add_parser("pull")
    run = sub.add_parser("run")
    run.add_argument("script", choices=sorted(SCRIPTS))
    run.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    a.adb = resolve_adb(a.adb)
    try:
        validate_remote(a.remote)
    except ValueError as exc:
        p.error(str(exc))
    if not 1 <= a.timeout <= 600:
        p.error("--timeout must be 1..600 seconds")
    base = [a.adb, *select_device(a.adb, a.serial, a.transport_id)]
    if a.action == "push":
        guard = "import json,pathlib\np=pathlib.Path(" + repr(a.remote) + ")\nassert p.resolve()==p, 'Refusing a target symlink'\n"
        guard += "if p.exists() and any(p.iterdir()):\n marker=p/'.provision-owner.json'\n known=(marker.is_file() and json.loads(marker.read_text()).get('package')=='qb560d-workshop-bootstrap-v1') or (p/'target/common.sh').is_file()\n assert known, 'Target folder is not a recognized training tree'\n"
        guard += "p.mkdir(parents=True,exist_ok=True)\nprint('TRAINING_DIRECTORY_READY')"
        mkdir_result = run_shell(base, "python3 -c " + shlex.quote(guard), timeout=30)
        if mkdir_result.returncode:
            raise RuntimeError(mkdir_result.stdout.decode(errors="replace"))
        # Stage only runtime material. Avoid pushing host evidence or account tokens.
        for name in ("target", "config", "app", "ai", "models", "media", "wheelhouse"):
            if (ROOT / name).exists():
                transfer(base, "push", str(ROOT / name), a.remote + "/")
        return 0
    if a.action == "pull":
        dest = ROOT / "evidence" / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-target")
        dest.mkdir(parents=True, exist_ok=True)
        transfer(base, "pull", a.remote + "/evidence", str(dest))
        return 0
    dest = ROOT / "evidence" / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest.mkdir(parents=True, exist_ok=False)
    if a.action == "inventory":
        command = (ROOT / "target" / "preflight.sh").read_text(encoding="utf-8")
    else:
        command = " ".join(shlex.quote(x) for x in ["sh", a.remote + "/target/" + a.script + ".sh", *a.args])
    timed_out = False
    try:
        result = run_shell(base, marked_command(command), timeout=a.timeout)
        output = result.stdout
        status = remote_exit_status(result.returncode, output)
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        output = getattr(exc, "stdout", None) or b""
        status, timed_out = 124, True
    (dest / "output.log").write_bytes(output)
    (dest / "result.json").write_text(json.dumps({"action": a.action, "script": getattr(a, "script", "preflight"), "exit_code": status, "timed_out": timed_out, "at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}, indent=2), encoding="utf-8")
    print(output.decode("utf-8", errors="replace"))
    print(f"Evidence: {dest}")
    return status


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError, RuntimeError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

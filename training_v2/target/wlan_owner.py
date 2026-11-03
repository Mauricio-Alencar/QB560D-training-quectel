"""Reserve wlan0 for NetworkManager on the observed BSP; preserve all other interfaces.

Run once, as root, after confirming that the existing dhcpcd daemon also owns
wlan0. This edits only the global denyinterfaces line, with a dated backup.
It does not stop/restart a global service or disconnect interfaces.
"""
import datetime as dt
import hashlib
from pathlib import Path
import re
import shutil

path = Path("/etc/dhcpcd.conf")
original = path.read_bytes()
text = original.decode("utf-8")
lines = text.splitlines(keepends=True)
global_end = next((i for i, line in enumerate(lines) if re.match(r"\s*(interface|profile|ssid)\s+", line)), len(lines))
matches = [i for i, line in enumerate(lines[:global_end]) if re.match(r"\s*denyinterfaces\s+", line)]
if len(matches) != 1:
    raise SystemExit("Expected one existing global denyinterfaces line. Inspect config before changing.")
index = matches[0]
line = lines[index]
settings, separator, comment = line.rstrip("\r\n").partition("#")
tokens = settings.split()
if "wlan0" in tokens[1:]:
    print("wlan0 is already excluded from dhcpcd; no config write")
else:
    if "bridge0" not in tokens[1:]:
        raise SystemExit("Expected the observed bridge0 exclusion; inspect BSP config first")
    backup = path.with_name(path.name + ".qb560d-training-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".bak")
    if backup.exists() or path.read_bytes() != original:
        raise SystemExit("Config or backup changed; inspect before proceeding")
    shutil.copy2(str(path), str(backup))
    backup.chmod(0o600)
    newline = "\r\n" if line.endswith("\r\n") else "\n"
    lines[index] = settings.rstrip() + " wlan0" + (" #" + comment if separator else "") + newline
    changed = "".join(lines).encode("utf-8")
    with path.open("r+b") as stream:
        if stream.read() != original:
            raise SystemExit("Concurrent config change")
        stream.seek(0)
        stream.write(changed)
        stream.truncate()
    print("Updated global denyinterfaces: preserved bridge0 and added wlan0")
    print("Backup:", backup)
    print("Before SHA256:", hashlib.sha256(original).hexdigest())
    print("After SHA256:", hashlib.sha256(changed).hexdigest())

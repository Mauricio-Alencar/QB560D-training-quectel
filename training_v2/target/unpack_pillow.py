"""Stage the reviewed Pillow wheel locally when target pip is absent. No system writes."""
import hashlib
import json
import platform
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
if platform.machine() != "aarch64" or sys.version_info[:2] != (3, 8):
    raise SystemExit("This staged wheel is for the observed aarch64 / CPython 3.8 target only")
lock = json.loads((root / "wheelhouse" / "wheels.lock.json").read_text())
dest = root / ".python-deps"
reuse = dest.exists()
if reuse and (not dest.is_dir() or dest.resolve().parent != root.resolve()):
    raise SystemExit('Dependency directory must stay inside this lab')
for name, spec in lock.items():
    if Path(name).name != name or not name.startswith("pillow-10.4.0-cp38-cp38-") or not name.endswith("aarch64.whl"):
        raise SystemExit("Unexpected wheel filename")
    wheel = root / "wheelhouse" / name
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != spec["sha256"]:
        raise SystemExit("Wheel hash mismatch")
    with zipfile.ZipFile(wheel) as archive:
        for item in archive.infolist():
            resolved = (dest / item.filename).resolve()
            if dest.resolve() not in resolved.parents or "\\" in item.filename:
                raise SystemExit("Unsafe archive path")
        if reuse:
            for item in archive.infolist():
                if not item.is_dir():
                    current = dest / item.filename
                    if not current.is_file() or hashlib.sha256(current.read_bytes()).digest() != hashlib.sha256(archive.read(item)).digest():
                        raise SystemExit('Existing Pillow differs or is incomplete: ' + item.filename)
        else:
            dest.mkdir()
            archive.extractall(dest)
print(('Pillow verified in the existing private directory. ' if reuse else 'Pillow staged inside the lab only. ') + 'Use PYTHONPATH=' + str(dest))

"""Remove only an owned update_QIART tree. No wildcard or system path removal."""
import json,os,re,shutil,sys
from pathlib import Path
p=Path(sys.argv[1])
s=str(p)
assert re.fullmatch(r"/tmp/update-qiart-251-[A-Za-z0-9_-]{4,80}",s) or s=="/opt/qairt-isolated/2.51.40.260930"
assert p.resolve()==p and not p.is_symlink()
o=json.loads((p/"ownership.json").read_text())
assert o["package"]=="update_QIART" and o["remote"]==s and o["version"]=="2.51.40.260930"
for f in Path("/proc").glob("[0-9]*/cmdline"):
    try:cmd=f.read_bytes().replace(b"\0",b" ").decode(errors="replace")
    except OSError:continue
    if s+"/bin/qnn-net-run" in cmd and "cleanup_target.py" not in cmd:
        raise RuntimeError("An inference process still uses this tree")
os.chdir("/tmp")
shutil.rmtree(p)
print("Removed only "+s)


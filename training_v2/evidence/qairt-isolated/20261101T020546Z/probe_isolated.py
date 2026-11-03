"""SNPE runtime probe for the isolated QAIRT test. Does not load a model."""
import argparse, ctypes as C, json, os, sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--runtime",choices=["version","cpu","gpu","dsp"],default="version")
a=p.parse_args()
root=Path(__file__).resolve().parent
libpath=root/"lib"/"libSNPE.so"
l=C.CDLL(str(libpath))
l.Snpe_Util_GetLibraryVersion.restype=C.c_void_p
l.Snpe_Util_GetLibraryVersion.argtypes=[]
l.Snpe_DlVersion_ToString.restype=C.c_char_p
l.Snpe_DlVersion_ToString.argtypes=[C.c_void_p]
l.Snpe_DlVersion_Delete.restype=None
l.Snpe_DlVersion_Delete.argtypes=[C.c_void_p]
v=l.Snpe_Util_GetLibraryVersion()
version=l.Snpe_DlVersion_ToString(v).decode()
l.Snpe_DlVersion_Delete(v)
report={"library":str(libpath),"version":version,"scope":"Version/runtime availability only; no model inference"}
if a.runtime!="version":
    l.Snpe_Util_IsRuntimeAvailableCheckOption.restype=C.c_int
    l.Snpe_Util_IsRuntimeAvailableCheckOption.argtypes=[C.c_int,C.c_int]
    l.Snpe_Util_GetLastError.restype=C.c_char_p
    runtime={"cpu":0,"gpu":1,"dsp":2}[a.runtime]
    option=2 if a.runtime=="dsp" else 0
    report.update(runtime=a.runtime,check="UNSIGNEDPD_CHECK" if option==2 else "NORMAL_CHECK",available=bool(l.Snpe_Util_IsRuntimeAvailableCheckOption(runtime,option)),last_error=(l.Snpe_Util_GetLastError() or b"").decode(errors="replace"))
report["loaded_ai_libraries"]=[line.strip() for line in Path("/proc/self/maps").read_text().splitlines() if any(name in line for name in ("libSNPE","libSnpe","libQnn","libQairt"))]
print("ISOLATED_RESULT="+json.dumps(report),flush=True)
if report.get("available") is False:sys.exit(2)


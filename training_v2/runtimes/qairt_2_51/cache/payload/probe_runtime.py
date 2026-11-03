"""Query the SNPE library inside this owned runtime tree."""
import ctypes as C,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
l=C.CDLL(str(root/"lib/libSNPE.so"))
l.Snpe_Util_GetLibraryVersion.restype=C.c_void_p
l.Snpe_DlVersion_ToString.restype=C.c_char_p
l.Snpe_DlVersion_ToString.argtypes=[C.c_void_p]
l.Snpe_DlVersion_Delete.argtypes=[C.c_void_p]
v=l.Snpe_Util_GetLibraryVersion()
print(json.dumps({"library":str(root/"lib/libSNPE.so"),"version":l.Snpe_DlVersion_ToString(v).decode()}))
l.Snpe_DlVersion_Delete(v)


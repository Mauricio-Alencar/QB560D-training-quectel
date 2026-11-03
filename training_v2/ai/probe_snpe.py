"""Read-only SNPE runtime probe using the C API installed with the vendor BSP.

A positive availability result is not a model inference or a performance result.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="/usr/lib/aarch64-linux-gnu/snpe-2.12")
    p.add_argument("--output", default="evidence/snpe-probe.json")
    p.add_argument("--library", help="Explicit installed vendor library; no download or replacement")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--runtime", choices=["all", "cpu", "gpu", "dsp"], default="dsp")
    p.add_argument("--check", choices=["normal", "unsigned"], default="unsigned")
    a = p.parse_args()
    root = Path(a.root)
    native = root / "lib/aarch64_Linux"
    library = Path(a.library) if a.library else native / "libSNPE.so"
    if not library.is_file():
        p.error("SNPE library not found at " + str(library))
    # glibc reads LD_LIBRARY_PATH on process startup. Re-exec before loading
    # SNPE so its dlopen calls find the matching stub from the same SDK tree.
    if os.environ.get("QB560D_SNPE_PROBE_REEXEC") != str(native):
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(native) + ":" + env.get("LD_LIBRARY_PATH", "/usr/lib:/lib/aarch64-linux-gnu")
        env["QB560D_SNPE_PROBE_REEXEC"] = str(native)
        os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve())] + sys.argv[1:], env)
    # Scoped to this probe process; never replace vendor libraries or firmware.
    os.environ["ADSP_LIBRARY_PATH"] = ";".join((str(native / "hexagon-v68/unsigned"), "/usr/lib/rfsa/adsp", "/dsp", "/usr/lib"))
    lib = C.CDLL(str(library))
    signatures = {
        "Snpe_Util_GetLibraryVersion": (C.c_void_p, []),
        "Snpe_DlVersion_ToString": (C.c_char_p, [C.c_void_p]),
        "Snpe_DlVersion_Delete": (None, [C.c_void_p]),
        "Snpe_Util_IsRuntimeAvailableCheckOption": (C.c_int, [C.c_int, C.c_int]),
        "Snpe_Util_GetLastError": (C.c_char_p, []),
        "Snpe_Util_InitializeLoggingPath": (C.c_int, [C.c_int, C.c_char_p]),
    }
    for name, (result, args) in signatures.items():
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, args
    if a.verbose:
        logdir = Path(a.output).parent / (Path(a.output).stem + "-logs")
        logdir.mkdir(parents=True, exist_ok=True)
        lib.Snpe_Util_InitializeLoggingPath(4, os.fsencode(logdir.resolve()))
    version = lib.Snpe_Util_GetLibraryVersion()
    try:
        text = lib.Snpe_DlVersion_ToString(version).decode()
    finally:
        lib.Snpe_DlVersion_Delete(version)
    results = []
    for name, runtime in (("CPU_FLOAT32", 0), ("GPU_FLOAT32_16_HYBRID", 1), ("DSP_FIXED8_TF", 2)):
        if a.runtime != "all" and runtime != {"cpu": 0, "gpu": 1, "dsp": 2}[a.runtime]:
            continue
        for check, option in (("NORMAL_CHECK", 0), ("UNSIGNEDPD_CHECK", 2)):
            if option != {"normal": 0, "unsigned": 2}[a.check]:
                continue
            available = bool(lib.Snpe_Util_IsRuntimeAvailableCheckOption(runtime, option))
            error = (lib.Snpe_Util_GetLastError() or b"").decode(errors="replace")
            results.append({"runtime": name, "check": check, "available": available, "last_error": error})
    report = {"library": str(library), "version": text, "results": results,
              "scope": "Runtime availability probe only; no DLC loaded and no inference executed",
              "check_isolation": "One PD check mode per process; do not run normal then unsigned in the same SNPE 2.12 process",
              "adsp_library_path_process_only": os.environ["ADSP_LIBRARY_PATH"]}
    dest = Path(a.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

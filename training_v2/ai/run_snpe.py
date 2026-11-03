"""Execute a converted MobileNet DLC with an explicit SNPE runtime order.

The source TFLite and DLC have separate hashes. Inspect the saved DiagLog to
confirm actual layer placement; this runner never appends CPU to DSP/GPU order.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

import numpy as np
from PIL import Image, ImageOps
from run_demo import annotate


def configure_process(sdk):
    native = sdk / 'lib/aarch64_Linux'
    if not native.exists():
        native = sdk / 'lib/aarch64-ubuntu-gcc9.4'
    if not native.exists():
        raise ValueError('Use a reviewed SNPE runtime tree for this Ubuntu target')
    if os.environ.get('QB560D_SNPE_EXEC_NATIVE') != str(native):
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = str(native) + ':' + env.get('LD_LIBRARY_PATH', '/usr/lib:/lib/aarch64-linux-gnu')
        env['QB560D_SNPE_EXEC_NATIVE'] = str(native)
        os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve())] + sys.argv[1:], env)
    skeleton = native / 'hexagon-v68/unsigned'
    if not skeleton.exists():
        skeleton = sdk / 'lib/hexagon-v68/unsigned'
    os.environ['ADSP_LIBRARY_PATH'] = ';'.join((str(skeleton), '/usr/lib/rfsa/adsp', '/dsp', '/usr/lib'))
    return native / 'libSNPE.so'


class Snpe:
    def __init__(self, library, model, backend, output, profiling, verbose=False, cpu_fixed_point=False):
        self.lib = C.CDLL(str(library))
        self.resources = []
        self.diag = None
        ptr, integer, text, size = C.c_void_p, C.c_int, C.c_char_p, C.c_size_t
        specs = {
            'Util_GetLibraryVersion': (ptr, []), 'DlVersion_ToString': (text, [ptr]), 'DlVersion_Delete': (integer, [ptr]),
            'Util_GetLastError': (text, []), 'Util_IsRuntimeAvailableCheckOption': (integer, [integer, integer]),
            'ErrorCode_GetLastErrorString': (text, []), 'Util_InitializeLoggingPath': (integer, [integer, text]),
            'DlContainer_Open': (ptr, [text]), 'DlContainer_Delete': (integer, [ptr]),
            'RuntimeList_Create': (ptr, []), 'RuntimeList_Add': (integer, [ptr, integer]), 'RuntimeList_Delete': (integer, [ptr]),
            'PlatformConfig_Create': (ptr, []), 'PlatformConfig_SetPlatformOptions': (integer, [ptr, text]), 'PlatformConfig_Delete': (integer, [ptr]),
            'SNPEBuilder_Create': (ptr, [ptr]), 'SNPEBuilder_Delete': (integer, [ptr]),
            'SNPEBuilder_SetRuntimeProcessorOrder': (integer, [ptr, ptr]), 'SNPEBuilder_SetPlatformConfig': (integer, [ptr, ptr]),
            'SNPEBuilder_SetProfilingLevel': (integer, [ptr, integer]), 'SNPEBuilder_SetUseUserSuppliedBuffers': (integer, [ptr, integer]),
            'SNPEBuilder_SetCpuFixedPointMode': (integer, [ptr, integer]),
            'SNPEBuilder_Build': (ptr, [ptr]), 'SNPE_Delete': (integer, [ptr]),
            'SNPE_GetInputTensorNames': (ptr, [ptr]), 'SNPE_GetInputDimensions': (ptr, [ptr, text]),
            'SNPE_GetDiagLogInterface_Ref': (ptr, [ptr]), 'SNPE_ExecuteITensors': (integer, [ptr, ptr, ptr]),
            'TensorShape_Rank': (size, [ptr]), 'TensorShape_At': (size, [ptr, size]), 'TensorShape_Delete': (integer, [ptr]),
            'Util_CreateITensor': (ptr, [ptr]), 'ITensor_Delete': (integer, [ptr]), 'ITensor_GetData': (ptr, [ptr]), 'ITensor_GetSize': (size, [ptr]),
            'TensorMap_Create': (ptr, []), 'TensorMap_Delete': (integer, [ptr]), 'TensorMap_Add': (None, [ptr, text, ptr]),
            'TensorMap_GetTensorNames': (ptr, [ptr]), 'TensorMap_GetTensor_Ref': (ptr, [ptr, text]),
            'StringList_Size': (size, [ptr]), 'StringList_At': (text, [ptr, size]), 'StringList_Delete': (integer, [ptr]),
            'IDiagLog_GetOptions': (ptr, [ptr]), 'IDiagLog_SetOptions': (integer, [ptr, ptr]),
            'IDiagLog_Start': (integer, [ptr]), 'IDiagLog_Stop': (integer, [ptr]),
            'Options_SetLogFileDirectory': (None, [ptr, text]), 'Options_Delete': (integer, [ptr]),
        }
        for suffix, (result, args) in specs.items():
            fn = getattr(self.lib, 'Snpe_' + suffix)
            fn.restype, fn.argtypes = result, args
        self.lib.Snpe_Util_InitializeLoggingPath(4 if verbose else 2, os.fsencode(output))
        version = self.lib.Snpe_Util_GetLibraryVersion()
        self.version = self.lib.Snpe_DlVersion_ToString(version).decode()
        self.lib.Snpe_DlVersion_Delete(version)
        runtime = {'cpu': 0, 'gpu': 1, 'dsp': 2}[backend]
        # Unsigned PD is an HTP option; CPU/GPU use their normal availability check.
        if not self.lib.Snpe_Util_IsRuntimeAvailableCheckOption(runtime, 2 if backend == 'dsp' else 0):
            raise RuntimeError('Requested SNPE runtime is unavailable; no CPU retry')
        container = self.own('DlContainer', self.lib.Snpe_DlContainer_Open(os.fsencode(model)))
        order = self.own('RuntimeList', self.lib.Snpe_RuntimeList_Create())
        self.check(self.lib.Snpe_RuntimeList_Add(order, runtime))
        platform = self.own('PlatformConfig', self.lib.Snpe_PlatformConfig_Create())
        if backend == 'dsp' and not self.lib.Snpe_PlatformConfig_SetPlatformOptions(platform, b'unsignedPD:ON'):
            raise RuntimeError('SNPE rejected unsigned PD option')
        builder = self.own('SNPEBuilder', self.lib.Snpe_SNPEBuilder_Create(container))
        self.check(self.lib.Snpe_SNPEBuilder_SetRuntimeProcessorOrder(builder, order))
        self.check(self.lib.Snpe_SNPEBuilder_SetPlatformConfig(builder, platform))
        self.check(self.lib.Snpe_SNPEBuilder_SetProfilingLevel(builder, profiling))
        self.check(self.lib.Snpe_SNPEBuilder_SetUseUserSuppliedBuffers(builder, 0))
        if backend == 'cpu' and cpu_fixed_point:
            self.check(self.lib.Snpe_SNPEBuilder_SetCpuFixedPointMode(builder, 1))
        self.handle = self.own('SNPE', self.lib.Snpe_SNPEBuilder_Build(builder))
        names = self.strings(self.lib.Snpe_SNPE_GetInputTensorNames(self.handle))
        if len(names) != 1:
            raise ValueError('Reviewed runner requires one input')
        self.input_name = names[0]
        shape = self.own('TensorShape', self.lib.Snpe_SNPE_GetInputDimensions(self.handle, names[0].encode()))
        self.input_shape = tuple(self.lib.Snpe_TensorShape_At(shape, i) for i in range(self.lib.Snpe_TensorShape_Rank(shape)))
        self.input = self.own('ITensor', self.lib.Snpe_Util_CreateITensor(shape))
        self.inputs = self.own('TensorMap', self.lib.Snpe_TensorMap_Create())
        self.outputs = self.own('TensorMap', self.lib.Snpe_TensorMap_Create())
        self.lib.Snpe_TensorMap_Add(self.inputs, names[0].encode(), self.input)
        if profiling:
            self.diag = self.lib.Snpe_SNPE_GetDiagLogInterface_Ref(self.handle)
            options = self.lib.Snpe_IDiagLog_GetOptions(self.diag)
            self.lib.Snpe_Options_SetLogFileDirectory(options, os.fsencode(output))
            self.check(self.lib.Snpe_IDiagLog_SetOptions(self.diag, options))
            self.lib.Snpe_Options_Delete(options)
            self.check(self.lib.Snpe_IDiagLog_Start(self.diag))

    def own(self, kind, handle):
        if not handle:
            raise RuntimeError(kind + ' creation failed: ' + (self.lib.Snpe_ErrorCode_GetLastErrorString() or self.lib.Snpe_Util_GetLastError() or b'').decode(errors='replace'))
        self.resources.append((kind, handle))
        return handle

    def check(self, code):
        if code:
            raise RuntimeError('SNPE error %s: %s' % (code, (self.lib.Snpe_ErrorCode_GetLastErrorString() or self.lib.Snpe_Util_GetLastError() or b'').decode(errors='replace')))

    def strings(self, handle):
        if not handle:
            raise RuntimeError('Missing tensor names')
        result = [self.lib.Snpe_StringList_At(handle, i).decode() for i in range(self.lib.Snpe_StringList_Size(handle))]
        self.lib.Snpe_StringList_Delete(handle)
        return result

    def tensor(self, handle):
        count = self.lib.Snpe_ITensor_GetSize(handle)
        data = self.lib.Snpe_ITensor_GetData(handle)
        if not data:
            raise RuntimeError('Missing tensor data')
        return np.ctypeslib.as_array(C.cast(data, C.POINTER(C.c_float)), shape=(count,))

    def set_input(self, data):
        if data.shape != self.input_shape or data.dtype != np.float32:
            raise ValueError('SNPE input shape/dtype mismatch')
        destination = self.tensor(self.input)
        if destination.size != data.size:
            raise ValueError('SNPE tensor element count mismatch')
        np.copyto(destination, data.reshape(-1))

    def invoke(self):
        self.check(self.lib.Snpe_SNPE_ExecuteITensors(self.handle, self.inputs, self.outputs))

    def output(self):
        names = self.strings(self.lib.Snpe_TensorMap_GetTensorNames(self.outputs))
        return {name: self.tensor(self.lib.Snpe_TensorMap_GetTensor_Ref(self.outputs, name.encode())).copy() for name in names}

    def close(self):
        if self.diag:
            self.lib.Snpe_IDiagLog_Stop(self.diag)
            self.diag = None
        for kind, handle in reversed(self.resources):
            getattr(self.lib, 'Snpe_' + kind + '_Delete')(handle)
        self.resources = []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', default='runtime/qairt226-ubuntu')
    parser.add_argument('--model', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--backend', choices=['cpu', 'gpu', 'dsp'], required=True)
    parser.add_argument('--input-mode', choices=['pixels', 'normalized'], required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--runs', type=int, default=50)
    parser.add_argument('--warmup', type=int, default=10)
    parser.add_argument('--profiling', choices=['off', 'basic', 'detailed'], default='basic')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--cpu-fixed-point', action='store_true', help='Use fixed-point CPU execution for a quantized DLC control')
    args = parser.parse_args()
    if not 1 <= args.runs <= 1000 or not 0 <= args.warmup <= 100:
        parser.error('Invalid run count')
    model, image = Path(args.model).resolve(), Path(args.image).resolve()
    if not model.is_file() or not image.is_file():
        parser.error('Model and image must exist')
    library = configure_process(Path(args.sdk_root).resolve())
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    engine = None
    try:
        engine = Snpe(library, model, args.backend, output, {'off': 0, 'basic': 1, 'detailed': 2}[args.profiling], args.verbose, args.cpu_fixed_point)
        pixels = np.asarray(ImageOps.exif_transpose(Image.open(image)).convert('RGB').resize((224, 224), Image.Resampling.BILINEAR), dtype=np.float32)[None]
        data = (pixels - 128.0) / 128.0 if args.input_mode == 'normalized' else pixels
        if engine.input_shape == (1, 3, 224, 224):
            data = data.transpose(0, 3, 1, 2)
        engine.set_input(np.ascontiguousarray(data))
        for _ in range(args.warmup):
            engine.invoke()
        durations = []
        for _ in range(args.runs):
            started = time.perf_counter()
            engine.invoke()
            durations.append((time.perf_counter() - started) * 1000)
        results = engine.output()
        if len(results) != 1 or next(iter(results.values())).size != 1001:
            raise ValueError('Expected one 1001-class MobileNet output')
        scores = next(iter(results.values()))
        top = np.argsort(scores)[-3:][::-1]
        labels = (Path(__file__).resolve().parents[1] / 'models/imagenet_labels.txt').read_text(encoding='utf-8').splitlines()
        report = {'backend_requested': args.backend, 'runtime_order': [args.backend], 'cpu_retry': False,
                  'cpu_fixed_point': bool(args.cpu_fixed_point and args.backend == 'cpu'),
                  'runtime_version': engine.version, 'library': str(library), 'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
                  'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'input_mode': args.input_mode,
                  'input_name': engine.input_name, 'input_shape': list(engine.input_shape), 'profiling': args.profiling,
                  'runs': args.runs, 'warmup': args.warmup, 'inference_ms_median': statistics.median(durations),
                  'inference_ms_p95': float(np.percentile(durations, 95)), 'timing_scope': 'SNPE ExecuteITensors only; excludes host preprocessing and output copy',
                  'top3': [{'class_id': int(i), 'label': labels[int(i)], 'score': float(scores[i])} for i in top],
                  'placement_confirmation': 'Inspect the associated SNPE DiagLog; runtime order alone is not per-layer evidence'}
        np.savez_compressed(output / 'outputs.npz', **results)
        (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        canvas = Image.fromarray(pixels[0].astype(np.uint8))
        annotate(canvas, report, 'classification', [], {}, 0.5).resize((768, 768)).save(output / 'classification.png')
        print(json.dumps(report, indent=2))
    finally:
        if engine is not None:
            engine.close()


if __name__ == '__main__':
    main()

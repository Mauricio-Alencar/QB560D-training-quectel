"""Small NumPy wrapper for the TFLite C API already shipped by the vendor BSP."""
import ctypes as C
import os
import numpy as np


class Quantization(C.Structure):
    _fields_ = [("scale", C.c_float), ("zero_point", C.c_int32)]


class GpuOptionsV2(C.Structure):
    # Public tensorflow/lite/delegates/gpu/delegate.h, TensorFlow v2.8.0.
    _fields_ = [("is_precision_loss_allowed", C.c_int32),
                ("inference_preference", C.c_int32),
                ("inference_priority1", C.c_int32),
                ("inference_priority2", C.c_int32),
                ("inference_priority3", C.c_int32),
                ("experimental_flags", C.c_int64),
                ("max_delegated_partitions", C.c_int32),
                ("serialization_dir", C.c_char_p), ("model_token", C.c_char_p)]


class HexagonOptions(C.Structure):
    # Public TensorFlow v2.8.0 hexagon_delegate.h. DSP NN, distinct from SNPE HTP.
    _fields_ = [("debug_level", C.c_int), ("powersave_level", C.c_int),
                ("print_graph_profile", C.c_bool), ("print_graph_debug", C.c_bool),
                ("max_delegated_partitions", C.c_int), ("min_nodes_per_partition", C.c_int),
                ("enable_dynamic_batch_size", C.c_bool), ("max_batch_size", C.c_int),
                ("input_batch_dimensions", C.c_void_p), ("output_batch_dimensions", C.c_void_p)]


TYPES = {1: np.float32, 2: np.int32, 3: np.uint8, 4: np.int64, 6: np.bool_, 7: np.int16, 9: np.int8, 10: np.float16, 11: np.float64}


class Interpreter:
    def __init__(self, model_path, num_threads=2, backend="cpu"):
        if backend not in ("cpu", "gpu", "dsp"):
            raise ValueError("C API backend must be cpu, gpu or dsp")
        self.backend = backend
        self.delegate = None
        self.hexagon_initialized = False
        self.lib = C.CDLL(os.environ.get("TFLITE_C_LIBRARY", "/usr/lib/libtensorflowlite_c.so"))
        signatures = {
            "TfLiteVersion": (C.c_char_p, []),
            "TfLiteModelCreateFromFile": (C.c_void_p, [C.c_char_p]),
            "TfLiteModelDelete": (None, [C.c_void_p]),
            "TfLiteInterpreterOptionsCreate": (C.c_void_p, []),
            "TfLiteInterpreterOptionsDelete": (None, [C.c_void_p]),
            "TfLiteInterpreterOptionsSetNumThreads": (None, [C.c_void_p, C.c_int]),
            "TfLiteInterpreterCreate": (C.c_void_p, [C.c_void_p, C.c_void_p]),
            "TfLiteInterpreterDelete": (None, [C.c_void_p]),
            "TfLiteInterpreterAllocateTensors": (C.c_int, [C.c_void_p]),
            "TfLiteInterpreterInvoke": (C.c_int, [C.c_void_p]),
            "TfLiteInterpreterGetInputTensorCount": (C.c_int, [C.c_void_p]),
            "TfLiteInterpreterGetOutputTensorCount": (C.c_int, [C.c_void_p]),
            "TfLiteInterpreterGetInputTensor": (C.c_void_p, [C.c_void_p, C.c_int]),
            "TfLiteInterpreterGetOutputTensor": (C.c_void_p, [C.c_void_p, C.c_int]),
            "TfLiteTensorType": (C.c_int, [C.c_void_p]),
            "TfLiteTensorName": (C.c_char_p, [C.c_void_p]),
            "TfLiteTensorNumDims": (C.c_int, [C.c_void_p]),
            "TfLiteTensorDim": (C.c_int, [C.c_void_p, C.c_int]),
            "TfLiteTensorByteSize": (C.c_size_t, [C.c_void_p]),
            "TfLiteTensorQuantizationParams": (Quantization, [C.c_void_p]),
            "TfLiteTensorCopyFromBuffer": (C.c_int, [C.c_void_p, C.c_void_p, C.c_size_t]),
            "TfLiteTensorCopyToBuffer": (C.c_int, [C.c_void_p, C.c_void_p, C.c_size_t]),
        }
        for name, (result, args) in signatures.items():
            fn = getattr(self.lib, name)
            fn.restype, fn.argtypes = result, args
        if backend != "cpu" and self.lib.TfLiteVersion() != b"2.8.4":
            raise RuntimeError("Delegate options ABI is scoped to the target BSP's TFLite 2.8.4")
        self.model = self.lib.TfLiteModelCreateFromFile(os.fsencode(model_path))
        if not self.model:
            raise RuntimeError("TFLite C API could not read the model")
        options = self.lib.TfLiteInterpreterOptionsCreate()
        self.lib.TfLiteInterpreterOptionsSetNumThreads(options, num_threads)
        if backend == "gpu":
            # Explicit defaults are required by this BSP: passing NULL crashes
            # its vendor build, despite upstream documenting NULL support.
            self.lib.TfLiteGpuDelegateOptionsV2Default.restype = GpuOptionsV2
            self.lib.TfLiteGpuDelegateOptionsV2Default.argtypes = []
            self.lib.TfLiteGpuDelegateV2Create.restype = C.c_void_p
            self.lib.TfLiteGpuDelegateV2Create.argtypes = [C.c_void_p]
            self.lib.TfLiteGpuDelegateV2Delete.argtypes = [C.c_void_p]
            self.lib.TfLiteGpuDelegateV2Delete.restype = None
            self.lib.TfLiteInterpreterOptionsAddDelegate.argtypes = [C.c_void_p, C.c_void_p]
            self.lib.TfLiteInterpreterOptionsAddDelegate.restype = None
            self.gpu_options = self.lib.TfLiteGpuDelegateOptionsV2Default()
            self.delegate = self.lib.TfLiteGpuDelegateV2Create(C.byref(self.gpu_options))
            if not self.delegate:
                raise RuntimeError("GPU delegate creation failed; CPU retry is disabled")
            self.lib.TfLiteInterpreterOptionsAddDelegate(options, self.delegate)
        if backend == "dsp":
            self.lib.TfLiteHexagonDelegateOptionsDefault.restype = HexagonOptions
            self.lib.TfLiteHexagonDelegateOptionsDefault.argtypes = []
            self.lib.TfLiteHexagonInit.argtypes = []
            self.lib.TfLiteHexagonInit.restype = None
            self.lib.TfLiteHexagonTearDown.argtypes = []
            self.lib.TfLiteHexagonTearDown.restype = None
            self.lib.TfLiteHexagonDelegateCreate.argtypes = [C.POINTER(HexagonOptions)]
            self.lib.TfLiteHexagonDelegateCreate.restype = C.c_void_p
            self.lib.TfLiteHexagonDelegateDelete.argtypes = [C.c_void_p]
            self.lib.TfLiteHexagonDelegateDelete.restype = None
            self.lib.TfLiteInterpreterOptionsAddDelegate.argtypes = [C.c_void_p, C.c_void_p]
            self.lib.TfLiteInterpreterOptionsAddDelegate.restype = None
            self.lib.TfLiteHexagonInit()
            self.hexagon_initialized = True
            self.hexagon_options = self.lib.TfLiteHexagonDelegateOptionsDefault()
            self.hexagon_options.max_delegated_partitions = 1
            self.hexagon_options.min_nodes_per_partition = 2
            self.hexagon_options.print_graph_profile = True
            self.hexagon_options.print_graph_debug = True
            self.delegate = self.lib.TfLiteHexagonDelegateCreate(C.byref(self.hexagon_options))
            if not self.delegate:
                self.lib.TfLiteInterpreterOptionsDelete(options)
                raise RuntimeError("Hexagon DSP delegate unavailable; CPU retry is disabled. Inspect DSP NN/skel/SoC compatibility.")
            self.lib.TfLiteInterpreterOptionsAddDelegate(options, self.delegate)
        self.handle = self.lib.TfLiteInterpreterCreate(self.model, options)
        self.lib.TfLiteInterpreterOptionsDelete(options)
        if not self.handle:
            raise RuntimeError("TFLite C API could not create an interpreter")
        self.tensors = {}

    def allocate_tensors(self):
        if self.lib.TfLiteInterpreterAllocateTensors(self.handle):
            raise RuntimeError("TFLite C API allocation failed. Inspect unsupported operators/runtime version.")

    def _details(self, output):
        count = self.lib.TfLiteInterpreterGetOutputTensorCount(self.handle) if output else self.lib.TfLiteInterpreterGetInputTensorCount(self.handle)
        getter = self.lib.TfLiteInterpreterGetOutputTensor if output else self.lib.TfLiteInterpreterGetInputTensor
        rows = []
        for slot in range(count):
            tensor = getter(self.handle, slot)
            index = slot + (1000 if output else 0)
            dtype = TYPES.get(self.lib.TfLiteTensorType(tensor))
            if dtype is None:
                raise RuntimeError("Unsupported TFLite tensor type")
            shape = np.array([self.lib.TfLiteTensorDim(tensor, j) for j in range(self.lib.TfLiteTensorNumDims(tensor))], dtype=np.int32)
            quant = self.lib.TfLiteTensorQuantizationParams(tensor)
            row = {"index": index, "name": (self.lib.TfLiteTensorName(tensor) or b"").decode(), "shape": shape, "dtype": dtype, "quantization": (quant.scale, quant.zero_point)}
            self.tensors[index] = (tensor, row)
            rows.append(row)
        return rows

    def get_input_details(self):
        return self._details(False)

    def get_output_details(self):
        return self._details(True)

    def set_tensor(self, index, value):
        tensor, row = self.tensors[index]
        value = np.ascontiguousarray(value)
        if value.dtype != row["dtype"] or list(value.shape) != list(row["shape"]):
            raise ValueError("Input shape/dtype differs from C API tensor")
        if value.nbytes != self.lib.TfLiteTensorByteSize(tensor) or self.lib.TfLiteTensorCopyFromBuffer(tensor, value.ctypes.data, value.nbytes):
            raise RuntimeError("TFLite C API input copy failed")

    def invoke(self):
        if self.lib.TfLiteInterpreterInvoke(self.handle):
            raise RuntimeError("TFLite C API inference failed")

    def get_tensor(self, index):
        tensor, row = self.tensors[index]
        value = np.empty(tuple(row["shape"]), dtype=row["dtype"])
        if value.nbytes != self.lib.TfLiteTensorByteSize(tensor) or self.lib.TfLiteTensorCopyToBuffer(tensor, value.ctypes.data, value.nbytes):
            raise RuntimeError("TFLite C API output copy failed")
        return value

    def __del__(self):
        if getattr(self, "handle", None):
            self.lib.TfLiteInterpreterDelete(self.handle)
            self.handle = None
        if getattr(self, "model", None):
            self.lib.TfLiteModelDelete(self.model)
            self.model = None
        if getattr(self, "delegate", None):
            if self.backend == "dsp":
                self.lib.TfLiteHexagonDelegateDelete(self.delegate)
            else:
                self.lib.TfLiteGpuDelegateV2Delete(self.delegate)
            self.delegate = None
        if getattr(self, "hexagon_initialized", False):
            self.lib.TfLiteHexagonTearDown()
            self.hexagon_initialized = False

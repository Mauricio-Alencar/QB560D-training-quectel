"""Create a small deterministic ONNX tensor model for the hosted compile/profile lab."""
from pathlib import Path
import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

dest = Path(__file__).resolve().parents[1] / "models"
dest.mkdir(exist_ok=True)
rng = np.random.RandomState(560)
weights = rng.normal(0, 0.1, (4, 3, 3, 3)).astype(np.float32)
nodes = [helper.make_node("Conv", ["image", "weights"], ["conv"], pads=[1, 1, 1, 1]),
         helper.make_node("Relu", ["conv"], ["relu"]),
         helper.make_node("GlobalAveragePool", ["relu"], ["pool"]),
         helper.make_node("Flatten", ["pool"], ["features"], axis=1)]
graph = helper.make_graph(nodes, "QB560D training tensor model", [helper.make_tensor_value_info("image", TensorProto.FLOAT, [1, 3, 32, 32])],
                          [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 4])], [numpy_helper.from_array(weights, "weights")])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
model.ir_version = 8
onnx.checker.check_model(model)
onnx.save(model, str(dest / "workbench_demo.onnx"))
sample = rng.uniform(0, 1, (1, 3, 32, 32)).astype(np.float32)
np.save(dest / "workbench_input.npy", sample)
# Independent NumPy reference for Conv(pad=1), ReLU, spatial mean, Flatten.
padded = np.pad(sample, ((0, 0), (0, 0), (1, 1), (1, 1)))
conv = np.zeros((1, 4, 32, 32), dtype=np.float32)
for ky in range(3):
    for kx in range(3):
        conv += np.einsum("nchw,oc->nohw", padded[:, :, ky:ky + 32, kx:kx + 32], weights[:, :, ky, kx])
np.save(dest / "workbench_expected.npy", np.maximum(conv, 0).mean(axis=(2, 3)))
print("Created synthetic ONNX compile/profile example; outputs have no semantic class labels.")

"""Inspect the downloaded CPU model contracts without running inference."""
import json
from pathlib import Path
from run_demo import interpreter_type

root = Path(__file__).resolve().parents[1]
cls, runtime = interpreter_type()
info = {"runtime": runtime, "models": {}}
for name, spec in json.loads((root / "ai" / "profiles.json").read_text()).items():
    interpreter = cls(model_path=str(root / "models" / spec["model"]))
    interpreter.allocate_tensors()
    def details(rows):
        return [{"slot": i, "name": d["name"], "shape": d["shape"].tolist(), "dtype": str(d["dtype"]), "quantization": list(d["quantization"])} for i, d in enumerate(rows)]
    info["models"][name] = {"inputs": details(interpreter.get_input_details()), "outputs": details(interpreter.get_output_details())}
print(json.dumps(info, indent=2))

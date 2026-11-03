"""Download reference inputs from official TensorFlow/MediaPipe sample storage."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai"))
from fetch_models import download

dest = Path(__file__).resolve().parents[1] / "media"
dest.mkdir(exist_ok=True)
sources = {
    "grace_hopper.jpg": "https://storage.googleapis.com/download.tensorflow.org/example_images/grace_hopper.jpg",
    "right_hands.jpg": "https://storage.googleapis.com/mediapipe-assets/right_hands.jpg",
}
for name, url in sources.items():
    (dest / name).write_bytes(download(url))
    print("Fetched sample: " + name)
(dest / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")

"""Download public original training PDFs, with source URLs and SHA-256 receipts."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "Qualcomm_AI_Hub_Training"
BASE = "https://www.fabricionarcizo.com/cvpr2025-edge-ai-in-action/"
ITEMS = [
    ("01_Introduction_to_Edge_AI_CVPR2025.pdf", "02-Introduction_to_Edge_AI.pdf", "Introduction to Edge AI", "Elizabete Munzlinger"),
    ("02_Model_Deployment_for_Edge_AI_CVPR2025.pdf", "03-Model_Deployment_for_Edge_AI.pdf", "Model Deployment for Edge AI", "Fabricio Batista Narcizo, Elizabete Munzlinger, Sai Narsi Reddy Donthi Reddy"),
    ("03_Accelerating_Edge_AI_with_Qualcomm_AI_Hub_CVPR2025.pdf", "04-Accelerating_Edge_AI_with_Qualcomm_AI_Hub.pdf", "Accelerating Edge AI with Qualcomm AI Hub", "Shan Ahmed Shaffi"),
    ("04_Qualcomm_AI_driven_Multimedia_Embedded_Vision_Summit_2025.pdf", "https://www.edge-ai-vision.com/wp-content/uploads/2025/06/E3W10_Bi_Qualcomm_2025.pdf", "How Qualcomm Is Powering AI-driven Multimedia at the Edge", "Ning Bi, VP Engineering, Qualcomm Technologies"),
]


def main():
    folder = DEST / "apresentacoes"
    folder.mkdir(parents=True, exist_ok=True)
    receipts = []
    for name, remote, title, author in ITEMS:
        official = remote.startswith("https://")
        url = remote if official else BASE + "pdfs/cvpr2025/" + remote
        request = urllib.request.Request(url, headers={"User-Agent": "QB560D-Training/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read(50 * 1024 * 1024 + 1)
        if not payload.startswith(b"%PDF-") or len(payload) > 50 * 1024 * 1024:
            raise ValueError("Unexpected PDF response: " + url)
        (folder / name).write_bytes(payload)
        receipts.append({"file": "apresentacoes/" + name, "title": title, "author": author,
                         "source": url, "event_page": "https://www.edge-ai-vision.com/2025/06/how-qualcomm-is-powering-ai-driven-multimedia-at-the-edge-a-presentation-from-qualcomm/" if official else BASE,
                         "origin": "Qualcomm Technologies presentation published by event organizer; supplementary context, not an AI Hub hands-on course" if official else "CVPR 2025 tutorial; original author/organizer publication, not an official Qualcomm Academy slide deck",
                         "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
        print(name, len(payload))
    (DEST / "materiais.lock.json").write_text(json.dumps({"downloaded_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "materials": receipts}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

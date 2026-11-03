"""Fetch the five CPU baseline models and write a SHA256 lock. Python stdlib only."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def download(url):
    if not url.startswith("https://storage.googleapis.com/"):
        raise ValueError("Model URL must use the reviewed official Google storage origin")
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(100 * 1024 * 1024 + 1)
    if len(data) > 100 * 1024 * 1024:
        raise ValueError("Download exceeds 100 MiB")
    return data


def member(data, url, name):
    # Read one exact allowlisted member. Never extract an archive to disk.
    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return archive.read(name)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        matches = [entry for entry in archive.getmembers() if entry.name == name or entry.name == "./" + name]
        if len(matches) != 1:
            raise ValueError("Expected exactly one archive member: " + name)
        info = matches[0]
        if not info.isfile() or info.size > 100 * 1024 * 1024:
            raise ValueError("Invalid model archive member")
        return archive.extractfile(info).read()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("names", nargs="*", default=[])
    p.add_argument("--verify", action="store_true", help="Offline verification of models.lock.json")
    a = p.parse_args()
    dest = ROOT / "models"
    dest.mkdir(exist_ok=True)
    lock_path = dest / "models.lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    if a.verify:
        if not lock:
            raise ValueError("No model lock exists. Fetch and review models first.")
        for name, spec in lock.items():
            if Path(name).name != name:
                raise ValueError("Invalid lock entry")
            if hashlib.sha256((dest / name).read_bytes()).hexdigest() != spec["sha256"]:
                raise ValueError("Hash mismatch: " + name)
        print("PASS: all locked model assets match")
        return
    profiles = json.loads((ROOT / "ai" / "profiles.json").read_text())
    names = a.names or list(profiles)
    for name in names:
        spec = profiles[name]
        data = download(spec["source"])
        model = member(data, spec["source"], spec["archive_member"]) if "archive_member" in spec else data
        if model[4:8] != b"TFL3":
            raise ValueError("Downloaded payload is not a TFLite FlatBuffer: " + name)
        assets = {spec["model"]: model}
        if "labels_member" in spec:
            assets[spec["labels"]] = member(data, spec["source"], spec["labels_member"])
        if "labels_url" in spec:
            assets[spec["labels"]] = download(spec["labels_url"])
        for filename, payload in assets.items():
            (dest / filename).write_bytes(payload)
            lock[filename] = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
                              "source": spec.get("labels_url", spec["source"]) if filename.endswith(".txt") else spec["source"]}
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print("Fetched: " + name)
    print("First download establishes the lock. Review it and freeze it for rehearsal.")


if __name__ == "__main__":
    main()

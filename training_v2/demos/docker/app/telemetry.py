"""D2-01 / D2-02: small HTTP telemetry application, without third-party packages."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import platform
import time

START = time.monotonic()


def snapshot():
    uptime = None
    try:
        uptime = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        pass
    return {"application": "qb560d-training", "version": os.environ.get("APP_VERSION", "1.0.0"),
            "machine": platform.machine(), "system_uptime_s": uptime,
            "process_uptime_s": round(time.monotonic() - START, 3)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/telemetry"):
            self.send_error(404)
            return
        payload = {"status": "ok"} if self.path == "/health" else snapshot()
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()

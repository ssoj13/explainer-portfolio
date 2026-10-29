#!/usr/bin/env python3
"""
Apple Studio Interactive Casting & Storyboard Server (C:\_apol\studio_server.py)
Serves C:\_apol over HTTP on port 8765 and provides real-time JSON persistence:
  - GET  /api/status     -> server health & paths
  - GET  /api/manifest   -> full C:\_apol\generation_manifest.json
  - GET  /api/selection  -> current C:\_apol\production_selection.json
  - POST /api/selection  -> atomically writes C:\_apol\production_selection.json
"""
import http.server
import json
import os
import socketserver
import tempfile
from datetime import datetime, timezone

ROOT_DIR = r"C:\_apol"
SELECTION_PATH = os.path.join(ROOT_DIR, "production_selection.json")
MANIFEST_PATH = os.path.join(ROOT_DIR, "generation_manifest.json")
PORT = 8765


class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/status"):
            self._send_json({
                "ok": True,
                "server": "Apple Studio Selection Server v2.0",
                "root_dir": ROOT_DIR,
                "selection_path": SELECTION_PATH,
                "manifest_path": MANIFEST_PATH
            })
            return
        if self.path.startswith("/api/selection"):
            if os.path.exists(SELECTION_PATH):
                with open(SELECTION_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
            self._send_json(data)
            return
        if self.path.startswith("/api/manifest"):
            if os.path.exists(MANIFEST_PATH):
                with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
            self._send_json(data)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/selection"):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
            payload["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat()
            # Atomic write to C:\_apol\production_selection.json
            fd, tmp_path = tempfile.mkstemp(dir=ROOT_DIR, prefix=".sel_", suffix=".json")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, SELECTION_PATH)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            self._send_json({
                "ok": True,
                "saved_to": SELECTION_PATH,
                "updated_at": payload["updated_at"],
                "bytes": os.path.getsize(SELECTION_PATH)
            })
            return
        self.send_response(404)
        self.end_headers()

    def _send_json(self, obj):
        body = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    with ThreadedHTTPServer(("127.0.0.1", PORT), StudioHandler) as httpd:
        print(f"Apple Studio Server listening on http://127.0.0.1:{PORT}")
        httpd.serve_forever()

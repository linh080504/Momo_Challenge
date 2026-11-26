"""DEV ONLY: minimal POST /v1/analyze on 127.0.0.1 so run_eval.py can hit the analyzer without the backend.

The real endpoint is owned by the backend (apps/api/app/api). Payload contract mirrors docs/TASKS.md:
{"text": str, "image_base64"?: str, "image_mime"?: "image/png"|"image/jpeg"} -> analysis.schema.json.

    cd apps/api && python -m app.analyzer.devserver --port 8765        # LLM_PROVIDER from env (default none)
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import AnalyzerError, analyze

STATUS = {"empty_input": 422, "unsupported_mime": 415, "image_too_large": 413}
MAX_BODY = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/analyze":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._send(413, {"error": "Ảnh quá 5 MB."})
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            image = base64.b64decode(payload["image_base64"], validate=True) if payload.get("image_base64") else None
        except (json.JSONDecodeError, binascii.Error, ValueError, TypeError):
            return self._send(422, {"error": "Dữ liệu gửi lên không hợp lệ."})
        try:
            result = asyncio.run(analyze(payload.get("text"), image, payload.get("image_mime")))
        except AnalyzerError as exc:
            return self._send(STATUS.get(exc.code, 502), {"error": exc.message, "code": exc.code})
        self._send(200, result)

    def log_message(self, fmt: str, *args) -> None:  # no request bodies in logs
        logging.getLogger("app.analyzer.devserver").debug("%s %s", self.command, self.path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"analyzer devserver on http://127.0.0.1:{args.port}/v1/analyze", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""A *deliberately vulnerable* local LFI lab for practising with POAD output.

FOR EDUCATION / AUTHORISED PRACTICE ONLY. This server is intentionally insecure:
it reads whatever file path you pass to ``?page=``. It binds to 127.0.0.1 so it
is only reachable from your own machine. Do not expose it, and never run code
like this in production.

Usage:
    python3 examples/vuln_lab.py            # http://127.0.0.1:8099
    # then, in another terminal:
    poad generate lfi --file examples/secret_flag.txt --depth 4 -o payloadlist.txt
    # and try entries from payloadlist.txt against:
    #   http://127.0.0.1:8099/?page=<PAYLOAD>

Stop with Ctrl+C.
"""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

HOST = "127.0.0.1"
PORT = 8099
# Serve relative to this examples directory to keep the "webroot" contained.
WEBROOT = os.path.dirname(os.path.abspath(__file__))


class VulnHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        page = params.get("page", [None])[0]

        if page is None:
            self._send(200,
                       "POAD vuln lab. Try /?page=secret_flag.txt (intentionally "
                       "vulnerable to path traversal).")
            return

        # INTENTIONALLY VULNERABLE: naive decode + open, relative to WEBROOT.
        candidate = unquote(page)
        target = os.path.normpath(os.path.join(WEBROOT, candidate))
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as fh:
                self._send(200, fh.read())
        except (OSError, ValueError) as exc:
            self._send(404, f"could not read {candidate!r}: {exc}")

    def log_message(self, *args) -> None:  # quieter output
        sys.stderr.write("[lab] " + (args[0] % args[1:]) + "\n")

    def _send(self, code: int, body: str) -> None:
        data = body.encode("utf-8", errors="replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), VulnHandler)
    print(f"[lab] Deliberately vulnerable LFI lab on http://{HOST}:{PORT}")
    print("[lab] Authorised local practice only. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[lab] stopping")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

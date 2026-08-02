#!/usr/bin/env python3
"""Local preview server for the built site — with HTTP Range support.

Python's stock ``http.server`` answers a Range request with the whole file
(HTTP 200), which makes Safari/iOS refuse to seek ``<audio>`` (currentTime
snaps back to 0). GitHub Pages supports Range, so audio seeking works in
production — but to reproduce that locally you need a Range-capable server.
This is that server.

    python serve.py                 # serves _site/ on http://127.0.0.1:8777
    python serve.py --dir . --port 9000
"""
from __future__ import annotations

import argparse
import http.server
import os
import re
import socketserver
from functools import partial

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that honors single-range ``Range:`` requests."""

    def send_head(self):
        range_header = self.headers.get("Range")
        if not range_header:
            resp = super().send_head()
            # Advertise range support so clients know seeking is available.
            return resp

        path = self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.exists(path):
            return super().send_head()

        m = _RANGE_RE.match(range_header.strip())
        if not m:
            return super().send_head()

        size = os.path.getsize(path)
        start_s, end_s = m.group(1), m.group(2)
        if start_s == "":
            # suffix range: last N bytes
            length = min(int(end_s), size)
            start = size - length
            end = size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
            end = min(end, size - 1)

        if start > end or start >= size:
            self.send_response(416)  # Range Not Satisfiable
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None

        f = open(path, "rb")
        f.seek(start)
        self._range_remaining = end - start + 1

        self.send_response(206)  # Partial Content
        ctype = self.guess_type(path)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(self._range_remaining))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_remaining", None)
        if remaining is None:
            super().copyfile(source, outputfile)
            return
        # Copy only the requested byte range.
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="_site", help="directory to serve (default: _site)")
    ap.add_argument("--port", type=int, default=8777, help="port (default: 8777)")
    ap.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    args = ap.parse_args()

    handler = partial(RangeRequestHandler, directory=args.dir)
    with socketserver.ThreadingTCPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {args.dir}/ with Range support at http://{args.host}:{args.port}")
        print("(Range support lets Safari/iOS seek audio, matching GitHub Pages.)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

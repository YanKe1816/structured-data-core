from __future__ import annotations

import argparse
import importlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


def load_app(target: str):
    module_name, app_name = target.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, app_name)


def run(app_target: str, host: str, port: int):
    app = load_app(app_target)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def _handle(self, method: str):
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            response = __import__("asyncio").run(app._execute(method, parsed.path, body))
            self.send_response(response.status_code)
            self.send_header("Content-type", response.media_type)
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.body)

    server = HTTPServer((host, port), Handler)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run(args.app, args.host, args.port)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Serve the blog locally without exposing directory listings or dotfiles."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def _requests_hidden_path(self) -> bool:
        path = unquote(urlparse(self.path).path)
        return any(part.startswith(".") for part in Path(path).parts if part not in {"/", "."})

    def send_head(self):
        if self._requests_hidden_path():
            self.send_error(404, "Not found")
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview the Half a Tree blog locally.")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler)
    print(f"Preview available at http://127.0.0.1:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()

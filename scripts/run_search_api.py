#!/usr/bin/env python3
"""Minimal HTTP API exposing search endpoints for Phase 2."""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.search import SearchQueryEngine  # type: ignore

DEFAULT_INDEX_PATH = REPO_ROOT / "data" / "search" / "inverted_index.json"


class SearchHandler(BaseHTTPRequestHandler):
    engine: SearchQueryEngine

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler signature
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/stats":
            self._send_json(SearchHandler.engine.stats())
            return
        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            if not query:
                self._send_json({"error": "missing query parameter 'q'"}, status=400)
                return
            language = params.get("lang", [None])[0]
            limit = int(params.get("limit", ["10"])[0])
            min_score = float(params.get("min_score", ["0"])[0])
            hits = SearchHandler.engine.search(query, language=language, limit=limit, min_score=min_score)
            self._send_json({"hits": [hit.__dict__ for hit in hits], "stats": SearchHandler.engine.stats()})
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - BaseHTTPRequestHandler signature
        return  # silence default logging


def main() -> None:
    index_path = DEFAULT_INDEX_PATH
    if not index_path.exists():
        print(f"index not found at {index_path}. build it with scripts/build_search_index.py", file=sys.stderr)
        sys.exit(1)
    SearchHandler.engine = SearchQueryEngine(index_path)
    server = HTTPServer(("0.0.0.0", 8080), SearchHandler)
    print("Search API running on http://0.0.0.0:8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

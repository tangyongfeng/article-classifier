#!/usr/bin/env python3
"""Run ad-hoc searches against the Phase 2 inverted index."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.search import SearchQueryEngine  # type: ignore

DEFAULT_INDEX_PATH = REPO_ROOT / "data" / "search" / "inverted_index.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Query text to search for")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH, help="Path to inverted index JSON")
    parser.add_argument("--language", help="Optional language filter (e.g. zh-cn)")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of hits to return")
    parser.add_argument("--min-score", type=float, default=0.0, help="Minimum score threshold")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = SearchQueryEngine(args.index)
    hits = engine.search(args.query, language=args.language, limit=args.limit, min_score=args.min_score)
    payload = [hit.__dict__ for hit in hits]
    print(json.dumps({"hits": payload, "stats": engine.stats()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

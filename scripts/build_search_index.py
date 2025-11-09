#!/usr/bin/env python3
"""Build the Phase 2 inverted index and optional vector store."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.search import InvertedIndexBuilder, VectorEncoder, VectorSearchEngine  # type: ignore
from src.storage import NoteJsonStorage  # type: ignore

DEFAULT_JSON_ROOT = REPO_ROOT / "data" / "json" / "ingest"
DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "search"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-root", type=Path, default=DEFAULT_JSON_ROOT, help="Path to note JSON storage root")
    parser.add_argument("--output", type=Path, default=DEFAULT_INDEX_DIR, help="Directory to write index files")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit on number of notes to index")
    parser.add_argument("--vector", action="store_true", help="Also build prototype vector embeddings")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    json_root = args.json_root
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    builder = InvertedIndexBuilder(json_root, output_dir=output_dir)
    result = builder.build(limit=args.limit)
    print(json.dumps({"index": str(result.output_path), "notes": result.note_count, "tokens": result.token_count}, ensure_ascii=False))

    if args.vector:
        storage = NoteJsonStorage(json_root)
        vector_path = output_dir / "vector_store.json"
        engine = VectorSearchEngine(vector_path, encoder=VectorEncoder())
        note_ids = list(storage.list_note_ids())
        for note_id in note_ids:
            bundle = storage.load_note_bundle(note_id)
            clean_variant = bundle.clean_text_variant
            content = clean_variant.content or ""
            if not content and clean_variant.content_path:
                content_path = Path(clean_variant.content_path)
                if content_path.exists():
                    content = content_path.read_text(encoding="utf-8")
            summary_payload = InvertedIndexBuilder._extract_summary(bundle)
            combined = content + "\n" + str(summary_payload.get("summary", ""))
            engine.upsert(note_id, combined)
        engine.persist()
        print(json.dumps({"vector_store": str(vector_path), "notes": len(note_ids)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

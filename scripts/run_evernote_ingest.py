#!/usr/bin/env python3
"""CLI entry point to run the Evernote ingest agent on a single file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingest import EvernoteIngestAgent  # type: ignore
from src.models import IngestTask  # type: ignore
from src.utils import ensure_directory  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Evernote ingest agent for a given source file.")
    parser.add_argument("source_path", type=Path, help="Path to the Evernote HTML/ENEX export")
    parser.add_argument("--json-root", type=Path, default=REPO_ROOT / "data" / "json" / "ingest", help="Directory to store agent output")
    parser.add_argument("--title", help="Optional title override")
    parser.add_argument("--language-hint", help="Optional language code hint")
    parser.add_argument("--external-id", help="External identifier to attach to ingest source")
    parser.add_argument("--batch-id", help="Batch identifier for journaling")
    parser.add_argument("--created-at", help="Original creation timestamp (ISO8601)")
    parser.add_argument("--captured-at", help="Capture timestamp (ISO8601)")
    parser.add_argument("--requested-output", action="append", default=[], help="Additional outputs to request (repeatable)")
    return parser.parse_args()


def build_task(args: argparse.Namespace) -> IngestTask:
    payload = {
        "source_path": str(args.source_path),
        "external_id": args.external_id,
        "batch_id": args.batch_id,
        "title": args.title,
        "language_hint": args.language_hint,
        "created_at": args.created_at,
        "captured_at": args.captured_at,
    }
    payload = {k: v for k, v in payload.items() if v}
    return IngestTask(
        task_id=uuid4(),
        agent=EvernoteIngestAgent.AGENT_ID,
        payload=payload,
        requested_outputs=list(args.requested_output),
    )


def main() -> None:
    args = parse_args()
    source_path = args.source_path.expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Source path not found: {source_path}")

    ensure_directory(args.json_root)
    agent = EvernoteIngestAgent(json_root=args.json_root)
    task = build_task(args)
    result = agent.process(task)

    summary = {
        "status": result.status.value,
        "task_id": str(result.task_id),
        "note_id": str(result.note.id) if result.note else None,
        "ingest_source_id": str(result.ingest_source.id) if result.ingest_source else None,
        "variants": [v.variant_type for v in result.content_variants],
        "output_root": str(args.json_root / "notes" / str(result.note.id) if result.note else args.json_root),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

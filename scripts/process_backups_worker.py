#!/usr/bin/env python3
"""Background worker to convert Evernote backup HTML files using the ingest pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Process
from pathlib import Path
from typing import Iterable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingest import EvernoteIngestAgent  # type: ignore
from src.models import IngestStatus, IngestTask  # type: ignore

DEFAULT_INPUT = REPO_ROOT / "backups"
DEFAULT_JSON_ROOT = REPO_ROOT / "data" / "json" / "ingest"
DEFAULT_LOG = REPO_ROOT / "data" / "logs" / "backup_ingest.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Directory containing Evernote HTML exports")
    parser.add_argument("--json-root", type=Path, default=DEFAULT_JSON_ROOT, help="Destination JSON storage root")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="Path to append worker progress logs")
    parser.add_argument("--daemon", action="store_true", help="Run worker in background and exit immediately")
    parser.add_argument("--limit", type=int, default=0, help="Process at most N files (0 = all)")
    parser.add_argument("--batch-id", help="Optional batch id recorded in ingest notes")
    return parser.parse_args()


def discover_html_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.htm")):
        yield path
    for path in sorted(root.rglob("*.html")):
        yield path


def run_worker(config: dict) -> None:
    input_dir = Path(config["input"])
    json_root = Path(config["json_root"])
    log_path = Path(config["log"])
    limit = int(config["limit"])
    batch_id = config.get("batch_id")

    agent = EvernoteIngestAgent(json_root=json_root)
    processed = 0
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for html_file in discover_html_files(input_dir):
        if limit and processed >= limit:
            break
        task = IngestTask(
            task_id=uuid4(),
            agent="evernote_ingest",
            payload={
                "source_path": str(html_file),
                "source_type": "evernote_html",
                "batch_id": batch_id,
            },
        )
        result = agent.process(task)
        record = {
            "file": str(html_file),
            "status": result.status.value if isinstance(result.status, IngestStatus) else str(result.status),
            "note_id": str(result.note.id) if result.note else None,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        processed += 1

    print(json.dumps({"processed": processed, "log": str(log_path)}, ensure_ascii=False))


def main() -> None:
    args = parse_args()
    config = {
        "input": str(args.input),
        "json_root": str(args.json_root),
        "log": str(args.log),
        "limit": args.limit,
        "batch_id": args.batch_id,
    }

    if args.daemon:
        process = Process(target=run_worker, args=(config,), daemon=False)
        process.start()
        print(
            json.dumps({"status": "started", "pid": process.pid, "log": str(args.log)}, ensure_ascii=False),
            flush=True,
        )
        return

    run_worker(config)


if __name__ == "__main__":
    main()

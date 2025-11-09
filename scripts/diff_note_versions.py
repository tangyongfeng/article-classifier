#!/usr/bin/env python3
"""CLI utility to compare raw/clean/LLM outputs for notes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core import NoteVersionDiffer
from src.storage import NoteJsonStorage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-root",
    type=Path,
    default=REPO_ROOT / "data" / "json" / "ingest",
        help="Path to JSON storage root.",
    )
    parser.add_argument("note_ids", nargs="*", help="Specific note UUIDs to diff.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of notes to process (ignored if note_ids provided).",
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Print unified diff segments; otherwise only show excerpts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write JSON report instead of printing.",
    )
    return parser.parse_args()


def iter_note_ids(storage: NoteJsonStorage, explicit: Iterable[str], limit: int) -> Iterable[str]:
    if explicit:
        for note_id in explicit:
            yield note_id
        return
    count = 0
    for note_id in storage.list_note_ids():
        if limit and count >= limit:
            break
        yield note_id
        count += 1


def format_diff_segment(segment) -> str:
    header = segment.label or "@@"
    body = "\n".join(segment.lines)
    return f"{header}\n{body}"


def main() -> None:
    args = parse_args()
    storage = NoteJsonStorage(args.json_root)
    differ = NoteVersionDiffer(args.json_root)

    reports = []
    for note_id in iter_note_ids(storage, args.note_ids, args.limit):
        try:
            reports.append(differ.diff_note(note_id))
        except FileNotFoundError:
            print(f"[warn] metadata.json not found for {note_id}")
        except Exception as exc:
            print(f"[error] failed to diff {note_id}: {exc}")

    if args.output:
        payload = []
        for report in reports:
            payload.append(
                {
                    "note_id": str(report.note.id),
                    "title": report.note.canonical_title,
                    "language": report.note.language,
                    "raw_excerpt": report.raw_excerpt,
                    "clean_excerpt": report.clean_excerpt,
                    "summary_excerpt": report.summary_excerpt,
                    "raw_to_clean_diff": [format_diff_segment(seg) for seg in report.raw_to_clean_diff],
                    "clean_to_summary_diff": [format_diff_segment(seg) for seg in report.clean_to_summary_diff],
                }
            )
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote report for {len(reports)} notes to {args.output}")
        return

    for report in reports:
        print("=" * 80)
        print(f"Note: {report.note.id} | {report.note.canonical_title}")
        print(f"Language: {report.note.language}")
        print("- Raw excerpt:\n" + report.raw_excerpt)
        print("- Clean excerpt:\n" + report.clean_excerpt)
        print("- Summary excerpt:\n" + report.summary_excerpt)
        if args.show_diff:
            print("-- Raw vs Clean diff --")
            for segment in report.raw_to_clean_diff:
                print(format_diff_segment(segment))
            print("-- Clean vs Summary diff --")
            for segment in report.clean_to_summary_diff:
                print(format_diff_segment(segment))
    if not reports:
        print("No notes processed. Check note IDs or json-root path.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Probe Evernote export samples and summarize structural features."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, List, Optional
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils import (  # type: ignore
    compute_file_checksum,
    ensure_directory,
    extract_text_from_html,
    guess_language,
)

SUPPORTED_EXTENSIONS = {".html", ".htm", ".enex", ".xml"}


@dataclass
class ItemSummary:
    source_file: str
    file_checksum: str
    detected_type: str
    item_index: int
    title: str
    language: str
    char_count: int
    line_count: int
    resource_count: int
    created_at: Optional[str]
    updated_at: Optional[str]


def iter_sample_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from iter_sample_files(sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS or p.is_dir()))
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Evernote export samples for ingest design.")
    parser.add_argument("paths", nargs="+", type=Path, help="Files or folders to inspect")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "json" / "snapshots", help="Directory to store JSON report")
    parser.add_argument("--max-items", type=int, default=0, help="Limit total analyzed items (0 = all)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary to stdout")
    return parser.parse_args()


def analyze_html_payload(html: str, *, title_hint: str = "") -> tuple[str, str, int, int]:
    text, derived_title = extract_text_from_html(html)
    title = title_hint or derived_title
    char_count = len(text)
    line_count = text.count("\n") + 1 if text else 0
    return text, title, char_count, line_count


def analyze_html_file(path: Path, item_index: int) -> ItemSummary:
    html = path.read_text(encoding="utf-8", errors="ignore")
    text, title, char_count, line_count = analyze_html_payload(html)
    language = guess_language(text)
    checksum = compute_file_checksum(path)
    return ItemSummary(
        source_file=str(path),
        file_checksum=checksum,
        detected_type="html_note",
        item_index=item_index,
        title=title or path.stem,
        language=language,
        char_count=char_count,
        line_count=line_count,
        resource_count=0,
        created_at=None,
        updated_at=None,
    )


def _extract_enml_content(content: str) -> str:
    start = content.find("<en-note")
    if start == -1:
        return content
    return content[start:]


def analyze_enex_file(path: Path, starting_index: int) -> List[ItemSummary]:
    summaries: List[ItemSummary] = []
    tree = ElementTree.parse(path)
    root = tree.getroot()
    checksum = compute_file_checksum(path)

    notes = [node for node in root.iter() if node.tag.split("}")[-1] == "note"]

    for local_index, note in enumerate(notes, start=0):
        title = (_find_child_text(note, "title") or "").strip()
        created_raw = _find_child_text(note, "created")
        updated_raw = _find_child_text(note, "updated")
        content_raw = _find_child_text(note, "content") or ""
        enml = _extract_enml_content(content_raw)
        text, title_candidate, char_count, line_count = analyze_html_payload(enml, title_hint=title)
        language = guess_language(text)
        resources = [node for node in note if node.tag.split("}")[-1] == "resource"]
        global_index = starting_index + local_index
        summaries.append(
            ItemSummary(
                source_file=f"{path}::note[{local_index}]",
                file_checksum=checksum,
                detected_type="enex_note",
                item_index=global_index,
                title=title_candidate or f"note-{global_index}",
                language=language,
                char_count=char_count,
                line_count=line_count,
                resource_count=len(resources),
                created_at=_parse_enex_timestamp(created_raw),
                updated_at=_parse_enex_timestamp(updated_raw),
            )
        )
    return summaries


def _find_child_text(node: ElementTree.Element, tag_name: str) -> Optional[str]:
    for child in node:
        if child.tag.split("}")[-1] == tag_name:
            return child.text
    return None


def _parse_enex_timestamp(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").isoformat() + "Z"
    except ValueError:
        return None


def run_analysis(args: argparse.Namespace) -> dict:
    items: List[ItemSummary] = []
    files_scanned: List[Path] = []
    running_index = 1

    for path in iter_sample_files(args.paths):
        files_scanned.append(path)
        if path.suffix.lower() in {".html", ".htm"}:
            items.append(analyze_html_file(path, running_index))
            running_index += 1
        else:
            summaries = analyze_enex_file(path, running_index)
            items.extend(summaries)
            running_index += max(len(summaries), 1)
        if args.max_items and len(items) >= args.max_items:
            items = items[: args.max_items]
            break

    language_counter = Counter(item.language or "und" for item in items)
    type_counter = Counter(item.detected_type for item in items)

    report = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scanned_inputs": [str(p) for p in args.paths],
        "total_files": len(files_scanned),
        "total_items": len(items),
        "by_language": dict(language_counter),
        "by_type": dict(type_counter),
        "items": [asdict(item) for item in items],
    }
    return report


def write_report(report: dict, output_dir: Path) -> Path:
    ensure_directory(output_dir)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"evernote_analysis_{timestamp}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    report = run_analysis(args)
    output_path = write_report(report, args.output_dir)

    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = {
            "output": str(output_path),
            "total_items": report["total_items"],
            "languages": report["by_language"],
            "types": report["by_type"],
        }
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

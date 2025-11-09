"""Utilities for comparing note content across ingest stages."""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from ..models import Note
from ..storage import NoteJsonStorage


@dataclass
class DiffSegment:
    label: str
    lines: List[str]


@dataclass
class VersionDiff:
    note: Note
    raw_excerpt: str
    clean_excerpt: str
    summary_excerpt: str
    raw_to_clean_diff: List[DiffSegment]
    clean_to_summary_diff: List[DiffSegment]


class NoteVersionDiffer:
    """Build diff reports between raw HTML, cleaned text, and LLM outputs."""

    def __init__(self, storage_root: Path) -> None:
        self._storage = NoteJsonStorage(storage_root)

    def list_note_ids(self) -> Iterable[str]:
        return self._storage.list_note_ids()

    def diff_note(self, note_id: str) -> VersionDiff:
        bundle = self._storage.load_note_bundle(note_id)
        note = bundle.note
        raw_text = self._resolve_variant_content(bundle.raw_html_variant)
        clean_text = self._resolve_variant_content(bundle.clean_text_variant)
        summary_text = self._resolve_latest_summary(bundle)

        raw_excerpt = raw_text[:400]
        clean_excerpt = clean_text[:400]
        summary_excerpt = summary_text[:400]

        raw_diff = self._build_unified_diff(raw_text, clean_text, label_a="raw", label_b="clean")
        summary_diff = self._build_unified_diff(clean_text, summary_text, label_a="clean", label_b="summary")

        return VersionDiff(
            note=note,
            raw_excerpt=raw_excerpt,
            clean_excerpt=clean_excerpt,
            summary_excerpt=summary_excerpt,
            raw_to_clean_diff=raw_diff,
            clean_to_summary_diff=summary_diff,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_variant_content(variant) -> str:
        if variant.content:
            return variant.content
        if variant.content_path:
            path = Path(variant.content_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""

    @staticmethod
    def _resolve_latest_summary(bundle) -> str:
        if not bundle.extractions:
            return ""
        llm_runs = [ex for ex in bundle.extractions if ex.extractor.startswith("llm_enhance:v0")]
        target = llm_runs[-1] if llm_runs else bundle.extractions[-1]
        payload = target.payload or {}
        summary = payload.get("summary", "")
        if isinstance(summary, str):
            return summary
        return json.dumps(summary, ensure_ascii=False, indent=2)

    @staticmethod
    def _build_unified_diff(text_a: str, text_b: str, *, label_a: str, label_b: str) -> List[DiffSegment]:
        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)
        diff = difflib.unified_diff(lines_a, lines_b, fromfile=label_a, tofile=label_b)
        segments: List[DiffSegment] = []
        current_label = ""
        current_lines: List[str] = []
        for line in diff:
            if line.startswith("@@"):
                if current_lines:
                    segments.append(DiffSegment(label=current_label, lines=current_lines))
                    current_lines = []
                current_label = line.strip()
                continue
            current_lines.append(line.rstrip("\n"))
        if current_lines:
            segments.append(DiffSegment(label=current_label, lines=current_lines))
        return segments


def generate_report(differ: NoteVersionDiffer, note_ids: Iterable[str]) -> List[VersionDiff]:
    reports: List[VersionDiff] = []
    for note_id in note_ids:
        try:
            reports.append(differ.diff_note(note_id))
        except FileNotFoundError:
            continue
    return reports

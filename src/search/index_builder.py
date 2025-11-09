"""Build inverted index structures from stored notes."""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from ..storage import NoteJsonStorage

TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]{2,}")


@dataclass
class IndexBuildResult:
    output_path: Path
    note_count: int
    token_count: int


class InvertedIndexBuilder:
    """Construct a basic inverted index over note clean text and LLM keywords."""

    def __init__(self, json_root: Path, *, output_dir: Path) -> None:
        self._json_root = json_root
        self._output_dir = output_dir
        self._storage = NoteJsonStorage(json_root)

    def build(self, *, limit: int = 0) -> IndexBuildResult:
        ensure_dir = self._output_dir
        ensure_dir.mkdir(parents=True, exist_ok=True)
        postings: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        note_metadata: Dict[str, Dict[str, object]] = {}
        total_tokens = 0

        note_ids = self._prepare_note_ids(limit)
        document_freq: Counter[str] = Counter()
        field_weights = {"clean": 1.0, "summary": 1.5, "keywords": 2.0}

        for note_id in note_ids:
            bundle = self._storage.load_note_bundle(note_id)
            note = bundle.note
            clean_text = self._resolve_variant_content(bundle.clean_text_variant)
            summary_info = self._extract_summary(bundle)
            keywords = summary_info.get("keywords", [])
            summary_text = summary_info.get("summary", "")

            tokens = self._tokenize(clean_text)
            summary_tokens = self._tokenize(summary_text)
            keyword_tokens = [kw.lower() for kw in keywords if isinstance(kw, str)]

            field_counter: Dict[str, Counter[str]] = {
                "clean": Counter(tokens),
                "summary": Counter(summary_tokens),
                "keywords": Counter(keyword_tokens),
            }

            merged_counts: Counter[str] = Counter()
            for field, counter in field_counter.items():
                for token, count in counter.items():
                    weight = field_weights[field]
                    merged_counts[token] += count * weight

            total_tokens += sum(merged_counts.values())
            for token, score in merged_counts.items():
                postings[token].append((note_id, float(score)))
                document_freq[token] += 1

            note_metadata[note_id] = {
                "title": note.canonical_title,
                "language": note.language,
                "keywords": keywords,
                "summary": summary_text,
                "created_at": note.ingested_at.isoformat().replace("+00:00", "Z"),
            }

        index_payload = {
            "built_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "documents": note_metadata,
            "postings": self._normalize_postings(postings, document_freq, len(note_metadata)),
            "stats": {
                "note_count": len(note_metadata),
                "token_count": total_tokens,
            },
        }

        output_path = self._output_dir / "inverted_index.json"
        output_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return IndexBuildResult(output_path=output_path, note_count=len(note_metadata), token_count=total_tokens)

    def _prepare_note_ids(self, limit: int) -> Iterable[str]:
        count = 0
        for note_id in self._storage.list_note_ids():
            yield note_id
            count += 1
            if limit and count >= limit:
                break

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]

    @staticmethod
    def _normalize_postings(
        postings: Dict[str, List[Tuple[str, float]]],
        document_freq: Counter,
        document_count: int,
    ) -> Dict[str, List[Dict[str, object]]]:
        normalized: Dict[str, List[Dict[str, object]]] = {}
        for token, entries in postings.items():
            idf = math.log(1 + document_count / (1 + document_freq[token]))
            normalized[token] = [
                {"note_id": note_id, "score": round(score * idf, 4)} for note_id, score in sorted(entries, key=lambda x: x[1], reverse=True)
            ]
        return normalized

    @staticmethod
    def _extract_summary(bundle) -> Dict[str, object]:
        if not bundle.extractions:
            return {"summary": "", "keywords": []}
        llm_runs = [ex for ex in bundle.extractions if ex.extractor.startswith("llm_enhance:v0")]
        target = llm_runs[-1] if llm_runs else bundle.extractions[-1]
        payload = target.payload or {}
        summary = payload.get("summary", "")
        if isinstance(summary, str):
            summary_text = summary
        else:
            summary_text = json.dumps(summary, ensure_ascii=False)
        keywords = payload.get("keywords", [])
        return {"summary": summary_text, "keywords": keywords}

    @staticmethod
    def _resolve_variant_content(variant) -> str:
        if variant.content:
            return variant.content
        if variant.content_path:
            path = Path(variant.content_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""

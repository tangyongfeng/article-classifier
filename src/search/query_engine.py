"""Query inverted index for basic search functionality."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .index_builder import TOKEN_PATTERN, InvertedIndexBuilder


@dataclass
class SearchHit:
    note_id: str
    title: str
    language: str
    score: float
    summary: str
    keywords: List[str]


class SearchQueryEngine:
    """Provide ranked results with optional metadata filters."""

    def __init__(self, index_path: Path) -> None:
        if not index_path.exists():
            raise FileNotFoundError(f"index not found at {index_path}")
        self._index_path = index_path
        self._payload = json.loads(index_path.read_text(encoding="utf-8"))
        self._documents: Dict[str, Dict[str, object]] = self._payload.get("documents", {})
        self._postings: Dict[str, List[Dict[str, object]]] = self._payload.get("postings", {})
        self._stats = self._payload.get("stats", {})

    def search(
        self,
        query: str,
        *,
        language: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[SearchHit]:
        tokens = self._normalize_tokens(query)
        if not tokens:
            return []

        accumulator: Dict[str, float] = {}
        for token in tokens:
            for entry in self._postings.get(token, []):
                note_id = entry["note_id"]
                accumulator.setdefault(note_id, 0.0)
                accumulator[note_id] += float(entry.get("score", 0.0))

        ranked: List[SearchHit] = []
        for note_id, score in sorted(accumulator.items(), key=lambda pair: pair[1], reverse=True):
            if score < min_score:
                continue
            doc = self._documents.get(note_id)
            if not doc:
                continue
            if language and doc.get("language") != language:
                continue
            ranked.append(
                SearchHit(
                    note_id=note_id,
                    title=str(doc.get("title", "")),
                    language=str(doc.get("language", "")),
                    score=round(score, 4),
                    summary=str(doc.get("summary", "")),
                    keywords=[str(item) for item in doc.get("keywords", [])],
                )
            )
            if limit and len(ranked) >= limit:
                break
        return ranked

    def stats(self) -> Dict[str, object]:
        return {
            "notes_indexed": self._stats.get("note_count", 0),
            "tokens_indexed": self._stats.get("token_count", 0),
            "unique_terms": len(self._postings),
        }

    @staticmethod
    def _normalize_tokens(text: str) -> List[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]

    def rebuild_if_missing(self, json_root: Path, *, output_dir: Path) -> None:
        if self._index_path.exists():
            return
        builder = InvertedIndexBuilder(json_root, output_dir=output_dir)
        builder.build()
        self.__init__(self._index_path)

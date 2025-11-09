"""Prototype vector search components for Phase 2 experimentation."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .index_builder import TOKEN_PATTERN


@dataclass
class VectorSearchHit:
    note_id: str
    score: float


class VectorEncoder:
    """Lightweight embedding model using token frequency vectors."""

    def encode(self, text: str) -> Dict[str, float]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
        if not tokens:
            return {}
        counts: Dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        norm = math.sqrt(sum(count * count for count in counts.values()))
        if norm == 0:
            norm = 1.0
        return {token: count / norm for token, count in counts.items()}


class VectorSearchEngine:
    """Store simple embeddings and evaluate cosine similarity."""

    def __init__(self, storage_path: Path, *, encoder: VectorEncoder | None = None) -> None:
        self._storage_path = storage_path
        self._encoder = encoder or VectorEncoder()
        self._vectors: Dict[str, Dict[str, float]] = {}
        if storage_path.exists():
            self._vectors = json.loads(storage_path.read_text(encoding="utf-8"))

    def upsert(self, note_id: str, text: str) -> None:
        self._vectors[note_id] = self._encoder.encode(text)

    def bulk_upsert(self, items: Iterable[Tuple[str, str]]) -> None:
        for note_id, text in items:
            self.upsert(note_id, text)

    def search(self, query: str, *, limit: int = 5, min_score: float = 0.1) -> List[VectorSearchHit]:
        query_vec = self._encoder.encode(query)
        if not query_vec:
            return []
        ranked: List[VectorSearchHit] = []
        for note_id, vector in self._vectors.items():
            score = self._cosine_similarity(query_vec, vector)
            if score >= min_score:
                ranked.append(VectorSearchHit(note_id=note_id, score=round(score, 4)))
        ranked.sort(key=lambda hit: hit.score, reverse=True)
        if limit:
            ranked = ranked[:limit]
        return ranked

    def persist(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(json.dumps(self._vectors, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        common = set(vec_a.keys()) & set(vec_b.keys())
        numerator = sum(vec_a[token] * vec_b[token] for token in common)
        norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
        norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return numerator / (norm_a * norm_b)

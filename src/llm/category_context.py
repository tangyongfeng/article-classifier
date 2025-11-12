"""Utilities for injecting existing category context into LLM prompts."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


class CategoryContextProvider:
    """Load and format category hierarchies for prompt guidance."""

    DEFAULT_CANDIDATES: tuple[Path, ...] = (
        Path("data/json/categories.json"),
        Path("data/json/ingest/categories.json"),
        Path("archive/20251109_cleanup/data/json/categories.json"),
    )

    def __init__(self, repo_root: Path, *, max_lines: int = 80) -> None:
        self._repo_root = repo_root
        self._max_lines = max_lines

    def get_guidance(self) -> str:
        return self._render_categories(self._load_categories())

    @lru_cache(maxsize=1)
    def _load_categories(self) -> list[dict]:
        for relative_path in self.DEFAULT_CANDIDATES:
            candidate = (self._repo_root / relative_path).resolve()
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            categories = payload.get("categories")
            if isinstance(categories, list):
                return categories
        return []

    @lru_cache(maxsize=1)
    def _path_index(self) -> Dict[Tuple[str, ...], List[str]]:
        index: Dict[Tuple[str, ...], List[str]] = {}

        def walk(node: dict, trail: List[str]) -> None:
            name_raw = node.get("name")
            if not isinstance(name_raw, str):
                return
            name = name_raw.strip()
            if not name:
                return
            current_path = trail + [name]
            normalized_path = tuple(self._normalize_name(part) for part in current_path)
            index[normalized_path] = current_path
            for child in node.get("children", []) or []:
                if isinstance(child, dict):
                    walk(child, current_path)

        for root in self._load_categories():
            if isinstance(root, dict):
                walk(root, [])

        return index

    def canonicalize_path(self, path: Iterable[str]) -> Optional[List[str]]:
        tokens = [self._normalize_name(part) for part in path if isinstance(part, str) and part.strip()]
        if not tokens:
            return None

        index = self._path_index()
        normalized_tuple = tuple(tokens)
        if normalized_tuple in index:
            return index[normalized_tuple]

        prefix_matches = {
            tuple(index_path[: len(tokens)])
            for normalized, index_path in index.items()
            if len(normalized) >= len(tokens) and normalized[: len(tokens)] == normalized_tuple
        }
        if len(prefix_matches) == 1:
            # Convert back to list of original names with exact casing
            only_match = next(iter(prefix_matches))
            return list(only_match)

        return None

    def default_path(self) -> Optional[List[str]]:
        index = self._path_index()
        if not index:
            return None
        first_key = next(iter(index))
        return index[first_key]

    def _normalize_name(self, value: str) -> str:
        return value.strip().lower()

    def _render_categories(self, categories: Iterable[dict]) -> str:
        lines: list[str] = []
        total_nodes = 0

        def walk(node: dict, trail: list[str]) -> None:
            nonlocal total_nodes
            name = str(node.get("name", "")).strip()
            if not name:
                return
            count = node.get("article_count")
            lineage = trail + [name]
            label = " > ".join(lineage)
            if isinstance(count, int) and count >= 0:
                label = f"{label} ({count})"
            if len(lines) < self._max_lines:
                lines.append(f"- {label}")
            total_nodes += 1
            for child in node.get("children", []) or []:
                if isinstance(child, dict):
                    walk(child, lineage)

        for root in categories:
            if isinstance(root, dict):
                walk(root, [])
            if len(lines) >= self._max_lines:
                break

        if not lines:
            return "No category data available"
        if total_nodes > len(lines):
            lines.append("- ... (truncated list, see full catalog for more)")
        return "\n".join(lines)


def infer_repo_root(json_root: Path) -> Optional[Path]:
    try:
        return json_root.resolve().parents[2]
    except (IndexError, RuntimeError):
        return None

"""Quality metrics for LLM-generated note enhancements."""
from __future__ import annotations

import re
from typing import Dict


def compute_quality_metrics(clean_text: str, payload: Dict[str, object]) -> Dict[str, float]:
    """Compute lightweight quality metrics for downstream scoring."""
    normalized_source = clean_text or ""
    normalized_summary = str(payload.get("summary", ""))
    keywords = [str(item) for item in payload.get("keywords", []) if str(item).strip()]
    action_items = [str(item) for item in payload.get("action_items", []) if str(item).strip()]

    total_chars = float(len(normalized_source.strip()))
    summary_chars = float(len(normalized_summary.strip()))
    coverage_ratio = 0.0 if total_chars == 0 else min(summary_chars / total_chars, 1.0)

    lowered_source = normalized_source.lower()
    keyword_hits = 0
    for keyword in keywords:
        token = keyword.strip().lower()
        if token and token in lowered_source:
            keyword_hits += 1
    keyword_hit_rate = 0.0 if not keywords else keyword_hits / float(len(keywords))

    sentences = [segment.strip() for segment in re.split(r"[。.!?]", normalized_summary) if segment.strip()]
    unique_summary_sentences = float(len(set(sentences)))

    estimated_read_seconds = 0.0 if total_chars == 0 else round((total_chars / 1000.0) * 60.0, 1)

    return {
        "input_chars": total_chars,
        "input_lines": float(len([line for line in normalized_source.splitlines() if line.strip()])),
        "summary_chars": summary_chars,
        "summary_coverage_ratio": round(coverage_ratio, 3),
        "keyword_hit_rate": round(keyword_hit_rate, 3),
        "action_item_count": float(len(action_items)),
        "unique_summary_sentences": unique_summary_sentences,
        "estimated_read_seconds": estimated_read_seconds,
    }


__all__ = ["compute_quality_metrics"]

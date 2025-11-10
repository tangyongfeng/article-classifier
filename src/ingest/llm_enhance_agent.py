"""LLM-powered enhancement agent for notes."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Optional
from uuid import UUID

from ..llm import LLMDispatcher
from ..llm.category_context import CategoryContextProvider, infer_repo_root
from ..models import Extraction, ProcessingJournalEntry
from ..storage import ProcessingJournalWriter, serialize_entity
from ..utils import ensure_directory
from .quality_metrics import compute_quality_metrics


class LLMEnhanceAgent:
    """Generate summaries and structured metadata for notes via LLMs."""

    AGENT_ID = "llm_enhance:v0"

    def __init__(
        self,
        *,
        json_root: Path,
        dispatcher: LLMDispatcher,
        journal_writer: Optional[ProcessingJournalWriter] = None,
    ) -> None:
        self._json_root = ensure_directory(json_root)
        self._dispatcher = dispatcher
        journal_root = self._json_root / "_journal"
        self._journal_writer = journal_writer or ProcessingJournalWriter(journal_root)
        repo_root = infer_repo_root(self._json_root)
        self._category_provider: Optional[CategoryContextProvider] = (
            CategoryContextProvider(repo_root) if repo_root else None
        )

    def enhance_note(self, note_id: str, *, models: Optional[Iterable[str]] = None) -> dict:
        note_root = self._json_root / "notes" / note_id
        metadata_path = note_root / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"metadata.json not found for note {note_id}")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        clean_text = self._extract_clean_text(note_root, metadata)
        title = metadata.get("note", {}).get("canonical_title", "未命名")
        language = metadata.get("note", {}).get("language", "zh-cn")

        started_at = datetime.now(UTC)
        category_guidance = self._category_provider.get_guidance() if self._category_provider else None
        response = self._dispatcher.summarize_note(
            title=title,
            content=clean_text,
            language=language,
            models=models,
            category_guidance=category_guidance,
        )
        finished_at = datetime.now(UTC)

        if response.succeeded and isinstance(response.parsed, dict):
            payload = self._normalize_llm_payload(response.parsed, response.model.name)
            status = "success"
        else:
            payload = self._build_fallback_payload(clean_text)
            status = "fallback"

        metrics = compute_quality_metrics(clean_text, payload)
        quality_score = self._score_quality(status, metrics)
        model_used = payload.get("source") or (response.model.name if response.model else "unknown")

        extraction = self._create_extraction(
            note_id=note_id,
            metadata=metadata,
            payload=payload,
            model_name=model_used,
            quality_score=quality_score,
        )

        self._persist_extraction(note_root, metadata, extraction)
        llm_section = metadata.setdefault("llm", {})
        llm_section.update(
            {
                "status": status,
                "model": extraction.extractor.split("#", 1)[-1],
                "updated_at": finished_at.isoformat().replace("+00:00", "Z"),
                "latency_seconds": response.latency_seconds,
                "summary": payload,
                "quality": {
                    "score": quality_score,
                    "metrics": metrics,
                },
            }
        )
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        journal_entry = ProcessingJournalEntry.new(
            note_id=UUID(note_id),
            stage="llm_enhance",
            agent_id=self.AGENT_ID,
            status="success" if response.succeeded else "failed",
            started_at=started_at,
            finished_at=finished_at,
            input_ref={
                "note_id": note_id,
                "requested_models": list(models) if models else None,
                "dispatcher_model": response.model.name,
            },
            output_ref={
                "extraction_id": str(extraction.id),
                "status": status,
                "quality_score": quality_score,
            },
            error_detail=response.error if not response.succeeded else None,
        )
        self._journal_writer.write(journal_entry)

        return {
            "note_id": note_id,
            "status": status,
            "model": extraction.extractor.split("#", 1)[-1],
            "extraction_id": str(extraction.id),
            "latency_seconds": response.latency_seconds,
        }

    # ------------------------------------------------------------------
    def _extract_clean_text(self, note_root: Path, metadata: dict) -> str:
        variants = metadata.get("variants", [])
        for variant in variants:
            if variant.get("variant_type") != "clean_text":
                continue
            if variant.get("content"):
                return variant["content"]
            version = variant.get("version", 1)
            candidate = note_root / "clean" / f"v{version}.txt"
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        raise ValueError("No clean_text variant content available")

    def _build_fallback_payload(self, text: str) -> dict:
        normalized = " ".join(text.strip().split())
        summary = normalized[:80] if normalized else "内容为空"
        keywords: list[str] = []
        for raw_line in text.splitlines():
            token = raw_line.strip().strip("。.")
            if not token:
                continue
            if token not in keywords:
                keywords.append(token)
            if len(keywords) == 5:
                break
        while len(keywords) < 5:
            keywords.append("摘录")
        return {
            "summary": summary,
            "keywords": keywords[:5],
            "action_items": ["无"],
            "source": "fallback",
            "category_path": ["未分类"],
            "new_category_suggestion": None,
        }

    def _normalize_llm_payload(self, raw: dict, model_name: str) -> dict:
        summary = str(raw.get("summary", "")).strip()
        if not summary:
            summary = "（空摘要）"
        if len(summary) > 80:
            summary = summary[:80]

        keywords: list[str] = []
        for item in raw.get("keywords", []):
            token = str(item).strip()
            if token and token not in keywords:
                keywords.append(token)
            if len(keywords) == 5:
                break
        while len(keywords) < 5:
            keywords.append("待补充")

        action_items = [str(item).strip() for item in raw.get("action_items", []) if str(item).strip()]
        if not action_items:
            action_items = ["无"]

        category_path: list[str] = []
        raw_category_path = raw.get("category_path")
        if isinstance(raw_category_path, list):
            for item in raw_category_path:
                token = str(item).strip()
                if token:
                    category_path.append(token)
        elif isinstance(raw_category_path, str):
            token = raw_category_path.strip()
            if token:
                category_path.append(token)

        new_category = raw.get("new_category_suggestion")
        if isinstance(new_category, list):
            new_category = [str(item).strip() for item in new_category if str(item).strip()]
            if not new_category:
                new_category = None
        elif isinstance(new_category, str):
            new_category = new_category.strip() or None
        else:
            new_category = None

        return {
            "summary": summary,
            "keywords": keywords[:5],
            "action_items": action_items,
            "source": model_name,
            "category_path": category_path,
            "new_category_suggestion": new_category,
        }

    def _create_extraction(
        self,
        *,
        note_id: str,
        metadata: dict,
        payload: dict,
        model_name: str,
        quality_score: float,
    ) -> Extraction:
        versions = [
            entry.get("version", 0)
            for entry in metadata.get("extractions", [])
            if entry.get("extractor", "").startswith(self.AGENT_ID)
        ]
        next_version = (max(versions) + 1) if versions else 1
        note_uuid = UUID(note_id)
        extractor_id = f"{self.AGENT_ID}#{model_name}"
        extraction = Extraction.new(
            note_id=note_uuid,
            extractor=extractor_id,
            payload=payload,
            version=next_version,
            created_by=self.AGENT_ID,
            quality_score=quality_score,
        )
        return extraction

    def _persist_extraction(self, note_root: Path, metadata: dict, extraction: Extraction) -> None:
        extraction_dir = ensure_directory(note_root / "extractions")
        extraction_path = extraction_dir / f"{extraction.id}.json"
        extraction_path.write_text(
            json.dumps(serialize_entity(extraction), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        metadata.setdefault("extractions", []).append(serialize_entity(extraction))

    def _score_quality(self, status: str, metrics: dict) -> float:
        coverage = float(metrics.get("summary_coverage_ratio", 0.0))
        keyword_hit = float(metrics.get("keyword_hit_rate", 0.0))
        action_density = min(float(metrics.get("action_item_count", 0.0)) / 3.0, 1.0)
        base_score = (0.5 * coverage) + (0.3 * keyword_hit) + (0.2 * action_density)
        if status != "success":
            base_score *= 0.4
        clamped = max(0.0, min(base_score, 1.0))
        return round(clamped, 3)
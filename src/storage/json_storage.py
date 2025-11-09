"""JSON-based storage helpers for ingest outputs."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional
from uuid import UUID

from ..utils import ensure_directory

if TYPE_CHECKING:  # pragma: no cover
    from ..models import (
        ContentVariant,
        Extraction,
        IngestSource,
        Note,
        ProcessingJournalEntry,
    )


class NoteJsonStorage:
    """Persist note bundles composed during ingest."""

    def __init__(self, root: Path) -> None:
        self._root = ensure_directory(root)

    def save_note_bundle(
        self,
        *,
        ingest_source: "IngestSource",
        note: "Note",
        variants: Iterable["ContentVariant"],
        extractions: Iterable["Extraction"],
        journal: "ProcessingJournalEntry",
    ) -> Path:
        variants = list(variants)
        extractions = list(extractions)
        note_root = self._note_root(note.id)
        ensure_directory(note_root)
        extractions_dir = ensure_directory(note_root / "extractions")
        for variant in variants:
            self._write_variant_content(note_root, variant)
        for extraction in extractions:
            extraction_path = extractions_dir / f"{extraction.id}.json"
            extraction_path.write_text(
                json.dumps(_serialize_dataclass(extraction), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        metadata = {
            "ingest_source": _serialize_dataclass(ingest_source),
            "note": _serialize_dataclass(note),
            "variants": [_serialize_dataclass(v) for v in variants],
            "extractions": [_serialize_dataclass(e) for e in extractions],
            "journal": _serialize_dataclass(journal),
        }
        metadata_path = note_root / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return note_root

    def list_note_ids(self) -> Iterable[str]:
        notes_root = ensure_directory(self._root / "notes")
        for entry in sorted(notes_root.iterdir()):
            if entry.is_dir():
                yield entry.name

    def load_note_bundle(self, note_id: str):
        note_uuid = UUID(note_id)
        note_root = self._root / "notes" / str(note_uuid)
        metadata_path = note_root / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"metadata.json not found for note {note_id}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return self._deserialize_bundle(metadata, note_root)

    def _note_root(self, note_id: UUID) -> Path:
        return ensure_directory(self._root / "notes" / str(note_id))

    def _deserialize_bundle(self, metadata: Dict[str, Any], note_root: Path):
        from ..models import (
            ContentVariant,
            Extraction,
            IngestSource,
            Note,
            ProcessingJournalEntry,
        )

        ingest_source = _deserialize_ingest_source(metadata["ingest_source"], IngestSource)
        note = _deserialize_note(metadata["note"], Note)
        variants = [_deserialize_variant(item, ContentVariant) for item in metadata.get("variants", [])]
        extractions = [_deserialize_extraction(item, Extraction) for item in metadata.get("extractions", [])]
        journal = _deserialize_journal(metadata["journal"], ProcessingJournalEntry)

        class Bundle:
            def __init__(self):
                self.ingest_source = ingest_source
                self.note = note
                self.variants = variants
                self.extractions = extractions
                self.journal = journal
                for variant in self.variants:
                    if not variant.content and variant.content_path is None:
                        subdir = NoteJsonStorage._variant_subdir(variant.variant_type)
                        ext = NoteJsonStorage._variant_extension(variant.variant_type)
                        candidate = note_root / subdir / f"v{variant.version}{ext}"
                        if candidate.exists():
                            variant.content_path = str(candidate)

            @property
            def raw_html_variant(self):
                for variant in self.variants:
                    if variant.variant_type == "raw_html":
                        return variant
                raise ValueError("raw_html variant missing")

            @property
            def clean_text_variant(self):
                for variant in self.variants:
                    if variant.variant_type == "clean_text":
                        return variant
                raise ValueError("clean_text variant missing")

        return Bundle()

    def _write_variant_content(self, note_root: Path, variant: "ContentVariant") -> Optional[Path]:
        if variant.content is None:
            return None
        subdir = self._variant_subdir(variant.variant_type)
        variant_dir = ensure_directory(note_root / subdir)
        ext = self._variant_extension(variant.variant_type)
        file_path = variant_dir / f"v{variant.version}{ext}"
        file_path.write_text(variant.content, encoding="utf-8")
        return file_path

    @staticmethod
    def _variant_subdir(variant_type: str) -> str:
        mapping = {
            "raw_html": "raw",
            "clean_text": "clean",
        }
        return mapping.get(variant_type, variant_type)

    @staticmethod
    def _variant_extension(variant_type: str) -> str:
        mapping = {
            "raw_html": ".html",
            "clean_text": ".txt",
        }
        return mapping.get(variant_type, ".txt")


class ProcessingJournalWriter:
    """Append processing journal entries to a JSONL log and update metrics."""

    def __init__(
        self,
        root: Path,
        *,
        filename: str = "processing_journal.jsonl",
        metrics_filename: str = "processing_metrics.json",
    ) -> None:
        self._root = ensure_directory(root)
        self._file = self._root / filename
        self._metrics_file = self._root / metrics_filename

    def write(self, entry: "ProcessingJournalEntry") -> Path:
        payload = _serialize_dataclass(entry)
        with self._file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._update_metrics(payload)
        return self._file

    def _update_metrics(self, payload: Dict[str, Any]) -> None:
        metrics = {
            "total": 0,
            "by_stage": {},
            "by_status": {},
            "last_updated": None,
        }
        if self._metrics_file.exists():
            try:
                metrics.update(json.loads(self._metrics_file.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass

        stage = payload.get("stage", "unknown")
        status = payload.get("status", "unknown")

        metrics["total"] = int(metrics.get("total", 0)) + 1
        stage_bucket = metrics.setdefault("by_stage", {})
        stage_bucket[stage] = int(stage_bucket.get(stage, 0)) + 1
        status_bucket = metrics.setdefault("by_status", {})
        status_bucket[status] = int(status_bucket.get(status, 0)) + 1
        metrics["last_updated"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        self._metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def _serialize_dataclass(obj: Any) -> Dict[str, Any]:
    data = asdict(obj)
    for key, value in list(data.items()):
        if isinstance(value, UUID):
            data[key] = str(value)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                data[key] = value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
            else:
                data[key] = value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        elif isinstance(value, dict):
            data[key] = _serialize_nested_dict(value)
    return data


def _serialize_nested_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                result[key] = value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
            else:
                result[key] = value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        else:
            result[key] = value
    return result


def serialize_entity(obj: Any) -> Dict[str, Any]:
    """Expose serialization helper for reuse outside of storage class."""

    return _serialize_dataclass(obj)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def _deserialize_ingest_source(data: Dict[str, Any], cls):
    return cls(
        id=UUID(data["id"]),
        source_type=data["source_type"],
        source_path=data["source_path"],
    collected_at=_parse_datetime(data.get("collected_at")) or datetime.now(UTC),
        external_id=data.get("external_id"),
        title_hint=data.get("title_hint"),
        language_hint=data.get("language_hint"),
        captured_at=_parse_datetime(data.get("captured_at")),
        checksum=data.get("checksum"),
        status=data.get("status", "pending"),
        notes=data.get("notes", {}),
    )


def _deserialize_note(data: Dict[str, Any], cls):
    return cls(
        id=UUID(data["id"]),
        ingest_source_id=UUID(data["ingest_source_id"]),
        canonical_title=data["canonical_title"],
        language=data.get("language", "und"),
    ingested_at=_parse_datetime(data.get("ingested_at")) or datetime.now(UTC),
    created_at=_parse_datetime(data.get("created_at")),
        status=data.get("status", "active"),
        importance=int(data.get("importance", 0)),
        attributes=data.get("attributes", {}),
    )


def _deserialize_variant(data: Dict[str, Any], cls):
    diff_base = data.get("diff_base_variant_id")
    return cls(
        id=UUID(data["id"]),
        note_id=UUID(data["note_id"]),
        variant_type=data["variant_type"],
        version=int(data.get("version", 1)),
        created_by=data.get("created_by", "unknown"),
    created_at=_parse_datetime(data.get("created_at")) or datetime.now(UTC),
        content=data.get("content"),
        content_path=data.get("content_path"),
        diff_base_variant_id=UUID(diff_base) if diff_base else None,
        metadata=data.get("metadata", {}),
    )


def _deserialize_extraction(data: Dict[str, Any], cls):
    return cls(
        id=UUID(data["id"]),
        note_id=UUID(data["note_id"]),
        extractor=data["extractor"],
        payload=data.get("payload", {}),
        version=int(data.get("version", 1)),
    created_at=_parse_datetime(data.get("created_at")) or datetime.now(UTC),
        created_by=data.get("created_by", "system"),
        quality_score=data.get("quality_score"),
    )


def _deserialize_journal(data: Dict[str, Any], cls):
    note_id = data.get("note_id")
    return cls(
        id=UUID(data["id"]),
        note_id=UUID(note_id) if note_id else None,
        stage=data.get("stage", "unknown"),
        agent_id=data.get("agent_id", "unknown"),
    started_at=_parse_datetime(data.get("started_at")) or datetime.now(UTC),
    finished_at=_parse_datetime(data.get("finished_at")) or datetime.now(UTC),
        status=data.get("status", "unknown"),
        input_ref=data.get("input_ref", {}),
        output_ref=data.get("output_ref", {}),
        error_detail=data.get("error_detail"),
    )

"""Evernote ingest agent for Phase 1a."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Set

from ..models import (
    ContentVariant,
    Extraction,
    IngestResult,
    IngestSource,
    IngestStatus,
    IngestTask,
    Note,
    ProcessingJournalEntry,
)
from ..storage import NoteJsonStorage, ProcessingJournalWriter
from ..utils import compute_file_checksum, ensure_directory, extract_text_from_html, guess_language
from .cleaning_rules import CleaningContext, apply_cleaning_rules


class EvernoteIngestAgent:
    """Process Evernote-exported files into normalized note entities."""

    AGENT_ID = "evernote_ingest:v0"

    def __init__(
        self,
        *,
        json_root: Path,
        requested_outputs: Optional[Iterable[str]] = None,
        storage: Optional[NoteJsonStorage] = None,
        journal_writer: Optional[ProcessingJournalWriter] = None,
    ) -> None:
        self._json_root = ensure_directory(json_root)
        self._requested_outputs: Set[str] = set(requested_outputs or [])
        self._storage = storage or NoteJsonStorage(self._json_root)
        journal_root = self._json_root / "_journal"
        self._journal_writer = journal_writer or ProcessingJournalWriter(journal_root)

    def process(self, task: IngestTask) -> IngestResult:
        try:
            return self._process_success_path(task)
        except Exception as exc:  # pragma: no cover - defensive logging
            journal_entry = ProcessingJournalEntry.new(
                note_id=None,
                stage="ingest",
                agent_id=self.AGENT_ID,
                status="failed",
                input_ref={"task_id": str(task.task_id), "payload_keys": list(task.payload.keys())},
                error_detail=str(exc),
            )
            self._journal_writer.write(journal_entry)
            return IngestResult(
                task_id=task.task_id,
                status=IngestStatus.FAILED,
                journal_entry=journal_entry,
                error={"message": str(exc)},
            )

    def _process_success_path(self, task: IngestTask) -> IngestResult:
        source_path = Path(task.payload["source_path"])
        source_type = task.payload.get("source_type", "evernote_html")

        html_content = source_path.read_text(encoding="utf-8")
        checksum = compute_file_checksum(source_path)
        cleaned_text, detected_title = extract_text_from_html(html_content)
        language = guess_language(cleaned_text, fallback=task.payload.get("language_hint", "und"))

        cleaning_context = CleaningContext(
            source_type=source_type,
            language=language,
            metadata=task.payload,
        )
        cleaning_result = apply_cleaning_rules(cleaned_text, cleaning_context)
        cleaned_text = cleaning_result.text

        ingest_source = IngestSource.new(
            source_type=source_type,
            source_path=str(source_path),
            external_id=task.payload.get("external_id"),
            title_hint=task.payload.get("title"),
            language_hint=language,
            captured_at=self._parse_datetime(task.payload.get("captured_at")),
            checksum=checksum,
            notes={"batch_id": task.payload.get("batch_id")},
        )

        note_title = task.payload.get("title") or detected_title or source_path.stem
        note = Note.new(
            ingest_source_id=ingest_source.id,
            canonical_title=note_title,
            language=language,
            created_at=self._parse_datetime(task.payload.get("created_at")),
            attributes={"source_filename": source_path.name},
        )

        raw_variant = ContentVariant.new(
            note_id=note.id,
            variant_type="raw_html",
            created_by=self.AGENT_ID,
            content=html_content,
            metadata={"checksum": checksum, "path": str(source_path)},
        )

        clean_metadata = {
            "language": language,
            "length": len(cleaned_text),
        }
        clean_metadata.update(cleaning_result.to_metadata())

        clean_variant = ContentVariant.new(
            note_id=note.id,
            variant_type="clean_text",
            created_by=self.AGENT_ID,
            content=cleaned_text,
            metadata=clean_metadata,
        )

        extractions = []
        if "extraction_stub" in self._resolve_requested_outputs(task):
            extractions.append(
                Extraction.new(
                    note_id=note.id,
                    extractor=f"{self.AGENT_ID}#stub",
                    payload={
                        "summary": cleaned_text[:280],
                        "keywords": [],
                        "status": "pending_llm",
                    },
                    created_by=self.AGENT_ID,
                )
            )

        journal_entry = ProcessingJournalEntry.new(
            note_id=note.id,
            stage="ingest",
            agent_id=self.AGENT_ID,
            status="success",
            input_ref={
                "task_id": str(task.task_id),
                "source_path": str(source_path),
                "checksum": checksum,
            },
            output_ref={
                "ingest_source": str(ingest_source.id),
                "note": str(note.id),
                "variants": [str(raw_variant.id), str(clean_variant.id)],
            },
        )

        self._storage.save_note_bundle(
            ingest_source=ingest_source,
            note=note,
            variants=[raw_variant, clean_variant],
            extractions=extractions,
            journal=journal_entry,
        )
        self._journal_writer.write(journal_entry)

        return IngestResult(
            task_id=task.task_id,
            status=IngestStatus.SUCCESS,
            ingest_source=ingest_source,
            note=note,
            content_variants=[raw_variant, clean_variant],
            extractions=extractions,
            journal_entry=journal_entry,
            error=None,
        )

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _resolve_requested_outputs(self, task: IngestTask) -> Set[str]:
        requested = set(self._requested_outputs)
        requested.update(task.requested_outputs or [])
        return requested

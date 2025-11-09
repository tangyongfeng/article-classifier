"""Dataclasses describing the core persistent entities for the ingest pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class IngestSource:
    id: UUID
    source_type: str
    source_path: str
    collected_at: datetime
    external_id: Optional[str] = None
    title_hint: Optional[str] = None
    language_hint: Optional[str] = None
    captured_at: Optional[datetime] = None
    checksum: Optional[str] = None
    status: str = "pending"
    notes: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(
        source_type: str,
        source_path: str,
        *,
        external_id: Optional[str] = None,
        title_hint: Optional[str] = None,
        language_hint: Optional[str] = None,
        captured_at: Optional[datetime] = None,
        checksum: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> "IngestSource":
        return IngestSource(
            id=uuid4(),
            source_type=source_type,
            source_path=source_path,
            collected_at=datetime.utcnow(),
            external_id=external_id,
            title_hint=title_hint,
            language_hint=language_hint,
            captured_at=captured_at,
            checksum=checksum,
            notes=notes or {},
        )


@dataclass
class Note:
    id: UUID
    ingest_source_id: UUID
    canonical_title: str
    language: str
    ingested_at: datetime
    created_at: Optional[datetime] = None
    status: str = "active"
    importance: int = 0
    attributes: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(
        ingest_source_id: UUID,
        canonical_title: str,
        language: str,
        *,
        created_at: Optional[datetime] = None,
        status: str = "active",
        importance: int = 0,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> "Note":
        return Note(
            id=uuid4(),
            ingest_source_id=ingest_source_id,
            canonical_title=canonical_title,
            language=language,
            ingested_at=datetime.utcnow(),
            created_at=created_at,
            status=status,
            importance=importance,
            attributes=attributes or {},
        )


@dataclass
class ContentVariant:
    id: UUID
    note_id: UUID
    variant_type: str
    version: int
    created_by: str
    created_at: datetime
    content: Optional[str] = None
    content_path: Optional[str] = None
    diff_base_variant_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(
        note_id: UUID,
        variant_type: str,
        created_by: str,
        *,
        version: int = 1,
        content: Optional[str] = None,
        content_path: Optional[str] = None,
        diff_base_variant_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ContentVariant":
        return ContentVariant(
            id=uuid4(),
            note_id=note_id,
            variant_type=variant_type,
            version=version,
            created_by=created_by,
            created_at=datetime.utcnow(),
            content=content,
            content_path=content_path,
            diff_base_variant_id=diff_base_variant_id,
            metadata=metadata or {},
        )


@dataclass
class Extraction:
    id: UUID
    note_id: UUID
    extractor: str
    payload: Dict[str, Any]
    version: int
    created_at: datetime
    created_by: str
    quality_score: Optional[float] = None

    @staticmethod
    def new(
        note_id: UUID,
        extractor: str,
        payload: Dict[str, Any],
        *,
        version: int = 1,
        created_by: str = "system",
        quality_score: Optional[float] = None,
    ) -> "Extraction":
        return Extraction(
            id=uuid4(),
            note_id=note_id,
            extractor=extractor,
            payload=payload,
            version=version,
            created_at=datetime.utcnow(),
            created_by=created_by,
            quality_score=quality_score,
        )


@dataclass
class ProcessingJournalEntry:
    id: UUID
    note_id: Optional[UUID]
    stage: str
    agent_id: str
    started_at: datetime
    finished_at: datetime
    status: str
    input_ref: Dict[str, Any] = field(default_factory=dict)
    output_ref: Dict[str, Any] = field(default_factory=dict)
    error_detail: Optional[str] = None

    @staticmethod
    def new(
    note_id: Optional[UUID],
        stage: str,
        agent_id: str,
        status: str,
        *,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        input_ref: Optional[Dict[str, Any]] = None,
        output_ref: Optional[Dict[str, Any]] = None,
        error_detail: Optional[str] = None,
    ) -> "ProcessingJournalEntry":
        return ProcessingJournalEntry(
            id=uuid4(),
            note_id=note_id,
            stage=stage,
            agent_id=agent_id,
            status=status,
            started_at=started_at or datetime.utcnow(),
            finished_at=finished_at or datetime.utcnow(),
            input_ref=input_ref or {},
            output_ref=output_ref or {},
            error_detail=error_detail,
        )

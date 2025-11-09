"""Task and result models shared by ingest agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from .entities import ContentVariant, Extraction, IngestSource, Note, ProcessingJournalEntry


class IngestStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class IngestTask:
    task_id: UUID
    agent: str
    payload: Dict[str, Any]
    requested_outputs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IngestResult:
    task_id: UUID
    status: IngestStatus
    ingest_source: Optional[IngestSource] = None
    note: Optional[Note] = None
    content_variants: List[ContentVariant] = field(default_factory=list)
    extractions: List[Extraction] = field(default_factory=list)
    journal_entry: Optional[ProcessingJournalEntry] = None
    error: Optional[Dict[str, Any]] = None

"""Core utilities for note post-processing."""
from .version_diff import NoteVersionDiffer, VersionDiff, DiffSegment, generate_report

__all__ = [
    "NoteVersionDiffer",
    "VersionDiff",
    "DiffSegment",
    "generate_report",
]

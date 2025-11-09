"""Filesystem helper utilities."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union


PathLike = Union[str, Path]


def ensure_directory(path: PathLike) -> Path:
    """Ensure a directory exists and return it as Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def compute_file_checksum(path: PathLike, algorithm: str = "sha256") -> str:
    """Compute the checksum for a file using the given algorithm."""
    hasher = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

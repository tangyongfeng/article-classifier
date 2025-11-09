"""HTML parsing helpers for Evernote exports."""
from __future__ import annotations

import re
from typing import Tuple

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0  # deterministic language detection


def extract_text_from_html(html_content: str) -> Tuple[str, str]:
    """Return cleaned text and inferred title from an HTML payload."""
    soup = BeautifulSoup(html_content, "html.parser")

    title = (soup.title.string or "").strip() if soup.title else ""
    # Remove scripts and styles to avoid noise
    for element in soup(["script", "style"]):
        element.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = text.strip()
    return text, title


def guess_language(text: str, fallback: str = "und") -> str:
    """Guess text language using langdetect with graceful fallback."""
    sample = text[:4000] if len(text) > 4000 else text
    if not sample.strip():
        return fallback
    try:
        lang = detect(sample)
    except Exception:
        return fallback
    return lang

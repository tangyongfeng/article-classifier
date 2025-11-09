"""Cleaning rule registry for source-specific text normalization."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Mapping, Tuple


@dataclass(frozen=True)
class CleaningContext:
    """Lightweight descriptor for a note's origin."""

    source_type: str = ""
    language: str = "und"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def tags(self) -> frozenset[str]:
        tags = set()
        source = (self.source_type or "").lower()
        if any(token in source for token in ("forum", "bbs", "community")):
            tags.add("forum")
        if any(token in source for token in ("weibo", "twitter", "social", "wechat")):
            tags.add("social")
        if "email" in source or self.metadata.get("channel") == "email":
            tags.add("email")
        if "ai" in source or self.metadata.get("generator") == "llm":
            tags.add("ai_generated")
        if "blog" in source or self.metadata.get("category") == "blog":
            tags.add("longform")
        return frozenset(tags)


@dataclass
class CleaningRule:
    rule_id: str
    description: str
    priority: int
    predicate: Callable[[str, CleaningContext], bool]
    transform: Callable[[str, CleaningContext], Tuple[str, str]]


@dataclass
class CleaningResult:
    text: str
    applied_rules: List[dict[str, str]]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "rule_count": len(self.applied_rules),
            "applied_rules": self.applied_rules,
        }


def apply_cleaning_rules(text: str, context: CleaningContext) -> CleaningResult:
    """Run all matching rules and return the cleaned text and audit trail."""
    applied: List[dict[str, str]] = []
    active_text = text
    for rule in sorted(_RULES, key=lambda item: item.priority):
        if not rule.predicate(active_text, context):
            continue
        new_text, note = rule.transform(active_text, context)
        if new_text == active_text:
            continue
        entry = {"rule_id": rule.rule_id, "description": rule.description}
        if note:
            entry["note"] = note
        applied.append(entry)
        active_text = new_text
    return CleaningResult(text=active_text.strip(), applied_rules=applied)


# ---------------------------------------------------------------------------

def _strip_forum_quotes(text: str, _: CleaningContext) -> Tuple[str, str]:
    stripped = re.sub(r"\[quote[^\]]*\].*?\[/quote\]", "", text, flags=re.IGNORECASE | re.DOTALL)
    lines = [line for line in stripped.splitlines() if not line.lstrip().startswith(">")]
    return "\n".join(lines), "removed quoted blocks"


def _strip_social_handles(text: str, _: CleaningContext) -> Tuple[str, str]:
    pattern = re.compile(r"^(?:[@#][\w\-]{2,})(?::\s*)?$", flags=re.MULTILINE)
    cleaned = pattern.sub("", text)
    cleaned = re.sub(r"\n{2,}", "\n\n", cleaned)
    return cleaned, "removed social handle only lines"


def _strip_ai_disclaimer(text: str, _: CleaningContext) -> Tuple[str, str]:
    cleaned = re.sub(r"^.*?(?:As an AI language model|I cannot assist with).*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    return cleaned, "removed AI disclaimer"


def _strip_signature_block(text: str, _: CleaningContext) -> Tuple[str, str]:
    signature_pattern = re.compile(
        r"(\n--\s+|\nSent from my [^\n]+|\n发自[^\n]+|\nBest regards,\n).*",
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = signature_pattern.sub("", text)
    return cleaned, "removed trailing signature"


def _dedupe_repeated_lines(text: str, _: CleaningContext) -> Tuple[str, str]:
    lines = text.splitlines()
    unique_lines: List[str] = []
    for line in lines:
        if unique_lines and unique_lines[-1].strip() == line.strip():
            continue
        unique_lines.append(line)
    return "\n".join(unique_lines), "collapsed duplicate adjacent lines"


def _collapse_whitespace(text: str, _: CleaningContext) -> Tuple[str, str]:
    compact = re.sub(r"[\t\x0b\x0c]+", " ", text)
    compact = re.sub(r" \n", "\n", compact)
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    return compact.strip(), "collapsed whitespace"


def _tags_any(context: CleaningContext, candidates: Iterable[str]) -> bool:
    return any(tag in context.tags for tag in candidates)


_RULES: List[CleaningRule] = [
    CleaningRule(
        rule_id="forum_quotes",
        description="Remove forum style quoted sections",
        priority=10,
        predicate=lambda text, ctx: "[quote" in text.lower() or _tags_any(ctx, {"forum"}),
        transform=_strip_forum_quotes,
    ),
    CleaningRule(
        rule_id="social_handles",
        description="Drop standalone social handles and hashtags",
        priority=20,
        predicate=lambda text, ctx: _tags_any(ctx, {"social"}) or re.search(r"^[@#]", text, flags=re.MULTILINE),
        transform=_strip_social_handles,
    ),
    CleaningRule(
        rule_id="ai_disclaimer",
        description="Remove boilerplate AI disclaimers",
        priority=30,
        predicate=lambda text, ctx: "ai language model" in text.lower() or _tags_any(ctx, {"ai_generated"}),
        transform=_strip_ai_disclaimer,
    ),
    CleaningRule(
        rule_id="signature",
        description="Strip trailing signatures",
        priority=40,
        predicate=lambda text, ctx: _tags_any(ctx, {"email"}) or "sent from my" in text.lower(),
        transform=_strip_signature_block,
    ),
    CleaningRule(
        rule_id="dedupe_lines",
        description="Collapse adjacent duplicate lines",
        priority=50,
        predicate=lambda text, _: "\n" in text,
        transform=_dedupe_repeated_lines,
    ),
    CleaningRule(
        rule_id="whitespace",
        description="Normalize whitespace",
        priority=100,
        predicate=lambda _text, _ctx: True,
        transform=_collapse_whitespace,
    ),
]

__all__ = ["CleaningContext", "CleaningResult", "apply_cleaning_rules"]

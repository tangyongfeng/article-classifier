"""Data models shared across LLM tooling."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMModelConfig:
    """Configuration for a concrete LLM backend."""

    name: str
    provider: str = "ollama"
    parameters: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 2


@dataclass
class LLMRequest:
    """Normalized LLM request payload."""

    model: LLMModelConfig
    prompt: str
    expected_format: str = "plain"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Result produced by the dispatcher."""

    model: LLMModelConfig
    prompt: str
    content: str
    succeeded: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: Optional[str] = None
    parsed: Optional[Any] = None
    latency_seconds: Optional[float] = None


@dataclass
class LLMRunLog:
    """Serialized footprint of an LLM invocation for journaling."""

    request: LLMRequest
    response: LLMResponse

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": {
                "model": self.request.model.name,
                "provider": self.request.model.provider,
                "prompt_length": len(self.request.prompt),
                "expected_format": self.request.expected_format,
                "metadata": self.request.metadata,
            },
            "response": {
                "succeeded": self.response.succeeded,
                "error": self.response.error,
                "latency_seconds": self.response.latency_seconds,
                "created_at": self.response.created_at.isoformat(),
            },
        }

    def to_json(self) -> Dict[str, Any]:
        return self.to_dict()

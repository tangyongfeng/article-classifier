"""LLM dispatcher with multi-model fallback."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .models import LLMModelConfig, LLMRequest, LLMResponse, LLMRunLog
from .prompts import SUMMARY_TEMPLATE


class LLMDispatcher:
    """Coordinate LLM invocations with fallback and journaling."""

    def __init__(
        self,
        models: Iterable[LLMModelConfig],
        *,
        default_model: str,
        journal_path: Optional[Path] = None,
        timeout_seconds: int = 120,
    ) -> None:
        self._models: Dict[str, LLMModelConfig] = {model.name: model for model in models}
        if default_model not in self._models:
            raise ValueError(f"Default model '{default_model}' is not registered")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds
        self._journal_path = journal_path
        if journal_path is not None:
            journal_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def dispatch(
        self,
        prompt: str,
        *,
        models: Optional[Iterable[str]] = None,
        expected_format: str = "plain",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        model_sequence = list(models) if models else [self._default_model]
        if not model_sequence:
            raise ValueError("At least one model must be specified")
        metadata = metadata or {}
        last_error: Optional[str] = None

        for model_name in model_sequence:
            config = self._require_model(model_name)
            request = LLMRequest(model=config, prompt=prompt, expected_format=expected_format, metadata=metadata)
            response = self._invoke_model(request)
            self._log_run(request, response)
            if not response.succeeded:
                last_error = response.error
                continue
            if expected_format == "json":
                parsed = self._try_parse_json(response.content)
                if parsed is None:
                    response.succeeded = False
                    response.error = "JSON parse failed"
                    last_error = response.error
                    self._log_run(request, response)
                    continue
                response.parsed = parsed
            return response

        return LLMResponse(
            model=self._require_model(model_sequence[-1]),
            prompt=prompt,
            content="",
            succeeded=False,
            error=last_error or "All models failed",
        )

    def summarize_note(
        self,
        *,
        title: str,
        content: str,
        language: str = "zh-cn",
        models: Optional[Iterable[str]] = None,
    ) -> LLMResponse:
        prompt = SUMMARY_TEMPLATE.render(title=title or "未命名", content=content, language=language)
        metadata = {"task": "note_summary", "language": language, "title": title}
        return self.dispatch(prompt, models=models, expected_format="json", metadata=metadata)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_model(self, model_name: str) -> LLMModelConfig:
        if model_name not in self._models:
            raise ValueError(f"Model '{model_name}' is not registered")
        return self._models[model_name]

    def _invoke_model(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        try:
            if request.model.provider == "ollama":
                completed = subprocess.run(
                    ["ollama", "run", request.model.name],
                    input=request.prompt,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_seconds,
                )
            else:
                raise ValueError(f"Unsupported provider: {request.model.provider}")
        except subprocess.TimeoutExpired as exc:
            latency = time.perf_counter() - start
            return LLMResponse(
                model=request.model,
                prompt=request.prompt,
                content="",
                succeeded=False,
                error=f"Timeout after {self._timeout_seconds}s",
                latency_seconds=latency,
            )

        latency = time.perf_counter() - start
        if completed.returncode != 0:
            return LLMResponse(
                model=request.model,
                prompt=request.prompt,
                content=completed.stdout.strip(),
                succeeded=False,
                error=completed.stderr.strip() or f"Model {request.model.name} exited with {completed.returncode}",
                latency_seconds=latency,
            )

        content = completed.stdout.strip()
        return LLMResponse(
            model=request.model,
            prompt=request.prompt,
            content=content,
            succeeded=True,
            latency_seconds=latency,
        )

    def _try_parse_json(self, payload: str) -> Optional[Any]:
        payload = payload.strip()
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            if payload.startswith("```"):
                lines = payload.splitlines()
                if lines:
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                payload_inner = "\n".join(lines).strip()
                if payload_inner:
                    return self._try_parse_json(payload_inner)
            candidate = self._extract_json_candidate(payload)
            if candidate:
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
            return None

    def _log_run(self, request: LLMRequest, response: LLMResponse) -> None:
        if self._journal_path is None:
            return
        log = LLMRunLog(request=request, response=response)
        with self._journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log.to_json(), ensure_ascii=False) + "\n")

    def _extract_json_candidate(self, payload: str) -> Optional[str]:
        indices = [idx for idx, ch in enumerate(payload) if ch == "{"]
        for start in reversed(indices):
            candidate = self._slice_balanced_braces(payload, start)
            if candidate:
                return candidate.strip()
        return None

    def _slice_balanced_braces(self, payload: str, start: int) -> Optional[str]:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(payload)):
            ch = payload[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "\"":
                    in_string = False
                continue
            if ch == "\"":
                in_string = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return payload[start : idx + 1]
        return None
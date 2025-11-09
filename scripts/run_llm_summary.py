#!/usr/bin/env python3
"""CLI to summarize note content via the LLM dispatcher."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.llm import LLMDispatcher, LLMModelConfig  # type: ignore

DEFAULT_JOURNAL = REPO_ROOT / "data" / "json" / "ingest" / "_journal" / "llm_runs.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize note content with available LLM models")
    parser.add_argument("input", type=Path, help="Path to the text file containing note content")
    parser.add_argument("--title", default="未命名", help="Note title for prompt context")
    parser.add_argument("--language", default="zh-cn", help="Target summary language (default: zh-cn)")
    parser.add_argument(
        "--models",
        nargs="+",
        default=[],
        help="Optional model override list (default: dispatcher fallback order)",
    )
    return parser.parse_args()


def build_dispatcher(models: list[str]) -> LLMDispatcher:
    configs = [
        LLMModelConfig(name="deepseek-v3.1:671b-cloud"),
        LLMModelConfig(name="qwen3-vl:235b-cloud"),
        LLMModelConfig(name="qwen3:30b"),
        LLMModelConfig(name="gpt-oss:20b"),
    ]
    preferred = models[0] if models else "deepseek-v3.1:671b-cloud"
    return LLMDispatcher(configs, default_model=preferred, journal_path=DEFAULT_JOURNAL)


def main() -> None:
    args = parse_args()
    note_path = args.input.expanduser().resolve()
    if not note_path.exists():
        raise SystemExit(f"Input file not found: {note_path}")

    content = note_path.read_text(encoding="utf-8")
    dispatcher = build_dispatcher(args.models)
    response = dispatcher.summarize_note(title=args.title, content=content, language=args.language, models=args.models)

    if not response.succeeded:
        raise SystemExit(f"LLM summary failed: {response.error}")

    print(json.dumps(response.parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Batch-apply LLM enhancements to stored notes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingest import LLMEnhanceAgent  # type: ignore
from src.llm import LLMDispatcher, LLMModelConfig  # type: ignore

JSON_ROOT = REPO_ROOT / "data" / "json" / "ingest"
DEFAULT_MODELS = [
    LLMModelConfig(name="deepseek-v3.1:671b-cloud"),
    LLMModelConfig(name="qwen3-vl:235b-cloud"),
    LLMModelConfig(name="qwen3:30b"),
    LLMModelConfig(name="gpt-oss:20b"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM summarization over existing note bundles")
    parser.add_argument("--note-id", nargs="*", help="Specific note UUIDs to process; defaults to all")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of notes to process")
    parser.add_argument("--models", nargs="*", default=[], help="Override model order for dispatcher")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    return parser.parse_args()


def build_dispatcher(model_names: Iterable[str]) -> LLMDispatcher:
    if model_names:
        configs = [LLMModelConfig(name=name) for name in model_names]
        default = model_names[0]
    else:
        configs = DEFAULT_MODELS
        default = DEFAULT_MODELS[0].name
    return LLMDispatcher(configs, default_model=default, journal_path=JSON_ROOT / "_journal" / "llm_runs.jsonl")


def iter_note_ids(filter_ids: Iterable[str] | None, limit: int) -> Iterable[str]:
    note_dir = JSON_ROOT / "notes"
    all_ids = sorted(p.name for p in note_dir.iterdir() if p.is_dir())
    if filter_ids:
        target = [nid for nid in all_ids if nid in set(filter_ids)]
    else:
        target = all_ids
    if limit and limit > 0:
        target = target[:limit]
    return target


def main() -> None:
    args = parse_args()
    dispatcher = build_dispatcher(args.models)
    agent = LLMEnhanceAgent(json_root=JSON_ROOT, dispatcher=dispatcher)

    results = []
    for note_id in iter_note_ids(args.note_id, args.limit):
        if args.dry_run:
            print(json.dumps({"note_id": note_id, "status": "skipped", "reason": "dry_run"}, ensure_ascii=False))
            continue
        try:
            result = agent.enhance_note(note_id, models=args.models)
            print(json.dumps(result, ensure_ascii=False))
            results.append(result)
        except Exception as exc:  # pragma: no cover - operational logging
            error = {
                "note_id": note_id,
                "status": "error",
                "error": str(exc),
            }
            print(json.dumps(error, ensure_ascii=False))

    if args.dry_run:
        print("Dry run completed")


if __name__ == "__main__":
    main()

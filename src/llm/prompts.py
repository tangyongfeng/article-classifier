"""Prompt templates used by LLM dispatcher."""
from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    """Simple string-based prompt template."""

    name: str
    template: str

    def render(self, **context: Any) -> str:
        return self.template.format(**context)


SUMMARY_TEMPLATE = PromptTemplate(
    name="note_summary_v1",
    template=dedent(
        """
        你是一名知识整理助手。请阅读以下笔记内容并输出严格的 JSON：
        {{"summary": "不超过80字的中文总结", "keywords": ["5个关键词"], "action_items": ["如无待办则填'无'"]}}
        笔记标题: {title}
        目标语言: {language}
        ----------
        {content}
        ----------
        如果无法解析，请仅回复 JSON 字段中的错误描述。
        """
    ).strip(),
)

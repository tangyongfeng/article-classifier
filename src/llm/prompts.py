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
    name="note_summary_with_categories_v1",
    template=dedent(
        """
        你是一名知识整理与分类助手。请阅读以下内容后输出严格的 JSON：
        {{
          "summary": "不超过80字的中文总结",
          "keywords": ["5个关键词"],
          "action_items": ["如无待办则填'无'"],
          "category_path": ["优先复用现有分类"],
          "new_category_suggestion": null
        }}
        现有分类体系（按层级使用 ">" 连接）：
        {category_guidance}
        笔记标题: {title}
        目标语言: {language}
        ----------
        {content}
        ----------
        说明：
        1. 必须优先使用以上已有分类（含子类），只有完全不匹配时才在 new_category_suggestion 中提出新分类，并说明理由。
        2. 如果选择现有分类，category_path 必须返回完整层级（最多3级）。
        3. 若无新分类建议，请将 new_category_suggestion 设为 null。
        4. 仅返回 JSON，不得包含额外说明。
        如果无法解析，请仅回复 JSON 字段中的错误描述。
        """
    ).strip(),
)

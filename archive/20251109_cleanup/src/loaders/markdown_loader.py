"""Markdown 文件加载器"""
from typing import Dict, Any
from datetime import datetime
import frontmatter

from .base import DocumentLoader, LoaderFactory


class MarkdownLoader(DocumentLoader):
    """Markdown 加载器"""

    def load(self) -> Dict[str, Any]:
        """加载 Markdown 文件"""
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            post = frontmatter.load(f)

        # 提取 front matter 元数据
        metadata = post.metadata
        title = metadata.get('title', self.file_path.stem)

        # 提取创建时间
        created_at = None
        for key in ['created', 'date', 'created_at']:
            if key in metadata:
                date_val = metadata[key]
                if isinstance(date_val, datetime):
                    created_at = date_val
                elif isinstance(date_val, str):
                    try:
                        created_at = datetime.fromisoformat(date_val)
                    except Exception:
                        pass
                break

        # 内容
        content = post.content.strip()

        return {
            "title": title,
            "content": content,
            "raw_content": content,
            "created_at": created_at,
            "metadata": metadata
        }


# 注册加载器
LoaderFactory.register('md', MarkdownLoader)
LoaderFactory.register('markdown', MarkdownLoader)

"""纯文本文件加载器"""
from typing import Dict, Any

from .base import DocumentLoader, LoaderFactory


class TextLoader(DocumentLoader):
    """纯文本加载器"""

    def load(self) -> Dict[str, Any]:
        """加载文本文件"""
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()

        # 使用文件名作为标题
        title = self.file_path.stem

        # 尝试从第一行提取标题
        lines = content.split('\n', 1)
        if lines and len(lines[0]) < 100:
            title = lines[0].strip()

        return {
            "title": title,
            "content": content,
            "raw_content": content,
            "created_at": None,
            "metadata": {}
        }


# 注册加载器
LoaderFactory.register('txt', TextLoader)

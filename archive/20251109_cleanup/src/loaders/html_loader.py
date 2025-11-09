"""HTML 文件加载器（Evernote 格式）"""
import re
from datetime import datetime
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base import DocumentLoader, LoaderFactory


class HTMLLoader(DocumentLoader):
    """HTML 加载器"""

    def load(self) -> Dict[str, Any]:
        """加载 HTML 文件"""
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()

        # 解析 HTML
        soup = BeautifulSoup(raw_content, 'lxml')

        # 提取 title（从 YAML front matter 或 HTML title）
        title = self._extract_title(soup, raw_content)

        # 提取创建时间
        created_at = self._extract_created_at(soup, raw_content)

        # 提取作者
        author = self._extract_author(soup, raw_content)

        # 提取纯文本内容
        content = self._extract_content(soup)

        return {
            "title": title,
            "content": content,
            "raw_content": raw_content,
            "created_at": created_at,
            "metadata": {
                "author": author,
                "source": "evernote"
            }
        }

    def _extract_title(self, soup: BeautifulSoup, raw_content: str) -> str:
        """提取标题"""
        # 从 YAML front matter 提取
        match = re.search(r'^---\s*\ntitle:\s*(.+?)\n', raw_content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # 从 HTML title 标签提取
        if soup.title:
            return soup.title.string.strip()

        # 使用文件名
        return self.file_path.stem

    def _extract_created_at(self, soup: BeautifulSoup, raw_content: str) -> datetime | None:
        """提取创建时间"""
        # 从 YAML front matter 提取
        patterns = [
            r'^created:\s*(.+?)$',
            r'^updated:\s*(.+?)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_content, re.MULTILINE)
            if match:
                date_str = match.group(1).strip()
                try:
                    # 尝试解析多种日期格式
                    for fmt in [
                        '%Y-%m-%d %H:%M:%SZ',
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d',
                    ]:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass

        return None

    def _extract_author(self, soup: BeautifulSoup, raw_content: str) -> str | None:
        """提取作者"""
        match = re.search(r'^author:\s*(.+?)$', raw_content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取文本内容"""
        # 移除 script 和 style 标签
        for tag in soup(['script', 'style', 'head']):
            tag.decompose()

        # 获取 en-note 标签（Evernote 特有）
        en_note = soup.find('en-note')
        if en_note:
            text = en_note.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # 清理多余空行
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()


# 注册加载器
LoaderFactory.register('html', HTMLLoader)
LoaderFactory.register('htm', HTMLLoader)

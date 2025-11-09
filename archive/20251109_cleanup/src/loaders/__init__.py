"""文件加载器模块

导入所有加载器以触发注册
"""
from .base import DocumentLoader, LoaderFactory
from .html_loader import HTMLLoader
from .markdown_loader import MarkdownLoader
from .text_loader import TextLoader

__all__ = [
    'DocumentLoader',
    'LoaderFactory',
    'HTMLLoader',
    'MarkdownLoader',
    'TextLoader',
]

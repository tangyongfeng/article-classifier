"""文件加载器基类"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class DocumentLoader(ABC):
    """文档加载器基类"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """
        加载文档内容

        返回格式:
        {
            "title": str,
            "content": str,  # 纯文本内容
            "raw_content": str,  # 原始内容
            "created_at": datetime or None,
            "metadata": dict
        }
        """
        pass

    def get_file_size(self) -> int:
        """获取文件大小（字节）"""
        return self.file_path.stat().st_size

    def get_file_format(self) -> str:
        """获取文件格式"""
        return self.file_path.suffix.lstrip('.')


class LoaderFactory:
    """加载器工厂"""

    _loaders = {}

    @classmethod
    def register(cls, file_format: str, loader_class):
        """注册加载器"""
        cls._loaders[file_format.lower()] = loader_class

    @classmethod
    def create_loader(cls, file_path: str) -> DocumentLoader:
        """创建加载器"""
        path = Path(file_path)
        file_format = path.suffix.lstrip('.').lower()

        loader_class = cls._loaders.get(file_format)
        if not loader_class:
            raise ValueError(f"不支持的文件格式: {file_format}")

        return loader_class(file_path)

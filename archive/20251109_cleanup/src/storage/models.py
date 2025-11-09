"""数据模型"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Article(BaseModel):
    """文章模型"""
    id: Optional[int] = None
    file_path: str
    json_path: str
    title: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: datetime = Field(default_factory=datetime.now)
    file_format: str
    file_size: int
    confidence: float = 0.0


class Category(BaseModel):
    """分类模型"""
    id: Optional[int] = None
    name: str
    parent_id: Optional[int] = None
    level: int = Field(ge=1, le=3)
    description: Optional[str] = None
    article_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Keyword(BaseModel):
    """关键词模型"""
    id: Optional[int] = None
    keyword: str
    usage_count: int = 0


class ClassificationResult(BaseModel):
    """分类结果模型"""
    category_path: List[str]  # ["一级", "二级", "三级"]
    category_ids: Optional[List[int]] = None
    new_category_suggestion: Optional[Dict[str, str]] = None
    summary: str
    keywords: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class ArticleDocument(BaseModel):
    """文章文档模型（JSON 存储格式）"""
    id: int
    metadata: Dict[str, Any]
    content: Dict[str, str]
    classification: Dict[str, Any]
    processing_info: Dict[str, Any]


class CategoryTree(BaseModel):
    """分类树模型"""
    id: int
    name: str
    level: int
    parent_id: Optional[int] = None
    article_count: int = 0
    children: List['CategoryTree'] = []


class ProcessingStats(BaseModel):
    """处理统计"""
    total_files: int = 0
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.processed / self.total_files * 100


# 解决 CategoryTree 的前向引用
CategoryTree.model_rebuild()

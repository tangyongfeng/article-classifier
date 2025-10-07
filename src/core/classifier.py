"""分类核心引擎"""
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..loaders.base import LoaderFactory
from ..storage.database import get_database
from ..storage.json_storage import get_json_storage
from ..storage.models import Article, ArticleDocument, ClassificationResult
from ..utils.config import get_config
from ..utils.logger import get_logger
from .llm_service import get_llm_service
from .category_manager import get_category_manager
from .category_optimizer import get_category_optimizer

logger = get_logger()


class ArticleClassifier:
    """文章分类器"""

    def __init__(self):
        self.config = get_config()
        self.db = get_database()
        self.storage = get_json_storage()
        self.llm = get_llm_service()
        self.category_manager = get_category_manager()
        self.optimizer = get_category_optimizer()

    def classify_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        分类单个文件

        Args:
            file_path: 文件路径

        Returns:
            处理结果字典，失败返回 None
        """
        try:
            start_time = time.time()

            # 1. 检查文件是否已处理
            if self.db.article_exists(file_path):
                logger.info(f"文件已处理，跳过: {file_path}")
                return {"status": "skipped", "reason": "already_processed"}

            # 2. 加载文件
            loader = LoaderFactory.create_loader(file_path)
            doc_data = loader.load()

            # 3. 获取当前分类体系
            category_tree = self.category_manager.load_category_tree()

            # 4. 调用 LLM 分类
            classification = self.llm.classify_article(
                title=doc_data.get("title", ""),
                content=doc_data.get("content", ""),
                current_categories=category_tree
            )

            # 5. 创建分类路径
            category_path = classification.get("category_path", ["未分类"])
            category_ids = self.category_manager.create_category_path(category_path)

            # 6. 保存到数据库
            article = Article(
                file_path=file_path,
                json_path="",  # 稍后更新
                title=doc_data.get("title"),
                summary=classification.get("summary", ""),
                created_at=doc_data.get("created_at"),
                file_format=loader.get_file_format(),
                file_size=loader.get_file_size(),
                confidence=classification.get("confidence", 0.5)
            )

            article_id = self.db.insert_article(article)

            # 7. 关联分类
            for cat_id in category_ids:
                self.db.link_article_category(article_id, cat_id)
                self.db.increment_category_count(cat_id)

            # 8. 处理关键词
            keywords = classification.get("keywords", [])
            for keyword in keywords:
                keyword_id = self.db.insert_keyword(keyword)
                self.db.link_article_keyword(article_id, keyword_id)

            # 9. 保存到 JSON
            json_path = self._save_article_json(
                article_id=article_id,
                doc_data=doc_data,
                classification=classification,
                category_ids=category_ids,
                processing_time=time.time() - start_time
            )

            # 更新 json_path
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE articles SET json_path = %s WHERE id = %s",
                    (str(json_path), article_id)
                )

            # 10. 检查是否需要优化
            total_articles = self.db.get_total_articles()
            if self.config.classifier.auto_optimize and \
               self.optimizer.should_optimize(total_articles, self.config.classifier.optimization_interval):
                logger.info(f"已处理 {total_articles} 篇文章，触发分类优化...")
                self.optimizer.optimize()

            # 11. 定期保存分类树
            if total_articles % 50 == 0:
                self.category_manager.save_category_tree()

            logger.info(f"✓ 分类完成: {Path(file_path).name} -> {'/'.join(category_path)}")

            return {
                "status": "success",
                "article_id": article_id,
                "category_path": category_path,
                "confidence": classification.get("confidence"),
                "processing_time": time.time() - start_time
            }

        except Exception as e:
            logger.error(f"✗ 分类失败: {file_path} - {e}")
            self.storage.save_failed_file(file_path, str(e))
            return {
                "status": "failed",
                "error": str(e)
            }

    def _save_article_json(
        self,
        article_id: int,
        doc_data: Dict[str, Any],
        classification: Dict[str, Any],
        category_ids: list,
        processing_time: float
    ) -> Path:
        """保存文章 JSON"""
        article_doc = ArticleDocument(
            id=article_id,
            metadata={
                "file_path": doc_data.get("file_path", ""),
                "title": doc_data.get("title", ""),
                "created_at": doc_data.get("created_at").isoformat() if doc_data.get("created_at") else None,
                "processed_at": datetime.now().isoformat(),
                "file_format": doc_data.get("file_format", ""),
                "file_size": doc_data.get("file_size", 0),
                **doc_data.get("metadata", {})
            },
            content={
                "raw": doc_data.get("raw_content", "") if self.config.storage.save_raw_content else "",
                "cleaned": doc_data.get("content", "")
            },
            classification={
                "category_path": classification.get("category_path", []),
                "category_ids": category_ids,
                "confidence": classification.get("confidence", 0.0),
                "keywords": classification.get("keywords", []),
                "summary": classification.get("summary", "")
            },
            processing_info={
                "llm_model": self.config.ollama.model,
                "processing_time_seconds": round(processing_time, 2)
            }
        )

        return self.storage.save_article(article_doc)

    def initialize_category_system(self, sample_files: list):
        """
        初始化分类体系（处理前100篇文章）

        Args:
            sample_files: 样本文件列表
        """
        logger.info(f"初始化分类体系: 分析前 {len(sample_files)} 篇文章...")

        for file_path in sample_files:
            self.classify_file(file_path)

        # 保存初始分类树
        self.category_manager.save_category_tree()
        logger.info("分类体系初始化完成")


# 全局实例
_classifier: Optional[ArticleClassifier] = None


def get_classifier() -> ArticleClassifier:
    """获取分类器实例"""
    global _classifier
    if _classifier is None:
        _classifier = ArticleClassifier()
    return _classifier

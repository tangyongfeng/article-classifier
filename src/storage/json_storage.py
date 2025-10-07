"""JSON 文件存储模块"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from ..utils.config import get_config
from ..utils.logger import get_logger
from .models import ArticleDocument

logger = get_logger()


class JSONStorage:
    """JSON 文件存储管理"""

    def __init__(self):
        self.config = get_config()
        self.json_root = self.config.get_json_path()
        self.articles_dir = self.json_root / "articles"
        self.articles_dir.mkdir(parents=True, exist_ok=True)

    def _get_article_path(self, article_id: int, created_at: Optional[datetime] = None) -> Path:
        """获取文章JSON文件路径（按年月组织）"""
        if self.config.storage.organize_by_date and created_at:
            year = created_at.strftime("%Y")
            month = created_at.strftime("%m")
            dir_path = self.articles_dir / year / month
        else:
            dir_path = self.articles_dir

        dir_path.mkdir(parents=True, exist_ok=True)
        filename = f"{article_id:06d}.json"
        return dir_path / filename

    def save_article(self, article_doc: ArticleDocument) -> Path:
        """保存文章JSON"""
        created_at = article_doc.metadata.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        file_path = self._get_article_path(article_doc.id, created_at)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                article_doc.model_dump(),
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.debug(f"保存文章 JSON: {file_path}")
        return file_path

    def load_article(self, article_id: int, created_at: Optional[datetime] = None) -> Optional[ArticleDocument]:
        """加载文章JSON"""
        file_path = self._get_article_path(article_id, created_at)
        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return ArticleDocument(**data)

    def save_categories(self, categories: Dict[str, Any]):
        """保存分类体系"""
        categories_file = self.json_root / "categories.json"
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        logger.info(f"分类体系已保存: {categories_file}")

    def load_categories(self) -> Optional[Dict[str, Any]]:
        """加载分类体系"""
        categories_file = self.json_root / "categories.json"
        if not categories_file.exists():
            return None

        with open(categories_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_snapshot(self, category_tree: Dict[str, Any], total_articles: int):
        """保存分类快照"""
        snapshots_dir = self.json_root / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = snapshots_dir / f"categories_{timestamp}.json"

        snapshot_data = {
            "timestamp": datetime.now().isoformat(),
            "total_articles": total_articles,
            "category_tree": category_tree
        }

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

        logger.info(f"分类快照已保存: {snapshot_file}")

    def save_failed_file(self, file_path: str, error: str):
        """保存失败文件信息"""
        failed_dir = self.config.get_failed_path()
        failed_log = failed_dir / "failed_files.json"

        failed_data = []
        if failed_log.exists():
            with open(failed_log, 'r', encoding='utf-8') as f:
                failed_data = json.load(f)

        failed_data.append({
            "file_path": file_path,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

        with open(failed_log, 'w', encoding='utf-8') as f:
            json.dump(failed_data, f, ensure_ascii=False, indent=2)


# 全局实例
_storage: Optional[JSONStorage] = None


def get_json_storage() -> JSONStorage:
    """获取 JSON 存储实例"""
    global _storage
    if _storage is None:
        _storage = JSONStorage()
    return _storage

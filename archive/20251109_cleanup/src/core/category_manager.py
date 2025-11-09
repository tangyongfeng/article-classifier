"""分类管理器"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..storage.database import get_database
from ..storage.json_storage import get_json_storage
from ..storage.models import Category
from ..utils.logger import get_logger

logger = get_logger()


class CategoryManager:
    """分类管理器"""

    def __init__(self):
        self.db = get_database()
        self.storage = get_json_storage()

    def create_category_path(self, category_path: List[str]) -> List[int]:
        """
        创建分类路径（如果不存在）

        Args:
            category_path: 分类路径，如 ["技术", "编程语言", "Python"]

        Returns:
            分类 ID 列表
        """
        category_ids = []
        parent_id = None

        for level, cat_name in enumerate(category_path, start=1):
            if level > 3:
                logger.warning(f"分类层级超过3层，忽略: {cat_name}")
                break

            # 查询是否已存在
            existing_cat = self.db.get_category_by_name_and_parent(cat_name, parent_id)

            if existing_cat:
                category_id = existing_cat.id
            else:
                # 创建新分类
                category = Category(
                    name=cat_name,
                    parent_id=parent_id,
                    level=level,
                    description=f"自动创建的{['一级', '二级', '三级'][level-1]}分类"
                )
                category_id = self.db.insert_category(category)
                logger.info(f"创建新分类: {cat_name} (level={level}, parent_id={parent_id})")

            category_ids.append(category_id)
            parent_id = category_id

        return category_ids

    def get_category_tree(self) -> Dict[str, Any]:
        """
        获取分类树

        Returns:
            分类树字典
        """
        tree = self.db.get_category_tree()
        total_articles = self.db.get_total_articles()

        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_articles": total_articles,
            "categories": tree
        }

    def save_category_tree(self):
        """保存分类树到 JSON"""
        tree = self.get_category_tree()
        self.storage.save_categories(tree)

    def load_category_tree(self) -> Optional[Dict[str, Any]]:
        """从 JSON 加载分类树"""
        return self.storage.load_categories()

    def get_category_distribution(self) -> List[Dict[str, Any]]:
        """获取分类分布统计"""
        return self.db.get_category_distribution()

    def update_category_counts(self):
        """更新所有分类的文章计数"""
        categories = self.db.get_all_categories()

        for cat in categories:
            # 统计该分类下的文章数
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM article_categories
                    WHERE category_id = %s
                """, (cat.id,))
                count = cursor.fetchone()['count']
                self.db.update_category_count(cat.id, count)

        logger.info("分类计数已更新")

    def merge_categories(self, source_ids: List[int], target_id: int):
        """
        合并分类

        Args:
            source_ids: 源分类 ID 列表
            target_id: 目标分类 ID
        """
        with self.db.get_cursor() as cursor:
            for source_id in source_ids:
                # 更新文章关联
                cursor.execute("""
                    UPDATE article_categories
                    SET category_id = %s
                    WHERE category_id = %s
                """, (target_id, source_id))

                # 删除源分类
                cursor.execute("DELETE FROM categories WHERE id = %s", (source_id,))

        self.update_category_counts()
        logger.info(f"合并分类: {source_ids} -> {target_id}")

    def split_category(
        self,
        parent_id: int,
        new_subcategories: List[str]
    ) -> List[int]:
        """
        拆分分类

        Args:
            parent_id: 父分类 ID
            new_subcategories: 新子类别名称列表

        Returns:
            新创建的子分类 ID 列表
        """
        parent = self.db.get_all_categories()
        parent_cat = next((c for c in parent if c.id == parent_id), None)

        if not parent_cat:
            raise ValueError(f"父分类不存在: {parent_id}")

        new_ids = []
        for sub_name in new_subcategories:
            category = Category(
                name=sub_name,
                parent_id=parent_id,
                level=parent_cat.level + 1,
                description=f"从 {parent_cat.name} 拆分"
            )
            cat_id = self.db.insert_category(category)
            new_ids.append(cat_id)

        logger.info(f"拆分分类 {parent_cat.name}: {new_subcategories}")
        return new_ids


# 全局实例
_category_manager: Optional[CategoryManager] = None


def get_category_manager() -> CategoryManager:
    """获取分类管理器实例"""
    global _category_manager
    if _category_manager is None:
        _category_manager = CategoryManager()
    return _category_manager

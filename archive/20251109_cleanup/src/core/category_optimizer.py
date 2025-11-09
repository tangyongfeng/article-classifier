"""分类优化器"""
from typing import Dict, Any, Optional
from ..storage.database import get_database
from ..utils.logger import get_logger
from .llm_service import get_llm_service
from .category_manager import get_category_manager

logger = get_logger()


class CategoryOptimizer:
    """分类优化器"""

    def __init__(self):
        self.db = get_database()
        self.llm = get_llm_service()
        self.manager = get_category_manager()

    def should_optimize(self, total_articles: int, optimization_interval: int = 100) -> bool:
        """判断是否需要优化"""
        return total_articles > 0 and total_articles % optimization_interval == 0

    def optimize(self):
        """执行分类优化"""
        logger.info("开始分类优化...")

        # 获取统计信息
        total_articles = self.db.get_total_articles()
        distribution = self.manager.get_category_distribution()

        if not distribution:
            logger.info("暂无分类数据，跳过优化")
            return

        # 调用 LLM 获取优化建议
        category_dist_dict = {
            "total_articles": total_articles,
            "categories": distribution
        }

        try:
            suggestions = self.llm.optimize_categories(total_articles, category_dist_dict)
            actions = suggestions.get("optimization_actions", [])

            if not actions:
                logger.info("暂无优化建议")
                return

            logger.info(f"收到 {len(actions)} 条优化建议")

            # 执行优化动作
            for action in actions:
                self._execute_action(action)

            # 更新分类计数
            self.manager.update_category_counts()

            # 保存分类树
            self.manager.save_category_tree()

            logger.info("分类优化完成")

        except Exception as e:
            logger.error(f"分类优化失败: {e}")

    def _execute_action(self, action: Dict[str, Any]):
        """执行优化动作"""
        action_type = action.get("action")

        try:
            if action_type == "split":
                # 拆分分类
                category_name = action.get("category")
                new_subcategories = action.get("new_subcategories", [])

                # 查找分类 ID
                categories = self.db.get_all_categories()
                cat = next((c for c in categories if c.name == category_name and c.level == 1), None)

                if cat:
                    self.manager.split_category(cat.id, new_subcategories)
                    logger.info(f"已拆分分类: {category_name} -> {new_subcategories}")

            elif action_type == "merge":
                # 合并分类
                source_names = action.get("categories", [])
                target_name = action.get("into")

                # 查找分类 ID
                categories = self.db.get_all_categories()
                source_ids = [c.id for c in categories if c.name in source_names and c.level == 1]
                target_cat = next((c for c in categories if c.name == target_name and c.level == 1), None)

                if not target_cat:
                    # 创建目标分类
                    from ..storage.models import Category
                    category = Category(name=target_name, level=1)
                    target_id = self.db.insert_category(category)
                else:
                    target_id = target_cat.id

                if source_ids:
                    self.manager.merge_categories(source_ids, target_id)
                    logger.info(f"已合并分类: {source_names} -> {target_name}")

            elif action_type == "create":
                # 创建新分类
                category_name = action.get("category")
                reason = action.get("reason", "")

                from ..storage.models import Category
                category = Category(
                    name=category_name,
                    level=1,
                    description=reason
                )
                cat_id = self.db.insert_category(category)
                logger.info(f"已创建新分类: {category_name} (原因: {reason})")

        except Exception as e:
            logger.error(f"执行优化动作失败 {action}: {e}")


# 全局实例
_optimizer: Optional = None


def get_category_optimizer():
    """获取分类优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = CategoryOptimizer()
    return _optimizer

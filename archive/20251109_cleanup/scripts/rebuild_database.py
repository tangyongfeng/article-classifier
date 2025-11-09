#!/usr/bin/env python3
"""清空并重建数据库分类数据"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import get_database
from src.utils.logger import get_logger

logger = get_logger()


def main():
    """主函数"""
    logger.info("="* 60)
    logger.info("清空并重建数据库")
    logger.info("=" * 60)

    db = get_database()

    try:
        with db.get_cursor() as cursor:
            # 清空关联表
            logger.info("清空文章-分类关联...")
            cursor.execute("DELETE FROM article_categories")

            logger.info("清空文章-关键词关联...")
            cursor.execute("DELETE FROM article_keywords")

            # 清空主表
            logger.info("清空分类表...")
            cursor.execute("DELETE FROM categories")

            logger.info("清空关键词表...")
            cursor.execute("DELETE FROM keywords")

            logger.info("清空文章表...")
            cursor.execute("DELETE FROM articles")

        logger.info("数据库已清空，现在可以运行 sync_to_database.py 重新同步数据")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"清空数据库失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

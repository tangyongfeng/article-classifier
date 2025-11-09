#!/usr/bin/env python3
"""将 JSON 文件中的分类结果同步到数据库"""
import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import get_database
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger()


def sync_article_to_db(article_file: Path, db):
    """同步单个文章到数据库"""
    try:
        with open(article_file, 'r', encoding='utf-8') as f:
            article_data = json.load(f)

        article_id = article_data['id']
        metadata = article_data.get('metadata', {})
        classification = article_data.get('classification', {})
        content = article_data.get('content', {})

        # 提取分类路径和关键词
        category_path = classification.get('category_path', [])
        category_ids = classification.get('category_ids', [])
        keywords = classification.get('keywords', [])
        summary = classification.get('summary', '')
        confidence = classification.get('confidence', 0.0)

        # 如果没有分类或是"未分类",跳过
        if not category_path or category_path[0] == '未分类':
            return False

        with db.get_cursor() as cursor:
            # 检查文章是否存在
            cursor.execute("SELECT id FROM articles WHERE id = %s", (article_id,))
            article_exists = cursor.fetchone() is not None

            if article_exists:
                # 更新文章信息
                cursor.execute("""
                    UPDATE articles
                    SET summary = %s, confidence = %s, json_path = %s
                    WHERE id = %s
                """, (summary, confidence, str(article_file), article_id))

                # 删除旧的分类关联
                cursor.execute("DELETE FROM article_categories WHERE article_id = %s", (article_id,))

                # 删除旧的关键词关联
                cursor.execute("DELETE FROM article_keywords WHERE article_id = %s", (article_id,))
            else:
                # 插入新文章
                cursor.execute("""
                    INSERT INTO articles (id, file_path, json_path, title, summary,
                                        created_at, file_format, file_size, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    article_id,
                    metadata.get('file_path', ''),
                    str(article_file),
                    metadata.get('title', ''),
                    summary,
                    metadata.get('created_at'),
                    metadata.get('file_format', ''),
                    metadata.get('file_size', 0),
                    confidence
                ))

            # 添加分类关联
            for cat_id in category_ids:
                cursor.execute("""
                    INSERT INTO article_categories (article_id, category_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (article_id, cat_id))

            # 添加关键词
            for keyword in keywords:
                # 插入关键词（如果不存在）
                cursor.execute("""
                    INSERT INTO keywords (keyword)
                    VALUES (%s)
                    ON CONFLICT (keyword) DO UPDATE SET keyword = EXCLUDED.keyword
                    RETURNING id
                """, (keyword,))
                keyword_id = cursor.fetchone()['id']

                # 关联文章和关键词
                cursor.execute("""
                    INSERT INTO article_keywords (article_id, keyword_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (article_id, keyword_id))

        return True
    except Exception as e:
        logger.error(f"同步文章 {article_file} 失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("="* 60)
    logger.info("同步 JSON 分类结果到数据库")
    logger.info("=" * 60)

    config = get_config()
    db = get_database()

    # 获取所有文章JSON文件
    json_root = config.get_json_path()
    articles_dir = json_root / "articles"

    if not articles_dir.exists():
        logger.error(f"文章目录不存在: {articles_dir}")
        return

    article_files = list(articles_dir.rglob('*.json'))
    total = len(article_files)

    logger.info(f"找到 {total} 个文章文件")
    logger.info("开始同步...")

    synced = 0
    skipped = 0
    failed = 0

    for i, article_file in enumerate(article_files, 1):
        if i % 50 == 0 or i == total:
            logger.info(f"进度: {i}/{total}")

        result = sync_article_to_db(article_file, db)
        if result:
            synced += 1
        elif result is False:
            skipped += 1
        else:
            failed += 1

    logger.info("=" * 60)
    logger.info("同步完成!")
    logger.info(f"总文件数: {total}")
    logger.info(f"已同步: {synced}")
    logger.info(f"已跳过: {skipped}")
    logger.info(f"失败: {failed}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

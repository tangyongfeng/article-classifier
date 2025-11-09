#!/usr/bin/env python3
"""将 JSON 文件中的分类结果同步到数据库 - V2 版本
先构建分类体系，再同步文章
"""
import sys
from pathlib import Path
import json
from collections import defaultdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import get_database
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger()


def build_category_structure(article_files):
    """从文章中提取所有分类，构建分类结构"""
    categories = {}  # {category_name: {parent: None or name, children: set()}}

    for article_file in article_files:
        try:
            with open(article_file, 'r', encoding='utf-8') as f:
                article_data = json.load(f)

            category_path = article_data.get('classification', {}).get('category_path', [])

            if not category_path or category_path[0] == '未分类':
                continue

            # 记录分类路径
            for i, cat_name in enumerate(category_path):
                if cat_name not in categories:
                    categories[cat_name] = {'parent': None, 'children': set()}

                # 如果不是根分类，设置父分类
                if i > 0:
                    parent_name = category_path[i-1]
                    categories[cat_name]['parent'] = parent_name
                    categories[parent_name]['children'].add(cat_name)

        except Exception as e:
            continue

    return categories


def create_categories_in_db(categories, db):
    """在数据库中创建分类，返回 {name: id} 映射"""
    category_id_map = {}

    # 按层级创建（先父后子）
    created = set()
    to_create = list(categories.keys())

    while to_create:
        batch_created = False
        remaining = []

        for cat_name in to_create:
            cat_info = categories[cat_name]
            parent_name = cat_info['parent']

            # 如果是根分类，或者父分类已创建，则可以创建
            if parent_name is None or parent_name in created:
                parent_id = category_id_map.get(parent_name)

                with db.get_cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO categories (name, parent_id, article_count)
                        VALUES (%s, %s, 0)
                        RETURNING id
                    """, (cat_name, parent_id))
                    cat_id = cursor.fetchone()['id']
                    category_id_map[cat_name] = cat_id
                    created.add(cat_name)
                    batch_created = True
            else:
                remaining.append(cat_name)

        to_create = remaining

        if not batch_created and to_create:
            # 无法创建任何分类，可能有循环依赖
            logger.warning(f"无法创建以下分类（可能缺少父分类）: {to_create}")
            break

    return category_id_map


def sync_article_to_db(article_file, category_id_map, db):
    """同步单个文章到数据库"""
    try:
        with open(article_file, 'r', encoding='utf-8') as f:
            article_data = json.load(f)

        article_id = article_data['id']
        metadata = article_data.get('metadata', {})
        classification = article_data.get('classification', {})

        # 提取分类路径和关键词
        category_path = classification.get('category_path', [])
        keywords = classification.get('keywords', [])
        summary = classification.get('summary', '')
        confidence = classification.get('confidence', 0.0)

        # 如果没有分类或是"未分类",跳过
        if not category_path or category_path[0] == '未分类':
            return False

        # 将分类名称映射到ID
        category_ids = []
        for cat_name in category_path:
            if cat_name in category_id_map:
                category_ids.append(category_id_map[cat_name])

        if not category_ids:
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
                file_path = metadata.get('file_path', '')
                if not file_path:  # 如果为空，使用json路径作为标识
                    file_path = str(article_file)

                cursor.execute("""
                    INSERT INTO articles (id, file_path, json_path, title, summary,
                                        created_at, file_format, file_size, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    article_id,
                    file_path,
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

                # 更新分类的文章计数
                cursor.execute("""
                    UPDATE categories
                    SET article_count = article_count + 1
                    WHERE id = %s
                """, (cat_id,))

            # 添加关键词
            for keyword in keywords:
                cursor.execute("""
                    INSERT INTO keywords (keyword)
                    VALUES (%s)
                    ON CONFLICT (keyword) DO UPDATE SET keyword = EXCLUDED.keyword
                    RETURNING id
                """, (keyword,))
                keyword_id = cursor.fetchone()['id']

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
    logger.info("同步 JSON 分类结果到数据库 (V2)")
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

    # 步骤1: 构建分类结构
    logger.info("步骤 1/3: 分析分类结构...")
    categories = build_category_structure(article_files)
    logger.info(f"发现 {len(categories)} 个唯一分类")

    # 步骤2: 创建分类
    logger.info("步骤 2/3: 在数据库中创建分类...")
    category_id_map = create_categories_in_db(categories, db)
    logger.info(f"已创建 {len(category_id_map)} 个分类")

    # 步骤3: 同步文章
    logger.info("步骤 3/3: 同步文章...")

    synced = 0
    skipped = 0
    failed = 0

    for i, article_file in enumerate(article_files, 1):
        if i % 50 == 0 or i == total:
            logger.info(f"进度: {i}/{total}")

        result = sync_article_to_db(article_file, category_id_map, db)
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

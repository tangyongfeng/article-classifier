"""数据库操作模块"""
import os
from typing import List, Optional, Dict, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from contextlib import contextmanager

from ..utils.config import get_config
from ..utils.logger import get_logger
from .models import Article, Category, Keyword

logger = get_logger()


class Database:
    """数据库管理类"""

    def __init__(self):
        self.config = get_config()
        self.conn = None

    def connect(self):
        """连接数据库"""
        if self.conn is None or self.conn.closed:
            password = os.getenv('POSTGRES_PASSWORD', 'AcUs3r#2025!Px7Qm')
            self.conn = psycopg2.connect(
                host=self.config.database.host,
                port=self.config.database.port,
                database=self.config.database.database,
                user=self.config.database.user,
                password=password
            )
        return self.conn

    def close(self):
        """关闭连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()

    @contextmanager
    def get_cursor(self):
        """获取游标"""
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            cursor.close()

    # ========== Article 操作 ==========

    def insert_article(self, article: Article) -> int:
        """插入文章"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO articles (file_path, json_path, title, summary, created_at,
                                    processed_at, file_format, file_size, confidence)
                VALUES (%(file_path)s, %(json_path)s, %(title)s, %(summary)s, %(created_at)s,
                       %(processed_at)s, %(file_format)s, %(file_size)s, %(confidence)s)
                RETURNING id
            """, article.model_dump())
            return cursor.fetchone()['id']

    def get_article_by_path(self, file_path: str) -> Optional[Article]:
        """根据文件路径查询文章"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM articles WHERE file_path = %s", (file_path,))
            row = cursor.fetchone()
            return Article(**dict(row)) if row else None

    def article_exists(self, file_path: str) -> bool:
        """检查文章是否存在"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT 1 FROM articles WHERE file_path = %s", (file_path,))
            return cursor.fetchone() is not None

    def get_total_articles(self) -> int:
        """获取文章总数"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM articles")
            return cursor.fetchone()['count']

    # ========== Category 操作 ==========

    def insert_category(self, category: Category) -> int:
        """插入分类"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO categories (name, parent_id, level, description, article_count)
                VALUES (%(name)s, %(parent_id)s, %(level)s, %(description)s, %(article_count)s)
                ON CONFLICT (name, parent_id) DO UPDATE
                SET updated_at = NOW()
                RETURNING id
            """, category.model_dump(exclude={'id', 'created_at', 'updated_at'}))
            return cursor.fetchone()['id']

    def get_category_by_name_and_parent(self, name: str, parent_id: Optional[int]) -> Optional[Category]:
        """根据名称和父ID查询分类"""
        with self.get_cursor() as cursor:
            if parent_id is None:
                cursor.execute("SELECT * FROM categories WHERE name = %s AND parent_id IS NULL", (name,))
            else:
                cursor.execute("SELECT * FROM categories WHERE name = %s AND parent_id = %s", (name, parent_id))
            row = cursor.fetchone()
            return Category(**dict(row)) if row else None

    def get_all_categories(self) -> List[Category]:
        """获取所有分类"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY level, name")
            return [Category(**dict(row)) for row in cursor.fetchall()]

    def update_category_count(self, category_id: int, count: int):
        """更新分类文章数"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE categories
                SET article_count = %s, updated_at = NOW()
                WHERE id = %s
            """, (count, category_id))

    def increment_category_count(self, category_id: int):
        """增加分类文章数"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE categories
                SET article_count = article_count + 1, updated_at = NOW()
                WHERE id = %s
            """, (category_id,))

    def get_category_tree(self) -> List[Dict[str, Any]]:
        """获取分类树"""
        categories = self.get_all_categories()

        # 构建分类字典
        cat_dict = {cat.id: cat.model_dump() for cat in categories}
        for cat in cat_dict.values():
            cat['children'] = []

        # 构建树结构
        roots = []
        for cat in cat_dict.values():
            if cat['parent_id'] is None:
                roots.append(cat)
            else:
                parent = cat_dict.get(cat['parent_id'])
                if parent:
                    parent['children'].append(cat)

        return roots

    # ========== Article-Category 关联 ==========

    def link_article_category(self, article_id: int, category_id: int):
        """关联文章和分类"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO article_categories (article_id, category_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (article_id, category_id))

    def get_article_categories(self, article_id: int) -> List[Category]:
        """获取文章的所有分类"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.* FROM categories c
                JOIN article_categories ac ON c.id = ac.category_id
                WHERE ac.article_id = %s
                ORDER BY c.level
            """, (article_id,))
            return [Category(**dict(row)) for row in cursor.fetchall()]

    # ========== Keyword 操作 ==========

    def insert_keyword(self, keyword_text: str) -> int:
        """插入关键词"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO keywords (keyword, usage_count)
                VALUES (%s, 1)
                ON CONFLICT (keyword) DO UPDATE
                SET usage_count = keywords.usage_count + 1
                RETURNING id
            """, (keyword_text,))
            return cursor.fetchone()['id']

    def link_article_keyword(self, article_id: int, keyword_id: int):
        """关联文章和关键词"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO article_keywords (article_id, keyword_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (article_id, keyword_id))

    def get_top_keywords(self, limit: int = 20) -> List[Tuple[str, int]]:
        """获取热门关键词"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT keyword, usage_count FROM keywords
                ORDER BY usage_count DESC
                LIMIT %s
            """, (limit,))
            return [(row['keyword'], row['usage_count']) for row in cursor.fetchall()]

    # ========== 统计 ==========

    def get_category_distribution(self) -> List[Dict[str, Any]]:
        """获取分类分布统计"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.name, c.level, c.article_count,
                       ROUND(c.article_count * 100.0 / NULLIF((SELECT SUM(article_count) FROM categories WHERE level = 1), 0), 2) as percentage
                FROM categories c
                WHERE c.level = 1
                ORDER BY c.article_count DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def save_snapshot(self, category_tree: Dict[str, Any], statistics: Dict[str, Any]):
        """保存分类快照"""
        import json
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO category_snapshots (total_articles, category_tree, statistics)
                VALUES (%s, %s, %s)
            """, (
                self.get_total_articles(),
                json.dumps(category_tree, ensure_ascii=False),
                json.dumps(statistics, ensure_ascii=False)
            ))


# 全局数据库实例
_db: Optional[Database] = None


def get_database() -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = Database()
    return _db

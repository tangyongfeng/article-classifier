"""文章查询服务"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from src.storage.database import get_database
from src.utils.config import get_config


class ArticleService:
    """文章服务"""

    def __init__(self):
        self.db = get_database()
        self.config = get_config()

    def get_total_count(self) -> int:
        """获取文章总数"""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM articles")
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_articles_by_category(
        self,
        category_id: int,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'created_at'
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取指定分类下的文章（分页）"""
        offset = (page - 1) * per_page

        # 确定排序字段
        order_clause = "a.created_at DESC"
        if sort_by == 'confidence':
            order_clause = "a.confidence DESC, a.created_at DESC"

        with self.db.get_cursor() as cursor:
            # 获取文章列表
            cursor.execute(f"""
                SELECT a.id, a.title, a.summary, a.confidence, a.created_at, a.json_path
                FROM articles a
                JOIN article_categories ac ON a.id = ac.article_id
                WHERE ac.category_id = %s
                ORDER BY {order_clause}
                LIMIT %s OFFSET %s
            """, (category_id, per_page, offset))
            articles = cursor.fetchall()

            # 获取每篇文章的关键词
            article_list = []
            for article in articles:
                # 获取关键词
                cursor.execute("""
                    SELECT k.keyword
                    FROM keywords k
                    JOIN article_keywords ak ON k.id = ak.keyword_id
                    WHERE ak.article_id = %s
                    LIMIT 5
                """, (article['id'],))
                keywords = [row['keyword'] for row in cursor.fetchall()]

                article_list.append({
                    'id': article['id'],
                    'title': article['title'],
                    'summary': article['summary'],
                    'confidence': float(article['confidence']) if article['confidence'] else 0.0,
                    'created_at': article['created_at'],
                    'keywords': keywords
                })

            # 获取总数
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM article_categories
                WHERE category_id = %s
            """, (category_id,))
            total = cursor.fetchone()['count']

        return article_list, total

    def get_article_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        """获取文章详情（包括完整内容）"""
        with self.db.get_cursor() as cursor:
            # 获取文章基本信息
            cursor.execute("""
                SELECT id, file_path, json_path, title, summary,
                       created_at, file_format, file_size, confidence
                FROM articles
                WHERE id = %s
            """, (article_id,))
            article = cursor.fetchone()

            if not article:
                return None

            # 获取关键词
            cursor.execute("""
                SELECT k.id, k.keyword
                FROM keywords k
                JOIN article_keywords ak ON k.id = ak.keyword_id
                WHERE ak.article_id = %s
            """, (article_id,))
            keywords = [{'id': row['id'], 'keyword': row['keyword']}
                       for row in cursor.fetchall()]

            # 从 JSON 文件读取完整内容
            content = self._load_article_content(article['json_path'])

            return {
                'id': article['id'],
                'title': article['title'],
                'summary': article['summary'],
                'confidence': float(article['confidence']) if article['confidence'] else 0.0,
                'created_at': article['created_at'],
                'file_path': article['file_path'],
                'file_format': article['file_format'],
                'file_size': article['file_size'],
                'keywords': keywords,
                'content': content.get('cleaned', ''),
                'raw_content': content.get('raw', ''),
                'metadata': content.get('metadata', {})
            }

    def get_article_category_paths(self, article_id: int) -> List[List[Dict[str, Any]]]:
        """获取文章的所有分类路径"""
        with self.db.get_cursor() as cursor:
            # 获取文章的所有分类 ID
            cursor.execute("""
                SELECT category_id
                FROM article_categories
                WHERE article_id = %s
            """, (article_id,))
            category_ids = [row['category_id'] for row in cursor.fetchall()]

        # 导入分类服务
        from web.services.category_service import CategoryService
        category_service = CategoryService()

        # 获取每个分类的路径
        paths = []
        for cat_id in category_ids:
            path = category_service.get_category_path(cat_id)
            paths.append(path)

        return paths

    def search_articles(
        self,
        query: str,
        category_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """搜索文章"""
        offset = (page - 1) * per_page

        with self.db.get_cursor() as cursor:
            # 构建搜索 SQL
            if category_id:
                # 在指定分类下搜索
                cursor.execute("""
                    SELECT DISTINCT a.id, a.title, a.summary, a.confidence, a.created_at
                    FROM articles a
                    LEFT JOIN article_categories ac ON a.id = ac.article_id
                    LEFT JOIN keywords k ON a.id = (
                        SELECT article_id FROM article_keywords WHERE keyword_id = k.id LIMIT 1
                    )
                    WHERE ac.category_id = %s
                      AND (a.title ILIKE %s OR a.summary ILIKE %s OR k.keyword ILIKE %s)
                    ORDER BY a.created_at DESC
                    LIMIT %s OFFSET %s
                """, (category_id, f'%{query}%', f'%{query}%', f'%{query}%', per_page, offset))
            else:
                # 全局搜索
                cursor.execute("""
                    SELECT DISTINCT a.id, a.title, a.summary, a.confidence, a.created_at
                    FROM articles a
                    LEFT JOIN article_keywords ak ON a.id = ak.article_id
                    LEFT JOIN keywords k ON ak.keyword_id = k.id
                    WHERE a.title ILIKE %s OR a.summary ILIKE %s OR k.keyword ILIKE %s
                    ORDER BY a.created_at DESC
                    LIMIT %s OFFSET %s
                """, (f'%{query}%', f'%{query}%', f'%{query}%', per_page, offset))

            articles = cursor.fetchall()

            # 获取每篇文章的关键词
            article_list = []
            for article in articles:
                cursor.execute("""
                    SELECT k.keyword
                    FROM keywords k
                    JOIN article_keywords ak ON k.id = ak.keyword_id
                    WHERE ak.article_id = %s
                    LIMIT 5
                """, (article['id'],))
                keywords = [row['keyword'] for row in cursor.fetchall()]

                article_list.append({
                    'id': article['id'],
                    'title': article['title'],
                    'summary': article['summary'],
                    'confidence': float(article['confidence']) if article['confidence'] else 0.0,
                    'created_at': article['created_at'],
                    'keywords': keywords
                })

            # 获取总数（简化版，不完全准确但足够用）
            total = len(article_list)

        return article_list, total

    def update_article(
        self,
        article_id: int,
        summary: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        category_ids: Optional[List[int]] = None,
        content: Optional[str] = None
    ) -> bool:
        """更新文章信息"""
        try:
            with self.db.get_cursor() as cursor:
                # 更新基本信息
                if summary is not None:
                    cursor.execute("""
                        UPDATE articles SET summary = %s WHERE id = %s
                    """, (summary, article_id))

                if confidence is not None:
                    cursor.execute("""
                        UPDATE articles SET confidence = %s WHERE id = %s
                    """, (confidence, article_id))

                # 更新关键词
                if keywords is not None:
                    # 删除旧关键词关联
                    cursor.execute("""
                        DELETE FROM article_keywords WHERE article_id = %s
                    """, (article_id,))

                    # 添加新关键词
                    for keyword in keywords:
                        # 插入或获取关键词 ID
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
                        """, (article_id, keyword_id))

                # 更新分类
                if category_ids is not None:
                    # 删除旧分类关联
                    cursor.execute("""
                        DELETE FROM article_categories WHERE article_id = %s
                    """, (article_id,))

                    # 添加新分类关联
                    for cat_id in category_ids:
                        cursor.execute("""
                            INSERT INTO article_categories (article_id, category_id)
                            VALUES (%s, %s)
                        """, (article_id, cat_id))

                # 同步更新 JSON 文件
                self._update_json_file(article_id, summary, keywords, confidence, content)

            return True
        except Exception as e:
            print(f"更新文章失败: {e}")
            return False

    def _load_article_content(self, json_path: str) -> Dict[str, Any]:
        """从 JSON 文件加载文章内容"""
        try:
            json_file = Path(json_path)
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('content', {})
        except Exception as e:
            print(f"加载文章内容失败: {e}")

        return {'cleaned': '', 'raw': ''}

    def _update_json_file(
        self,
        article_id: int,
        summary: Optional[str],
        keywords: Optional[List[str]],
        confidence: Optional[float],
        content: Optional[str] = None
    ):
        """更新 JSON 文件中的文章信息"""
        try:
            # 获取 JSON 路径
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT json_path FROM articles WHERE id = %s", (article_id,))
                result = cursor.fetchone()
                if not result:
                    return

            json_path = Path(result['json_path'])
            if not json_path.exists():
                return

            # 读取 JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新字段
            if summary is not None:
                data['classification']['summary'] = summary

            if keywords is not None:
                data['classification']['keywords'] = keywords

            if confidence is not None:
                data['classification']['confidence'] = confidence

            if content is not None:
                # 更新清理后的内容
                if 'content' not in data:
                    data['content'] = {}
                data['content']['cleaned'] = content

            # 写回文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"更新 JSON 文件失败: {e}")

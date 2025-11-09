"""分类查询服务"""
from typing import List, Dict, Any, Optional
from src.storage.database import get_database


class CategoryService:
    """分类服务"""

    def __init__(self):
        self.db = get_database()

    def get_category_tree(self) -> List[Dict[str, Any]]:
        """获取完整的分类树"""
        with self.db.get_cursor() as cursor:
            # 获取所有分类
            cursor.execute("""
                SELECT id, name, parent_id, article_count
                FROM categories
                ORDER BY name
            """)
            all_categories = cursor.fetchall()

        # 构建树形结构
        categories_dict = {}
        root_categories = []

        # 第一遍：创建所有节点
        for cat in all_categories:
            categories_dict[cat['id']] = {
                'id': cat['id'],
                'name': cat['name'],
                'parent_id': cat['parent_id'],
                'article_count': cat['article_count'],
                'children': []
            }

        # 第二遍：建立父子关系
        for cat_id, cat_data in categories_dict.items():
            parent_id = cat_data['parent_id']
            if parent_id is None:
                # 顶级分类
                root_categories.append(cat_data)
            else:
                # 子分类
                if parent_id in categories_dict:
                    categories_dict[parent_id]['children'].append(cat_data)

        return root_categories

    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取分类信息"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, name, parent_id, article_count
                FROM categories
                WHERE id = %s
            """, (category_id,))
            return cursor.fetchone()

    def get_category_path(self, category_id: int) -> List[Dict[str, Any]]:
        """获取分类路径（用于面包屑导航）"""
        path = []
        current_id = category_id

        with self.db.get_cursor() as cursor:
            while current_id is not None:
                cursor.execute("""
                    SELECT id, name, parent_id
                    FROM categories
                    WHERE id = %s
                """, (current_id,))
                cat = cursor.fetchone()

                if cat:
                    path.insert(0, {
                        'id': cat['id'],
                        'name': cat['name']
                    })
                    current_id = cat['parent_id']
                else:
                    break

        return path

    def get_total_count(self) -> int:
        """获取分类总数"""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM categories")
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_all_categories_flat(self) -> List[Dict[str, Any]]:
        """获取所有分类的扁平列表（用于编辑时选择）"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, name, parent_id
                FROM categories
                ORDER BY name
            """)
            categories = cursor.fetchall()

        # 添加完整路径显示
        result = []
        for cat in categories:
            path = self.get_category_path(cat['id'])
            full_name = ' > '.join([c['name'] for c in path])
            result.append({
                'id': cat['id'],
                'name': cat['name'],
                'full_name': full_name,
                'parent_id': cat['parent_id']
            })

        return result

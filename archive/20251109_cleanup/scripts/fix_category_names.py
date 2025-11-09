#!/usr/bin/env python3
"""修复现有分类名称，统一中英文"""
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import get_database
from src.utils.logger import get_logger
from src.utils.category_normalizer import normalize_category_name

logger = get_logger()


class CategoryFixer:
    """分类名称修复工具"""

    def __init__(self):
        self.db = get_database()
        self.updates = []
        self.json_updates = []
        self.stats = {
            "categories_scanned": 0,
            "categories_updated": 0,
            "json_files_updated": 0,
            "mapping": {}  # 记录 old_name -> new_name
        }

    def scan_and_fix_categories(self):
        """扫描并修复数据库中的分类"""
        logger.info("开始扫描数据库中的分类...")

        with self.db.get_cursor() as cursor:
            # 获取所有分类
            cursor.execute("""
                SELECT id, name, parent_id, article_count
                FROM categories
                ORDER BY id
            """)
            categories = cursor.fetchall()

            self.stats["categories_scanned"] = len(categories)
            logger.info(f"找到 {len(categories)} 个分类")

            # 检查每个分类是否需要标准化
            for cat in categories:
                cat_id = cat['id']
                name = cat['name']
                parent_id = cat['parent_id']
                article_count = cat['article_count']

                normalized_name = normalize_category_name(name)

                if normalized_name != name:
                    self.updates.append({
                        "id": cat_id,
                        "old_name": name,
                        "new_name": normalized_name,
                        "parent_id": parent_id,
                        "article_count": article_count
                    })
                    self.stats["mapping"][name] = normalized_name
                    logger.info(f"  需要更新: '{name}' -> '{normalized_name}' (ID: {cat_id}, 文章数: {article_count})")

            logger.info(f"需要更新 {len(self.updates)} 个分类")

    def update_database(self):
        """更新数据库中的分类名称（合并重复分类）"""
        if not self.updates:
            logger.info("无需更新数据库")
            return

        logger.info(f"开始更新数据库中的 {len(self.updates)} 个分类...")

        with self.db.get_cursor() as cursor:
            for update in self.updates:
                cat_id = update["id"]
                new_name = update["new_name"]

                # 实时获取当前的parent_id（可能已被前面的操作改变）
                cursor.execute("SELECT parent_id FROM categories WHERE id = %s", (cat_id,))
                row = cursor.fetchone()
                if not row:
                    # 分类已被删除（在前面的合并操作中）
                    logger.info(f"  跳过（已被合并）: ID {cat_id}")
                    continue

                parent_id = row['parent_id']

                # 检查是否已存在同名分类
                cursor.execute(
                    "SELECT id FROM categories WHERE name = %s AND parent_id IS NOT DISTINCT FROM %s AND id != %s",
                    (new_name, parent_id, cat_id)
                )
                existing = cursor.fetchone()

                if existing:
                    # 已存在同名分类，合并
                    target_id = existing['id']
                    logger.info(f"  合并分类: '{update['old_name']}' (ID: {cat_id}) -> '{new_name}' (ID: {target_id})")

                    # 1. 更新文章关联（避免重复）
                    cursor.execute(
                        """
                        DELETE FROM article_categories ac1
                        WHERE category_id = %s
                        AND EXISTS (
                            SELECT 1 FROM article_categories ac2
                            WHERE ac2.article_id = ac1.article_id
                            AND ac2.category_id = %s
                        )
                        """,
                        (cat_id, target_id)
                    )
                    cursor.execute(
                        "UPDATE article_categories SET category_id = %s WHERE category_id = %s",
                        (target_id, cat_id)
                    )

                    # 2. 更新子分类的父级
                    cursor.execute(
                        "UPDATE categories SET parent_id = %s WHERE parent_id = %s",
                        (target_id, cat_id)
                    )

                    # 3. 更新目标分类的文章计数
                    cursor.execute(
                        "SELECT article_count FROM categories WHERE id = %s",
                        (cat_id,)
                    )
                    old_count = cursor.fetchone()['article_count']
                    cursor.execute(
                        "UPDATE categories SET article_count = article_count + %s WHERE id = %s",
                        (old_count, target_id)
                    )

                    # 4. 删除旧分类
                    cursor.execute("DELETE FROM categories WHERE id = %s", (cat_id,))

                else:
                    # 不存在同名分类，直接重命名
                    logger.info(f"  重命名分类: '{update['old_name']}' -> '{new_name}' (ID: {cat_id})")
                    cursor.execute(
                        "UPDATE categories SET name = %s WHERE id = %s",
                        (new_name, cat_id)
                    )

                self.stats["categories_updated"] += 1

        logger.info(f"✓ 数据库更新完成，已处理 {self.stats['categories_updated']} 个分类")

    def update_json_files(self):
        """更新 JSON 文件中的分类路径"""
        if not self.stats["mapping"]:
            logger.info("无需更新 JSON 文件")
            return

        logger.info("开始更新 JSON 文件中的分类路径...")

        json_root = project_root / "data" / "json"
        if not json_root.exists():
            logger.warning(f"JSON 目录不存在: {json_root}")
            return

        # 递归查找所有 JSON 文件
        json_files = list(json_root.rglob("*.json"))
        logger.info(f"找到 {len(json_files)} 个 JSON 文件")

        updated_count = 0
        for json_file in json_files:
            try:
                # 读取 JSON 文件
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 检查是否需要更新
                if "classification" not in data or "category_path" not in data["classification"]:
                    continue

                category_path = data["classification"]["category_path"]
                updated = False

                # 更新分类路径
                new_path = []
                for cat_name in category_path:
                    if cat_name in self.stats["mapping"]:
                        new_path.append(self.stats["mapping"][cat_name])
                        updated = True
                    else:
                        new_path.append(cat_name)

                if updated:
                    data["classification"]["category_path"] = new_path

                    # 写回文件
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    updated_count += 1
                    self.json_updates.append({
                        "file": str(json_file.relative_to(project_root)),
                        "old_path": category_path,
                        "new_path": new_path
                    })

            except Exception as e:
                logger.error(f"更新 JSON 文件失败: {json_file} - {e}")

        self.stats["json_files_updated"] = updated_count
        logger.info(f"✓ JSON 文件更新完成，已更新 {updated_count} 个文件")

    def generate_report(self):
        """生成修复报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = project_root / "data" / "logs"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"category_fix_report_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "categories_scanned": self.stats["categories_scanned"],
                "categories_updated": self.stats["categories_updated"],
                "json_files_updated": self.stats["json_files_updated"]
            },
            "category_updates": self.updates,
            "name_mapping": self.stats["mapping"],
            "sample_json_updates": self.json_updates[:10]  # 只保存前10个示例
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n修复报告已保存: {report_file}")

        # 打印摘要
        print("\n" + "=" * 60)
        print("分类修复摘要")
        print("=" * 60)
        print(f"扫描分类数: {self.stats['categories_scanned']}")
        print(f"更新分类数: {self.stats['categories_updated']}")
        print(f"更新 JSON 文件数: {self.stats['json_files_updated']}")
        print("\n分类名称映射:")
        for old_name, new_name in self.stats["mapping"].items():
            print(f"  '{old_name}' -> '{new_name}'")
        print("=" * 60)

    def run(self):
        """执行完整修复流程"""
        try:
            # 1. 扫描并分析
            self.scan_and_fix_categories()

            if not self.updates:
                logger.info("所有分类名称已经标准化，无需修复")
                return

            # 2. 确认更新
            print("\n" + "=" * 60)
            print(f"将更新 {len(self.updates)} 个分类名称:")
            for update in self.updates[:10]:  # 只显示前10个
                print(f"  '{update['old_name']}' -> '{update['new_name']}'")
            if len(self.updates) > 10:
                print(f"  ... 还有 {len(self.updates) - 10} 个")
            print("=" * 60)

            # 3. 更新数据库
            self.update_database()

            # 4. 更新 JSON 文件
            self.update_json_files()

            # 5. 生成报告
            self.generate_report()

            logger.info("\n✓ 分类修复完成！")

        except Exception as e:
            logger.error(f"修复过程出错: {e}")
            raise


def main():
    """主函数"""
    fixer = CategoryFixer()
    fixer.run()


if __name__ == "__main__":
    main()

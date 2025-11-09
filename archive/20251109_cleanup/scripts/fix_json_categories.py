#!/usr/bin/env python3
"""只修复 JSON 文件中的分类名称，不修改数据库"""
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger
from src.utils.category_normalizer import normalize_category_path

logger = get_logger()


def fix_json_categories():
    """修复所有 JSON 文件中的分类路径"""
    json_root = project_root / "data" / "json" / "articles"

    if not json_root.exists():
        logger.error(f"JSON 目录不存在: {json_root}")
        return

    # 统计
    stats = {
        "total_files": 0,
        "updated_files": 0,
        "errors": 0,
        "updates": []
    }

    logger.info(f"开始扫描 JSON 文件: {json_root}")

    # 递归查找所有 JSON 文件
    json_files = list(json_root.rglob("*.json"))
    stats["total_files"] = len(json_files)
    logger.info(f"找到 {len(json_files)} 个 JSON 文件")

    for json_file in json_files:
        try:
            # 读取 JSON 文件
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查是否需要更新
            if "classification" not in data or "category_path" not in data["classification"]:
                continue

            old_path = data["classification"]["category_path"]
            new_path = normalize_category_path(old_path)

            if old_path != new_path:
                # 更新分类路径
                data["classification"]["category_path"] = new_path

                # 写回文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                stats["updated_files"] += 1
                stats["updates"].append({
                    "file": str(json_file.relative_to(project_root)),
                    "old_path": old_path,
                    "new_path": new_path
                })

                if stats["updated_files"] % 100 == 0:
                    logger.info(f"  已更新 {stats['updated_files']} 个文件...")

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"处理文件失败: {json_file} - {e}")

    # 生成报告
    logger.info(f"\n✓ JSON 文件更新完成")
    logger.info(f"  总文件数: {stats['total_files']}")
    logger.info(f"  更新文件数: {stats['updated_files']}")
    logger.info(f"  错误数: {stats['errors']}")

    # 保存详细报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = project_root / "data" / "logs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"json_category_fix_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_files": stats["total_files"],
            "updated_files": stats["updated_files"],
            "errors": stats["errors"]
        },
        "updates": stats["updates"][:100]  # 只保存前100个示例
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n报告已保存: {report_file}")

    # 显示示例
    if stats["updates"]:
        logger.info("\n示例更新（前10个）:")
        for update in stats["updates"][:10]:
            logger.info(f"  {' > '.join(update['old_path'])} -> {' > '.join(update['new_path'])}")


def main():
    """主函数"""
    fix_json_categories()


if __name__ == "__main__":
    main()

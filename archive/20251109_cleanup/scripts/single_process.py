#!/usr/bin/env python3
"""单文件处理脚本"""
import sys
import os
from pathlib import Path
import argparse

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.classifier import get_classifier
from src.utils.logger import get_logger


def process_single_file(file_path: str):
    """处理单个文件"""
    logger = get_logger()

    logger.info(f"处理文件: {file_path}")

    # 获取分类器
    classifier = get_classifier()

    # 分类
    result = classifier.classify_file(file_path)

    if result and result.get("status") == "success":
        logger.info("分类成功!")
        logger.info(f"  分类路径: {' > '.join(result.get('category_path', []))}")
        logger.info(f"  置信度: {result.get('confidence', 0):.2f}")
        logger.info(f"  处理时间: {result.get('processing_time', 0):.2f} 秒")
        return 0
    elif result and result.get("status") == "skipped":
        logger.info("文件已处理，跳过")
        return 0
    else:
        logger.error("分类失败")
        if result:
            logger.error(f"  错误: {result.get('error', 'Unknown')}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="单文件分类处理")
    parser.add_argument(
        "file",
        help="文件路径"
    )

    args = parser.parse_args()

    # 设置环境变量
    if not os.getenv('POSTGRES_PASSWORD'):
        os.environ['POSTGRES_PASSWORD'] = 'AcUs3r#2025!Px7Qm'

    try:
        return process_single_file(args.file)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""重新处理失败文章的脚本"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from src.core.classifier import get_classifier
from src.storage.database import get_database
from src.utils.config import get_config
from src.utils.logger import get_batch_logger


def get_failed_files() -> list:
    """从失败日志中获取失败的文件列表"""
    config = get_config()
    failed_log = config.get_failed_path() / "failed_files.json"

    if not failed_log.exists():
        print("未找到失败文件记录")
        return []

    with open(failed_log, 'r', encoding='utf-8') as f:
        failed_data = json.load(f)

    # 提取文件路径（去重）
    file_paths = list(set(item['file_path'] for item in failed_data))
    return file_paths


def retry_failed_files(log_name: str = "retry", clear_failed_log: bool = False):
    """
    重新处理失败的文件

    Args:
        log_name: 日志文件名前缀
        clear_failed_log: 是否在开始前清空失败日志
    """
    logger = get_batch_logger(log_name)
    config = get_config()
    classifier = get_classifier()
    db = get_database()

    logger.info("=" * 60)
    logger.info("重新处理失败文章")
    logger.info("=" * 60)

    # 获取失败文件列表
    failed_files = get_failed_files()

    if not failed_files:
        logger.info("没有失败的文件需要重新处理")
        return

    logger.info(f"发现 {len(failed_files)} 个失败文件")

    # 过滤已处理的文件
    to_retry = []
    for file_path in failed_files:
        # 检查文件是否存在
        if not Path(file_path).exists():
            logger.warning(f"文件不存在，跳过: {file_path}")
            continue

        # 检查是否已经处理成功
        if db.article_exists(file_path):
            logger.debug(f"文件已处理成功，跳过: {file_path}")
            continue

        to_retry.append(file_path)

    logger.info(f"需要重试: {len(to_retry)} 个文件")
    logger.info(f"已处理（跳过）: {len(failed_files) - len(to_retry)} 个文件")

    if not to_retry:
        logger.info("没有待重试文件，退出")
        return

    # 可选：清空失败日志（开始新的重试周期）
    if clear_failed_log:
        failed_log = config.get_failed_path() / "failed_files.json"
        if failed_log.exists():
            failed_log.unlink()
            logger.info("已清空原有失败日志")

    # 统计
    success_count = 0
    failed_count = 0
    start_time = datetime.now()

    # 处理文件
    logger.info(f"开始重新处理...")

    for file_path in tqdm(to_retry, desc="重试处理"):
        result = classifier.classify_file(file_path)

        if result and result.get("status") == "success":
            success_count += 1
        elif result and result.get("status") == "failed":
            failed_count += 1

    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 最终保存
    from src.core.category_manager import get_category_manager
    category_manager = get_category_manager()
    category_manager.update_category_counts()
    category_manager.save_category_tree()

    # 输出统计
    logger.info("=" * 60)
    logger.info("重试处理完成")
    logger.info("=" * 60)
    logger.info(f"总文件数: {len(to_retry)}")
    logger.info(f"成功处理: {success_count} ({success_count/len(to_retry)*100:.1f}%)")
    logger.info(f"处理失败: {failed_count} ({failed_count/len(to_retry)*100:.1f}%)")
    logger.info(f"总耗时: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")

    if success_count > 0:
        avg_time = duration / success_count
        logger.info(f"平均处理时间: {avg_time:.2f} 秒/篇")

    # 分类分布
    distribution = category_manager.get_category_distribution()
    if distribution:
        logger.info("\n当前分类分布:")
        logger.info("-" * 60)
        for cat in distribution[:10]:
            logger.info(f"  {cat['name']}: {cat['article_count']} 篇 ({cat.get('percentage', 0):.1f}%)")

    logger.info("=" * 60)

    # 如果还有失败的，提示用户
    if failed_count > 0:
        logger.warning(f"\n仍有 {failed_count} 篇文章处理失败")
        logger.warning(f"失败日志位置: {config.get_failed_path() / 'failed_files.json'}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="重新处理失败的文章")
    parser.add_argument(
        "--log",
        default="retry",
        help="日志文件名前缀（默认: retry）"
    )
    parser.add_argument(
        "--clear-log",
        action="store_true",
        help="开始前清空失败日志"
    )

    args = parser.parse_args()

    # 设置环境变量（如果未设置）
    if not os.getenv('POSTGRES_PASSWORD'):
        os.environ['POSTGRES_PASSWORD'] = 'AcUs3r#2025!Px7Qm'

    try:
        retry_failed_files(
            log_name=args.log,
            clear_failed_log=args.clear_log
        )
    except KeyboardInterrupt:
        print("\n\n用户中断处理")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

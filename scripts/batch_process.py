#!/usr/bin/env python3
"""批量处理脚本（支持 nohup）"""
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from src.core.classifier import get_classifier
from src.storage.database import get_database
from src.utils.config import get_config
from src.utils.logger import get_batch_logger
from src.storage.models import ProcessingStats


def collect_files(input_dir: str, extensions: list = None) -> list:
    """收集待处理文件"""
    if extensions is None:
        extensions = ['.html', '.htm', '.md', '.markdown', '.txt']

    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    files = []
    for ext in extensions:
        files.extend(input_path.rglob(f'*{ext}'))

    return [str(f) for f in files]


def batch_process(
    input_dir: str,
    log_name: str = "batch",
    extensions: list = None
):
    """
    批量处理文件

    Args:
        input_dir: 输入目录
        log_name: 日志文件名前缀
        extensions: 支持的文件扩展名列表
    """
    # 初始化
    logger = get_batch_logger(log_name)
    config = get_config()
    classifier = get_classifier()
    db = get_database()

    logger.info("=" * 60)
    logger.info("文章分类批量处理开始")
    logger.info("=" * 60)
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"LLM 模型: {config.ollama.model}")

    # 收集文件
    logger.info("正在扫描文件...")
    all_files = collect_files(input_dir, extensions)
    logger.info(f"发现 {len(all_files)} 个文件")

    # 过滤已处理文件
    to_process = []
    for file_path in all_files:
        if not db.article_exists(file_path):
            to_process.append(file_path)

    logger.info(f"需要处理: {len(to_process)} 个文件")
    logger.info(f"已处理（跳过）: {len(all_files) - len(to_process)} 个文件")

    if not to_process:
        logger.info("没有待处理文件，退出")
        return

    # 统计信息
    stats = ProcessingStats(
        total_files=len(to_process),
        start_time=datetime.now()
    )

    # 初始化分类体系（前100篇）
    if db.get_total_articles() < config.classifier.initial_training_size:
        sample_size = min(config.classifier.initial_training_size, len(to_process))
        logger.info(f"初始化分类体系: 分析前 {sample_size} 篇文章...")

        for file_path in tqdm(to_process[:sample_size], desc="初始化分类体系"):
            result = classifier.classify_file(file_path)
            if result and result.get("status") == "success":
                stats.processed += 1
            elif result and result.get("status") == "failed":
                stats.failed += 1
            elif result and result.get("status") == "skipped":
                stats.skipped += 1

        # 保存分类树
        from src.core.category_manager import get_category_manager
        get_category_manager().save_category_tree()

        logger.info("分类体系初始化完成")

        # 移除已处理的文件
        to_process = to_process[sample_size:]
        stats.total_files = len(to_process)
        stats.processed = 0
        stats.failed = 0
        stats.skipped = 0

    # 批量处理剩余文件
    logger.info(f"开始批量处理 {len(to_process)} 个文件...")

    checkpoint_counter = 0
    for file_path in tqdm(to_process, desc="处理文章"):
        result = classifier.classify_file(file_path)

        if result:
            if result.get("status") == "success":
                stats.processed += 1
            elif result.get("status") == "failed":
                stats.failed += 1
            elif result.get("status") == "skipped":
                stats.skipped += 1

        # 检查点保存
        checkpoint_counter += 1
        if checkpoint_counter >= config.processing.checkpoint_interval:
            logger.info(f"检查点: 已处理 {stats.processed} / {stats.total_files} 篇")
            from src.core.category_manager import get_category_manager
            get_category_manager().save_category_tree()
            checkpoint_counter = 0

    # 完成
    stats.end_time = datetime.now()

    # 最终保存
    from src.core.category_manager import get_category_manager
    category_manager = get_category_manager()
    category_manager.update_category_counts()
    category_manager.save_category_tree()

    # 输出统计
    logger.info("=" * 60)
    logger.info("批量处理完成")
    logger.info("=" * 60)
    logger.info(f"总文件数: {stats.total_files}")
    logger.info(f"成功处理: {stats.processed} ({stats.success_rate:.1f}%)")
    logger.info(f"处理失败: {stats.failed}")
    logger.info(f"已跳过: {stats.skipped}")
    logger.info(f"总耗时: {stats.duration_seconds:.1f} 秒 ({stats.duration_seconds/60:.1f} 分钟)")

    if stats.processed > 0:
        avg_time = stats.duration_seconds / stats.processed
        logger.info(f"平均处理时间: {avg_time:.2f} 秒/篇")

    # 分类分布
    distribution = category_manager.get_category_distribution()
    if distribution:
        logger.info("\n分类分布:")
        logger.info("-" * 60)
        for cat in distribution[:10]:  # 显示前10个
            logger.info(f"  {cat['name']}: {cat['article_count']} 篇 ({cat.get('percentage', 0):.1f}%)")

    logger.info("=" * 60)

    # 保存统计报告
    save_summary_report(stats, distribution)


def save_summary_report(stats: ProcessingStats, distribution: list):
    """保存处理摘要报告"""
    import json
    from pathlib import Path

    report_dir = Path(__file__).parent.parent / "data" / "logs"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"summary_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_files": stats.total_files,
        "processed": stats.processed,
        "failed": stats.failed,
        "skipped": stats.skipped,
        "success_rate": stats.success_rate,
        "duration_seconds": stats.duration_seconds,
        "category_distribution": distribution
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n摘要报告已保存: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文章分类批量处理")
    parser.add_argument(
        "--input",
        required=True,
        help="输入目录路径"
    )
    parser.add_argument(
        "--log",
        default="batch",
        help="日志文件名前缀（默认: batch）"
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".html", ".htm", ".md", ".markdown", ".txt"],
        help="文件扩展名列表（默认: .html .htm .md .markdown .txt）"
    )

    args = parser.parse_args()

    # 设置环境变量（如果未设置）
    if not os.getenv('POSTGRES_PASSWORD'):
        os.environ['POSTGRES_PASSWORD'] = 'AcUs3r#2025!Px7Qm'

    try:
        batch_process(
            input_dir=args.input,
            log_name=args.log,
            extensions=args.extensions
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

#!/usr/bin/env python3
"""
分类合并工具
使用LLM智能检测并合并相似的分类
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.category_similarity import CategorySimilarityDetector


def collect_all_category_paths():
    """收集所有分类路径及其文章数"""
    articles_dir = Path('data/json/articles')
    category_articles = defaultdict(list)  # 分类路径 -> 文章文件列表

    for json_file in articles_dir.rglob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                article = json.load(f)

            if 'classification' in article and 'category_path' in article['classification']:
                cat_path = article['classification']['category_path']
                if cat_path:
                    # 使用 tuple 作为 key（list 不能作为字典 key）
                    cat_tuple = tuple(cat_path)
                    category_articles[cat_tuple].append(json_file)

        except Exception as e:
            print(f"读取文件失败 {json_file}: {e}")

    return category_articles


def display_similar_categories(detector: CategorySimilarityDetector, category_articles: Dict):
    """显示相似的分类"""
    # 转换为列表格式
    all_paths = list(category_articles.keys())

    print(f"\n检测到 {len(all_paths)} 个不同的分类路径")
    print("正在检测相似分类...\n")

    similar_pairs = detector.find_similar_categories([list(path) for path in all_paths])

    if not similar_pairs:
        print("✓ 没有发现相似的分类")
        return []

    print(f"发现 {len(similar_pairs)} 组相似分类：\n")

    merge_suggestions = []
    for i, (path1, path2, similarity) in enumerate(similar_pairs, 1):
        path1_tuple = tuple(path1)
        path2_tuple = tuple(path2)

        count1 = len(category_articles[path1_tuple])
        count2 = len(category_articles[path2_tuple])

        print(f"{i}. 相似度: {similarity:.2f}")
        print(f"   A. {' > '.join(path1)} ({count1} 篇)")
        print(f"   B. {' > '.join(path2)} ({count2} 篇)")

        suggestion = detector.suggest_merge(path1, path2)
        keep_path = suggestion['keep']
        merge_path = suggestion['merge_from']

        print(f"   建议: 保留 '{' > '.join(keep_path)}', 合并 '{' > '.join(merge_path)}'")
        print()

        merge_suggestions.append({
            'keep': keep_path,
            'merge_from': merge_path,
            'similarity': similarity,
            'keep_count': len(category_articles[tuple(keep_path)]),
            'merge_count': len(category_articles[tuple(merge_path)])
        })

    return merge_suggestions


def merge_categories(category_articles: Dict, merge_suggestions: List[Dict], auto_merge: bool = False):
    """
    合并分类

    Args:
        category_articles: 分类->文章映射
        merge_suggestions: 合并建议列表
        auto_merge: 是否自动合并（不询问）
    """
    if not merge_suggestions:
        return

    print("\n" + "="*60)
    print("开始合并分类")
    print("="*60 + "\n")

    merged_count = 0

    for suggestion in merge_suggestions:
        keep_path = suggestion['keep']
        merge_path = suggestion['merge_from']

        if not auto_merge:
            response = input(
                f"是否将 '{' > '.join(merge_path)}' ({suggestion['merge_count']}篇) "
                f"合并到 '{' > '.join(keep_path)}' ({suggestion['keep_count']}篇)? [y/N]: "
            ).strip().lower()

            if response != 'y':
                print("跳过")
                continue

        # 执行合并
        merge_tuple = tuple(merge_path)
        articles_to_update = category_articles.get(merge_tuple, [])

        print(f"正在合并 {len(articles_to_update)} 篇文章...")

        for article_file in articles_to_update:
            try:
                with open(article_file, 'r', encoding='utf-8') as f:
                    article = json.load(f)

                # 更新分类路径
                article['classification']['category_path'] = keep_path

                # 写回文件
                with open(article_file, 'w', encoding='utf-8') as f:
                    json.dump(article, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"  ✗ 更新失败 {article_file.name}: {e}")

        print(f"✓ 已合并 {len(articles_to_update)} 篇文章\n")
        merged_count += 1

    print(f"\n合并完成！共合并了 {merged_count} 组分类")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='检测并合并相似的分类')
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.8,
        help='相似度阈值 (0-1)，默认 0.8'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='自动合并，不询问'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只显示相似分类，不执行合并'
    )

    args = parser.parse_args()

    # 初始化检测器
    detector = CategorySimilarityDetector(similarity_threshold=args.threshold)

    # 收集分类
    print("正在扫描文章...")
    category_articles = collect_all_category_paths()

    # 显示相似分类
    merge_suggestions = display_similar_categories(detector, category_articles)

    # 执行合并
    if not args.dry_run and merge_suggestions:
        merge_categories(category_articles, merge_suggestions, auto_merge=args.auto)
    elif args.dry_run:
        print("\n[Dry Run] 未执行实际合并")


if __name__ == '__main__':
    main()

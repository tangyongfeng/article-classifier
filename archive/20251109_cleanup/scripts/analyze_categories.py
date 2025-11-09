#!/usr/bin/env python3
"""
分类分析工具
生成分类报告，帮助识别需要合并的重复分类
"""

import json
from pathlib import Path
from collections import Counter, defaultdict


def collect_categories():
    """收集所有分类及其文章列表"""
    articles_dir = Path('data/json/articles')
    category_info = defaultdict(lambda: {'count': 0, 'articles': []})

    for json_file in articles_dir.rglob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                article = json.load(f)

            if 'classification' in article and 'category_path' in article['classification']:
                cat_path = article['classification']['category_path']
                if cat_path:
                    path_str = ' > '.join(cat_path)
                    category_info[path_str]['count'] += 1
                    category_info[path_str]['articles'].append({
                        'file': json_file.name,
                        'title': article.get('metadata', {}).get('title', ''),
                    })

        except Exception as e:
            pass

    return category_info


def print_category_tree(category_info):
    """打印分类树形结构"""
    # 按分类路径组织
    tree = {}

    for path_str, info in category_info.items():
        parts = path_str.split(' > ')
        current = tree

        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {'_children': {}, '_count': 0, '_direct': 0}

            # 累加总数
            current[part]['_count'] += info['count']

            # 如果是最后一层，记录直接文章数
            if i == len(parts) - 1:
                current[part]['_direct'] = info['count']

            current = current[part]['_children']

    # 递归打印
    def print_node(node, level=0, name='ROOT'):
        indent = '  ' * level
        direct = node.get('_direct', 0)
        total = node.get('_count', 0)

        if name != 'ROOT':
            if direct > 0:
                print(f'{indent}├─ {name} ({direct}篇直接, {total}篇总计)')
            else:
                print(f'{indent}├─ {name} ({total}篇)')

        # 排序子节点（按文章数降序）
        children = sorted(
            node.get('_children', {}).items(),
            key=lambda x: x[1]['_count'],
            reverse=True
        )

        for child_name, child_node in children:
            print_node(child_node, level + 1, child_name)

    print("\n=== 分类树形结构 ===\n")
    print_node(tree)


def find_potential_duplicates(category_info):
    """找出可能重复的分类"""
    print("\n" + "="*60)
    print("可能重复或需要审查的分类")
    print("="*60 + "\n")

    # 按最后一级分类名称分组
    last_level_groups = defaultdict(list)

    for path_str, info in category_info.items():
        parts = path_str.split(' > ')
        last_level = parts[-1]
        last_level_groups[last_level].append({
            'path': path_str,
            'count': info['count']
        })

    # 找出有多个路径的分类名称
    duplicates_found = False

    for name, paths in sorted(last_level_groups.items()):
        if len(paths) > 1:
            duplicates_found = True
            print(f"\n【{name}】出现在 {len(paths)} 个不同路径:")
            for item in sorted(paths, key=lambda x: x['count'], reverse=True):
                print(f"  - {item['path']} ({item['count']}篇)")

    if not duplicates_found:
        print("未发现明显的重复分类")


def analyze_specific_patterns(category_info):
    """分析特定模式（如同义词）"""
    print("\n" + "="*60)
    print("同义词检测")
    print("="*60 + "\n")

    synonym_patterns = [
        (['语言', '语言学', '语言学习'], '可能是语言学习的同义词'),
        (['股市', '股票市场', '证券'], '可能是股市的同义词'),
        (['旅行经历', '旅行经验', '旅游体验'], '可能是旅行经历的同义词'),
        (['技术创新', '创新技术'], '可能是技术创新的同义词'),
    ]

    for synonyms, description in synonym_patterns:
        found = []
        for path_str, info in category_info.items():
            for syn in synonyms:
                if syn in path_str.split(' > '):
                    found.append((path_str, info['count']))
                    break

        if found:
            print(f"\n{description}:")
            for path, count in sorted(found, key=lambda x: x[1], reverse=True):
                print(f"  - {path} ({count}篇)")


def main():
    print("正在分析分类...")
    category_info = collect_categories()

    print(f"\n总计: {len(category_info)} 个不同的分类路径")
    print(f"总文章数: {sum(info['count'] for info in category_info.values())}")

    # 打印分类树
    print_category_tree(category_info)

    # 找潜在重复
    find_potential_duplicates(category_info)

    # 同义词检测
    analyze_specific_patterns(category_info)

    # 统计信息
    print("\n" + "="*60)
    print("分类统计")
    print("="*60 + "\n")

    # 文章数最多的分类
    top_categories = sorted(
        category_info.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:15]

    print("文章数最多的15个分类:")
    for path, info in top_categories:
        print(f"  {info['count']:4d} | {path}")

    # 文章数最少的分类
    print("\n文章数最少的分类 (≤2篇):")
    small_categories = [
        (path, info['count'])
        for path, info in category_info.items()
        if info['count'] <= 2
    ]
    for path, count in sorted(small_categories, key=lambda x: x[1]):
        print(f"  {count:4d} | {path}")


if __name__ == '__main__':
    main()

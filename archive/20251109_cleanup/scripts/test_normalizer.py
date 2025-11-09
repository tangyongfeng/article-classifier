#!/usr/bin/env python3
"""测试分类标准化功能"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.category_normalizer import normalize_category_name, normalize_category_path


def test_normalize_category_name():
    """测试单个分类名称标准化"""
    print("=== 测试单个分类名称标准化 ===")

    test_cases = [
        ("Technology", "技术"),
        ("technology", "技术"),
        ("Travel", "旅行"),
        ("Language Learning", "语言学习"),
        ("Finance", "金融"),
        ("Unclassified", "未分类"),
        ("Education", "教育"),
        ("技术", "技术"),  # 已经是中文
        ("旅行", "旅行"),  # 已经是中文
        ("", "未分类"),    # 空字符串
    ]

    all_passed = True
    for input_val, expected in test_cases:
        result = normalize_category_name(input_val)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} '{input_val}' -> '{result}' (期望: '{expected}')")

    return all_passed


def test_normalize_category_path():
    """测试分类路径标准化"""
    print("\n=== 测试分类路径标准化 ===")

    test_cases = [
        (["Technology", "Programming", "Python"], ["技术", "编程", "Python"]),
        (["Travel", "Asia"], ["旅行", "Asia"]),
        (["Language Learning"], ["语言学习"]),
        (["Finance", "Investment"], ["金融", "投资"]),
        (["Unclassified"], ["未分类"]),
        (["技术", "编程"], ["技术", "编程"]),  # 已经是中文
        ([], ["未分类"]),  # 空列表
    ]

    all_passed = True
    for input_val, expected in test_cases:
        result = normalize_category_path(input_val)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} {input_val} -> {result}")
        if result != expected:
            print(f"   期望: {expected}")

    return all_passed


def main():
    """主测试函数"""
    print("开始测试分类标准化功能...\n")

    test1_passed = test_normalize_category_name()
    test2_passed = test_normalize_category_path()

    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

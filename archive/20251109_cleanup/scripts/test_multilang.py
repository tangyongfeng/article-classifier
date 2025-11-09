#!/usr/bin/env python3
"""测试多语言分类配置"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import get_config
from src.core.llm_service import OllamaService


def test_prompt_generation():
    """测试不同语言配置下的提示词生成"""

    print("=" * 70)
    print("测试多语言提示词生成")
    print("=" * 70)

    # 测试数据
    title = "Introduction to Machine Learning"
    content = "Machine learning is a subset of artificial intelligence..."

    # 测试不同语言配置
    for lang in ["zh", "en", "auto"]:
        print(f"\n{'='*70}")
        print(f"语言配置: {lang}")
        print(f"{'='*70}")

        # 临时修改配置
        config = get_config()
        original_lang = config.classifier.category_language
        config.classifier.category_language = lang

        # 创建 LLM 服务并生成提示词
        llm_service = OllamaService()
        prompt = llm_service._build_classification_prompt(
            title=title,
            content=content,
            current_categories=None
        )

        # 显示关键部分
        lines = prompt.split('\n')
        for i, line in enumerate(lines):
            if '要求：' in line or '**要求**' in line:
                # 显示要求部分
                print('\n'.join(lines[i:i+8]))
                break

        # 恢复配置
        config.classifier.category_language = original_lang

    print("\n" + "=" * 70)
    print("✓ 多语言提示词生成测试完成")
    print("=" * 70)


def show_current_config():
    """显示当前配置"""
    config = get_config()

    print("\n" + "=" * 70)
    print("当前分类语言配置")
    print("=" * 70)
    print(f"category_language: {config.classifier.category_language}")

    lang_desc = {
        "zh": "中文 - 所有分类使用中文",
        "en": "English - All categories in English",
        "auto": "自动检测 - 根据文章语言自动选择分类语言"
    }

    print(f"说明: {lang_desc.get(config.classifier.category_language, '未知')}")
    print("=" * 70)


def main():
    """主函数"""
    show_current_config()

    print("\n是否测试提示词生成? (y/n): ", end='')
    choice = input().strip().lower()

    if choice == 'y':
        test_prompt_generation()
    else:
        print("跳过提示词测试")


if __name__ == "__main__":
    main()

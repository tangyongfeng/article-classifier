#!/usr/bin/env python3
"""系统测试脚本"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """测试 Python 导入"""
    print("1. 测试 Python 模块导入...")
    try:
        import psycopg2
        print("   ✓ psycopg2")
    except ImportError as e:
        print(f"   ✗ psycopg2: {e}")
        return False

    try:
        from bs4 import BeautifulSoup
        print("   ✓ beautifulsoup4")
    except ImportError as e:
        print(f"   ✗ beautifulsoup4: {e}")
        return False

    try:
        import yaml
        print("   ✓ pyyaml")
    except ImportError as e:
        print(f"   ✗ pyyaml: {e}")
        return False

    try:
        from tqdm import tqdm
        print("   ✓ tqdm")
    except ImportError as e:
        print(f"   ✗ tqdm: {e}")
        return False

    print("   所有依赖已安装 ✓\n")
    return True


def test_config():
    """测试配置加载"""
    print("2. 测试配置文件...")
    try:
        from src.utils.config import get_config
        config = get_config()
        print(f"   ✓ 配置加载成功")
        print(f"   - Ollama 模型: {config.ollama.model}")
        print(f"   - 数据库: {config.database.database}")
        print()
        return True
    except Exception as e:
        print(f"   ✗ 配置加载失败: {e}\n")
        return False


def test_database():
    """测试数据库连接"""
    print("3. 测试数据库连接...")

    # 设置环境变量
    if not os.getenv('POSTGRES_PASSWORD'):
        os.environ['POSTGRES_PASSWORD'] = 'AcUs3r#2025!Px7Qm'

    try:
        from src.storage.database import get_database
        db = get_database()
        db.connect()
        print("   ✓ 数据库连接成功")

        # 测试查询
        total = db.get_total_articles()
        print(f"   - 当前文章数: {total}")
        print()
        return True
    except Exception as e:
        print(f"   ✗ 数据库连接失败: {e}")
        print("   请确保:")
        print("   1. PostgreSQL 已安装并运行")
        print("   2. 已执行 scripts/setup_database.sql")
        print("   3. 密码正确（在 .env 文件中）\n")
        return False


def test_ollama():
    """测试 Ollama 连接"""
    print("4. 测试 Ollama 服务...")
    try:
        import requests
        from src.utils.config import get_config
        config = get_config()

        response = requests.get(
            f"{config.ollama.base_url}/api/tags",
            timeout=5
        )
        response.raise_for_status()

        models = response.json().get('models', [])
        model_names = [m.get('name', '') for m in models]

        print("   ✓ Ollama 服务运行中")
        print(f"   - 可用模型: {', '.join(model_names)}")

        # 检查配置的模型
        if config.ollama.model in model_names:
            print(f"   ✓ 配置的模型 {config.ollama.model} 已安装")
        else:
            print(f"   ✗ 配置的模型 {config.ollama.model} 未找到")
            print(f"   请运行: ollama pull {config.ollama.model}")

        print()
        return True
    except Exception as e:
        print(f"   ✗ Ollama 连接失败: {e}")
        print("   请确保 Ollama 服务正在运行:")
        print("   - 检查: curl http://localhost:11434/api/tags")
        print("   - 启动: ollama serve\n")
        return False


def test_file_loader():
    """测试文件加载器"""
    print("5. 测试文件加载器...")
    try:
        from src.loaders.base import LoaderFactory
        print("   ✓ 加载器模块导入成功")

        # 检查是否有测试文件
        test_files = list(Path("../2023年6月/IT技术").glob("*.html"))[:1] if Path("../2023年6月/IT技术").exists() else []

        if test_files:
            test_file = str(test_files[0])
            loader = LoaderFactory.create_loader(test_file)
            data = loader.load()
            print(f"   ✓ 成功加载测试文件: {Path(test_file).name}")
            print(f"   - 标题: {data.get('title', 'N/A')[:50]}...")
        else:
            print("   ⚠ 未找到测试文件（这是正常的）")

        print()
        return True
    except Exception as e:
        print(f"   ✗ 文件加载失败: {e}\n")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("智能文章分类系统 - 安装测试")
    print("=" * 60)
    print()

    results = []

    results.append(("依赖导入", test_imports()))
    results.append(("配置加载", test_config()))
    results.append(("数据库连接", test_database()))
    results.append(("Ollama 服务", test_ollama()))
    results.append(("文件加载器", test_file_loader()))

    # 汇总
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("🎉 所有测试通过！系统已就绪。")
        print()
        print("下一步:")
        print("  python scripts/batch_process.py --input \"../2023年6月\"")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())

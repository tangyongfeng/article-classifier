#!/usr/bin/env python3
"""Web 界面启动脚本"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.app import app
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger()


def main():
    """启动 Web 服务"""
    config = get_config()

    host = config.web.host
    port = config.web.port
    debug = config.web.debug

    logger.info("="* 60)
    logger.info("Article Classifier Web 界面")
    logger.info("=" * 60)
    logger.info(f"访问地址: http://localhost:{port}")
    logger.info(f"监听地址: {host}:{port}")
    logger.info(f"调试模式: {'开启' if debug else '关闭'}")
    logger.info("=" * 60)
    logger.info("按 Ctrl+C 停止服务")
    logger.info("")

    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("\n正在停止 Web 服务...")
    except Exception as e:
        logger.error(f"Web 服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""日志模块"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """日志管理器"""

    def __init__(
        self,
        name: str = "article_classifier",
        log_file: Optional[Path] = None,
        level: str = "INFO"
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # 避免重复添加 handler
        if self.logger.handlers:
            return

        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件输出
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(message)

    def info(self, message: str):
        """信息日志"""
        self.logger.info(message)

    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(message)

    def error(self, message: str):
        """错误日志"""
        self.logger.error(message)

    def critical(self, message: str):
        """严重错误日志"""
        self.logger.critical(message)

    def exception(self, message: str):
        """异常日志（包含堆栈信息）"""
        self.logger.exception(message)


def get_logger(
    name: str = "article_classifier",
    log_file: Optional[str] = None,
    level: str = "INFO"
) -> Logger:
    """获取日志实例"""
    log_path = Path(log_file) if log_file else None
    return Logger(name, log_path, level)


def get_batch_logger(batch_name: str = "batch") -> Logger:
    """获取批处理日志实例"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent.parent / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{batch_name}_{timestamp}.log"
    return Logger("batch_processor", log_file, "INFO")

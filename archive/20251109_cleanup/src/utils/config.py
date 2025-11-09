"""配置管理模块"""
import os
from pathlib import Path
from typing import Any, Dict
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class OllamaConfig(BaseSettings):
    """Ollama 配置"""
    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="gpt-oss:20b")
    temperature: float = Field(default=0.3)
    timeout: int = Field(default=60)
    max_retries: int = Field(default=3)


class ClassifierConfig(BaseSettings):
    """分类器配置"""
    max_category_levels: int = Field(default=3)
    min_confidence: float = Field(default=0.6)
    initial_training_size: int = Field(default=100)
    optimization_interval: int = Field(default=100)
    auto_optimize: bool = Field(default=True)
    category_language: str = Field(default="zh")  # zh, en, or auto


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="article_classifier")
    user: str = Field(default="article_classifier_user")
    password: str = Field(default="")

    class Config:
        env_prefix = "POSTGRES_"


class StorageConfig(BaseSettings):
    """存储配置"""
    json_root: str = Field(default="data/json")
    organize_by_date: bool = Field(default=True)
    save_raw_content: bool = Field(default=True)
    compression: bool = Field(default=False)


class ProcessingConfig(BaseSettings):
    """处理配置"""
    batch_size: int = Field(default=10)
    enable_parallel: bool = Field(default=False)
    checkpoint_interval: int = Field(default=100)
    log_level: str = Field(default="INFO")


class WebConfig(BaseSettings):
    """Web 界面配置"""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=7888)
    debug: bool = Field(default=False)
    articles_per_page: int = Field(default=20)


class Config:
    """全局配置类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config_data: Dict[str, Any] = {}
        self._load_config()

        # 初始化各个配置模块
        self.ollama = OllamaConfig(**self._config_data.get("ollama", {}))
        self.classifier = ClassifierConfig(**self._config_data.get("classifier", {}))
        self.database = DatabaseConfig(**self._config_data.get("database", {}))
        self.storage = StorageConfig(**self._config_data.get("storage", {}))
        self.processing = ProcessingConfig(**self._config_data.get("processing", {}))
        self.web = WebConfig(**self._config_data.get("web", {}))

        # 项目根目录
        self.project_root = Path(__file__).parent.parent.parent

    def _load_config(self):
        """加载配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        else:
            # 使用默认配置
            self._config_data = {}

    def get_database_url(self) -> str:
        """获取数据库连接 URL"""
        # 从环境变量读取密码
        password = os.getenv('POSTGRES_PASSWORD', self.database.password)
        return (
            f"postgresql://{self.database.user}:{password}@"
            f"{self.database.host}:{self.database.port}/{self.database.database}"
        )

    def get_json_path(self, relative_path: str = "") -> Path:
        """获取 JSON 存储路径"""
        base_path = self.project_root / self.storage.json_root
        if relative_path:
            return base_path / relative_path
        return base_path

    def get_log_path(self, log_name: str = "") -> Path:
        """获取日志路径"""
        log_dir = self.project_root / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        if log_name:
            return log_dir / log_name
        return log_dir

    def get_failed_path(self) -> Path:
        """获取失败文件存储路径"""
        failed_dir = self.project_root / "data" / "failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        return failed_dir


# 全局配置实例
_config: Config | None = None


def get_config(config_path: str = "config.yaml") -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        # 如果 config_path 是相对路径，转换为绝对路径
        if not Path(config_path).is_absolute():
            # 从项目根目录查找
            project_root = Path(__file__).parent.parent.parent
            config_path = str(project_root / config_path)
        _config = Config(config_path)
    return _config


def reload_config(config_path: str = "config.yaml"):
    """重新加载配置"""
    global _config
    _config = None
    return get_config(config_path)

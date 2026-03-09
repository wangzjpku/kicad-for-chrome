"""
配置管理模块
统一管理所有配置，支持环境变量和 pydantic-settings
"""

import os
import logging
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AppConfig(BaseModel):
    """应用配置"""

    # 环境
    environment: str = Field(default="development", description="运行环境: development/production")

    # API 安全
    api_key: Optional[str] = Field(default=None, description="API Key 认证")
    require_api_key: bool = Field(default=False, description="是否强制要求 API Key")

    # CORS
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:3004",
            "http://localhost:3005",
        ],
        description="允许的 CORS 源"
    )

    # 文件上传
    max_file_size: int = Field(default=50 * 1024 * 1024, description="最大文件大小 (50MB)")
    allowed_extensions: set[str] = Field(
        default_factory=lambda: {
            ".kicad_pro", ".kicad_sch", ".kicad_pcb",
            ".kicad_mod", ".zip", ".kicad_sym"
        },
        description="允许的文件扩展名"
    )

    # 项目目录
    projects_dir: str = Field(default="/projects", description="项目目录")
    output_dir: str = Field(default="/output", description="输出目录")

    # KiCad 配置
    kicad_cli_path: Optional[str] = Field(default=None, description="KiCad CLI 路径")
    use_virtual_display: bool = Field(default=False, description="是否使用虚拟显示")

    # 日志
    log_level: str = Field(default="INFO", description="日志级别")

    # 缓存配置
    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    cache_ttl: int = Field(default=3600, description="缓存 TTL (秒)")

    class Config:
        env_file = ".env"
        extra = "ignore"


def get_environment() -> str:
    """获取当前环境"""
    return os.getenv("ENV", os.getenv("ENVIRONMENT", "development")).lower()


@lru_cache()
def get_settings() -> AppConfig:
    """
    获取应用配置（单例）
    使用 lru_cache 确保只加载一次
    """
    env = get_environment()

    # 构建配置
    config = AppConfig(
        environment=env,
        api_key=os.getenv("API_KEY"),
        require_api_key=os.getenv("REQUIRE_API_KEY", "").lower() == "true" if os.getenv("REQUIRE_API_KEY") else env == "production",
        allowed_origins=os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else None,
        max_file_size=int(os.getenv("MAX_FILE_SIZE", "52428800")),
        projects_dir=os.getenv("PROJECTS_DIR", "/projects"),
        output_dir=os.getenv("OUTPUT_DIR", "/output"),
        kicad_cli_path=os.getenv("KICAD_CLI_PATH") or os.getenv("KICAD_PATH"),
        use_virtual_display=os.getenv("USE_VIRTUAL_DISPLAY", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        cache_ttl=int(os.getenv("CACHE_TTL", "3600")),
    )

    # 生产环境强制要求 API Key
    if env == "production" and not config.api_key:
        logger.warning(
            "⚠️ 生产环境运行但未配置 API_KEY！"
            "请设置环境变量 API_KEY 以确保安全。"
            "或者设置 REQUIRE_API_KEY=false 来跳过此检查（不推荐）"
        )

    return config


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    验证 API Key

    Returns:
        True: 验证通过
        False: 验证失败（API_KEY 未设置）
        None: 不需要验证
    """
    settings = get_settings()

    # 如果不要求 API Key，直接通过
    if not settings.require_api_key:
        return None

    # 如果要求 API Key 但未设置，是配置错误
    if not settings.api_key:
        raise RuntimeError(
            "API_KEY is required but not configured! "
            "Please set the API_KEY environment variable."
        )

    # 验证 API Key
    if api_key != settings.api_key:
        return False

    return True


# 导出便捷函数
__all__ = [
    "get_settings",
    "get_environment",
    "validate_api_key",
    "AppConfig",
]

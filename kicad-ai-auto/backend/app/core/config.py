"""
应用配置
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用设置"""

    # 应用信息
    APP_NAME: str = "KiCad Web Editor"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # API 配置
    API_V1_STR: str = "/api/v1"

    # CORS 配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # 数据库配置 (SQLite for local deployment)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./kicad_editor.db"
    )

    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # KiCad 配置
    KICAD_CLI_PATH: str = os.getenv("KICAD_CLI_PATH", "")
    KICAD_SHARE_PATH: str = os.getenv("KICAD_SHARE_PATH", "/usr/share/kicad")
    USE_VIRTUAL_DISPLAY: bool = (
        os.getenv("USE_VIRTUAL_DISPLAY", "false").lower() == "true"
    )

    # 文件路径
    PROJECTS_DIR: str = os.getenv("PROJECTS_DIR", "./projects")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天

    # 上传限制
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".kicad_pro",
        ".kicad_sch",
        ".kicad_pcb",
        ".kicad_mod",
        ".kicad_sym",
        ".zip",
    ]

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = 30  # 秒

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局设置实例
settings = Settings()

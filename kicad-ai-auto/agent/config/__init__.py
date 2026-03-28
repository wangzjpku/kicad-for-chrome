"""
配置管理模块
统一管理项目配置
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class KiCadConfig:
    """KiCad 相关配置"""

    kicad_path: Optional[str] = None
    projects_dir: str = "./projects"
    max_retries: int = 3
    connection_timeout: int = 30


@dataclass
class AIConfig:
    """AI 相关配置"""

    glm_api_key: Optional[str] = None
    glm_model: str = "glm-4"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class AppConfig:
    """应用配置"""

    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list = None

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


def load_config() -> dict:
    """从环境变量加载配置

    优先级: 环境变量 > 默认值
    """
    config = {
        "kicad": KiCadConfig(
            kicad_path=os.getenv("KICAD_PATH"),
            projects_dir=os.getenv("PROJECTS_DIR", "./projects"),
            max_retries=int(os.getenv("KICAD_MAX_RETRIES", "3")),
            connection_timeout=int(os.getenv("KICAD_TIMEOUT", "30")),
        ),
        "ai": AIConfig(
            glm_api_key=os.getenv("ZHIPU_API_KEY"),
            glm_model=os.getenv("GLM_MODEL", "glm-4"),
            temperature=float(os.getenv("GLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("GLM_MAX_TOKENS", "4096")),
        ),
        "app": AppConfig(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        ),
    }

    return config


# 全局配置实例
CONFIG = load_config()

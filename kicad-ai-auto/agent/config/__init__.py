"""
配置管理模块
统一管理项目配置

Phase 3.3 Enhanced:
- Added KiCad CLI path auto-detection
- Added Redis configuration
- Added JWT configuration
- Added server configuration
- Added convenience accessor functions
"""

import os
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KiCadConfig:
    """KiCad 相关配置"""
    kicad_path: Optional[str] = None
    kicad_cli_path: Optional[str] = None
    projects_dir: str = "./projects"
    output_dir: str = "./output"
    data_dir: str = "./data"
    max_retries: int = 3
    connection_timeout: int = 30
    use_virtual_display: bool = True

    def __post_init__(self):
        # Auto-detect KiCad paths if not set
        if not self.kicad_cli_path:
            self.kicad_cli_path = self._detect_kicad_cli()
        if not self.kicad_path:
            self.kicad_path = self._detect_kicad_path()

    def _detect_kicad_cli(self) -> Optional[str]:
        """Auto-detect KiCad CLI path"""
        windows_paths = [
            "E:/Program Files/KiCad/9.0/bin/kicad-cli.exe",
            "C:/Program Files/KiCad/9.0/bin/kicad-cli.exe",
            "E:/Program Files/KiCad/8.0/bin/kicad-cli.exe",
            "C:/Program Files/KiCad/8.0/bin/kicad-cli.exe",
        ]
        for path in windows_paths:
            if Path(path).exists():
                logger.info(f"Auto-detected KiCad CLI at: {path}")
                return path
        unix_paths = [
            "/usr/bin/kicad-cli",
            "/usr/local/bin/kicad-cli",
        ]
        for path in unix_paths:
            if Path(path).exists():
                logger.info(f"Auto-detected KiCad CLI at: {path}")
                return path
        return None

    def _detect_kicad_path(self) -> Optional[str]:
        """Auto-detect KiCad installation path"""
        windows_paths = [
            "E:/Program Files/KiCad/9.0",
            "C:/Program Files/KiCad/9.0",
        ]
        for path in windows_paths:
            if Path(path).exists():
                logger.info(f"Auto-detected KiCad at: {path}")
                return path
        unix_paths = [
            "/usr/share/kicad",
            "/usr/local/share/kicad",
        ]
        for path in unix_paths:
            if Path(path).exists():
                logger.info(f"Auto-detected KiCad at: {path}")
                return path
        return None


@dataclass
class AIConfig:
    """AI 相关配置"""
    kimi_api_key: Optional[str] = None
    kimi_api_url: str = "https://api.moonshot.cn/v1"
    glm_api_key: Optional[str] = None
    glm_api_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm_model: str = "glm-4"
    temperature: float = 0.7
    max_tokens: int = 4096

    def __post_init__(self):
        # Load API keys from environment
        self.kimi_api_key = os.getenv("KIMI_API_KEY", self.kimi_api_key)
        self.glm_api_key = os.getenv("GLM_API_KEY", self.glm_api_key)


@dataclass
class AuthConfig:
    """认证配置"""
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    def __post_init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET", self.jwt_secret)


@dataclass
class RedisConfig:
    """Redis 配置"""
    url: str = "redis://localhost:6379"
    enabled: bool = False

    def __post_init__(self):
        self.enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        self.url = os.getenv("REDIS_URL", self.url)


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])
    api_key: Optional[str] = None
    api_prefix: str = "/api"

    def __post_init__(self):
        self.host = os.getenv("HOST", self.host)
        self.port = int(os.getenv("PORT", str(self.port)))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", self.log_level).upper()
        self.api_key = os.getenv("API_KEY", self.api_key)

        # Parse CORS origins
        origins = os.getenv("ALLOWED_ORIGINS", "")
        if origins:
            self.cors_origins = [o.strip() for o in origins.split(",") if o.strip()]


@dataclass
class AppConfig:
    """应用配置 - 根配置"""
    kicad: KiCadConfig = field(default_factory=KiCadConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    def __post_init__(self):
        # Initialize all sub-configs
        self.kicad.__post_init__()
        self.ai.__post_init__()
        self.auth.__post_init__()
        self.redis.__post_init__()
        self.server.__post_init__()

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.server.debug and os.getenv("ENVIRONMENT", "development") == "production"

    def get_api_url(self, endpoint: str = "") -> str:
        """Get full API URL for an endpoint"""
        base = f"http://{self.server.host}:{self.server.port}"
        if self.server.api_prefix:
            return f"{base}{self.server.api_prefix}/{endpoint.lstrip('/')}"
        return f"{base}/{endpoint.lstrip('/')}"

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        # Check critical paths
        if not self.kicad.kicad_cli_path and not self.is_production():
            issues.append("KICAD_CLI_PATH not set - KiCad IPC may not work")

        # Check API keys if in production
        if self.is_production():
            if not self.auth.jwt_secret:
                issues.append("JWT_SECRET not set - required for production")
            if not self.ai.kimi_api_key and not self.ai.glm_api_key:
                issues.append("No AI API key configured - at least one required")

        return issues


def load_config() -> AppConfig:
    """Load configuration from environment variables

    Priority: Environment variables > Default values
    """
    config = AppConfig()
    config.__post_init__()

    # Ensure directories exist
    for dir_path in [config.kicad.projects_dir, config.kicad.output_dir, config.kicad.data_dir]:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")

    # Log configuration warnings
    issues = config.validate()
    for issue in issues:
        logger.warning(f"Configuration issue: {issue}")

    return config


# Global configuration instance
CONFIG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance (singleton)"""
    global CONFIG
    if CONFIG is None:
        CONFIG = load_config()
    return CONFIG


def reload_config() -> AppConfig:
    """Reload configuration from environment"""
    global CONFIG
    CONFIG = load_config()
    return CONFIG


# ============================================================================
# Convenience accessor functions
# ============================================================================

def get_kicad_cli_path() -> Optional[str]:
    """Get KiCad CLI path"""
    return get_config().kicad.kicad_cli_path


def get_kicad_path() -> Optional[str]:
    """Get KiCad installation path"""
    return get_config().kicad.kicad_path


def get_projects_dir() -> str:
    """Get projects directory"""
    return get_config().kicad.projects_dir


def get_output_dir() -> str:
    """Get output directory"""
    return get_config().kicad.output_dir


def get_data_dir() -> str:
    """Get data directory"""
    return get_config().kicad.data_dir


def get_log_level() -> str:
    """Get configured log level"""
    return get_config().server.log_level


def is_debug() -> bool:
    """Check if debug mode is enabled"""
    return get_config().server.debug


def get_api_key() -> Optional[str]:
    """Get API key (if configured)"""
    return get_config().server.api_key


def get_kimi_api_key() -> Optional[str]:
    """Get Kimi API key"""
    return get_config().ai.kimi_api_key


def get_glm_api_key() -> Optional[str]:
    """Get GLM API key"""
    return get_config().ai.glm_api_key


def get_jwt_secret() -> str:
    """Get JWT secret (generate if not set)"""
    secret = get_config().auth.jwt_secret
    if not secret:
        import secrets
        secret = secrets.token_hex(32)
        logger.warning("JWT_SECRET not set, using generated secret (not suitable for production)")
    return secret


def get_redis_url() -> str:
    """Get Redis URL"""
    return get_config().redis.url


def is_redis_enabled() -> bool:
    """Check if Redis is enabled"""
    return get_config().redis.enabled


def is_virtual_display() -> bool:
    """Check if virtual display should be used"""
    return get_config().kicad.use_virtual_display


def get_cors_origins() -> List[str]:
    """Get allowed CORS origins"""
    return get_config().server.cors_origins


def get_server_port() -> int:
    """Get server port"""
    return get_config().server.port


def get_server_host() -> str:
    """Get server host"""
    return get_config().server.host

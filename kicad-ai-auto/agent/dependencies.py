"""
共享依赖模块
提供 JWT 认证、数据库连接等跨路由共享的依赖项
"""

import os
import sqlite3
import jwt
import logging
from typing import Optional
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# JWT 配置（与 auth_routes.py 保持一致）
_JWT_SECRET: Optional[str] = None
_JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """延迟加载 JWT_SECRET，避免模块导入时循环依赖"""
    global _JWT_SECRET
    if _JWT_SECRET is None:
        _JWT_SECRET = os.getenv("JWT_SECRET")
        if not _JWT_SECRET:
            # 尝试从 .env 文件加载
            from dotenv import load_dotenv

            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
            _JWT_SECRET = os.getenv("JWT_SECRET")
            if not _JWT_SECRET:
                raise RuntimeError(
                    "JWT_SECRET environment variable is not set. "
                    "Please set it in the .env file or environment."
                )
    return _JWT_SECRET


# 数据库路径
DB_PATH = Path(__file__).parent / "data" / "users.db"


class TokenPayload(BaseModel):
    """JWT payload 模型"""
    user_id: int
    email: str
    exp: Optional[int] = None
    iat: Optional[int] = None


def get_current_user(authorization: str = Header(None)) -> dict:
    """
    获取当前认证用户（共享版本）

    使用 jwt.decode() 进行正确的签名验证，防止身份冒充攻击。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[_JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的token")


def require_admin(user_info: dict = None) -> dict:
    """
    验证管理员权限

    在 get_current_user 之后调用，检查用户是否为管理员。
    可以作为 Depends 依赖使用，或在 get_current_user 之后直接调用。
    """
    if not user_info:
        raise HTTPException(status_code=401, detail="无效的认证")

    user_id = user_info.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的认证")

    # 从数据库查询用户的 is_admin 状态
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return user_info

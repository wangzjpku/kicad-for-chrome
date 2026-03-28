"""
用户认证路由 - JWT 认证
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, field_validator
from models.user import (
    init_db,
    create_user,
    verify_user,
    get_user_by_id,
    get_user_by_email,
    update_user_test_mode,
)

# 初始化数据库
init_db()

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required. Please set it before starting the server.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

router = APIRouter(prefix="/api/auth", tags=["认证"])


def create_token(user_id: int, email: str) -> str:
    """创建JWT token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """验证JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")


# ========== 请求模型 ==========


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str
    user: dict


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    token_balance: int
    is_test_mode: bool
    is_admin: bool
    created_at: str


class UpdateTestModeRequest(BaseModel):
    is_test_mode: bool


# ========== 依赖项 ==========


async def get_current_user(authorization: Optional[str] = Header(None)):
    """获取当前登录用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")

    # Bearer token 格式
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="无效的认证格式")

    token = parts[1]
    payload = verify_token(token)
    user = get_user_by_id(payload["user_id"])

    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


async def get_optional_user(authorization: Optional[str] = Header(None)):
    """获取当前登录用户（可选，未登录返回None）"""
    if not authorization:
        return None

    # Bearer token 格式
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    try:
        payload = verify_token(token)
        user = get_user_by_id(payload["user_id"])
        return user
    except Exception:
        return None


async def get_current_admin(current_user: dict = Depends(get_current_user)):
    """获取当前管理员用户"""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ========== 路由 ==========


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        user = create_user(request.email, request.password, request.username)
        token = create_token(user["id"], user["email"])

        # 获取完整用户信息
        full_user = get_user_by_id(user["id"])

        return LoginResponse(
            success=True,
            token=token,
            user={
                "id": full_user["id"],
                "email": full_user["email"],
                "username": full_user["username"],
                "token_balance": full_user["token_balance"],
                "is_test_mode": full_user["is_test_mode"],
                "is_admin": full_user["is_admin"],
                "created_at": full_user["created_at"]
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    user = verify_user(request.email, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = create_token(user["id"], user["email"])

    return LoginResponse(
        success=True,
        token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "token_balance": user["token_balance"],
            "is_test_mode": user["is_test_mode"],
            "is_admin": user["is_admin"],
            "created_at": user["created_at"]
        }
    )


@router.get("/profile", response_model=UserInfo)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfo(
        id=current_user["id"],
        email=current_user["email"],
        username=current_user["username"],
        token_balance=current_user["token_balance"],
        is_test_mode=current_user["is_test_mode"],
        is_admin=current_user["is_admin"],
        created_at=current_user["created_at"]
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出（前端删除token即可）"""
    return {"success": True, "message": "已登出"}


@router.put("/test-mode")
async def set_test_mode(
    request: UpdateTestModeRequest,
    current_user: dict = Depends(get_current_admin)
):
    """管理员设置用户测试模式"""
    # 这里简化处理，实际应该传用户ID
    update_user_test_mode(current_user["id"], request.is_test_mode)
    return {"success": True, "is_test_mode": request.is_test_mode}

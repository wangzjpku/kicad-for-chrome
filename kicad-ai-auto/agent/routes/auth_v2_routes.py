"""
Phase 12B-1: JWT Authentication API Routes

REST endpoints for user authentication:
- POST /register - Create account
- POST /login - Get access + refresh tokens
- POST /refresh - Rotate refresh token
- GET /me - Get current user info
- PUT /me/password - Change password
- GET /users - List users (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional

from services.auth_service import get_auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---- Models ----

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "editor"

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ---- Auth dependency ----

def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency to extract current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization[7:]
    auth = get_auth_service()
    payload = auth.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---- Endpoints ----

@router.post("/register", summary="Register a new user")
async def register(req: RegisterRequest):
    auth = get_auth_service()
    result = auth.register(
        username=req.username,
        email=req.email,
        password=req.password,
        role=req.role,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/login", summary="Login and get tokens")
async def login(req: LoginRequest):
    auth = get_auth_service()
    result = auth.login(username=req.username, password=req.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.post("/refresh", summary="Refresh access token")
async def refresh(req: RefreshRequest):
    auth = get_auth_service()
    result = auth.refresh_token(req.refresh_token)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.get("/me", summary="Get current user info")
async def get_me(user: dict = Depends(get_current_user)):
    auth = get_auth_service()
    user_info = auth.get_user(user["user_id"])
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")
    return user_info


@router.put("/me/password", summary="Change password")
async def change_password(
    req: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    auth = get_auth_service()
    result = auth.change_password(
        user_id=user["user_id"],
        old_password=req.old_password,
        new_password=req.new_password,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/users", summary="List all users (admin only)")
async def list_users(admin: dict = Depends(require_admin)):
    auth = get_auth_service()
    return {"users": auth.list_users()}


@router.put("/users/{user_id}", summary="Update user (admin only)")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: dict = Depends(require_admin),
):
    auth = get_auth_service()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = auth.update_user(user_id, **updates)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/users/{user_id}", summary="Delete user (admin only)")
async def delete_user(
    user_id: str,
    admin: dict = Depends(require_admin),
):
    auth = get_auth_service()
    result = auth.delete_user(user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

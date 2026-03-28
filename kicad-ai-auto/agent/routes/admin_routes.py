"""
Admin管理API - 用户/Token/运营管理
"""

import sqlite3
import logging
import json
logger = logging.getLogger(__name__)
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pathlib import Path

from dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])

DB_PATH = Path(__file__).parent.parent / "data" / "users.db"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    token_balance: int
    is_admin: int
    is_test_mode: int
    created_at: str


class TokenUpdateRequest(BaseModel):
    user_id: int
    amount: int


class UserUpdateRequest(BaseModel):
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    is_admin: Optional[bool] = None


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(user_info: dict = Depends(require_admin)):
    """获取所有用户列表"""

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, token_balance, is_admin, is_test_mode, created_at
        FROM users ORDER BY id DESC
    """)

    users = cursor.fetchall()
    conn.close()
    return [UserResponse(**dict(u)) for u in users]


@router.post("/user/token")
async def update_user_token(request: TokenUpdateRequest, user_info: dict = Depends(require_admin)):
    """修改用户Token余额"""

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT token_balance FROM users WHERE id = ?", (request.user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    new_balance = row[0] + request.amount
    if new_balance < 0:
        conn.close()
        raise HTTPException(status_code=400, detail="余额不足")

    cursor.execute("UPDATE users SET token_balance = ? WHERE id = ?", (new_balance, request.user_id))
    conn.commit()
    conn.close()

    return {"success": True, "user_id": request.user_id, "old_balance": row[0], "new_balance": new_balance}


@router.post("/user/update")
async def update_user(request: UserUpdateRequest, user_info: dict = Depends(require_admin)):
    """更新用户信息"""

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (request.user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    updates = []
    params = []
    if request.username:
        updates.append("username = ?")
        params.append(request.username)
    if request.email:
        updates.append("email = ?")
        params.append(request.email)
    if request.is_admin is not None:
        updates.append("is_admin = ?")
        params.append(1 if request.is_admin else 0)

    if updates:
        params.append(request.user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()
    return {"success": True, "message": "用户信息已更新"}


@router.post("/user/delete/{user_id}")
async def delete_user(user_id: int, user_info: dict = Depends(require_admin)):
    """删除用户"""

    if user_id == user_info.get("user_id"):
        raise HTTPException(status_code=400, detail="不能删除自己的账户")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"success": True, "message": "用户已删除"}


@router.get("/stats")
async def get_stats(user_info: dict = Depends(require_admin)):
    """获取运营统计数据"""

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), SUM(token_balance) FROM users")
    user_row = cursor.fetchone()

    cursor.execute("SELECT SUM(token_count) FROM token_logs")
    consumed_row = cursor.fetchone()

    cursor.execute("SELECT SUM(token_count) FROM token_logs WHERE date(created_at) = date('now')")
    today_row = cursor.fetchone()

    projects_file = Path(__file__).parent.parent / "projects_data.json"
    project_count = 0
    if projects_file.exists():
        import json
        try:
            with open(projects_file, encoding='utf-8') as f:
                projects = json.load(f)
                project_count = len(projects) if isinstance(projects, dict) else 0
        except Exception as e:
            project_count = 0

    conn.close()

    return {
        "users": {"total": user_row[0] or 0, "total_tokens": user_row[1] or 0},
        "tokens": {"total_consumed": consumed_row[0] or 0, "today_consumed": today_row[0] or 0},
        "projects": {"total": project_count}
    }

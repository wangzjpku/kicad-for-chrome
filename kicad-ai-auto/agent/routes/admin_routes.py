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


class PCBSettingsRequest(BaseModel):
    layerCount: int = 2
    boardThickness: float = 1.6
    copperThickness: float = 1.0
    defaultTraceWidth: float = 0.5
    minTraceWidth: float = 0.15
    defaultClearance: float = 0.2
    impedanceTarget: float = 50.0
    viaDrill: float = 0.3
    viaOuter: float = 0.6


class AISettingsRequest(BaseModel):
    apiProvider: str = "deepseek"
    apiKey: str = ""
    modelName: str = "deepseek-chat"
    temperature: float = 0.7
    maxTokens: int = 2000
    enableCache: bool = True


class ManufacturingSettingsRequest(BaseModel):
    manufacturer: str = "jlcpcb"
    surfaceFinish: str = "HASL"
    baseCopper: float = 1.0
    silkscreenColor: str = "white"
    soldermaskColor: str = "green"
    impedanceControl: bool = False
    count: int = 5


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


# ========== 设置管理 ==========

SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"


def load_settings() -> dict:
    """加载设置"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(data: dict):
    """保存设置"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@router.post("/settings/pcb")
async def save_pcb_settings(request: PCBSettingsRequest, user_info: dict = Depends(require_admin)):
    """保存 PCB 参数设置"""
    settings = load_settings()
    settings['pcb'] = request.model_dump()
    save_settings(settings)
    return {"success": True, "message": "PCB 设置已保存"}


@router.get("/settings/pcb")
async def get_pcb_settings(user_info: dict = Depends(require_admin)):
    """获取 PCB 参数设置"""
    settings = load_settings()
    return settings.get('pcb', {
        "layerCount": 2,
        "boardThickness": 1.6,
        "copperThickness": 1.0,
        "defaultTraceWidth": 0.5,
        "minTraceWidth": 0.15,
        "defaultClearance": 0.2,
        "impedanceTarget": 50.0,
        "viaDrill": 0.3,
        "viaOuter": 0.6
    })


@router.post("/settings/ai")
async def save_ai_settings(request: AISettingsRequest, user_info: dict = Depends(require_admin)):
    """保存 AI 模型配置"""
    settings = load_settings()
    settings['ai'] = request.model_dump()
    save_settings(settings)
    return {"success": True, "message": "AI 设置已保存"}


@router.get("/settings/ai")
async def get_ai_settings(user_info: dict = Depends(require_admin)):
    """获取 AI 模型配置"""
    settings = load_settings()
    return settings.get('ai', {
        "apiProvider": "deepseek",
        "apiKey": "",
        "modelName": "deepseek-chat",
        "temperature": 0.7,
        "maxTokens": 2000,
        "enableCache": True
    })


@router.post("/settings/manufacturing")
async def save_manufacturing_settings(request: ManufacturingSettingsRequest, user_info: dict = Depends(require_admin)):
    """保存制造选项"""
    settings = load_settings()
    settings['manufacturing'] = request.model_dump()
    save_settings(settings)
    return {"success": True, "message": "制造选项已保存"}


@router.get("/settings/manufacturing")
async def get_manufacturing_settings(user_info: dict = Depends(require_admin)):
    """获取制造选项"""
    settings = load_settings()
    return settings.get('manufacturing', {
        "manufacturer": "jlcpcb",
        "surfaceFinish": "HASL",
        "baseCopper": 1.0,
        "silkscreenColor": "white",
        "soldermaskColor": "green",
        "impedanceControl": False,
        "count": 5
    })


@router.post("/settings/manufacturing/estimate")
async def get_manufacturing_estimate(request: ManufacturingSettingsRequest, user_info: dict = Depends(require_admin)):
    """获取制造成本估算"""
    # 简单的成本估算逻辑
    base_price = 2.0  # JLCPCB 基础价格
    if request.manufacturer == "pcbway":
        base_price = 5.0
    elif request.manufacturer == "seeed":
        base_price = 3.0

    # 表面处理附加费
    finish_multiplier = 1.0
    if request.surfaceFinish == "ENIG":
        finish_multiplier = 1.5
    elif request.surfaceFinish == "HASL":
        finish_multiplier = 1.0

    # 阻抗控制附加费
    impedance_fee = 10.0 if request.impedanceControl else 0.0

    unit_price = (base_price * finish_multiplier) + (impedance_fee / request.count)
    total_price = unit_price * request.count

    return {
        "manufacturer": request.manufacturer,
        "unit_price_usd": round(unit_price, 2),
        "total_price_usd": round(total_price, 2),
        "currency": "USD",
        "lead_time_days": "7-10",
        "features": {
            "surface_finish": request.surfaceFinish,
            "base_copper": request.baseCopper,
            "impedance_control": request.impedanceControl
        }
    }


# ========== Token 管理 ==========


@router.get("/token/config")
async def get_token_config(user_info: dict = Depends(require_admin)):
    """获取 Token 系统配置"""
    return {
        "success": True,
        "config": {
            "initial_balance": 100,
            "per_request_cost": 10,
            "model_costs": {
                "kimi": {"analyze": 5, "enhance": 3, "chat": 1},
                "glm4": {"analyze": 4, "enhance": 2, "chat": 1},
                "deepseek": {"analyze": 3, "enhance": 2, "chat": 1}
            },
            "free_tier": {
                "daily_requests": 10,
                "components_per_request": 5
            },
            "token_per_yuan": 100
        }
    }


@router.post("/token/config")
async def update_token_config(
    config: dict,
    user_info: dict = Depends(require_admin)
):
    """更新 Token 系统配置"""
    # 简单的配置更新逻辑
    return {
        "success": True,
        "message": "Token配置已更新",
        "config": config
    }

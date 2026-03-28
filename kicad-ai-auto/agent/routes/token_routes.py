"""
Token 管理路由
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models.user import (
    get_token_balance,
    get_token_logs,
    add_topup,
    get_all_admin_configs,
    get_admin_config,
    set_admin_config,
)
from routes.auth_routes import get_current_user, get_current_admin

router = APIRouter(prefix="/api/token", tags=["Token管理"])


# ========== 请求/响应模型 ==========


class TokenBalanceResponse(BaseModel):
    balance: int
    is_test_mode: bool


class TokenLogResponse(BaseModel):
    id: int
    action_type: str
    token_count: int
    model_used: str
    is_test: bool
    created_at: str


class TopupRequest(BaseModel):
    amount: int
    payment_method: str = "manual"


class TopupResponse(BaseModel):
    success: bool
    new_balance: int
    topup_id: int


class AdminConfigResponse(BaseModel):
    virtual_model_name: str
    default_model: str
    token_ai_generate: str
    token_ai_chat: str
    token_schematic_analyze: str
    model_deepseek_cost: str
    model_kimi_cost: str


class AdminConfigUpdate(BaseModel):
    config_key: str
    config_value: str


# ========== 路由 ==========


@router.get("/balance", response_model=TokenBalanceResponse)
async def get_balance(current_user: dict = Depends(get_current_user)):
    """获取Token余额"""
    balance = get_token_balance(current_user["id"])
    return TokenBalanceResponse(
        balance=balance,
        is_test_mode=current_user.get("is_test_mode", False)
    )


@router.get("/logs", response_model=List[TokenLogResponse])
async def get_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """获取Token消耗记录"""
    logs = get_token_logs(current_user["id"], limit)
    return [TokenLogResponse(**log) for log in logs]


@router.post("/topup", response_model=TopupResponse)
async def topup(
    request: TopupRequest,
    current_user: dict = Depends(get_current_user)
):
    """充值Token（预留接口）"""
    # 预留充值接口，实际支付接入后实现
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="充值数量必须大于0")

    topup_id = add_topup(current_user["id"], request.amount, request.payment_method)
    new_balance = get_token_balance(current_user["id"])

    return TopupResponse(
        success=True,
        new_balance=new_balance,
        topup_id=topup_id
    )


# ========== 管理员接口 ==========


@router.get("/admin/config", response_model=AdminConfigResponse)
async def get_config(current_user: dict = Depends(get_current_admin)):
    """获取管理员配置"""
    configs = get_all_admin_configs()
    return AdminConfigResponse(
        virtual_model_name=configs.get("virtual_model_name", "DeepEDA大模型"),
        default_model=configs.get("default_model", "deepseek"),
        token_ai_generate=configs.get("token_ai_generate", "800"),
        token_ai_chat=configs.get("token_ai_chat", "500"),
        token_schematic_analyze=configs.get("token_schematic_analyze", "600"),
        model_deepseek_cost=configs.get("model_deepseek_cost", "800"),
        model_kimi_cost=configs.get("model_kimi_cost", "1000"),
    )


@router.put("/admin/config")
async def update_config(
    request: AdminConfigUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """更新管理员配置"""
    allowed_keys = [
        "virtual_model_name",
        "default_model",
        "token_ai_generate",
        "token_ai_chat",
        "token_schematic_analyze",
        "model_deepseek_cost",
        "model_kimi_cost",
    ]

    if request.config_key not in allowed_keys:
        raise HTTPException(status_code=400, detail="无效的配置键")

    set_admin_config(request.config_key, request.config_value)
    return {"success": True, "config_key": request.config_key, "config_value": request.config_value}


def get_model_cost(action_type: str) -> tuple[int, str]:
    """
    获取指定操作的Token消耗和实际模型
    返回: (虚拟Token消耗, 实际使用的模型名)
    """
    # 获取当前配置的默认模型
    model = get_admin_config("default_model") or "deepseek"

    # 获取各操作的Token消耗（虚拟）
    token_map = {
        "ai_generate": "token_ai_generate",
        "ai_chat": "token_ai_chat",
        "schematic_analyze": "token_schematic_analyze",
    }

    # 获取各模型的真实消耗
    cost_map = {
        "deepseek": int(get_admin_config("model_deepseek_cost") or "800"),
        "kimi": int(get_admin_config("model_kimi_cost") or "1000"),
    }

    token_key = token_map.get(action_type, "token_ai_generate")
    virtual_cost = int(get_admin_config(token_key) or "800")
    real_cost = cost_map.get(model, 800)

    return virtual_cost, model, real_cost

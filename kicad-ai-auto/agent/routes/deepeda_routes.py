"""
DeepEDA 虚拟大模型路由 - 统一入口
整合现有 AI 逻辑，封装为虚拟模型
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models.user import deduct_token, get_admin_config
from routes.auth_routes import get_current_user, get_optional_user
from routes.token_routes import get_model_cost
from deepseek_client import get_deepseek_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deepeda", tags=["DeepEDA大模型"])


# ========== 请求模型 ==========


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    model: str  # 显示为虚拟模型名
    token_used: int
    remaining_balance: int


class GeneratePCBRequest(BaseModel):
    requirements: str
    options: Optional[Dict[str, Any]] = None


class GenerateResponse(BaseModel):
    success: bool
    project_path: str
    message: str
    model: str
    token_used: int
    remaining_balance: int


# 获取虚拟模型名称
def get_virtual_model_name() -> str:
    return get_admin_config("virtual_model_name") or "DeepEDA大模型"


# ========== 路由 ==========


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """DeepEDA 大模型对话"""
    # 获取Token消耗
    virtual_cost, model, real_cost = get_model_cost("ai_chat")

    # 检查并扣除Token
    is_test = current_user.get("is_test_mode", False)
    success = deduct_token(
        current_user["id"],
        "ai_chat",
        virtual_cost,
        model,
        is_test
    )

    if not success:
        raise HTTPException(status_code=402, detail="Token余额不足")

    # 获取虚拟模型名称
    virtual_name = get_virtual_model_name()

    # 调用实际的 DeepSeek AI
    try:
        deepseek = get_deepseek_client()
        result = deepseek.chat(
            message=request.message,
            history=request.history
        )
        response_text = result["content"]
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        response_text = f"[{virtual_name}] AI服务暂时不可用，请稍后再试。"

    # 计算剩余余额
    from models.user import get_token_balance
    remaining = get_token_balance(current_user["id"])

    return ChatResponse(
        success=True,
        response=response_text,
        model=virtual_name,
        token_used=virtual_cost,
        remaining_balance=remaining
    )


@router.post("/generate-pcb", response_model=GenerateResponse)
async def generate_pcb(
    request: GeneratePCBRequest,
    current_user: dict = Depends(get_current_user)
):
    """DeepEDA AI 生成 PCB"""
    # 获取Token消耗
    virtual_cost, model, real_cost = get_model_cost("ai_generate")

    # 检查并扣除Token
    is_test = current_user.get("is_test_mode", False)
    success = deduct_token(
        current_user["id"],
        "ai_generate",
        virtual_cost,
        model,
        is_test
    )

    if not success:
        raise HTTPException(status_code=402, detail="Token余额不足")

    # 获取虚拟模型名称
    virtual_name = get_virtual_model_name()

    # 构建项目输出路径
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = request.options.get("project_name", f"deepeda_pcb_{timestamp}") if request.options else f"deepeda_pcb_{timestamp}"
    projects_dir = os.environ.get("PROJECTS_DIR", "/projects")
    project_path = os.path.join(projects_dir, project_name)

    # 获取 PCB 参数
    pcb_params = request.options.get("pcb_params", {}) if request.options else {}
    schematic_data = request.options.get("schematic", None) if request.options else None

    try:
        # 调用实际的 AI 分析和生成逻辑
        from routes.ai_routes import analyze_requirements, AnalyzeRequest

        # 构建分析请求
        analyze_req = AnalyzeRequest(
            requirements=request.requirements,
            answers=request.options.get("answers") if request.options else None,
            mode="full" if not schematic_data else "schematic_only",
            pcb_params=pcb_params,
            schematic=schematic_data,
        )

        # 调用生成
        result = await analyze_requirements(analyze_req)

        # 创建项目目录并保存
        os.makedirs(project_path, exist_ok=True)

        # 保存生成结果
        if result.schematic:
            from routes.project_routes import _save_schematic_data
            # 使用生成的project id或创建临时id
            project_id = request.options.get("project_id", f"deepeda_{timestamp}") if request.options else f"deepeda_{timestamp}"
            schematic_save_path = os.path.join(project_path, "schematic_data.json")
            with open(schematic_save_path, "w", encoding="utf-8") as f:
                import json
                json.dump(result.schematic.model_dump(), f, ensure_ascii=False, indent=2)

        if result.pcb:
            pcb_save_path = os.path.join(project_path, "pcb_data.json")
            with open(pcb_save_path, "w", encoding="utf-8") as f:
                import json
                json.dump(result.pcb, f, ensure_ascii=False, indent=2)

        response_text = f"[{virtual_name}] PCB项目已生成: {project_name}"

    except Exception as e:
        logger.error(f"PCB生成失败: {e}")
        response_text = f"[{virtual_name}] 生成失败: {str(e)}"

    # 计算剩余余额
    from models.user import get_token_balance
    remaining = get_token_balance(current_user["id"])

    return GenerateResponse(
        success=True,
        project_path=project_path,
        message=response_text,
        model=virtual_name,
        token_used=virtual_cost,
        remaining_balance=remaining
    )


@router.get("/model-info")
async def get_model_info(current_user: dict = Depends(get_optional_user)):
    """获取当前模型信息（无需认证）"""
    _, model, real_cost = get_model_cost("ai_chat")
    virtual_name = get_virtual_model_name()

    # 如果未认证，返回默认值
    if not current_user:
        return {
            "virtual_model": virtual_name,
            "actual_model": model,
            "model_cost": real_cost,
            "token_balance": 0,
            "is_test_mode": True
        }

    from models.user import get_token_balance
    balance = get_token_balance(current_user["id"])

    return {
        "virtual_model": virtual_name,
        "actual_model": model,
        "model_cost": real_cost,
        "token_balance": balance,
        "is_test_mode": current_user.get("is_test_mode", False)
    }

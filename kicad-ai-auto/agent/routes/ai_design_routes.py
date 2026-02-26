"""
AI 设计循环 API 端点
提供完整的 AI 电路设计-验证-修复 API
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path

# 使用绝对导入避免相对导入问题
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generators.factory import get_schematic_generator, generate_schematic
from validators import validate_schematic
from loops.design_loop import AICircuitDesigner, LoopConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/design", tags=["AI Design"])

# 全局设计器实例（简化版）
_designer = None


class DesignRequest(BaseModel):
    """AI 设计请求"""

    requirements: str
    project_name: str = "ai_circuit"
    generator_version: str = "v2"
    max_iterations: int = 3
    auto_fix: bool = True
    validate: bool = True


class DesignResponse(BaseModel):
    """AI 设计响应"""

    success: bool
    message: str
    output_path: Optional[str] = None
    iterations: int = 0
    erc_result: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []


class GenerateAndValidateRequest(BaseModel):
    """生成并验证请求"""

    json_data: Dict[str, Any]
    output_path: str
    generator_version: str = "v2"
    validate: bool = True
    auto_fix: bool = False
    max_fix_iterations: int = 2


class ValidateRequest(BaseModel):
    """验证请求"""

    schematic_path: str


@router.post("/", response_model=DesignResponse)
async def design_circuit(request: DesignRequest):
    """
    AI 完整设计流程：需求 → 设计 → 验证 → 修复

    这是一个完整的闭环设计接口:
    1. 分析用户需求生成电路 JSON
    2. 生成 KiCad 原理图
    3. 运行 ERC 验证
    4. 如果有错误，自动使用 LLM 修复
    5. 重复直到通过或达到最大迭代
    """

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_path = str(output_dir / f"{request.project_name}.kicad_sch")

    try:
        # 获取生成器
        generator = get_schematic_generator(request.generator_version)

        # 创建设计循环配置
        config = LoopConfig(
            max_iterations=request.max_iterations,
            auto_fix=request.auto_fix,
            validate_after_generate=request.validate,
        )

        # 创建简化的设计器
        designer = AICircuitDesigner(config=config)

        # 运行设计流程
        result = designer.design(
            requirements=request.requirements, output_path=output_path
        )

        return DesignResponse(
            success=result.success,
            message=result.message,
            output_path=result.output_path if result.success else None,
            iterations=result.iterations,
            erc_result=result.erc_result,
            errors=result.errors,
            warnings=result.warnings,
        )

    except Exception as e:
        logger.error(f"AI 设计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-validate")
async def generate_and_validate(request: GenerateAndValidateRequest):
    """
    生成并验证原理图

    支持自动修复（可选）:
    - 生成原理图
    - 运行 ERC 验证
    - 如果有错误且 auto_fix=True，尝试修复并重新生成
    """

    try:
        # 第一次生成
        result = generate_schematic(
            json_data=request.json_data,
            output_path=request.output_path,
            version=request.generator_version,
            validate=False,  # 手动验证以便控制修复流程
        )

        if not result.success:
            return {"success": False, "stage": "generation", "errors": result.errors}

        # 验证
        erc_result = None
        if request.validate:
            erc_result = validate_schematic(request.output_path)

            # 自动修复（如果需要且启用）
            if (
                request.auto_fix
                and erc_result.get("has_errors", False)
                and request.max_fix_iterations > 0
            ):
                # TODO: 实现自动修复逻辑
                logger.info("自动修复功能待实现")

        return {
            "success": result.success,
            "output_path": result.output_path,
            "erc_result": erc_result,
            "iterations": 1,
        }

    except Exception as e:
        logger.error(f"生成验证失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_schematic_endpoint(request: ValidateRequest):
    """
    验证原理图

    使用 ERC 检查原理图错误
    """

    try:
        result = validate_schematic(request.schematic_path)

        return result

    except Exception as e:
        logger.error(f"验证失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """获取 AI 设计系统状态"""

    from generators.schematic_v2 import is_v2_available

    return {
        "v2_available": is_v2_available(),
        "generators": ["v1", "v2"] if is_v2_available() else ["v1"],
        "validators": ["cli", "sch_api"] if is_v2_available() else ["cli"],
    }


__all__ = ["router"]

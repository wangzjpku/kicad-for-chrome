"""
设计审查 API 路由

Phase 10: 实时设计审查 + AI 学习

Author: Claude Code
Date: 2026-03-31
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from drc.design_review import get_review_engine, ReviewCategory, ReviewSeverity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/review", tags=["Design Review"])


class ReviewRequest(BaseModel):
    """设计审查请求"""
    pcb_data: Dict[str, Any] = Field(..., description="PCB 数据")
    include_suggestions: bool = Field(True, description="是否包含建议")


class CorrectionRequest(BaseModel):
    """用户修正记录"""
    rule_id: str = Field(..., description="规则 ID")
    action: str = Field(..., description="用户行为: accepted | dismissed | modified")
    details: str = Field("", description="详细说明")


@router.post("/run")
async def run_review(request: ReviewRequest):
    """
    执行实时设计审查

    多维度检查:
    - 设计规则 (DRC)
    - 电源完整性 (PI)
    - 信号完整性 (SI)
    - 可制造性 (DFM)
    - 热管理
    - EMI
    """
    try:
        engine = get_review_engine()
        result = engine.review(request.pcb_data)

        return {
            "success": True,
            "score": result.score,
            "issues": [
                {
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "title": issue.title,
                    "description": issue.description,
                    "location": issue.location,
                    "suggestion": issue.suggestion if request.include_suggestions else "",
                    "rule_id": issue.rule_id,
                }
                for issue in result.issues
            ],
            "summary": result.summary,
            "duration_s": result.duration_s,
            "board_stats": result.board_stats,
        }

    except Exception as e:
        logger.error(f"Design review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correction")
async def record_correction(request: CorrectionRequest):
    """记录用户修正行为 (AI 学习)"""
    engine = get_review_engine()
    engine.record_correction(
        rule_id=request.rule_id,
        action=request.action,
        details=request.details,
    )
    return {"success": True, "message": f"Correction recorded: {request.rule_id} -> {request.action}"}


@router.get("/learning-stats")
async def get_learning_stats():
    """获取 AI 学习统计"""
    engine = get_review_engine()
    return {
        "success": True,
        **engine.get_learning_stats(),
    }


@router.get("/rules")
async def list_review_rules():
    """列出所有审查规则"""
    from drc.design_review import COMMON_MISTAKES

    rules = []
    for key, rule in COMMON_MISTAKES.items():
        rules.append({
            "rule_id": rule["rule_id"],
            "key": key,
            "title": rule["title"],
            "category": rule["category"].value,
            "severity": rule["severity"].value,
            "description": rule["description"],
        })

    return {
        "success": True,
        "rules": rules,
        "total": len(rules),
    }

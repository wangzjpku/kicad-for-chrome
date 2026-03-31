"""
多步设计 Agent API 路由

Phase 7E: 端到端设计自动化流水线 API

Author: Claude Code
Date: 2026-03-31
"""

import logging
import threading
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from loops.multi_step_agent import (
    MultiStepDesignAgent,
    get_task_progress,
    list_active_tasks,
    StepStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Design Agent"])


class DesignRequest(BaseModel):
    """设计请求"""
    requirements: str = Field(..., min_length=1, max_length=5000, description="自然语言需求描述")
    max_iterations: int = Field(3, ge=1, le=10, description="最大修复迭代次数")
    project_name: Optional[str] = Field(None, description="项目名称")


class DesignResponse(BaseModel):
    """设计响应"""
    success: bool
    task_id: str
    message: str


class ProgressResponse(BaseModel):
    """进度响应"""
    task_id: str
    current_step: str
    step_index: int
    total_steps: int
    progress_pct: float
    status: str
    intermediate_results: Dict[str, Any] = {}
    step_durations: Dict[str, float] = {}


class StepResultResponse(BaseModel):
    """步骤结果"""
    step_type: str
    status: str
    message: str
    duration_s: float = 0.0
    data: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []


class DesignResultResponse(BaseModel):
    """设计结果"""
    task_id: str
    success: bool
    steps: List[StepResultResponse]
    total_duration_s: float = 0.0
    iterations: int = 1
    error_message: str = ""
    schematic: Optional[Dict] = None
    pcb: Optional[Dict] = None
    drc_result: Optional[Dict] = None
    bom: Optional[List[Dict]] = None


# 线程存储: task_id -> result
_completed_results: Dict[str, Dict[str, Any]] = {}


@router.post("/design")
async def start_design(request: DesignRequest) -> DesignResponse:
    """
    启动多步设计流水线（异步执行）

    设计步骤: 需求分析 → 模板匹配 → 原理图生成 → ERC验证
    → 自动修复 → PCB布局 → PCB布线 → DRC检查 → 铺铜 → 最终验证
    """
    agent = MultiStepDesignAgent()

    def run_design():
        try:
            result = agent.design(
                requirements=request.requirements,
                max_iterations=request.max_iterations,
            )
            _completed_results[result.task_id] = {
                "task_id": result.task_id,
                "success": result.success,
                "steps": [
                    {
                        "step_type": s.step_type.value,
                        "status": s.status.value,
                        "message": s.message,
                        "duration_s": s.duration_s,
                        "data": s.data,
                        "errors": s.errors,
                        "warnings": s.warnings,
                    }
                    for s in result.steps
                ],
                "total_duration_s": result.total_duration_s,
                "iterations": result.iterations,
                "error_message": result.error_message,
                "schematic": result.schematic,
                "pcb": result.pcb,
                "drc_result": result.drc_result,
                "bom": result.bom,
            }
        except Exception as e:
            logger.error(f"Design task failed: {e}")
            # Store error result
            tid = getattr(agent, "_task_id", "unknown")
            _completed_results[tid] = {
                "task_id": tid,
                "success": False,
                "steps": [],
                "total_duration_s": 0,
                "iterations": 0,
                "error_message": str(e),
            }

    thread = threading.Thread(target=run_design, daemon=True)
    thread.start()

    # Wait briefly to get the task_id
    import time
    for _ in range(20):
        if agent._task_id:
            break
        time.sleep(0.05)

    return DesignResponse(
        success=True,
        task_id=agent._task_id or "pending",
        message=f"Design pipeline started with {request.max_iterations} max iterations",
    )


@router.get("/progress/{task_id}")
async def get_progress(task_id: str) -> ProgressResponse:
    """获取设计任务实时进度"""
    progress = get_task_progress(task_id)
    if not progress:
        # Check completed results
        if task_id in _completed_results:
            result = _completed_results[task_id]
            return ProgressResponse(
                task_id=task_id,
                current_step="completed",
                step_index=result.get("steps", []).__len__(),
                total_steps=10,
                progress_pct=100.0,
                status="completed" if result.get("success") else "failed",
                intermediate_results={},
                step_durations={},
            )
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return ProgressResponse(
        task_id=progress.task_id,
        current_step=progress.current_step,
        step_index=progress.step_index,
        total_steps=progress.total_steps,
        progress_pct=progress.progress_pct,
        status=progress.status.value,
        intermediate_results=progress.intermediate_results,
        step_durations=progress.step_durations,
    )


@router.get("/result/{task_id}")
async def get_result(task_id: str) -> DesignResultResponse:
    """获取设计最终结果"""
    if task_id not in _completed_results:
        # Still running?
        progress = get_task_progress(task_id)
        if progress:
            raise HTTPException(status_code=202, detail="Design still in progress")
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return DesignResultResponse(**_completed_results[task_id])


@router.get("/tasks")
async def list_tasks():
    """列出所有活跃和最近完成的任务"""
    active = []
    for p in list_active_tasks():
        active.append({
            "task_id": p.task_id,
            "current_step": p.current_step,
            "progress_pct": p.progress_pct,
            "status": p.status.value,
        })

    recent_completed = []
    for tid, result in list(_completed_results.items())[-10:]:
        recent_completed.append({
            "task_id": tid,
            "success": result.get("success", False),
            "total_duration_s": result.get("total_duration_s", 0),
        })

    return {
        "active": active,
        "recent_completed": recent_completed,
        "total_active": len(active),
    }


@router.post("/cancel/{task_id}")
async def cancel_design(task_id: str):
    """取消正在运行的设计任务"""
    progress = get_task_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Set cancelled flag via progress status
    progress.status = StepStatus.FAILED
    return {"success": True, "message": f"Task {task_id} cancelled"}

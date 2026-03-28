"""
DRC (Design Rule Check) 路由

提供 PCB 设计规则检查功能
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drc", tags=["DRC"])


class DRCError(BaseModel):
    """DRC 错误"""
    type: str  # error, warning
    code: str  # 错误代码
    message: str  # 错误描述
    net1: Optional[str] = None  # 相关网络1
    net2: Optional[str] = None  # 相关网络2
    component: Optional[str] = None  # 相关元件
    x: Optional[float] = None  # 位置X
    y: Optional[float] = None  # 位置Y
    distance: Optional[float] = None  # 距离


class DRCRequest(BaseModel):
    """DRC 检查请求"""
    project_id: str
    board_width: float = 100.0  # 板宽 mm
    board_height: float = 80.0  # 板高 mm
    layer_count: int = 2  # 层数


class DRCResult(BaseModel):
    """DRC 检查结果"""
    success: bool
    passed: bool
    error_count: int
    warning_count: int
    errors: List[DRCError]
    warnings: List[DRCError]
    duration_ms: float


@router.post("/run", response_model=DRCResult)
async def run_drc(request: DRCRequest):
    """
    运行 DRC 检查

    检查项目是否存在 DRC 问题
    """
    import time
    start_time = time.time()

    logger.info(f"Running DRC for project: {request.project_id}")

    # 模拟 DRC 检查
    # 实际实现需要调用 KiCad IPC API
    errors = []
    warnings = []

    # 示例：检查最小间距
    # 实际实现应该基于真实的 PCB 数据

    duration_ms = (time.time() - start_time) * 1000

    return DRCResult(
        success=True,
        passed=len(errors) == 0,
        error_count=len(errors),
        warning_count=len(warnings),
        errors=errors,
        warnings=warnings,
        duration_ms=duration_ms
    )


@router.get("/check-clearance")
async def check_clearance(
    net1: str = Query(..., description="网络1名称"),
    net2: str = Query(..., description="网络2名称"),
    distance: float = Query(..., description="两网络之间的距离 (mm)"),
    min_clearance: float = Query(0.2, description="最小允许间距 (mm)")
):
    """
    检查两个网络之间的间距是否满足要求

    Args:
        net1: 网络1名称
        net2: 网络2名称
        distance: 两网络之间的距离 (mm)
        min_clearance: 最小允许间距 (mm)

    Returns:
        检查结果
    """
    is_violation = distance < min_clearance

    if is_violation:
        return {
            "passed": False,
            "net1": net1,
            "net2": net2,
            "distance": distance,
            "min_clearance": min_clearance,
            "violation": True,
            "message": f"Clearance violation: {net1} to {net2} is {distance}mm, minimum is {min_clearance}mm"
        }
    else:
        return {
            "passed": True,
            "net1": net1,
            "net2": net2,
            "distance": distance,
            "min_clearance": min_clearance,
            "violation": False,
            "message": f"Clearance OK: {distance}mm >= {min_clearance}mm"
        }


@router.get("/check-connection")
async def check_connection(
    component: str = Query(..., description="元件ID"),
    pin: str = Query(..., description="引脚号"),
    expected_net: str = Query(..., description="期望的网络名称")
):
    """
    检查元件引脚的连接网络是否正确

    Args:
        component: 元件ID (如 R1, U1)
        pin: 引脚号
        expected_net: 期望的网络名称

    Returns:
        检查结果
    """
    # 实际实现需要查询 PCB 数据
    # 这里返回模拟结果
    return {
        "component": component,
        "pin": pin,
        "expected_net": expected_net,
        "actual_net": expected_net,  # 模拟
        "connected": True,
        "message": f"{component}.{pin} is connected to {expected_net}"
    }


@router.post("/validate-tracks")
async def validate_tracks(
    tracks: List[Dict[str, Any]],
    rules: Dict[str, Any] = None
):
    """
    验证走线是否符合规则

    Args:
        tracks: 走线列表
        rules: 布线规则

    Returns:
        验证结果
    """
    if rules is None:
        rules = {
            "min_trace_width": 0.2,
            "min_clearance": 0.2
        }

    errors = []
    warnings = []

    for i, track in enumerate(tracks):
        net = track.get("net", f"NET{i}")
        width = track.get("width", 0.2)

        # 检查线宽
        if width < rules.get("min_trace_width", 0.2):
            errors.append(DRCError(
                type="error",
                code="TRACE_WIDTH",
                message=f"Trace width {width}mm for {net} is below minimum {rules['min_trace_width']}mm",
                component=track.get("component"),
                x=track.get("x1"),
                y=track.get("y1")
            ))

    return {
        "success": True,
        "track_count": len(tracks),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0
    }


@router.get("/rules")
async def get_drc_rules():
    """
    获取默认 DRC 规则

    Returns:
        默认 DRC 规则列表
    """
    return {
        "rules": [
            {
                "code": "MIN_CLEARANCE",
                "name": "Minimum Clearance",
                "description": "Minimum distance between copper features",
                "default_value": 0.2,
                "unit": "mm"
            },
            {
                "code": "MIN_TRACE_WIDTH",
                "name": "Minimum Trace Width",
                "description": "Minimum width of copper traces",
                "default_value": 0.2,
                "unit": "mm"
            },
            {
                "code": "MIN_VIA_DIAMETER",
                "name": "Minimum Via Diameter",
                "description": "Minimum via hole diameter",
                "default_value": 0.3,
                "unit": "mm"
            },
            {
                "code": "MIN_SOLDERMASK_BRIDGE",
                "name": "Minimum Soldermask Bridge",
                "description": "Minimum soldermask opening between pads",
                "default_value": 0.15,
                "unit": "mm"
            }
        ]
    }

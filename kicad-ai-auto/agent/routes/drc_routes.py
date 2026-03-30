"""
DRC (Design Rule Check) 路由

提供 PCB 设计规则检查功能
Phase 3: 扩展至30+条规则，支持网络类和制造约束
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drc", tags=["DRC"])

# 导入高级DRC引擎
try:
    from drc.advanced_drc import (
        AdvancedDRCEngine,
        create_jlcpcb_drc,
        create_pcbway_drc,
        RuleType,
        RuleSeverity,
    )
    ADVANCED_DRC_AVAILABLE = True
except ImportError:
    ADVANCED_DRC_AVAILABLE = False
    logger.warning("Advanced DRC engine not available")



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


# ========== Phase 3: 高级DRC API ==========

class AdvancedDRCRequest(BaseModel):
    """高级DRC检查请求"""
    project_id: str
    pcb_data: Dict[str, Any] = Field(default_factory=dict)
    manufacturer: str = "jlcpcb"  # jlcpcb, pcbway
    level: str = "standard"       # standard, advanced
    check_types: List[str] = Field(default_factory=lambda: [
        "clearance", "track_width", "via_size", "manufacturing"
    ])


class AdvancedDRCResponse(BaseModel):
    """高级DRC检查响应"""
    success: bool
    passed: bool
    error_count: int
    warning_count: int
    info_count: int
    violations: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    duration_ms: float


@router.post("/advanced-check", response_model=AdvancedDRCResponse)
async def run_advanced_drc(request: AdvancedDRCRequest):
    """
    运行高级DRC检查 (Phase 3)

    支持30+条规则，包括：
    - 间距规则 (track-to-track, via-to-pad, etc.)
    - 尺寸规则 (min width, via size, annular ring)
    - 网络类规则 (Power, Signal, HighSpeed)
    - 差分对规则
    - 制造约束 (JLCPCB/PCBWay标准)
    - 高速信号规则

    Args:
        request: DRC检查请求

    Returns:
        详细检查结果
    """
    if not ADVANCED_DRC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Advanced DRC engine not available"
        )

    try:
        # 创建DRC引擎
        if request.manufacturer == "jlcpcb":
            engine = create_jlcpcb_drc(level=request.level)
        elif request.manufacturer == "pcbway":
            engine = create_pcbway_drc(level=request.level)
        else:
            engine = AdvancedDRCEngine(
                manufacturer=request.manufacturer,
                level=request.level
            )

        # 准备PCB数据
        pcb_data = request.pcb_data
        if not pcb_data:
            # 从项目加载PCB数据
            pcb_data = await _load_pcb_data(request.project_id)

        # 运行检查
        result = engine.check(pcb_data)

        # 转换违规项为字典
        violations = []
        for v in result.violations:
            violations.append({
                "rule_name": v.rule_name,
                "rule_type": v.rule_type.value if v.rule_type else None,
                "severity": v.severity.value if v.severity else "error",
                "message": v.message,
                "net1": v.net1,
                "net2": v.net2,
                "component1": v.component1,
                "component2": v.component2,
                "x": v.x,
                "y": v.y,
                "expected": v.expected,
                "actual": v.actual,
                "layer": v.layer,
            })

        return AdvancedDRCResponse(
            success=True,
            passed=result.passed,
            error_count=result.error_count,
            warning_count=result.warning_count,
            info_count=result.info_count,
            violations=violations,
            statistics=result.statistics,
            duration_ms=result.duration_ms
        )

    except Exception as e:
        logger.error(f"Advanced DRC check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities/{manufacturer}")
async def get_manufacturer_capabilities(
    manufacturer: str,
    level: str = Query("standard", description="工艺等级")
):
    """
    获取制造商制造能力参数

    Args:
        manufacturer: 制造商 (jlcpcb, pcbway)
        level: 工艺等级 (standard, advanced)

    Returns:
        制造能力参数
    """
    if not ADVANCED_DRC_AVAILABLE:
        # 返回默认参数
        return {
            "manufacturer": manufacturer,
            "level": level,
            "capabilities": {
                "min_trace_width": 0.15,
                "min_trace_spacing": 0.15,
                "min_via_diameter": 0.60,
                "min_via_drill": 0.30,
            }
        }

    if manufacturer == "jlcpcb":
        engine = create_jlcpcb_drc(level=level)
    else:
        engine = AdvancedDRCEngine(manufacturer=manufacturer, level=level)

    return {
        "manufacturer": manufacturer,
        "level": level,
        "capabilities": engine.capabilities,
        "net_classes": {
            name: {
                "track_width": nc.track_width,
                "clearance": nc.clearance,
                "via_diameter": nc.via_diameter,
                "via_drill": nc.via_drill,
            }
            for name, nc in engine.net_classes.items()
        },
        "rules_summary": engine.get_rules_summary()
    }


@router.get("/rules-detailed")
async def get_detailed_rules(
    rule_type: Optional[str] = Query(None, description="规则类型过滤"),
    severity: Optional[str] = Query(None, description="严重程度过滤")
):
    """
    获取详细的DRC规则列表

    Args:
        rule_type: 规则类型 (clearance, track_width, etc.)
        severity: 严重程度 (error, warning, info)

    Returns:
        规则列表
    """
    if not ADVANCED_DRC_AVAILABLE:
        return {"rules": [], "count": 0}

    engine = create_jlcpcb_drc()

    rules = []
    for rule in engine.rules:
        # 应用过滤
        if rule_type and rule.rule_type.value != rule_type:
            continue
        if severity and rule.severity.value != severity:
            continue

        rules.append({
            "name": rule.name,
            "type": rule.rule_type.value,
            "value": rule.value,
            "tolerance": rule.tolerance,
            "severity": rule.severity.value,
            "description": rule.description,
            "category": rule.category,
        })

    return {
        "rules": rules,
        "count": len(rules),
        "by_type": engine.get_rules_summary()["by_type"]
    }


async def _load_pcb_data(project_id: str) -> Dict[str, Any]:
    """从项目加载PCB数据"""
    # 实际实现应该从文件或数据库加载
    # 这里返回空字典，由调用者处理
    return {}


# ========== Phase 5: SI 分析端点 ==========

class SIAnalyzeRequest(BaseModel):
    """SI 分析请求"""
    pcb_data: Dict[str, Any]  # PCB 数据
    include_impedance: bool = True
    include_crosstalk: bool = True
    include_loss: bool = True


class SIViolationModel(BaseModel):
    """SI 违规模型"""
    net_name: str
    severity: str
    violation_type: str
    message: str
    location: str = ""
    measured_value: float = 0
    target_value: str = ""


class SIResult(BaseModel):
    """SI 分析结果"""
    success: bool
    passed: bool
    impedance_violations: List[SIViolationModel] = []
    crosstalk_warnings: List[SIViolationModel] = []
    loss_warnings: List[SIViolationModel] = []
    summary: Dict[str, Any] = {}


@router.post("/si/analyze", response_model=SIResult)
async def analyze_si(request: SIAnalyzeRequest):
    """
    运行信号完整性 (SI) 分析

    Phase 5: 阻抗控制、串扰、传输线损耗分析

    分析内容:
    - 阻抗控制: 检查走线阻抗是否在目标范围内
    - 串扰: 估算相邻走线间的串扰系数
    - 传输损耗: 计算导体损耗和介质损耗
    """
    from drc.si_analyzer import SIAnalyzer, SIViolationSeverity

    try:
        analyzer = SIAnalyzer(request.pcb_data)
        report = analyzer.analyze_all()

        # 转换违规格式
        impedance_violations = []
        crosstalk_warnings = []
        loss_warnings = []

        for v in report.violations:
            violation = SIViolationModel(
                net_name=v.net_name,
                severity=v.severity.value,
                violation_type=v.violation_type,
                message=v.message,
                location=v.location,
                measured_value=v.measured_value,
                target_value=v.target_value,
            )

            if v.violation_type == "impedance":
                impedance_violations.append(violation)
            elif v.violation_type == "crosstalk":
                crosstalk_warnings.append(violation)
            elif v.violation_type == "loss":
                loss_warnings.append(violation)

        return SIResult(
            success=True,
            passed=report.passed,
            impedance_violations=impedance_violations,
            crosstalk_warnings=crosstalk_warnings,
            loss_warnings=loss_warnings,
            summary={
                "total_nets": report.summary.get("total_nets", 0),
                "critical_violations": report.summary.get("critical_violations", 0),
                "warnings": report.summary.get("warnings", 0),
            }
        )

    except Exception as e:
        logger.error(f"SI analysis failed: {e}")
        return SIResult(
            success=False,
            passed=False,
            summary={"error": str(e)}
        )


# ========== EMI 热点可视化 ==========

class EMIHotspotModel(BaseModel):
    """EMI 热点模型"""
    id: str
    type: str
    severity: str
    message: str
    suggestion: str
    x: float
    y: float
    layer: str
    color: str
    affected_nets: List[str]
    auto_fixable: bool


class EMIResult(BaseModel):
    """EMI 分析结果"""
    success: bool
    passed: bool
    hotspots: List[EMIHotspotModel] = []
    summary: Dict[str, Any] = {}


class EMIAnalyzeRequest(BaseModel):
    """EMI 分析请求"""
    pcb_data: Dict[str, Any]
    sensitivity: str = "medium"  # high, medium, low


@router.post("/emi/analyze", response_model=EMIResult)
async def analyze_emi(request: EMIAnalyzeRequest):
    """
    运行 EMI 热点分析

    Phase 5: 识别 PCB 上的 EMI 问题区域

    分析内容:
    - 时钟线未屏蔽检测
    - 跨越分割平面检测
    - 敏感信号走线过长
    - 差分对耦合问题
    - 串扰风险
    """
    try:
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        options = {
            "sensitivity": request.sensitivity,
            "include_clock": True,
            "include_plane_splits": True,
        }

        analyzer = EMIHotspotAnalyzer(request.pcb_data, options)
        report = analyzer.analyze()
        visualization = analyzer.get_hotspots_for_visualization()

        hotspots = [
            EMIHotspotModel(
                id=h["id"],
                type=h["type"],
                severity=h["severity"],
                message=h["message"],
                suggestion=h["suggestion"],
                x=h["x"],
                y=h["y"],
                layer=h["layer"],
                color=h["color"],
                affected_nets=h["affectedNets"],
                auto_fixable=h["autoFixable"],
            )
            for h in visualization
        ]

        return EMIResult(
            success=True,
            passed=report.passed,
            hotspots=hotspots,
            summary={
                "total_hotspots": report.summary.get("total_hotspots", 0),
                "critical": report.summary.get("critical", 0),
                "warning": report.summary.get("warning", 0),
                "info": report.summary.get("info", 0),
                "affected_nets": report.summary.get("affected_nets", []),
            }
        )

    except Exception as e:
        logger.error(f"EMI analysis failed: {e}")
        return EMIResult(
            success=False,
            passed=False,
            summary={"error": str(e)}
        )


@router.post("/emi/visualization", response_model=Dict[str, Any])
async def get_emi_visualization(request: EMIAnalyzeRequest):
    """
    获取 EMI 热点可视化数据

    返回前端渲染所需的热点位置和样式
    """
    try:
        from design_rules.emi_hotspot_analyzer import EMIHotspotAnalyzer

        options = {
            "sensitivity": request.sensitivity,
            "include_clock": True,
            "include_plane_splits": True,
        }

        analyzer = EMIHotspotAnalyzer(request.pcb_data, options)
        hotspots = analyzer.get_hotspots_for_visualization()

        return {
            "success": True,
            "hotspots": hotspots,
            "legend": {
                "critical": {"label": "严重", "color": "#ff0000"},
                "warning": {"label": "警告", "color": "#ff9900"},
                "info": {"label": "提示", "color": "#ffcc00"},
            }
        }

    except Exception as e:
        logger.error(f"EMI visualization failed: {e}")
        return {"success": False, "error": str(e)}

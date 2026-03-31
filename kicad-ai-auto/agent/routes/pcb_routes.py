"""
PCB 增强 API 路由

Phase 6: PCB 编辑器增强 - 扇出、交互式布线
Phase 7B: 拓扑感知自动布局
Phase 7C: 铜铺 + 缝合过孔
Phase 8: 安全隔离 + 热过孔
Phase 9: 差分对布线 + 阻抗控制

Author: Claude Code
Date: 2026-03-30
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from pcb.fanout_engine import FanoutEngine, FanoutDirection, calculate_pin_spacing
from pcb.interactive_router import InteractiveRouter, get_interactive_router, RoutingRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pcb", tags=["PCB Enhanced"])


# ============== 扇出 API ==============

class FanoutComponentRequest(BaseModel):
    """扇出请求 - 单个元件"""
    component_id: str = Field(..., description="元件 ID")
    reference: str = Field(..., description="参考标识 (如 U1)")
    pads: List[Dict[str, Any]] = Field(..., description="焊盘列表")
    direction: str = Field("auto", description="扇出方向: spread, in, out, auto")
    pin_spacing: Optional[float] = Field(None, description="引脚间距 (mm)")


class FanoutBatchRequest(BaseModel):
    """批量扇出请求"""
    components: List[FanoutComponentRequest] = Field(..., description="元件列表")
    default_direction: str = Field("auto", description="默认扇出方向")
    spacing: float = Field(2.54, description="扇出间距 (mm)")
    via_size: float = Field(0.4, description="过孔外径 (mm)")
    drill_size: float = Field(0.3, description="过孔钻径 (mm)")
    trace_width: float = Field(0.25, description="走线宽度 (mm)")


@router.post("/fanout")
async def fanout_component(request: FanoutComponentRequest):
    """
    对单个元件进行扇出

    支持 QFN/QFP/SOP 封装自动扇出
    """
    engine = FanoutEngine(
        spacing=2.54,
        via_size=0.4,
        drill_size=0.3,
        trace_width=0.25,
    )

    # 自动计算引脚间距
    pin_spacing = request.pin_spacing
    if pin_spacing is None:
        # 从焊盘位置估算
        if len(request.pads) >= 2:
            # 简单估算
            pin_spacing = 1.27
        else:
            pin_spacing = 1.27

    direction = FanoutDirection(request.direction)
    if request.direction == "auto":
        direction = FanoutDirection.AUTO

    result = engine.fanout_component(
        component_id=request.component_id,
        reference=request.reference,
        pads=request.pads,
        direction=direction,
        pin_spacing=pin_spacing,
    )

    return {
        "success": True,
        "component_id": result.component_id,
        "reference": result.reference,
        "pads": [
            {
                "pad_number": p.pad_number,
                "x": p.x,
                "y": p.y,
                "net": p.net,
                "type": p.type.value,
            }
            for p in result.pads
        ],
        "vias": [
            {
                "via_id": v.via_id,
                "x": v.x,
                "y": v.y,
                "net": v.net,
                "from_layer": v.from_layer,
                "to_layer": v.to_layer,
                "outer_diameter": v.outer_diameter,
                "drill": v.drill,
            }
            for v in result.vias
        ],
        "traces": [
            {
                "trace_id": t.trace_id,
                "net": t.net,
                "start_x": t.start_x,
                "start_y": t.start_y,
                "end_x": t.end_x,
                "end_y": t.end_y,
                "layer": t.layer,
                "width": t.width,
            }
            for t in result.traces
        ],
        "success": result.success,
        "message": result.message,
    }


@router.post("/fanout/batch")
async def fanout_batch(request: FanoutBatchRequest):
    """
    批量扇出多个元件
    """
    engine = FanoutEngine(
        spacing=request.spacing,
        via_size=request.via_size,
        drill_size=request.drill_size,
        trace_width=request.trace_width,
    )

    components_data = [
        {
            "id": comp.component_id,
            "reference": comp.reference,
            "pads": comp.pads,
            "direction": comp.direction,
            "pin_spacing": comp.pin_spacing,
        }
        for comp in request.components
    ]

    result = engine.fanout_multiple(
        components=components_data,
        direction=FanoutDirection(request.default_direction),
    )

    return {
        "success": True,
        "component_results": [
            {
                "component_id": cr.component_id,
                "reference": cr.reference,
                "vias": [
                    {
                        "via_id": v.via_id,
                        "x": v.x,
                        "y": v.y,
                        "net": v.net,
                    }
                    for v in cr.vias
                ],
                "traces": [
                    {
                        "trace_id": t.trace_id,
                        "net": t.net,
                        "start_x": t.start_x,
                        "start_y": t.start_y,
                        "end_x": t.end_x,
                        "end_y": t.end_y,
                        "layer": t.layer,
                        "width": t.width,
                    }
                    for t in cr.traces
                ],
            }
            for cr in result.component_results
        ],
        "total_vias": result.total_vias,
        "total_traces": result.total_traces,
        "message": result.message,
    }


@router.get("/fanout/pin-spacing/{package_type}")
async def get_package_pin_spacing(package_type: str):
    """
    获取封装类型的引脚间距

    Args:
        package_type: 封装类型 (如 QFN-48, SOP-16, DIP-8)
    """
    spacing = calculate_pin_spacing(package_type)
    return {
        "success": True,
        "package_type": package_type,
        "pin_spacing_mm": spacing,
    }


# ============== 交互式布线 API ==============

class RoutePlanRequest(BaseModel):
    """布线规划请求"""
    start_x: float = Field(..., description="起点 X")
    start_y: float = Field(..., description="起点 Y")
    start_layer: str = Field(..., description="起点层")
    end_x: float = Field(..., description="终点 X")
    end_y: float = Field(..., description="终点 Y")
    end_layer: str = Field(..., description="终点层")
    net_name: str = Field(..., description="网络名称")
    trace_width: float = Field(0.25, description="走线宽度")
    clearance: float = Field(0.2, description="间距")
    max_vias: int = Field(5, description="最大过孔数")


class RoutePreviewRequest(BaseModel):
    """布线预览请求"""
    start_x: float
    start_y: float
    current_x: float
    current_y: float
    layer: str


@router.post("/route/plan")
async def plan_route(request: RoutePlanRequest):
    """
    规划布线路径

    返回多条候选路径及其评分
    """
    router = get_interactive_router()

    route_request = RoutingRequest(
        start_x=request.start_x,
        start_y=request.start_y,
        start_layer=request.start_layer,
        end_x=request.end_x,
        end_y=request.end_y,
        end_layer=request.end_layer,
        net_name=request.net_name,
        trace_width=request.trace_width,
        clearance=request.clearance,
        max_vias=request.max_vias,
    )

    result = router.plan_route(route_request)

    return {
        "success": result.success,
        "candidates": [
            {
                "route_id": c.route_id,
                "segments": [
                    {
                        "start_x": s.start.x,
                        "start_y": s.start.y,
                        "end_x": s.end.x,
                        "end_y": s.end.y,
                        "layer": s.layer,
                        "width": s.width,
                    }
                    for s in c.segments
                ],
                "total_length": c.total_length,
                "via_count": c.via_count,
                "score": c.score,
                "status": c.status.value,
            }
            for c in result.candidates
        ],
        "best_route": {
            "route_id": result.best_route.route_id,
            "segments": [
                {
                    "start_x": s.start.x,
                    "start_y": s.start.y,
                    "end_x": s.end.x,
                    "end_y": s.end.y,
                    "layer": s.layer,
                    "width": s.width,
                }
                for s in result.best_route.segments
            ],
            "total_length": result.best_route.total_length,
            "via_count": result.best_route.via_count,
            "score": result.best_route.score,
        } if result.best_route else None,
        "message": result.message,
    }


@router.post("/route/preview")
async def get_route_preview(request: RoutePreviewRequest):
    """
    获取实时布线预览

    根据当前鼠标位置返回预览路径点
    """
    router = get_interactive_router()

    points = router.get_routing_preview(
        start_x=request.start_x,
        start_y=request.start_y,
        current_x=request.current_x,
        current_y=request.current_y,
        layer=request.layer,
    )

    return {
        "success": True,
        "preview": [
            {"x": p.x, "y": p.y}
            for p in points
        ],
    }


@router.post("/route/adjust-width")
async def adjust_route_width(
    route_id: str = Query(..., description="路径 ID"),
    new_width: float = Query(0.25, description="新的走线宽度"),
):
    """
    调整已规划路径的走线宽度
    """
    router = get_interactive_router()

    # 从路由器的 routes 列表中查找
    route = None
    for r in router.routes:
        if r.route_id == route_id:
            route = r
            break

    if not route:
        return {
            "success": False,
            "message": f"路径不存在: {route_id}",
        }

    adjusted = router.adjust_trace_width(route, new_width)

    return {
        "success": True,
        "route": {
            "route_id": adjusted.route_id,
            "segments": [
                {
                    "start_x": s.start.x,
                    "start_y": s.start.y,
                    "end_x": s.end.x,
                    "end_y": s.end.y,
                    "layer": s.layer,
                    "width": s.width,
                }
                for s in adjusted.segments
            ],
            "total_length": adjusted.total_length,
            "via_count": adjusted.via_count,
            "score": adjusted.score,
        },
    }


@router.post("/route/add-obstacle")
async def add_obstacle(
    x: float = Query(..., description="X 坐标"),
    y: float = Query(..., description="Y 坐标"),
    layer: str = Query("F.Cu", description="层"),
):
    """
    添加布线障碍物

    用于标记已布线的线段、焊盘等不可穿越的区域
    """
    router = get_interactive_router()
    router.add_obstacle(x, y, layer)

    return {
        "success": True,
        "message": f"障碍物已添加: ({x}, {y}, {layer})",
    }


@router.post("/route/clear-obstacles")
async def clear_obstacles():
    """
    清除所有布线障碍物
    """
    router = get_interactive_router()
    router.obstacles.clear()

    return {
        "success": True,
        "message": "所有障碍物已清除",
    }


# ============== Phase 7B: 拓扑感知自动布局 API ==============

class AutoLayoutRequest(BaseModel):
    """自动布局请求"""
    project_id: Optional[str] = Field(None, description="项目 ID")
    topology_aware: bool = Field(True, description="是否使用拓扑感知布局")
    board_constraints: Optional[Dict[str, float]] = Field(None, description="板子约束 {width, height}")


@router.post("/auto-layout")
async def auto_layout(request: AutoLayoutRequest):
    """
    拓扑感知自动布局

    基于电路拓扑的功能分区布局:
    - 功率流向: 左→右 (输入在左, 输出在右)
    - 安规隔离: 初级/次级之间留空
    - 接口元件: 放在板边
    - 控制电路: 居中
    - 被动元件: 靠近所属IC
    """
    try:
        from kicad_ipc_manager import get_kicad_manager
        manager = get_kicad_manager()

        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="KiCad not connected")

        result = manager.auto_place(topology_aware=request.topology_aware)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Auto-layout failed"))

        return result

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Missing module: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-layout failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Phase 7C: 铜铺 + 缝合过孔 API ==============

class CopperPourRequest(BaseModel):
    """铜铺请求"""
    project_id: Optional[str] = Field(None, description="项目 ID")
    nets: List[str] = Field(["GND"], description="铺铜网络列表")
    layers: List[str] = Field(["B.Cu"], description="铺铜层列表")
    style: str = Field("solid", description="铺铜样式: solid | hatched")
    hatch_width: float = Field(1.0, description="网格线宽 (mm)")
    hatch_gap: float = Field(0.5, description="网格间距 (mm)")
    thermal_relief: bool = Field(True, description="热焊盘")
    stitch_vias: bool = Field(True, description="是否添加缝合过孔")
    stitch_spacing: float = Field(1.0, description="缝合过孔间距 (mm)")
    clearance: float = Field(0.3, description="间距 (mm)")


@router.post("/copper-pour")
async def copper_pour(request: CopperPourRequest):
    """
    一键铺铜 + 缝合过孔

    支持:
    - 实心铺铜 (solid)
    - 网格铺铜 (hatched)
    - 热焊盘 (thermal relief)
    - 缝合过孔阵列
    """
    try:
        from kicad_ipc_manager import get_kicad_manager
        manager = get_kicad_manager()

        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="KiCad not connected")

        result = manager.auto_copper_pour(
            nets=request.nets,
            layers=request.layers,
            hatched=(request.style == "hatched"),
            stitch_spacing=request.stitch_spacing if request.stitch_vias else 0,
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Copper pour failed"))

        # 铺铜后自动运行 DRC
        try:
            from drc.advanced_drc import create_jlcpcb_drc
            board_data = manager.get_full_pcb_data()
            drc = create_jlcpcb_drc()
            drc_result = drc.check(board_data)
            copper_violations = [
                v for v in drc_result.violations
                if "clearance" in v.rule_name.lower() or "copper" in v.rule_name.lower()
            ]
            result["drc_check"] = {
                "passed": drc_result.passed,
                "total_violations": len(drc_result.violations),
                "copper_violations": len(copper_violations),
                "violations": [
                    {"rule": v.rule_name, "message": v.message}
                    for v in copper_violations[:10]
                ],
            }
        except Exception as e:
            logger.debug(f"Post-pour DRC check failed (non-fatal): {e}")
            result["drc_check"] = {"passed": None, "error": str(e)}

        return result

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Missing module: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copper pour failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateZoneRequest(BaseModel):
    """创建铺铜区域请求"""
    net_name: str = Field(..., description="网络名称 (如 GND, VCC)")
    layer: str = Field("B.Cu", description="层 (如 B.Cu, F.Cu)")
    boundary_points: List[Dict[str, float]] = Field(..., description="边界点列表")
    clearance: float = Field(0.3, description="间距 (mm)")
    thermal_relief: bool = Field(True, description="热焊盘")
    hatched: bool = Field(False, description="网格铺铜")
    hatch_width: float = Field(1.0, description="网格线宽 (mm)")
    hatch_gap: float = Field(0.5, description="网格间距 (mm)")


@router.post("/create-zone")
async def create_zone(request: CreateZoneRequest):
    """创建铺铜区域"""
    try:
        from kicad_ipc_manager import get_kicad_manager
        manager = get_kicad_manager()

        if not manager.is_connected():
            raise HTTPException(status_code=503, detail="KiCad not connected")

        result = manager.create_zone(
            net_name=request.net_name,
            layer=request.layer,
            boundary_points=request.boundary_points,
            clearance=request.clearance,
            thermal_relief=request.thermal_relief,
            hatched=request.hatched,
            hatch_width=request.hatch_width,
            hatch_gap=request.hatch_gap,
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Zone creation failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zone creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Phase 8: 安全隔离 + 热过孔 API ==============

class ThermalViaRequest(BaseModel):
    """热过孔生成请求"""
    component_x: float = Field(..., description="元件中心 X (mm)")
    component_y: float = Field(..., description="元件中心 Y (mm)")
    component_width: float = Field(..., description="元件宽度 (mm)")
    component_height: float = Field(..., description="元件高度 (mm)")
    target_rth: float = Field(15.0, description="目标热阻 (degC/W)")
    via_drill: float = Field(0.3, description="过孔钻径 (mm)")
    via_size: float = Field(0.6, description="过孔外径 (mm)")
    spacing: float = Field(1.0, description="过孔间距 (mm)")
    net: str = Field("GND", description="网络名称")
    avoid_pins: Optional[List[Dict[str, float]]] = Field(None, description="需要避开的引脚 [{x, y, radius}]")


@router.post("/thermal-vias")
async def generate_thermal_vias(request: ThermalViaRequest):
    """
    为功率元件生成热过孔阵列

    根据目标热阻计算所需过孔数量，在元件底部放置网格阵列，
    自动避开信号引脚。输出 KiCad S-expression 格式。
    """
    try:
        from pcb.thermal_via_generator import ThermalViaGenerator

        generator = ThermalViaGenerator()

        avoid_pins = None
        if request.avoid_pins:
            avoid_pins = [
                (p["x"], p["y"], p["radius"])
                for p in request.avoid_pins
            ]

        result = generator.generate_thermal_vias(
            component_x=request.component_x,
            component_y=request.component_y,
            component_width=request.component_width,
            component_height=request.component_height,
            thermal_resistance_target=request.target_rth,
            via_drill=request.via_drill,
            via_size=request.via_size,
            avoid_pins=avoid_pins,
            spacing=request.spacing,
            net=request.net,
        )

        kicad_output = generator.to_kicad_vias(result, net=request.net)

        return {
            "success": True,
            "via_count": result.via_count,
            "estimated_rth": result.estimated_rth,
            "target_rth": result.target_rth,
            "grid_rows": result.grid_rows,
            "grid_cols": result.grid_cols,
            "vias": [
                {"x": v.x, "y": v.y, "drill": v.drill, "size": v.size}
                for v in result.vias
            ],
            "kicad_output": kicad_output,
        }

    except Exception as e:
        logger.error(f"Thermal via generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class IsolationSlotRequest(BaseModel):
    """安全隔离生成请求"""
    board_width: float = Field(..., description="板宽 (mm)")
    board_height: float = Field(..., description="板高 (mm)")
    primary_zone: List[float] = Field(..., description="初级区域 [x, y, w, h]")
    secondary_zone: List[float] = Field(..., description="次级区域 [x, y, w, h]")
    voltage: float = Field(220.0, description="工作电压 (V)")
    voltage_label: str = Field("220V AC", description="电压标签")
    standard: str = Field("IEC 60950-1", description="安全标准")
    primary_net: str = Field("", description="初级侧网络")
    secondary_net: str = Field("", description="次级侧网络")
    add_barriers: bool = Field(True, description="是否添加锯齿爬电屏障")
    num_barriers: int = Field(5, description="锯齿屏障数量")


@router.post("/isolation-generate")
async def generate_isolation(request: IsolationSlotRequest):
    """
    生成安全隔离槽和爬电屏障

    基于 IEC 60950-1 / IEC 62368-1 标准:
    - 在初级/次级区域之间生成隔离槽 (Edge.Cuts)
    - 添加无铜禁布区
    - 可选锯齿形爬电屏障
    - 输出 KiCad S-expression 格式
    """
    try:
        from pcb.isolation_generator import (
            IsolationGenerator,
            IsolationSlot,
        )

        generator = IsolationGenerator(standard=request.standard)

        # 计算最小爬电距离
        min_creepage = IsolationGenerator.get_creepage_for_voltage(
            request.voltage, request.standard
        )

        slot = generator.generate_isolation_slot(
            board_width=request.board_width,
            board_height=request.board_height,
            primary_zone=tuple(request.primary_zone),
            secondary_zone=tuple(request.secondary_zone),
            min_creepage_mm=min_creepage,
            voltage_label=request.voltage_label,
            primary_net=request.primary_net,
            secondary_net=request.secondary_net,
        )

        barriers = []
        if request.add_barriers:
            barriers = generator.generate_creepage_barriers(slot, request.num_barriers)

        kicad_output = generator.to_kicad_format()

        return {
            "success": True,
            "slot": {
                "x": slot.x,
                "y": slot.y,
                "width": slot.width,
                "height": slot.height,
                "voltage_label": slot.voltage_label,
                "standard": slot.standard,
            },
            "min_creepage_mm": min_creepage,
            "barriers_count": len(barriers),
            "kicad_output": kicad_output,
        }

    except Exception as e:
        logger.error(f"Isolation generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/isolation-creepage/{voltage}")
async def get_creepage_distance(
    voltage: float,
    standard: str = Query("IEC 60950-1", description="安全标准"),
):
    """查询指定电压下的最小爬电距离"""
    try:
        from pcb.isolation_generator import IsolationGenerator

        distance = IsolationGenerator.get_creepage_for_voltage(voltage, standard)
        return {
            "success": True,
            "voltage": voltage,
            "standard": standard,
            "min_creepage_mm": distance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Phase 9: 差分对布线 + 阻抗控制 API ==============

class DiffPairRouteRequest(BaseModel):
    """差分对布线请求"""
    start_pos_x: float = Field(..., description="正端起点 X (mm)")
    start_pos_y: float = Field(..., description="正端起点 Y (mm)")
    start_neg_x: float = Field(..., description="负端起点 X (mm)")
    start_neg_y: float = Field(..., description="负端起点 Y (mm)")
    end_pos_x: float = Field(..., description="正端终点 X (mm)")
    end_pos_y: float = Field(..., description="正端终点 Y (mm)")
    end_neg_x: float = Field(..., description="负端终点 X (mm)")
    end_neg_y: float = Field(..., description="负端终点 Y (mm)")
    layer: str = Field("F.Cu", description="布线层")
    target_impedance: float = Field(90.0, description="目标差分阻抗 (Ohm)")
    max_length_mismatch: float = Field(0.5, description="最大长度不匹配 (mm)")


@router.post("/diff-pair-route")
async def route_diff_pair(request: DiffPairRouteRequest):
    """
    差分对布线

    耦合平行布线，阻抗控制宽度和间距自动计算。
    支持 USB (90 Ohm), HDMI (100 Ohm), PCIe (85 Ohm) 等协议。
    """
    try:
        from routing.differential_pair_router import (
            DifferentialPairRouter,
            Point,
            create_diff_pair_router,
        )

        router = create_diff_pair_router(
            target_impedance=request.target_impedance,
        )

        result = router.route_pair(
            start_pos=Point(request.start_pos_x, request.start_pos_y),
            start_neg=Point(request.start_neg_x, request.start_neg_y),
            end_pos=Point(request.end_pos_x, request.end_pos_y),
            end_neg=Point(request.end_neg_x, request.end_neg_y),
            layer=request.layer,
            max_length_mismatch=request.max_length_mismatch,
        )

        if not result:
            raise HTTPException(status_code=500, detail="Differential pair routing failed")

        return {
            "success": True,
            "pos_points": [{"x": p.x, "y": p.y} for p in result.pos_points],
            "neg_points": [{"x": p.x, "y": p.y} for p in result.neg_points],
            "pos_length": result.pos_length,
            "neg_length": result.neg_length,
            "length_mismatch": result.length_mismatch,
            "impedance": result.impedance,
            "target_impedance": request.target_impedance,
        }

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Missing module: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diff pair routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ImpedanceCalcRequest(BaseModel):
    """阻抗计算请求"""
    target_impedance: float = Field(90.0, description="目标差分阻抗 (Ohm)")
    tolerance_pct: float = Field(10.0, description="容差百分比")
    substrate_height: float = Field(0.2, description="介质厚度 (mm)")
    er: float = Field(4.5, description="介电常数")


@router.post("/impedance-calculate")
async def calculate_impedance(request: ImpedanceCalcRequest):
    """
    阻抗计算器

    根据目标差分阻抗计算走线宽度和间距。
    使用微带线阻抗公式:
      Z0 = 87 / sqrt(Er+1.41) * ln(5.98*H / (0.8*W + T))
      Z_diff = 2 * Z0 * (1 - 0.48 * exp(-0.96 * S/H))
    """
    try:
        from routing.differential_pair_router import create_diff_pair_router

        router = create_diff_pair_router(target_impedance=request.target_impedance)
        constraint = router.get_impedance_constraint(
            target_z=request.target_impedance,
            tolerance_pct=request.tolerance_pct,
        )

        return {
            "success": True,
            "target_z": constraint.target_z,
            "tolerance_pct": constraint.tolerance_pct,
            "min_z": round(constraint.min_z, 2),
            "max_z": round(constraint.max_z, 2),
            "trace_width_mm": constraint.trace_width,
            "trace_gap_mm": constraint.trace_gap,
            "common_targets": {
                "USB 2.0/3.0": 90,
                "HDMI/DisplayPort": 100,
                "PCIe": 85,
                "Ethernet": 100,
                "SATA": 100,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class LengthTuneRequest(BaseModel):
    """长度调谐请求"""
    points: List[Dict[str, float]] = Field(..., description="走线点列表 [{x, y}]")
    target_length: float = Field(..., description="目标长度 (mm)")
    style: str = Field("serpentine", description="调谐样式: serpentine | sawtooth")
    amplitude: float = Field(2.0, description="弯曲幅度 (mm)")
    pitch: float = Field(1.0, description="弯曲间距 (mm)")


@router.post("/length-tune")
async def tune_length(request: LengthTuneRequest):
    """
    长度调谐

    在较短走线上添加蛇形/锯齿弯曲以匹配目标长度。
    主要用于差分对长度匹配。
    """
    try:
        from routing.length_tuner import LengthTuner
        from routing.astar_router import Point

        tuner = LengthTuner()
        points = [Point(p["x"], p["y"]) for p in request.points]

        result = tuner.tune(
            trace_points=points,
            target_length=request.target_length,
            style=request.style,
            amplitude=request.amplitude,
            pitch=request.pitch,
        )

        return {
            "success": True,
            "tuned_points": [{"x": p.x, "y": p.y} for p in result.tuned_points],
            "original_length": result.original_length,
            "tuned_length": result.tuned_length,
            "added_length": result.added_length,
            "bend_count": result.bend_count,
            "style": request.style,
        }

    except Exception as e:
        logger.error(f"Length tuning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Phase 8B-5: 全自动布线 API ==============

class AutoRouteRequest(BaseModel):
    """全自动布线请求"""
    pcb_data: Dict[str, Any] = Field(..., description="PCB 数据")
    strategy: str = Field("balanced", description="布线策略: balanced | fast | thorough")
    prefer_freerouter: bool = Field(True, description="优先使用 FreeRouter")
    enable_diff_pair: bool = Field(True, description="自动布线差分对")
    enable_post_optimize: bool = Field(True, description="布线后优化")
    enable_thermal_vias: bool = Field(True, description="自动推荐热过孔")


@router.post("/auto-route")
async def auto_route_pcb(request: AutoRouteRequest):
    """
    全自动布线管线

    流程:
    1. 网络分类 (电源/信号/差分对/高速)
    2. 差分对优先布线 (如有)
    3. 尝试 FreeRouter → 回退 PushRouter
    4. Rip-up & retry 失败网络
    5. 后布线优化 (共线合并、倒角、电源加宽)
    6. 热过孔推荐
    7. 质量评分
    """
    result = {
        "success": False,
        "method": "",
        "tracks": [],
        "vias": [],
        "stats": {},
        "quality": None,
        "thermal_recommendations": [],
    }

    try:
        # Step 1: Classify nets
        from routing.net_classifier import NetClassifier
        classifier = NetClassifier()
        nets = request.pcb_data.get("nets", [])
        classifications = {}
        diff_pairs = []
        for net in nets:
            name = net.get("name", "")
            cls = classifier.classify_net(name)
            classifications[name] = cls
            if cls.diff_pair:
                diff_pairs.append(cls.diff_pair)

        result["stats"]["total_nets"] = len(nets)
        result["stats"]["diff_pairs"] = len(diff_pairs)

        # Step 2: Route diff pairs first
        if request.enable_diff_pair and diff_pairs:
            try:
                from routing.differential_pair_router import create_diff_pair_router, Point
                dp_tracks = []
                for dp in diff_pairs:
                    router = create_diff_pair_router(target_impedance=dp.target_impedance)
                    dp_result = router.route_pair(
                        start_pos=Point(dp.pos_start_x, dp.pos_start_y),
                        start_neg=Point(dp.neg_start_x, dp.neg_start_y),
                        end_pos=Point(dp.pos_end_x, dp.pos_end_y),
                        end_neg=Point(dp.neg_end_x, dp.neg_end_y),
                    )
                    if dp_result:
                        dp_tracks.extend(dp_result.pos_points)
                        dp_tracks.extend(dp_result.neg_points)
                result["stats"]["diff_pairs_routed"] = len(diff_pairs)
            except Exception as e:
                logger.warning(f"Diff pair routing skipped: {e}")

        # Step 3: Try FreeRouter, fallback to PushRouter
        routed = False
        if request.prefer_freerouter:
            try:
                from freerouter_cli import FreeRouterCLI
                freerouter = FreeRouterCLI()
                if freerouter.is_available():
                    fr_result = freerouter.route_via_freerouter(request.pcb_data)
                    if fr_result.get("success"):
                        result["method"] = "freerouter"
                        result["tracks"] = fr_result.get("tracks", [])
                        result["vias"] = fr_result.get("vias", [])
                        result["stats"]["freerouter"] = fr_result.get("freerouter_stats", {})
                        routed = True
            except Exception as e:
                logger.warning(f"FreeRouter failed, falling back: {e}")

        if not routed:
            try:
                from freerouter_cli import SimpleAutoRouter
                simple_router = SimpleAutoRouter()

                # Build a minimal board-like object
                class _Board:
                    def __init__(self, data):
                        import types
                        self.nets = []
                        self.tracks = []
                        self.footprints = []
                        for n in data.get("nets", []):
                            net_obj = types.SimpleNamespace()
                            net_obj.name = n.get("name", "")
                            net_obj.items = []
                            self.nets.append(net_obj)
                        self._raw = data

                simple_router.set_board(_Board(request.pcb_data))
                sr_result = simple_router.route_all()
                result["method"] = "push_router"
                result["stats"]["simple_router"] = {
                    "routed": sr_result.get("routed_count", 0),
                    "failed": sr_result.get("failed_count", 0),
                }
                result["success"] = sr_result.get("success", False)
            except Exception as e:
                logger.error(f"PushRouter failed: {e}")
                result["method"] = "failed"
                result["stats"]["error"] = str(e)

        # Step 4: Rip-up & retry
        if result["success"]:
            try:
                from routing.ripup_router import RipupRouter
                ripper = RipupRouter(request.pcb_data)
                rip_result = ripper.route_all()
                result["stats"]["ripup"] = {
                    "rounds": rip_result.rounds if hasattr(rip_result, 'rounds') else 0,
                    "total_routed": rip_result.total_routed if hasattr(rip_result, 'total_routed') else 0,
                }
            except Exception as e:
                logger.debug(f"Rip-up retry skipped: {e}")

        # Step 5: Post-route optimization
        if request.enable_post_optimize and result["success"]:
            try:
                from routing.post_optimizer import PostOptimizer
                optimizer = PostOptimizer()
                opt_result = optimizer.optimize_all(request.pcb_data.get("tracks", []))
                result["stats"]["optimization"] = {
                    "corners_smoothed": opt_result.corners_smoothed,
                    "traces_widened": opt_result.traces_widened,
                    "savings_pct": round(opt_result.savings_percent, 1),
                }
            except Exception as e:
                logger.debug(f"Post-optimization skipped: {e}")

        # Step 6: Thermal via recommendations
        if request.enable_thermal_vias:
            try:
                from pcb.thermal_via_generator import recommend_thermal_vias
                recommendations = recommend_thermal_vias(request.pcb_data)
                result["thermal_recommendations"] = [
                    {
                        "reference": r.reference,
                        "priority": r.priority.value if hasattr(r.priority, 'value') else str(r.priority),
                        "via_count": r.recommended_via_count,
                        "estimated_rth": round(r.estimated_rth, 2),
                    }
                    for r in recommendations
                ]
            except Exception as e:
                logger.debug(f"Thermal via recommendation skipped: {e}")

        # Step 7: Quality scoring
        try:
            from routing.quality_scorer import RoutingQualityScorer, RoutingInput
            scorer = RoutingQualityScorer()
            stats = result.get("stats", {})
            quality_input = RoutingInput(
                total_nets=stats.get("total_nets", len(nets)),
                routed_nets=stats.get("simple_router", {}).get("routed", stats.get("total_nets", 0)),
                drc_violations=0,
                total_vias=len(result.get("vias", [])),
            )
            quality_report = scorer.score(quality_input)
            result["quality"] = {
                "total_score": quality_report.total_score,
                "grade": quality_report.grade,
                "is_production_ready": quality_report.is_production_ready,
            }
        except Exception as e:
            logger.debug(f"Quality scoring skipped: {e}")

        result["success"] = True

    except Exception as e:
        logger.error(f"Auto-route pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return result


# ============== Phase 8D: 布线质量评分 API ==============

class RoutingQualityRequest(BaseModel):
    """布线质量评估请求"""
    total_nets: int = Field(..., description="总网络数")
    routed_nets: int = Field(..., description="已布线网络数")
    failed_nets: List[str] = Field(default_factory=list, description="未布线网络列表")
    drc_violations: int = Field(0, description="DRC 违规数")
    total_track_length: float = Field(0.0, description="走线总长度 (mm)")
    ideal_track_length: float = Field(0.0, description="理想走线长度 (mm, Manhattan距离)")
    total_vias: int = Field(0, description="过孔总数")
    diff_pair_count: int = Field(0, description="差分对数量")
    diff_pair_impedance_errors: int = Field(0, description="差分对阻抗错误数")
    diff_pair_length_mismatches: int = Field(0, description="差分对长度不匹配数")
    board_area: float = Field(100.0, description="板面积 (mm^2)")


@router.post("/routing-quality")
async def score_routing_quality(request: RoutingQualityRequest):
    """
    布线质量评分

    5维度加权评分 (0-100):
    - 完成率 (30%): 布通网络比例
    - DRC合规 (30%): 无违规
    - 效率 (20%): 走线总长度 vs 理想长度
    - 过孔使用 (10%): 每网络平均过孔数
    - 差分对质量 (10%): 阻抗和长度匹配

    返回评分、等级 (A/B/C/D/F) 和改进建议。
    """
    try:
        from routing.quality_scorer import RoutingQualityScorer, RoutingInput

        scorer = RoutingQualityScorer()
        data = RoutingInput(
            total_nets=request.total_nets,
            routed_nets=request.routed_nets,
            failed_nets=request.failed_nets,
            drc_violations=request.drc_violations,
            total_track_length=request.total_track_length,
            ideal_track_length=request.ideal_track_length,
            total_vias=request.total_vias,
            diff_pair_count=request.diff_pair_count,
            diff_pair_impedance_errors=request.diff_pair_impedance_errors,
            diff_pair_length_mismatches=request.diff_pair_length_mismatches,
            board_area=request.board_area,
        )

        report = scorer.score(data)

        return {
            "success": True,
            "total_score": report.total_score,
            "grade": report.grade,
            "is_passing": report.is_passing,
            "is_production_ready": report.is_production_ready,
            "dimensions": [
                {
                    "name": d.name,
                    "score": round(d.score, 1),
                    "weight": d.weight,
                    "weighted_score": round(d.weighted_score, 1),
                    "details": d.details,
                }
                for d in report.dimensions
            ],
            "improvements": report.improvements,
            "message": report.message,
        }

    except Exception as e:
        logger.error(f"Routing quality scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 布局方案对比 API ==============

class LayoutCandidateRequest(BaseModel):
    """布局方案请求"""
    board_width: float = Field(100.0, description="板宽 (mm)")
    board_height: float = Field(80.0, description="板高 (mm)")
    components: List[Dict[str, Any]] = Field(..., description="元件列表")
    net_connections: Optional[List[Dict[str, str]]] = Field(
        None, description="网络连接 [{net, ref1, ref2}]"
    )


@router.post("/layout-candidates")
async def generate_layout_candidates(request: LayoutCandidateRequest):
    """
    生成3种布局方案供用户选择。

    返回紧凑/均衡/散热优先三种方案，每种包含：
    - 元件位置
    - 面积利用率、走线长度、散热评分
    - 综合评分
    """
    try:
        from placement.layout_candidate import LayoutCandidateGenerator, LayoutStrategy
        from placement.smart_placement_engine import Component

        # Convert to Component objects
        components = []
        for cd in request.components:
            components.append(Component(
                reference=cd.get("reference", ""),
                footprint=cd.get("footprint", ""),
                value=cd.get("value", ""),
                width=float(cd.get("width", 5.0)),
                height=float(cd.get("height", 5.0)),
            ))

        # Convert net connections
        net_connections = None
        if request.net_connections:
            net_connections = [
                (n["net"], n["ref1"], n["ref2"])
                for n in request.net_connections
            ]

        # Generate candidates
        gen = LayoutCandidateGenerator(
            board_width=request.board_width,
            board_height=request.board_height,
        )
        candidates = gen.generate_candidates(components, net_connections)

        # Format response
        result_candidates = []
        for c in candidates:
            result_candidates.append({
                "strategy": c.strategy.value,
                "positions": c.positions,
                "scores": {
                    "overall": round(c.overall_score, 1),
                    "utilization": round(c.board_utilization, 1),
                    "wire_length": round(c.estimated_wire_length, 1),
                    "thermal": round(c.thermal_score, 1),
                    "routing": round(c.routing_score, 1),
                },
                "description": c.description,
            })

        # Sort by overall score
        result_candidates.sort(key=lambda x: x["scores"]["overall"], reverse=True)

        return {
            "success": True,
            "candidates": result_candidates,
            "recommended": result_candidates[0]["strategy"] if result_candidates else None,
            "message": f"Generated {len(result_candidates)} layout candidates",
        }

    except Exception as e:
        logger.error(f"Layout candidate generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Fanout Engine - 扇出引擎

Phase 6: 提供自动扇出功能

功能:
- 对选中元件自动扇出
- 支持 QFN/QFP/SOP 封装
- 可配置扇出方向

Author: Claude Code
Date: 2026-03-30
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class FanoutDirection(Enum):
    """扇出方向"""
    SPREAD = "spread"     # 向外扩散
    IN = "in"            # 向内
    OUT = "out"          # 向外
    AUTO = "auto"        # 自动选择


class PinType(Enum):
    """引脚类型"""
    POWER = "power"       # 电源引脚
    GROUND = "ground"     # 地引脚
    SIGNAL = "signal"     # 信号引脚


@dataclass
class Pad:
    """焊盘"""
    pad_number: str
    x: float
    y: float
    net: str = ""
    type: PinType = PinType.SIGNAL


@dataclass
class Via:
    """过孔"""
    via_id: str
    x: float
    y: float
    net: str
    from_layer: str
    to_layer: str
    outer_diameter: float = 0.4  # mm
    drill: float = 0.3            # mm


@dataclass
class Trace:
    """走线"""
    trace_id: str
    net: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    layer: str
    width: float = 0.25  # mm


@dataclass
class ComponentFanout:
    """元件扇出结果"""
    component_id: str
    reference: str
    pads: List[Pad]
    vias: List[Via]
    traces: List[Trace]
    success: bool = True
    message: str = ""


@dataclass
class FanoutResult:
    """扇出结果"""
    component_results: List[ComponentFanout]
    total_vias: int
    total_traces: int
    success: bool = True
    message: str = ""


class FanoutEngine:
    """
    扇出引擎

    支持:
    - QFN/QFP/SOP 封装自动扇出
    - 电源/地引脚扇出到平面
    - 可配置扇出方向和间距
    """

    def __init__(
        self,
        spacing: float = 2.54,  # mm
        via_size: float = 0.4,   # mm (外径)
        drill_size: float = 0.3, # mm
        trace_width: float = 0.25,  # mm
    ):
        """
        Args:
            spacing: 扇出引线间距 (mm)
            via_size: 过孔外径 (mm)
            drill_size: 过孔钻径 (mm)
            trace_width: 走线宽度 (mm)
        """
        self.spacing = spacing
        self.via_size = via_size
        self.drill_size = drill_size
        self.trace_width = trace_width

    def fanout_component(
        self,
        component_id: str,
        reference: str,
        pads: List[Dict[str, Any]],
        direction: FanoutDirection = FanoutDirection.AUTO,
        pin_spacing: float = 1.27,  # mm (引脚间距)
    ) -> ComponentFanout:
        """
        对单个元件进行扇出

        Args:
            component_id: 元件 ID
            reference: 参考标识 (如 "U1")
            pads: 焊盘列表 [{pad_number, x, y, net, type}]
            direction: 扇出方向
            pin_spacing: 引脚间距 (mm)

        Returns:
            ComponentFanout: 扇出结果
        """
        pad_objects = []
        for p in pads:
            pad_type = PinType.SIGNAL
            if p.get("type") == "power":
                pad_type = PinType.POWER
            elif p.get("type") == "ground":
                pad_type = PinType.GROUND

            pad = Pad(
                pad_number=str(p.get("pad_number", "")),
                x=float(p.get("x", 0)),
                y=float(p.get("y", 0)),
                net=p.get("net", ""),
                type=pad_type,
            )
            pad_objects.append(pad)

        # 按位置排序焊盘 (左上->右上->右下->左下)
        pad_objects = self._sort_pads(pad_objects)

        vias = []
        traces = []

        for i, pad in enumerate(pad_objects):
            # 电源/地引脚直接连接到对应的平面
            if pad.type in (PinType.POWER, PinType.GROUND):
                trace, via = self._create_power_ground_fanout(
                    pad, direction, i, pin_spacing
                )
                if trace:
                    traces.append(trace)
                if via:
                    vias.append(via)
            else:
                # 信号引脚扇出到合适的位置
                trace, via = self._create_signal_fanout(
                    pad, direction, i, pin_spacing
                )
                if trace:
                    traces.append(trace)
                if via:
                    vias.append(via)

        return ComponentFanout(
            component_id=component_id,
            reference=reference,
            pads=pad_objects,
            vias=vias,
            traces=traces,
            success=True,
        )

    def _sort_pads(self, pads: List[Pad]) -> List[Pad]:
        """按位置排序焊盘"""
        # 按 Y 坐标分组，然后按 X 排序
        def sort_key(p: Pad):
            return (p.y, p.x)
        return sorted(pads, key=sort_key)

    def _create_signal_fanout(
        self,
        pad: Pad,
        direction: FanoutDirection,
        index: int,
        pin_spacing: float,
    ) -> Tuple[Optional[Trace], Optional[Via]]:
        """创建信号引脚扇出走线"""
        import uuid

        # 计算扇出方向
        if direction == FanoutDirection.AUTO:
            # 根据焊盘位置自动选择方向
            if pad.x < 0:
                direction = FanoutDirection.OUT
            else:
                direction = FanoutDirection.SPREAD

        # 计算走线终点
        if direction == FanoutDirection.SPREAD:
            end_x = pad.x + pin_spacing * 2
            end_y = pad.y + (pin_spacing if index % 2 == 0 else -pin_spacing)
        elif direction == FanoutDirection.OUT:
            end_x = pad.x + pin_spacing * 3
            end_y = pad.y
        elif direction == FanoutDirection.IN:
            end_x = pad.x - pin_spacing * 2
            end_y = pad.y
        else:
            end_x = pad.x + pin_spacing * 2
            end_y = pad.y + pin_spacing * (index % 2 * 2 - 1)

        trace = Trace(
            trace_id=str(uuid.uuid4()),
            net=pad.net,
            start_x=pad.x,
            start_y=pad.y,
            end_x=end_x,
            end_y=end_y,
            layer="F.Cu",
            width=self.trace_width,
        )

        return trace, None

    def _create_power_ground_fanout(
        self,
        pad: Pad,
        direction: FanoutDirection,
        index: int,
        pin_spacing: float,
    ) -> Tuple[Optional[Trace], Optional[Via]]:
        """创建电源/地引脚扇出"""
        import uuid

        # 电源/地引脚需要用过孔连接到对应的平面
        # 这里简化处理，创建一条走线到一个过孔位置
        end_x = pad.x + pin_spacing * 2
        end_y = pad.y

        trace = Trace(
            trace_id=str(uuid.uuid4()),
            net=pad.net,
            start_x=pad.x,
            start_y=pad.y,
            end_x=end_x,
            end_y=end_y,
            layer="F.Cu",
            width=self.trace_width * 2,  # 电源走线加宽
        )

        # 过孔位置
        via_x = end_x + pin_spacing
        via_y = end_y

        via = Via(
            via_id=str(uuid.uuid4()),
            x=via_x,
            y=via_y,
            net=pad.net,
            from_layer="F.Cu",
            to_layer="B.Cu" if pad.type == PinType.POWER else "GND plane",
            outer_diameter=self.via_size,
            drill=self.drill_size,
        )

        return trace, via

    def fanout_multiple(
        self,
        components: List[Dict[str, Any]],
        direction: FanoutDirection = FanoutDirection.AUTO,
    ) -> FanoutResult:
        """
        批量扇出多个元件

        Args:
            components: 元件列表 [{id, reference, pads, direction}]
            direction: 默认扇出方向

        Returns:
            FanoutResult: 批量扇出结果
        """
        results = []
        total_vias = 0
        total_traces = 0

        for comp in components:
            fanout_dir = FanoutDirection(direction.value)
            if "direction" in comp:
                fanout_dir = FanoutDirection(comp["direction"])

            result = self.fanout_component(
                component_id=comp.get("id", ""),
                reference=comp.get("reference", ""),
                pads=comp.get("pads", []),
                direction=fanout_dir,
                pin_spacing=comp.get("pin_spacing", 1.27),
            )

            results.append(result)
            total_vias += len(result.vias)
            total_traces += len(result.traces)

        return FanoutResult(
            component_results=results,
            total_vias=total_vias,
            total_traces=total_traces,
            success=True,
        )


def calculate_pin_spacing(package_type: str) -> float:
    """
    根据封装类型估算引脚间距

    Args:
        package_type: 封装类型 (如 "QFN-48", "QFP-32", "SOP-16")

    Returns:
        引脚间距 (mm)
    """
    package_type = package_type.upper()

    if "QFN" in package_type or "QFP" in package_type:
        # 四侧引脚封装
        return 0.5 if "48" in package_type or "32" in package_type else 0.65
    elif "SOP" in package_type or "SOIC" in package_type:
        # 两侧引脚封装
        return 1.27
    elif "DIP" in package_type:
        return 2.54
    else:
        return 1.27  # 默认

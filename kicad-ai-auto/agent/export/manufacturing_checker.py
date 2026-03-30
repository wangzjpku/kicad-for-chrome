"""
Manufacturing Checker - 制造可行性检查

Phase 5: 检查 PCB 设计是否符合各制造商的制程能力

Author: Claude Code
Date: 2026-03-30
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Manufacturer(Enum):
    """制造商枚举"""
    JLCPCB = "jlcpcb"
    PCBWAY = "pcbway"
    SEEED = "seeed"
    GENERIC = "generic"


@dataclass
class ManufacturingRule:
    """制造规则"""
    name: str
    description: str
    min_value: float = 0
    max_value: float = float('inf')
    unit: str = ""


@dataclass
class ManufacturingViolation:
    """制造违规"""
    rule_name: str
    severity: str  # error, warning, info
    message: str
    location: str = ""
    current_value: float = 0
    required_range: str = ""


@dataclass
class ManufacturingReport:
    """制造可行性报告"""
    manufacturer: str
    passed: bool
    errors: List[ManufacturingViolation] = field(default_factory=list)
    warnings: List[ManufacturingViolation] = field(default_factory=list)
    infos: List[ManufacturingViolation] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_violations(self) -> int:
        return len(self.errors) + len(self.warnings)


class JLCPCBRules:
    """JLCPCB 制程能力规则"""

    # 最小线宽 (mm)
    MIN_LINE_WIDTH = 0.127

    # 最小间距 (mm)
    MIN_CLEARANCE = 0.127

    # 最小过孔钻孔 (mm)
    MIN_VIA_DRILL = 0.3

    # 最小过孔外径 (mm)
    MIN_VIA_OUTER = 0.45

    # 最小焊环 (mm)
    MIN_ANNULAR_RING = 0.15

    # 最小阻焊桥 (mm)
    MIN_SOLDER_BRIDGE = 0.1

    # 最小丝印线宽 (mm)
    MIN_SILK_WIDTH = 0.15

    # 最大板厚 (mm)
    MAX_BOARD_THICKNESS = 3.2

    # 最小板厚 (mm)
    MIN_BOARD_THICKNESS = 0.4

    # 板厚孔径比
    MAX_ASPECT_RATIO = 8.0

    # 支持的封装
    SUPPORTED_FOOTPRINTS = {
        "SOP", "QFP", "QFN", "BGA", "SOT-23", "SOT-223",
        "0805", "0603", "0402", "0201", "01005",
        "DIP", "PLCC", "LGA", "BGA",
    }

    # 不支持的封装 (需要特殊工艺)
    RESTRICTED_FOOTPRINTS = {
        "BGA": "BGA requires special tooling, extra cost",
        "01005": "01005 requires premium service",
    }


class PCBWayRules:
    """PCBWay 制程能力规则"""

    MIN_LINE_WIDTH = 0.15
    MIN_CLEARANCE = 0.15
    MIN_VIA_DRILL = 0.2
    MIN_VIA_OUTER = 0.4
    MIN_ANNULAR_RING = 0.15
    MIN_SOLDER_BRIDGE = 0.1
    MIN_SILK_WIDTH = 0.12
    MAX_BOARD_THICKNESS = 6.0
    MIN_BOARD_THICKNESS = 0.4
    MAX_ASPECT_RATIO = 10.0


class ManufacturingChecker:
    """
    制造可行性检查器

    支持:
    - JLCPCB
    - PCBWay
    - 通用制造能力
    """

    def __init__(self, pcb_data: Dict[str, Any]):
        """
        Args:
            pcb_data: PCB 数据
        """
        self.pcb_data = pcb_data
        self.tracks = pcb_data.get("tracks", [])
        self.vias = pcb_data.get("vias", [])
        self.components = pcb_data.get("components", [])

    def check_jlcpcb(self) -> ManufacturingReport:
        """检查是否符合 JLCPCB 制造能力"""
        return self._check(JLCPCBRules, "JLCPCB")

    def check_pcbway(self) -> ManufacturingReport:
        """检查是否符合 PCBWay 制造能力"""
        return self._check(PCBWayRules, "PCBWay")

    def check_generic(self) -> ManufacturingReport:
        """检查是否符合通用制造能力"""
        rules = type('GenericRules', (), {
            'MIN_LINE_WIDTH': 0.15,
            'MIN_CLEARANCE': 0.15,
            'MIN_VIA_DRILL': 0.3,
            'MIN_VIA_OUTER': 0.5,
            'MIN_ANNULAR_RING': 0.2,
            'MIN_SOLDER_BRIDGE': 0.15,
            'MIN_SILK_WIDTH': 0.2,
            'MAX_BOARD_THICKNESS': 3.2,
            'MIN_BOARD_THICKNESS': 0.6,
            'MAX_ASPECT_RATIO': 8.0,
        })()
        return self._check(rules, "Generic")

    def _check(self, rules: Any, manufacturer: str) -> ManufacturingReport:
        """执行制造检查"""
        errors = []
        warnings = []
        infos = []

        # 检查线宽
        for track in self.tracks:
            width = track.get("width", 0)
            if width < rules.MIN_LINE_WIDTH:
                errors.append(ManufacturingViolation(
                    rule_name="min_line_width",
                    severity="error",
                    message=f"Track width {width:.3f}mm is below minimum {rules.MIN_LINE_WIDTH}mm",
                    location=f"Track {track.get('id', 'unknown')}",
                    current_value=width,
                    required_range=f">={rules.MIN_LINE_WIDTH}mm",
                ))
            elif width < rules.MIN_LINE_WIDTH * 1.5:
                warnings.append(ManufacturingViolation(
                    rule_name="min_line_width",
                    severity="warning",
                    message=f"Track width {width:.3f}mm is close to minimum",
                    location=f"Track {track.get('id', 'unknown')}",
                    current_value=width,
                    required_range=f">={rules.MIN_LINE_WIDTH}mm",
                ))

        # 检查过孔
        for via in self.vias:
            drill = via.get("drill_diameter", 0)
            outer = via.get("outer_diameter", 0)

            if drill < rules.MIN_VIA_DRILL:
                errors.append(ManufacturingViolation(
                    rule_name="min_via_drill",
                    severity="error",
                    message=f"Via drill {drill:.3f}mm is below minimum {rules.MIN_VIA_DRILL}mm",
                    location=f"Via at ({via.get('x', 0)}, {via.get('y', 0)})",
                    current_value=drill,
                    required_range=f">={rules.MIN_VIA_DRILL}mm",
                ))

            if outer < rules.MIN_VIA_OUTER:
                errors.append(ManufacturingViolation(
                    rule_name="min_via_outer",
                    severity="error",
                    message=f"Via outer diameter {outer:.3f}mm is below minimum {rules.MIN_VIA_OUTER}mm",
                    location=f"Via at ({via.get('x', 0)}, {via.get('y', 0)})",
                    current_value=outer,
                    required_range=f">={rules.MIN_VIA_OUTER}mm",
                ))

            # 检查焊环
            annular_ring = (outer - drill) / 2
            if annular_ring < rules.MIN_ANNULAR_RING:
                errors.append(ManufacturingViolation(
                    rule_name="min_annular_ring",
                    severity="error",
                    message=f"Annular ring {annular_ring:.3f}mm is below minimum {rules.MIN_ANNULAR_RING}mm",
                    location=f"Via at ({via.get('x', 0)}, {via.get('y', 0)})",
                    current_value=annular_ring,
                    required_range=f">={rules.MIN_ANNULAR_RING}mm",
                ))

        # 检查板厚
        thickness = self.pcb_data.get("thickness", 1.6)
        if thickness < rules.MIN_BOARD_THICKNESS:
            errors.append(ManufacturingViolation(
                rule_name="board_thickness",
                severity="error",
                message=f"Board thickness {thickness}mm is below minimum {rules.MIN_BOARD_THICKNESS}mm",
                current_value=thickness,
                required_range=f"{rules.MIN_BOARD_THICKNESS}-{rules.MAX_BOARD_THICKNESS}mm",
            ))
        elif thickness > rules.MAX_BOARD_THICKNESS:
            errors.append(ManufacturingViolation(
                rule_name="board_thickness",
                severity="error",
                message=f"Board thickness {thickness}mm exceeds maximum {rules.MAX_BOARD_THICKNESS}mm",
                current_value=thickness,
                required_range=f"{rules.MIN_BOARD_THICKNESS}-{rules.MAX_BOARD_THICKNESS}mm",
            ))

        # 检查板厚孔径比
        if self.vias and thickness > 0:
            max_drill = max((v.get("drill_diameter", 0) for v in self.vias), default=0)
            aspect_ratio = thickness / max_drill if max_drill > 0 else 0
            if aspect_ratio > rules.MAX_ASPECT_RATIO:
                errors.append(ManufacturingViolation(
                    rule_name="aspect_ratio",
                    severity="error",
                    message=f"Aspect ratio {aspect_ratio:.1f}:1 exceeds maximum {rules.MAX_ASPECT_RATIO}:1",
                    current_value=aspect_ratio,
                    required_range=f"<={rules.MAX_ASPECT_RATIO}:1",
                ))

        # 检查封装支持
        for comp in self.components:
            footprint = comp.get("footprint", "")
            for restricted, reason in JLCPCBRules.RESTRICTED_FOOTPRINTS.items():
                if restricted in footprint.upper():
                    warnings.append(ManufacturingViolation(
                        rule_name="restricted_footprint",
                        severity="warning",
                        message=f"Footprint {footprint}: {reason}",
                        location=f"Component {comp.get('reference', 'unknown')}",
                    ))

        # 生成摘要
        summary = {
            "total_tracks": len(self.tracks),
            "total_vias": len(self.vias),
            "total_components": len(self.components),
            "board_thickness": thickness,
            "board_layers": self.pcb_data.get("layers", 2),
            "board_width": self.pcb_data.get("width", 0),
            "board_height": self.pcb_data.get("height", 0),
        }

        passed = len(errors) == 0

        return ManufacturingReport(
            manufacturer=manufacturer,
            passed=passed,
            errors=errors,
            warnings=warnings,
            infos=infos,
            summary=summary,
        )

    def get_cost_estimate(self, manufacturer: str = "jlcpcb") -> Dict[str, Any]:
        """
        获取制造费用估算

        Args:
            manufacturer: 制造商

        Returns:
            Dict: 费用估算
        """
        width = self.pcb_data.get("width", 100)
        height = self.pcb_data.get("height", 80)
        layers = self.pcb_data.get("layers", 2)
        thickness = self.pcb_data.get("thickness", 1.6)
        quantity = 5  # 默认数量

        # 计算面积 (mm^2 -> cm^2)
        area_cm2 = (width * height) / 100

        # 基础价格 (JLCPCB 5片起)
        if manufacturer == "jlcpcb":
            base_price = 2.0  # 2美元起
            per_cm2 = 0.01
            layer_multiplier = 1.5 if layers == 4 else (2.0 if layers == 6 else 1.0)
        elif manufacturer == "pcbway":
            base_price = 5.0
            per_cm2 = 0.015
            layer_multiplier = 1.4 if layers == 4 else (1.8 if layers == 6 else 1.0)
        else:
            base_price = 5.0
            per_cm2 = 0.02
            layer_multiplier = 1.5 if layers > 2 else 1.0

        unit_price = base_price + (area_cm2 * per_cm2 * layer_multiplier)
        total_price = unit_price * quantity

        return {
            "manufacturer": manufacturer,
            "dimensions": f"{width}x{height}mm",
            "layers": layers,
            "thickness": f"{thickness}mm",
            "quantity": quantity,
            "unit_price_usd": round(unit_price, 2),
            "total_price_usd": round(total_price, 2),
            "currency": "USD",
        }

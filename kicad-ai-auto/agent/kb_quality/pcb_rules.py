# -*- coding: utf-8 -*-
"""
PCB 制程规则

定义 PCB 可制造性规则，用于全链路验证中的 PCB 制程检查。
包含 JLCPCB、嘉立创、捷配等主流 PCB 厂家的制程约束。
"""

from dataclasses import dataclass
from typing import Dict, Any


# ─── JLCPCB 制程规则 ───────────────────────────────────────────────

JLC_RULES = {
    # 最小线宽 (mm)
    "min_track_width": 0.127,
    # 最小间距 (mm)
    "min_clearance": 0.127,
    # 最小过孔钻孔直径 (mm)
    "min_via_drill": 0.3,
    # 最小过孔外径 (mm)
    "min_via_outer": 0.6,
    # 最小铜环 (mm)
    "min_annular_ring": 0.15,
    # 最小阻焊开窗 (mm)
    "min_solder_mask_bridge": 0.15,
    # 最小字符线宽 (mm)
    "min_silkscreen_width": 0.15,
    # 最小字符高度 (mm)
    "min_silkscreen_height": 1.0,
    # 最小锣槽尺寸 (mm)
    "min_cNC_depth": 0.8,
    "min_cNC_width": 1.0,
    # 最小铜面积 (mm²)
    "min_copper_area": 0.2,
    # 最小邮票孔直径 (mm)
    "min_hole_diameter": 0.3,
    # 板厚选项 (mm)
    "board_thickness_options": [0.8, 1.0, 1.2, 1.6, 2.0],
    # 默认板厚
    "default_board_thickness": 1.6,
    # 铜厚选项 (oz)
    "copper_weight_options": [0.5, 1.0, 2.0],
    # 默认铜厚
    "default_copper_weight": 1.0,
    # 最小线宽覆盖（预防 DRC 误报的安全系数）
    "safe_track_width": 0.15,
    "safe_clearance": 0.15,
}

# ─── 嘉立创 SMT 规则 ───────────────────────────────────────────────

JLC_SMT_RULES = {
    # 最小引脚间距 (mm)
    "min_pin_pitch": 0.35,
    # QFP/BGA 最小引脚间距
    "min_qfp_pitch": 0.4,
    "min_bga_pitch": 0.5,
    # 最小 BGA 球径
    "min_bga_ball_diameter": 0.25,
    # QFN/DFN 散热焊盘要求
    "qfn_thermal_pad_required": True,
    "qfn_thermal_via_pitch": 1.27,
    # 阻容最小封装
    "min_resistor_size": "0402",
    "min_capacitor_size": "0402",
    # IC 封装支持列表
    "supported_packages": [
        "SOP", "SSOP", "TSSOP", "QFP", "LQFP",
        "QFN", "DFN", "DIP",
        "BGA", "CSP",
        "SOT-23", "SOT-223", "SOT-89",
        "TO-92", "TO-220", "TO-263",
        "0603", "0805", "1206", "0402", "0201",
    ],
    # 不支持的封装（引脚间距过密的 BGA 可能不被支持）
    "unsupported_packages": [],
}

# ─── 通用设计规则 ───────────────────────────────────────────────────

GENERIC_PCB_RULES = {
    "min_track_width": 0.15,
    "min_clearance": 0.15,
    "min_via_drill": 0.3,
    "min_via_outer": 0.5,
    "min_annular_ring": 0.15,
    "min_solder_mask_bridge": 0.1,
    "min_silkscreen_width": 0.1,
    "min_silkscreen_height": 0.8,
    "impedance_tolerance": 0.1,   # 阻抗公差 ±10%
    "via_in_pad_allowed": False,
}


@dataclass
class PCBCheckIssue:
    """PCB 规则检查问题"""

    code: str
    severity: str   # error, warning, info
    message: str
    location: str = ""
    value: str = ""
    rule: str = ""


class PCBRulesChecker:
    """
    PCB 制程规则检查器。

    使用方法:
        checker = PCBRulesChecker(fab="jlcpcb")
        issues = checker.check_pcb(pcb_data)
        for issue in issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
    """

    def __init__(self, fab: str = "jlcpcb"):
        """
        Args:
            fab: 板厂名称 ("jlcpcb", "generic")
        """
        self.rules = self._load_rules(fab)

    def _load_rules(self, fab: str) -> Dict[str, Any]:
        if fab == "jlcpcb":
            return {**GENERIC_PCB_RULES, **JLC_RULES, **JLC_SMT_RULES}
        return GENERIC_PCB_RULES

    def check_pcb(self, pcb_data: Dict[str, Any]) -> list:
        """
        检查 PCB 数据的可制造性。

        Args:
            pcb_data: PCB 数据（来自 schematic_data.json 或 KiCad IPC）

        Returns:
            PCBCheckIssue 列表
        """
        issues = []

        # 检查布线
        tracks = pcb_data.get("tracks", [])
        for track in tracks:
            issues.extend(self._check_track(track))

        # 检查过孔
        vias = pcb_data.get("vias", [])
        for via in vias:
            issues.extend(self._check_via(via))

        # 检查封装
        modules = pcb_data.get("modules", [])
        for module in modules:
            issues.extend(self._check_footprint(module))

        return issues

    def _check_track(self, track: Dict[str, Any]) -> list:
        issues = []
        width = track.get("width", 0)
        if width < self.rules["min_track_width"]:
            issues.append(PCBCheckIssue(
                code="TRACK_WIDTH_TOO_NARROW",
                severity="error",
                message=f"Track width {width}mm is below minimum {self.rules['min_track_width']}mm",
                location=track.get("net", ""),
                value=f"{width}mm",
                rule="min_track_width",
            ))
        return issues

    def _check_via(self, via: Dict[str, Any]) -> list:
        issues = []
        drill = via.get("drill", 0)
        outer = via.get("width", via.get("diameter", 0))

        if drill < self.rules["min_via_drill"]:
            issues.append(PCBCheckIssue(
                code="VIA_DRILL_TOO_SMALL",
                severity="error",
                message=f"Via drill {drill}mm is below minimum {self.rules['min_via_drill']}mm",
                value=f"{drill}mm",
                rule="min_via_drill",
            ))

        annular_ring = (outer - drill) / 2
        if annular_ring < self.rules["min_annular_ring"]:
            issues.append(PCBCheckIssue(
                code="ANNULAR_RING_TOO_NARROW",
                severity="error",
                message=f"Annular ring {annular_ring:.3f}mm is below minimum {self.rules['min_annular_ring']}mm",
                value=f"{annular_ring:.3f}mm",
                rule="min_annular_ring",
            ))

        return issues

    def _check_footprint(self, module: Dict[str, Any]) -> list:
        issues = []
        footprint = module.get("footprint", "")

        if not footprint:
            issues.append(PCBCheckIssue(
                code="MISSING_FOOTPRINT",
                severity="error",
                message="Module has no footprint assigned",
                location=module.get("ref", ""),
            ))

        # 检查封装是否在支持列表中
        supported = self.rules.get("supported_packages", [])
        unsupported = self.rules.get("unsupported_packages", [])

        if unsupported:
            for pkg in unsupported:
                if pkg and pkg in footprint:
                    issues.append(PCBCheckIssue(
                        code="UNSUPPORTED_PACKAGE",
                        severity="error",
                        message=f"Package '{pkg}' may not be supported by manufacturer",
                        location=module.get("ref", ""),
                        value=footprint,
                    ))

        return issues

    def validate_design_rules(self, pcb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证 PCB 设计规则，返回详细报告。

        Returns:
            {
                "passed": bool,
                "errors": [...],
                "warnings": [...],
                "summary": {...}
            }
        """
        issues = self.check_pcb(pcb_data)

        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        info = [i for i in issues if i.severity == "info"]

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "summary": {
                "total_issues": len(issues),
                "errors": len(errors),
                "warnings": len(warnings),
                "info": len(info),
                "fab": list(self.rules.keys())[:3],
            },
        }

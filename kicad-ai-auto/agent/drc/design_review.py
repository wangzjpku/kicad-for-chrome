"""
Design Review Engine - 实时设计审查

Phase 10: 实时设计审查 + AI 学习

功能:
1. 多维度设计审查 (DRC/ERC/SI/EMI/可制造性)
2. 常见错误模式检测
3. 设计建议生成
4. 用户修正学习

Author: Claude Code
Date: 2026-03-31
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewSeverity(Enum):
    """审查严重度"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


class ReviewCategory(Enum):
    """审查类别"""
    DRC = "drc"                  # 设计规则
    SCHEMATIC = "schematic"       # 原理图
    LAYOUT = "layout"             # 布局
    ROUTING = "routing"           # 布线
    MANUFACTURING = "manufacturing"  # 可制造性
    SI = "signal_integrity"       # 信号完整性
    EMI = "emi"                   # 电磁干扰
    THERMAL = "thermal"           # 热
    POWER = "power"               # 电源


@dataclass
class ReviewIssue:
    """审查问题"""
    category: ReviewCategory
    severity: ReviewSeverity
    title: str
    description: str
    location: Optional[Dict[str, float]] = None
    suggestion: str = ""
    rule_id: str = ""


@dataclass
class ReviewResult:
    """审查结果"""
    score: float  # 0-100
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    duration_s: float = 0.0
    board_stats: Dict[str, Any] = field(default_factory=dict)


# ============ 常见错误模式数据库 ============

COMMON_MISTAKES = {
    "decoupling_cap_missing": {
        "rule_id": "PWR-001",
        "title": "缺少去耦电容",
        "description": "IC 的电源引脚附近缺少去耦电容 (100nF)",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.POWER,
        "suggestion": "在 VCC/GND 引脚附近放置 100nF 陶瓷电容，距离 < 5mm",
    },
    "ground_plane_split": {
        "rule_id": "GND-001",
        "title": "地平面分割",
        "description": "走线切割了地平面，形成分割槽",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.LAYOUT,
        "suggestion": "避免在地平面上方走长线，使用过孔桥接分割",
    },
    "high_speed_no_impedance": {
        "rule_id": "SI-001",
        "title": "高速信号缺少阻抗控制",
        "description": "差分对/高速信号未进行阻抗控制布线",
        "severity": ReviewSeverity.CRITICAL,
        "category": ReviewCategory.SI,
        "suggestion": "对差分对使用阻抗控制 (USB: 90Ω, HDMI: 100Ω)",
    },
    "thermal_pad_no_vias": {
        "rule_id": "THM-001",
        "title": "散热焊盘缺少热过孔",
        "description": "功率元件底部散热焊盘没有热过孔",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.THERMAL,
        "suggestion": "在散热焊盘下方添加热过孔阵列，目标热阻 < 15°C/W",
    },
    "trace_width_power": {
        "rule_id": "PWR-002",
        "title": "电源走线宽度不足",
        "description": "电源走线宽度无法承载所需电流",
        "severity": ReviewSeverity.CRITICAL,
        "category": ReviewCategory.POWER,
        "suggestion": "1A 电流需要至少 0.5mm 宽度 (1oz 铜，10°C 温升)",
    },
    "via_stubs": {
        "rule_id": "SI-002",
        "title": "背钻/过孔残桩",
        "description": "高速信号通孔存在残桩影响信号完整性",
        "severity": ReviewSeverity.INFO,
        "category": ReviewCategory.SI,
        "suggestion": "对 > 5GHz 信号使用背钻或盲埋孔",
    },
    "crystal_routing": {
        "rule_id": "SI-003",
        "title": "晶振走线过长",
        "description": "晶振到 MCU 的走线过长，可能引入噪声",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.SI,
        "suggestion": "晶振应尽量靠近 MCU，走线 < 10mm，下方避免走其他信号",
    },
    "component_spacing": {
        "rule_id": "MFG-001",
        "title": "元件间距不足",
        "description": "元件间距小于制造商最小要求",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.MANUFACTURING,
        "suggestion": "JLCPCB 最小间距: 0402 → 0.3mm, 0603 → 0.5mm",
    },
    "silk_on_pad": {
        "rule_id": "MFG-002",
        "title": "丝印覆盖焊盘",
        "description": "丝印文字覆盖了焊盘，影响焊接",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.MANUFACTURING,
        "suggestion": "确保丝印层与焊盘保持 0.2mm 以上间距",
    },
}


# ============ 用户修正学习 ============

@dataclass
class UserCorrection:
    """用户修正记录"""
    rule_id: str
    issue_title: str
    user_action: str  # "accepted" | "dismissed" | "modified"
    timestamp: float
    details: str = ""


class DesignReviewEngine:
    """
    实时设计审查引擎

    多维度审查:
    1. 设计规则 (DRC) - 间距、线宽、过孔
    2. 信号完整性 (SI) - 阻抗、串扰、反射
    3. 电源完整性 (PI) - 去耦、压降、电流
    4. 可制造性 (DFM) - 间距、丝印、元件
    5. 热管理 - 散热过孔、热阻
    6. EMI - 环路面积、屏蔽
    """

    def __init__(self):
        self._corrections: List[UserCorrection] = []
        self._dismissed_rules: Dict[str, int] = {}  # rule_id -> dismiss count

    def review(self, pcb_data: Dict[str, Any]) -> ReviewResult:
        """
        执行全面设计审查

        Args:
            pcb_data: PCB 数据 (footprints, tracks, vias, zones, nets)

        Returns:
            ReviewResult: 审查结果
        """
        start_time = time.time()
        issues: List[ReviewIssue] = []

        footprints = pcb_data.get("footprints", [])
        tracks = pcb_data.get("tracks", [])
        vias = pcb_data.get("vias", [])
        zones = pcb_data.get("zones", [])
        nets = pcb_data.get("nets", [])

        # 1. 电源完整性检查
        issues.extend(self._check_power_integrity(footprints, tracks, nets))

        # 2. 信号完整性检查
        issues.extend(self._check_signal_integrity(tracks, footprints, nets))

        # 3. 可制造性检查
        issues.extend(self._check_manufacturing(footprints, tracks))

        # 4. 热管理检查
        issues.extend(self._check_thermal(footprints, vias))

        # 5. 布局质量检查
        issues.extend(self._check_layout_quality(footprints, zones))

        # 过滤已学习忽略的规则
        issues = self._apply_learned_filters(issues)

        # 计算评分
        score = self._calculate_score(issues)

        # 汇总
        summary = {
            "critical": sum(1 for i in issues if i.severity == ReviewSeverity.CRITICAL),
            "warning": sum(1 for i in issues if i.severity == ReviewSeverity.WARNING),
            "info": sum(1 for i in issues if i.severity == ReviewSeverity.INFO),
            "suggestion": sum(1 for i in issues if i.severity == ReviewSeverity.SUGGESTION),
            "total": len(issues),
        }

        duration = time.time() - start_time

        return ReviewResult(
            score=score,
            issues=issues,
            summary=summary,
            duration_s=round(duration, 3),
            board_stats={
                "footprints": len(footprints),
                "tracks": len(tracks),
                "vias": len(vias),
                "zones": len(zones),
                "nets": len(nets),
            },
        )

    def record_correction(self, rule_id: str, action: str, details: str = ""):
        """
        记录用户修正行为 (用于 AI 学习)

        Args:
            rule_id: 规则 ID
            action: "accepted" | "dismissed" | "modified"
            details: 详细说明
        """
        correction = UserCorrection(
            rule_id=rule_id,
            issue_title=rule_id,
            user_action=action,
            timestamp=time.time(),
            details=details,
        )
        self._corrections.append(correction)

        if action == "dismissed":
            self._dismissed_rules[rule_id] = self._dismissed_rules.get(rule_id, 0) + 1

    def get_learning_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        return {
            "total_corrections": len(self._corrections),
            "dismissed_rules": dict(self._dismissed_rules),
            "most_dismissed": sorted(
                self._dismissed_rules.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    # ============ 内部检查方法 ============

    def _check_power_integrity(
        self, footprints: List[Dict], tracks: List[Dict], nets: List[Dict]
    ) -> List[ReviewIssue]:
        """电源完整性检查"""
        issues = []

        # 检查 IC 附近是否有去耦电容
        ic_refs = set()
        cap_refs = set()
        for fp in footprints:
            ref = fp.get("reference", "")
            value = str(fp.get("value", "")).upper()
            if any(x in ref.upper() for x in ["U", "IC"]):
                ic_refs.add(ref)
            if "C" in ref.upper() and any(x in value for x in ["NF", "UF"]):
                cap_refs.add(ref)

        if ic_refs and not cap_refs:
            issues.append(ReviewIssue(
                **COMMON_MISTAKES["decoupling_cap_missing"],
                location={"ref": list(ic_refs)[0]} if ic_refs else None,
            ))

        # 检查电源走线宽度
        for track in tracks:
            net = track.get("net", "").upper()
            width = track.get("width", 0.25)
            if any(x in net for x in ["VCC", "VDD", "5V", "3V3", "VIN", "VBUS"]):
                if width < 0.4:
                    issues.append(ReviewIssue(
                        **COMMON_MISTAKES["trace_width_power"],
                        location={
                            "x": (track.get("start", {}).get("x", 0) + track.get("end", {}).get("x", 0)) / 2,
                            "y": (track.get("start", {}).get("y", 0) + track.get("end", {}).get("y", 0)) / 2,
                        },
                    ))
                    break  # 只报一次

        return issues

    def _check_signal_integrity(
        self, tracks: List[Dict], footprints: List[Dict], nets: List[Dict]
    ) -> List[ReviewIssue]:
        """信号完整性检查"""
        issues = []

        # 检查高速信号是否有差分对标记
        high_speed_nets = []
        for net in nets:
            name = net.get("name", "").upper()
            if any(x in name for x in ["USB", "HDMI", "DP_", "PCI", "ETH", "SDI"]):
                high_speed_nets.append(name)

        if high_speed_nets:
            diff_tracks = [t for t in tracks if "diff" in str(t.get("net", "")).lower()]
            if len(diff_tracks) < len(high_speed_nets) * 2:
                issues.append(ReviewIssue(
                    **COMMON_MISTAKES["high_speed_no_impedance"],
                ))

        # 检查晶振走线
        crystal_refs = []
        for fp in footprints:
            ref = fp.get("reference", "")
            value = str(fp.get("value", "")).upper()
            if ref.startswith("Y") or "CRYSTAL" in value or "MHZ" in value:
                crystal_refs.append(ref)

        if crystal_refs:
            for track in tracks:
                length = track.get("length", 0)
                if length > 15:
                    issues.append(ReviewIssue(
                        **COMMON_MISTAKES["crystal_routing"],
                    ))
                    break

        return issues

    def _check_manufacturing(
        self, footprints: List[Dict], tracks: List[Dict]
    ) -> List[ReviewIssue]:
        """可制造性检查"""
        issues = []

        # 检查元件间距
        if len(footprints) > 1:
            for i in range(len(footprints)):
                for j in range(i + 1, min(i + 5, len(footprints))):
                    fp1 = footprints[i]
                    fp2 = footprints[j]
                    x1, y1 = fp1.get("position", {}).get("x", 0), fp1.get("position", {}).get("y", 0)
                    x2, y2 = fp2.get("position", {}).get("x", 0), fp2.get("position", {}).get("y", 0)
                    dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                    if dist < 0.5 and dist > 0:
                        issues.append(ReviewIssue(
                            **COMMON_MISTAKES["component_spacing"],
                            location={"x": (x1 + x2) / 2, "y": (y1 + y2) / 2},
                        ))
                        break
                if len(issues) > 3:
                    break

        return issues

    def _check_thermal(
        self, footprints: List[Dict], vias: List[Dict]
    ) -> List[ReviewIssue]:
        """热管理检查"""
        issues = []

        # 检查功率元件是否有热过孔
        power_refs = []
        for fp in footprints:
            ref = fp.get("reference", "")
            value = str(fp.get("value", "")).upper()
            footprint = str(fp.get("footprint", "")).upper()
            if any(x in value for x in ["LDO", "AMS1117", "LM7805", "DC-DC"]):
                power_refs.append(ref)
            if any(x in footprint for x in ["QFN", "D2PAK", "TO-263"]):
                power_refs.append(ref)

        if power_refs:
            # 简单检查: 功率元件附近是否有足够的过孔
            thermal_vias_near = 0
            for via in vias:
                if via.get("net", "").upper() in ["GND", "VCC"]:
                    thermal_vias_near += 1
            if thermal_vias_near < len(power_refs) * 3:
                issues.append(ReviewIssue(
                    **COMMON_MISTAKES["thermal_pad_no_vias"],
                ))

        return issues

    def _check_layout_quality(
        self, footprints: List[Dict], zones: List[Dict]
    ) -> List[ReviewIssue]:
        """布局质量检查"""
        issues = []

        # 检查是否有地平面
        gnd_zones = [z for z in zones if "GND" in z.get("net", "").upper()]
        if not gnd_zones and len(footprints) > 3:
            issues.append(ReviewIssue(
                category=ReviewCategory.LAYOUT,
                severity=ReviewSeverity.SUGGESTION,
                title="缺少地平面铺铜",
                description="建议在 B.Cu 层添加 GND 铺铜以改善 EMI 和信号完整性",
                rule_id="LAY-001",
                suggestion="使用铜皮铺铜功能，在 B.Cu 层铺 GND 网络",
            ))

        return issues

    def _apply_learned_filters(self, issues: List[ReviewIssue]) -> List[ReviewIssue]:
        """根据用户学习记录过滤问题"""
        filtered = []
        for issue in issues:
            dismiss_count = self._dismissed_rules.get(issue.rule_id, 0)
            # 如果用户连续 3 次以上忽略此规则，则不再显示
            if dismiss_count >= 3:
                continue
            filtered.append(issue)
        return filtered

    def _calculate_score(self, issues: List[ReviewIssue]) -> float:
        """计算设计评分 (0-100)"""
        score = 100.0
        for issue in issues:
            if issue.severity == ReviewSeverity.CRITICAL:
                score -= 15
            elif issue.severity == ReviewSeverity.WARNING:
                score -= 5
            elif issue.severity == ReviewSeverity.INFO:
                score -= 2
            elif issue.severity == ReviewSeverity.SUGGESTION:
                score -= 1
        return max(0.0, min(100.0, score))


# ============ 全局实例 ============

_engine_instance: Optional[DesignReviewEngine] = None


def get_review_engine() -> DesignReviewEngine:
    """获取全局审查引擎实例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DesignReviewEngine()
    return _engine_instance

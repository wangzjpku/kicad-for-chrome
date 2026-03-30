"""
EMI Hotspot Analyzer - EMI 热点分析器

Phase 5: 在 PCB 编辑器中高亮 EMI 问题区域

检测以下 EMI 热点:
1. 高速信号跨越分割平面 (broken reference plane)
2. 时钟线未加屏蔽 (unsupported clock lines)
3. 电源层分割造成的信号跨越 (plane splits)
4. 敏感信号走线太长 (long unfiltered traces)
5. 差分对不耦合 (differential pair coupling issues)

Author: Claude Code
Date: 2026-03-30
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class EMISeverity(Enum):
    """EMI 问题严重程度"""
    CRITICAL = "critical"   # 必须修复
    WARNING = "warning"     # 建议修复
    INFO = "info"          # 信息


class EMIHotspotType(Enum):
    """EMI 热点类型"""
    PLANE_SPLIT = "plane_split"           # 跨越分割平面
    CLOCK_UNSHIELDED = "clock_unshielded"   # 时钟线未屏蔽
    LONG_SENSITIVE_TRACE = "long_sensitive" # 敏感线过长
    DIFF_PAIR_MISMATCH = "diff_mismatch"   # 差分对不匹配
    SIGNAL_INTEGRITY = "signal_integrity"   # 信号完整性问题
    CROSSTALK = "crosstalk"               # 串扰风险
    SHIELDING_GAP = "shielding_gap"       # 屏蔽缺口


@dataclass
class EMICoordinate:
    """EMI 热点坐标"""
    x: float          # mm
    y: float         # mm
    width: float = 0  # 热点宽度 mm
    height: float = 0 # 热点高度 mm


@dataclass
class EMIHotspot:
    """EMI 热点"""
    id: str
    hotspot_type: EMIHotspotType
    severity: EMISeverity
    message: str
    suggestion: str
    location: EMICoordinate
    affected_nets: List[str]
    auto_fixable: bool = False
    layer: str = "F.Cu"


@dataclass
class EMIAnalysisReport:
    """EMI 分析报告"""
    passed: bool
    hotspots: List[EMIHotspot]
    summary: Dict[str, Any]

    @property
    def critical_count(self) -> int:
        return len([h for h in self.hotspots if h.severity == EMISeverity.CRITICAL])

    @property
    def warning_count(self) -> int:
        return len([h for h in self.hotspots if h.severity == EMISeverity.WARNING])

    @property
    def info_count(self) -> int:
        return len([h for h in self.hotspots if h.severity == EMISeverity.INFO])


class EMIHotspotAnalyzer:
    """
    EMI 热点分析器

    分析 PCB 布局，识别潜在的 EMI 问题区域
    """

    # 高速信号频率阈值 (MHz)
    HIGH_SPEED_FREQUENCY_THRESHOLD = 50

    # 时钟信号关键词
    CLOCK_KEYWORDS = ["clk", "clock", "osc", "xtal", "crystal", "hse", "lse"]

    # 敏感信号关键词
    SENSITIVE_KEYWORDS = ["usb", "eth", "pcie", "hdmi", "dp", "lvds", "uart", "i2s", "dac", "adc", "sens"]

    def __init__(self, pcb_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None):
        """
        Args:
            pcb_data: PCB 数据
            options: 分析选项
                - sensitivity: 分析灵敏度 ("high", "medium", "low")
                - include_clock: 是否检查时钟线 (默认 True)
                - include_plane_splits: 是否检查分割平面 (默认 True)
        """
        self.pcb_data = pcb_data
        self.options = options or {}
        self.sensitivity = self.options.get("sensitivity", "medium")
        self.include_clock = self.options.get("include_clock", True)
        self.include_plane_splits = self.options.get("include_plane_splits", True)

        self.tracks = pcb_data.get("tracks", [])
        self.components = pcb_data.get("components", [])
        self.zones = pcb_data.get("zones", [])
        self.vias = pcb_data.get("vias", [])

    def analyze(self) -> EMIAnalysisReport:
        """
        执行完整的 EMI 分析

        Returns:
            EMIAnalysisReport: 分析报告
        """
        hotspots = []

        # 1. 检查时钟线未屏蔽
        if self.include_clock:
            hotspots.extend(self._check_clock_lines())

        # 2. 检查跨越分割平面
        if self.include_plane_splits:
            hotspots.extend(self._check_plane_splits())

        # 3. 检查敏感信号线过长
        hotspots.extend(self._check_sensitive_traces())

        # 4. 检查差分对耦合
        hotspots.extend(self._check_diff_pair_coupling())

        # 5. 检查串扰风险
        hotspots.extend(self._check_crosstalk_risk())

        passed = not any(h.severity == EMISeverity.CRITICAL for h in hotspots)

        return EMIAnalysisReport(
            passed=passed,
            hotspots=hotspots,
            summary={
                "total_hotspots": len(hotspots),
                "critical": len([h for h in hotspots if h.severity == EMISeverity.CRITICAL]),
                "warning": len([h for h in hotspots if h.severity == EMISeverity.WARNING]),
                "info": len([h for h in hotspots if h.severity == EMISeverity.INFO]),
                "affected_nets": list(set(n for h in hotspots for n in h.affected_nets)),
            }
        )

    def _check_clock_lines(self) -> List[EMIHotspot]:
        """检查未屏蔽的时钟线"""
        hotspots = []
        hotspot_id = 1

        for track in self.tracks:
            net_name = track.get("net", "").lower()
            layer = track.get("layer", "F.Cu")
            points = track.get("points", [])

            # 检查是否是时钟信号
            is_clock = any(kw in net_name for kw in self.CLOCK_KEYWORDS)

            if not is_clock:
                continue

            # 计算走线长度
            length_mm = self._calculate_trace_length(points)

            # 时钟线超过 20mm 且没有地平面参考
            if length_mm > 20:
                # 检查是否在信号层内层（内层时钟更敏感）
                is_internal = "In" in layer

                severity = EMISeverity.WARNING if is_internal else EMISeverity.INFO
                if length_mm > 50:
                    severity = EMISeverity.CRITICAL

                hotspots.append(EMIHotspot(
                    id=f"EMI-CLK-{hotspot_id}",
                    hotspot_type=EMIHotspotType.CLOCK_UNSHIELDED,
                    severity=severity,
                    message=f"时钟信号 {net_name} 走线过长 ({length_mm:.1f}mm) 且未屏蔽",
                    suggestion="为时钟线添加地平面参考，或在走线两侧添加接地保护走线",
                    location=self._get_trace_center(points),
                    affected_nets=[net_name],
                    auto_fixable=False,
                    layer=layer,
                ))
                hotspot_id += 1

        return hotspots

    def _check_plane_splits(self) -> List[EMIHotspot]:
        """检查跨越分割平面的信号"""
        hotspots = []
        hotspot_id = 1

        # 检测电源层分割
        power_zones = [z for z in self.zones if z.get("type") == "plane" and
                      any(p in z.get("net", "").lower() for p in ["vcc", "3v", "5v", "12v", "power"])]

        # 如果没有平面区域，检查过孔附近的高速信号
        for track in self.tracks:
            net_name = track.get("net", "").lower()
            layer = track.get("layer", "F.Cu")
            points = track.get("points", [])

            # 检查是否是高速信号
            is_high_speed = any(kw in net_name for kw in ["usb", "eth", "pcie", "hdmi", "dp"])
            if not is_high_speed:
                continue

            # 检查走线是否跨越多个区域（通过检查过孔）
            vias_on_track = self._get_vias_on_track(track)

            if len(vias_on_track) > 0:
                # 跨越了多个层，可能存在平面分割
                length_mm = self._calculate_trace_length(points)

                hotspots.append(EMIHotspot(
                    id=f"EMI-SPLIT-{hotspot_id}",
                    hotspot_type=EMIHotspotType.PLANE_SPLIT,
                    severity=EMISeverity.WARNING,
                    message=f"高速信号 {net_name} 跨越多个平面层，可能存在参考平面分割",
                    suggestion="确保高速信号走线下方有完整的地平面，避免跨越电源分割",
                    location=self._get_trace_center(points),
                    affected_nets=[net_name],
                    auto_fixable=False,
                    layer=layer,
                ))
                hotspot_id += 1

        return hotspots

    def _check_sensitive_traces(self) -> List[EMIHotspot]:
        """检查敏感信号走线"""
        hotspots = []
        hotspot_id = 1

        # 敏感信号长度阈值 (mm)
        length_threshold = {"high": 30, "medium": 50, "low": 80}.get(self.sensitivity, 50)

        for track in self.tracks:
            net_name = track.get("net", "").lower()
            layer = track.get("layer", "F.Cu")
            points = track.get("points", [])

            # 检查是否是敏感信号
            is_sensitive = any(kw in net_name for kw in self.SENSITIVE_KEYWORDS)

            if not is_sensitive:
                continue

            length_mm = self._calculate_trace_length(points)

            if length_mm > length_threshold:
                severity = EMISeverity.INFO
                if length_mm > length_threshold * 2:
                    severity = EMISeverity.WARNING

                hotspots.append(EMIHotspot(
                    id=f"EMI-SENS-{hotspot_id}",
                    hotspot_type=EMIHotspotType.LONG_SENSITIVE_TRACE,
                    severity=severity,
                    message=f"敏感信号 {net_name} 走线较长 ({length_mm:.1f}mm)，易受 EMI 干扰",
                    suggestion="添加滤波电容或共模电感，缩短走线或增加屏蔽",
                    location=self._get_trace_center(points),
                    affected_nets=[net_name],
                    auto_fixable=True,
                    layer=layer,
                ))
                hotspot_id += 1

        return hotspots

    def _check_diff_pair_coupling(self) -> List[EMIHotspot]:
        """检查差分对耦合问题"""
        hotspots = []
        hotspot_id = 1

        # 检测差分对信号
        diff_pairs_seen = set()

        for track in self.tracks:
            net_name = track.get("net", "").lower()
            layer = track.get("layer", "F.Cu")
            points = track.get("points", [])

            # 检测差分对
            is_pos = any(x in net_name for x in ["_p", "_n", "+", "-", "_d", "_b"])
            is_diff = any(x in net_name for x in ["usb", "eth", "hdmi", "dp", "lvds", "pcie"])

            if not (is_pos and is_diff):
                continue

            # 找到对应的负信号
            neg_net = net_name.replace("_p", "_n").replace("_P", "_N")
            neg_net = neg_net.replace("+", "-").replace("_D", "_B")

            if neg_net in diff_pairs_seen:
                continue

            diff_pairs_seen.add(net_name)

            # 检查正负信号长度差异
            neg_track = self._find_track_by_net(neg_net)
            if not neg_track:
                # 只找到一根，警告
                hotspots.append(EMIHotspot(
                    id=f"EMI-DIFF-{hotspot_id}",
                    hotspot_type=EMIHotspotType.DIFF_PAIR_MISMATCH,
                    severity=EMISeverity.WARNING,
                    message=f"差分对 {net_name} 缺少对应的负信号走线",
                    suggestion="确保差分对正负信号成对走线，长度匹配",
                    location=self._get_trace_center(points),
                    affected_nets=[net_name, neg_net],
                    auto_fixable=False,
                    layer=layer,
                ))
                hotspot_id += 1
                continue

            # 计算长度差异
            pos_len = self._calculate_trace_length(points)
            neg_len = self._calculate_trace_length(neg_track.get("points", []))
            length_diff = abs(pos_len - neg_len)

            # 长度差异超过 0.5mm (500μm)
            if length_diff > 0.5:
                hotspots.append(EMIHotspot(
                    id=f"EMI-DIFF-{hotspot_id}",
                    hotspot_type=EMIHotspotType.DIFF_PAIR_MISMATCH,
                    severity=EMISeverity.WARNING,
                    message=f"差分对 {net_name}/{neg_net} 长度不匹配，差异 {length_diff:.2f}mm",
                    suggestion="调整走线使正负信号长度匹配，差异应小于 0.5mm",
                    location=self._get_trace_center(points),
                    affected_nets=[net_name, neg_net],
                    auto_fixable=False,
                    layer=layer,
                ))
                hotspot_id += 1

        return hotspots

    def _check_crosstalk_risk(self) -> List[EMIHotspot]:
        """检查串扰风险"""
        hotspots = []
        hotspot_id = 1

        # 查找可能产生串扰的平行走线
        sensitivity_threshold = {"high": 0.2, "medium": 0.15, "low": 0.1}.get(self.sensitivity, 0.15)

        for i, track1 in enumerate(self.tracks):
            net1 = track1.get("net", "")
            layer1 = track1.get("layer", "F.Cu")
            points1 = track1.get("points", [])
            width1 = track1.get("width", 0.2)

            for track2 in self.tracks[i+1:]:
                layer2 = track2.get("layer", "F.Cu")

                # 只检查同层走线
                if layer1 != layer2:
                    continue

                points2 = track2.get("points", [])
                width2 = track2.get("width", 0.2)

                # 检查是否有平行段
                spacing = self._calculate_min_spacing(points1, points2)

                if spacing < sensitivity_threshold:
                    net2 = track2.get("net", "")

                    hotspots.append(EMIHotspot(
                        id=f"EMI-XTALK-{hotspot_id}",
                        hotspot_type=EMIHotspotType.CROSSTALK,
                        severity=EMISeverity.INFO,
                        message=f"走线 {net1} 和 {net2} 间距过近 ({spacing*1000:.1f}mil)，存在串扰风险",
                        suggestion="增加走线间距，或在两信号间插入地线隔离",
                        location=self._get_trace_center(points1),
                        affected_nets=[net1, net2],
                        auto_fixable=True,
                        layer=layer1,
                    ))
                    hotspot_id += 1

        return hotspots

    def _find_track_by_net(self, net_name: str) -> Optional[Dict]:
        """根据网络名查找走线"""
        for track in self.tracks:
            if track.get("net", "").lower() == net_name.lower():
                return track
        return None

    def _calculate_trace_length(self, points: List[Dict]) -> float:
        """计算走线长度"""
        if len(points) < 2:
            return 0

        total_length = 0
        for i in range(len(points) - 1):
            x1, y1 = points[i].get("x", 0), points[i].get("y", 0)
            x2, y2 = points[i+1].get("x", 0), points[i+1].get("y", 0)
            total_length += math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        return total_length

    def _get_trace_center(self, points: List[Dict]) -> EMICoordinate:
        """获取走线中心点"""
        if not points:
            return EMICoordinate(x=0, y=0)

        xs = [p.get("x", 0) for p in points]
        ys = [p.get("y", 0) for p in points]

        return EMICoordinate(
            x=sum(xs) / len(xs),
            y=sum(ys) / len(ys),
        )

    def _get_vias_on_track(self, track: Dict) -> List[Dict]:
        """获取走线上的过孔"""
        track_points = track.get("points", [])
        if len(track_points) < 2:
            return []

        vias_on_track = []
        for via in self.vias:
            via_x, via_y = via.get("x", 0), via.get("y", 0)

            # 简单检查：过孔位置是否在走线范围内
            min_x = min(p.get("x", 0) for p in track_points)
            max_x = max(p.get("x", 0) for p in track_points)
            min_y = min(p.get("y", 0) for p in track_points)
            max_y = max(p.get("y", 0) for p in track_points)

            if min_x - 0.5 <= via_x <= max_x + 0.5 and min_y - 0.5 <= via_y <= max_y + 0.5:
                vias_on_track.append(via)

        return vias_on_track

    def _calculate_min_spacing(self, points1: List[Dict], points2: List[Dict]) -> float:
        """计算两条走线之间的最小间距"""
        min_spacing = float("inf")

        for p1 in points1:
            x1, y1 = p1.get("x", 0), p1.get("y", 0)
            for p2 in points2:
                x2, y2 = p2.get("x", 0), p2.get("y", 0)
                dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                min_spacing = min(min_spacing, dist)

        return min_spacing if min_spacing != float("inf") else 0

    def get_hotspots_for_visualization(self) -> List[Dict[str, Any]]:
        """
        获取用于前端可视化的热点数据

        Returns:
            List[Dict]: 热点数据，包含位置、类型、严重程度
        """
        report = self.analyze()

        visualization_data = []
        for hotspot in report.hotspots:
            # 根据严重程度设置颜色
            color_map = {
                EMISeverity.CRITICAL: "#ff0000",  # 红色
                EMISeverity.WARNING: "#ff9900",   # 橙色
                EMISeverity.INFO: "#ffcc00",      # 黄色
            }

            visualization_data.append({
                "id": hotspot.id,
                "type": hotspot.hotspot_type.value,
                "severity": hotspot.severity.value,
                "message": hotspot.message,
                "suggestion": hotspot.suggestion,
                "x": hotspot.location.x,
                "y": hotspot.location.y,
                "layer": hotspot.layer,
                "color": color_map.get(hotspot.severity, "#ffcc00"),
                "affectedNets": hotspot.affected_nets,
                "autoFixable": hotspot.auto_fixable,
            })

        return visualization_data


def analyze_pcb_emi(pcb_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> EMIAnalysisReport:
    """
    便捷函数：分析 PCB 的 EMI 热点

    Args:
        pcb_data: PCB 数据
        options: 分析选项

    Returns:
        EMIAnalysisReport: 分析报告
    """
    analyzer = EMIHotspotAnalyzer(pcb_data, options)
    return analyzer.analyze()

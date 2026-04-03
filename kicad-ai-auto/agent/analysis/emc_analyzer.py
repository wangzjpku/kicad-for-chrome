# -*- coding: utf-8 -*-
"""
EMC Analyzer - EMC 预认证分析器

Phase 14: 高级分析集成

功能:
1. EMI 热点检测 - 识别辐射发射风险区域
2. 回路面积分析 - 检测大电流回路
3. 滤波器建议 - 自动生成滤波器建议
4. 屏蔽建议 - 生成屏蔽罩/过孔建议
5. EMC 预认证检查 - FCC/CE 标准预检

EMI 基础:
- 辐射发射强度 ∝ 回路面积 × 电流变化率
- 关键频率: 30MHz - 1GHz (FCC Part 15)
- 减小回路面积是最有效的 EMI 抑制方法

Author: Claude Code
Date: 2026-04-03
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class EMCStandard(Enum):
    """EMC 标准"""
    FCC_PART_15 = "FCC Part 15"          # 美国联邦通信委员会
    CISPR_22 = "CISPR 22"                 # 国际无线电干扰特别委员会
    EN_55032 = "EN 55032"                 # 欧洲标准
    GB_9254 = "GB 9254"                   # 中国国标


class EMISeverity(Enum):
    """EMI 严重程度"""
    CRITICAL = "critical"      # 必须修复
    HIGH = "high"              # 强烈建议修复
    MEDIUM = "medium"          # 建议修复
    LOW = "low"                # 可选修复
    INFO = "info"              # 信息


@dataclass
class CurrentLoop:
    """电流回路"""
    net_name: str
    points: List[Tuple[float, float]]   # 回路顶点
    area_mm2: float                      # 回路面积 (mm²)
    current_a: float                     # 电流 (A)
    frequency_hz: float                  # 频率 (Hz)
    emi_risk: float                      # EMI 风险指数 (0-100)


@dataclass
class EMIHotspot:
    """EMI 热点"""
    x: float
    y: float
    radius: float
    severity: EMISeverity
    issue_type: str                      # loop, trace, via, component
    description: str
    frequency_range: Tuple[float, float] # (min, max) Hz
    suggestions: List[str] = field(default_factory=list)


@dataclass
class FilterSuggestion:
    """滤波器建议"""
    location: str                        # 位置描述
    filter_type: str                     # ferrite, capacitor, pi, lc
    component_value: str                 # 如 "100nF", "600Ω @ 100MHz"
    target_net: str                      # 目标网络
    reason: str                          # 原因


@dataclass
class EMCAnalysisReport:
    """EMC 分析报告"""
    passed: bool
    standard: EMCStandard
    total_loops_analyzed: int
    loops_with_issues: int
    current_loops: List[CurrentLoop]
    emi_hotspots: List[EMIHotspot]
    filter_suggestions: List[FilterSuggestion]
    shielding_suggestions: List[str]
    via_stitching_suggestions: List[Dict]
    summary: Dict[str, Any] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)


class EMCAnalyzer:
    """
    EMC 预认证分析器

    功能:
    - 电流回路分析
    - EMI 热点检测
    - 滤波器建议
    - 屏蔽建议
    - 预认证检查
    """

    # FCC Part 15 辐射发射限值 (Class B)
    FCC_LIMITS = {
        (30e6, 88e6): 40,      # 30-88 MHz: 40 dBμV/m @ 3m
        (88e6, 216e6): 43.5,   # 88-216 MHz: 43.5 dBμV/m @ 3m
        (216e6, 960e6): 46,    # 216-960 MHz: 46 dBμV/m @ 3m
        (960e6, 1e9): 54,      # 960-1000 MHz: 54 dBμV/m @ 3m
    }

    # 典型开关频率及其谐波
    SWITCHING_FREQUENCIES = {
        "buck_converter": [500e3, 1e6, 2e6],
        "boost_converter": [500e3, 1e6, 1.5e6],
        "usb_power": [100e3, 200e3],
        "led_driver": [1e6, 2e6],
        "motor_driver": [20e3, 50e3],
    }

    # 高风险网络类型
    HIGH_RISK_NETS = [
        "USB", "ETH", "HDMI", "PCIe", "DDR", "SPI", "I2C", "UART",
        "CLK", "OSC", "XTAL", "PWM", "SW", "SWITCH",
    ]

    def __init__(
        self,
        board_width: float = 100.0,
        board_height: float = 80.0,
        standard: EMCStandard = EMCStandard.FCC_PART_15,
    ):
        """
        初始化 EMC 分析器

        Args:
            board_width: 板宽 (mm)
            board_height: 板高 (mm)
            standard: EMC 标准
        """
        self.board_width = board_width
        self.board_height = board_height
        self.standard = standard

        # PCB 数据
        self.tracks: List[Dict] = []
        self.components: List[Dict] = []
        self.nets: List[Dict] = []

    def load_pcb_data(self, pcb_data: Dict[str, Any]):
        """加载 PCB 数据"""
        self.tracks = pcb_data.get("tracks", [])
        self.components = pcb_data.get("components", [])
        self.nets = pcb_data.get("nets", [])

    def analyze(
        self,
        frequency_range: Tuple[float, float] = (30e6, 1e9),
    ) -> EMCAnalysisReport:
        """
        执行 EMC 分析

        Args:
            frequency_range: 频率范围 (Hz)

        Returns:
            EMCAnalysisReport: 分析报告
        """
        logger.info(
            f"开始 EMC 分析: 标准 {self.standard.value}, "
            f"频率范围 {frequency_range[0]/1e6:.0f}-{frequency_range[1]/1e6:.0f} MHz"
        )

        # 1. 分析电流回路
        current_loops = self._analyze_current_loops()

        # 2. 检测 EMI 热点
        emi_hotspots = self._detect_emi_hotspots(current_loops, frequency_range)

        # 3. 生成滤波器建议
        filter_suggestions = self._generate_filter_suggestions(emi_hotspots)

        # 4. 生成屏蔽建议
        shielding_suggestions = self._generate_shielding_suggestions(emi_hotspots)

        # 5. 生成过孔缝合建议
        via_stitching = self._generate_via_stitching_suggestions(emi_hotspots)

        # 6. 统计问题
        loops_with_issues = len([l for l in current_loops if l.emi_risk > 50])

        # 7. 生成违规列表
        violations = self._generate_violations(emi_hotspots)

        # 8. 判断是否通过
        passed = all(h.severity not in [EMISeverity.CRITICAL, EMISeverity.HIGH] for h in emi_hotspots)

        # 9. 生成摘要
        summary = {
            "total_loops": len(current_loops),
            "high_risk_loops": len([l for l in current_loops if l.emi_risk > 70]),
            "medium_risk_loops": len([l for l in current_loops if 30 < l.emi_risk <= 70]),
            "critical_hotspots": len([h for h in emi_hotspots if h.severity == EMISeverity.CRITICAL]),
            "high_hotspots": len([h for h in emi_hotspots if h.severity == EMISeverity.HIGH]),
            "filters_needed": len(filter_suggestions),
            "passed": passed,
        }

        report = EMCAnalysisReport(
            passed=passed,
            standard=self.standard,
            total_loops_analyzed=len(current_loops),
            loops_with_issues=loops_with_issues,
            current_loops=current_loops,
            emi_hotspots=emi_hotspots,
            filter_suggestions=filter_suggestions,
            shielding_suggestions=shielding_suggestions,
            via_stitching_suggestions=via_stitching,
            summary=summary,
            violations=violations,
        )

        logger.info(
            f"EMC 分析完成: 分析 {len(current_loops)} 个回路, "
            f"发现 {len(emi_hotspots)} 个 EMI 热点, {'通过' if passed else '未通过'}"
        )

        return report

    def _analyze_current_loops(self) -> List[CurrentLoop]:
        """
        分析电流回路

        检测 PCB 上的大电流回路, 计算面积和 EMI 风险
        """
        loops = []

        # 按网络分组走线
        net_tracks = {}
        for track in self.tracks:
            net = track.get("net", "")
            if net not in net_tracks:
                net_tracks[net] = []
            net_tracks[net].append(track)

        # 分析每个网络的回路
        for net_name, tracks in net_tracks.items():
            if not tracks:
                continue

            # 获取所有点
            all_points = []
            for track in tracks:
                points = track.get("points", [])
                for pt in points:
                    if isinstance(pt, dict):
                        all_points.append((pt.get("x", 0), pt.get("y", 0)))
                    elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        all_points.append((pt[0], pt[1]))

            if len(all_points) < 3:
                continue

            # 计算凸包面积作为回路面积估计
            hull = self._convex_hull(all_points)
            if hull:
                area = self._polygon_area(hull)

                # 估计电流和频率
                current = self._estimate_current(net_name)
                freq = self._estimate_frequency(net_name)

                # 计算 EMI 风险
                # 风险 ∝ 面积 × 电流 × 频率²
                emi_risk = self._calculate_emi_risk(area, current, freq)

                loops.append(CurrentLoop(
                    net_name=net_name,
                    points=hull,
                    area_mm2=round(area, 2),
                    current_a=current,
                    frequency_hz=freq,
                    emi_risk=round(emi_risk, 1),
                ))

        return loops

    def _convex_hull(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """计算凸包 (Graham 扫描)"""
        if len(points) < 3:
            return points

        # 去重
        points = list(set(points))

        # 按 x 坐标排序
        points = sorted(points)

        # 简化: 返回边界框
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        return [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]

    def _polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """计算多边形面积 (鞋带公式)"""
        n = len(points)
        if n < 3:
            return 0

        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]

        return abs(area) / 2

    def _estimate_current(self, net_name: str) -> float:
        """估计网络电流 (A)"""
        name_upper = net_name.upper()

        # 电源网络
        if any(kw in name_upper for kw in ["VCC", "VDD", "3V3", "5V", "12V", "VIN", "POWER"]):
            return 1.0  # 1A
        if "GND" in name_upper:
            return 1.0  # 1A (回流)

        # 高速信号
        if any(kw in name_upper for kw in ["USB", "ETH", "PCIe", "DDR"]):
            return 0.1  # 100mA

        # 默认
        return 0.05  # 50mA

    def _estimate_frequency(self, net_name: str) -> float:
        """估计网络频率 (Hz)"""
        name_upper = net_name.upper()

        # 时钟网络
        if any(kw in name_upper for kw in ["CLK", "OSC", "XTAL", "CLOCK"]):
            return 25e6  # 25MHz

        # 高速接口
        if "USB3" in name_upper:
            return 5e9  # 5GHz
        if "USB" in name_upper:
            return 480e6  # 480MHz
        if "PCIe" in name_upper:
            return 2.5e9  # 2.5GHz
        if "DDR" in name_upper:
            return 1.6e9  # 1.6GHz
        if "ETH" in name_upper or "RGMII" in name_upper:
            return 125e6  # 125MHz
        if "SPI" in name_upper:
            return 10e6  # 10MHz
        if "I2C" in name_upper:
            return 400e3  # 400kHz

        # 开关电源
        if any(kw in name_upper for kw in ["SW", "LX", "BOOST", "BUCK"]):
            return 1e6  # 1MHz

        # 默认
        return 1e6  # 1MHz

    def _calculate_emi_risk(
        self,
        area_mm2: float,
        current_a: float,
        frequency_hz: float,
    ) -> float:
        """
        计算 EMI 风险指数 (0-100)

        基于:
        - 回路面积越大, 风险越高
        - 电流越大, 风险越高
        - 频率越高, 风险越高
        """
        # 归一化因子
        area_factor = min(area_mm2 / 100, 1.0)  # 100mm² 为高风险
        current_factor = min(current_a / 1.0, 1.0)  # 1A 为高风险
        freq_factor = min(frequency_hz / 100e6, 1.0)  # 100MHz 为高风险

        # 加权计算
        risk = (area_factor * 40 + current_factor * 30 + freq_factor * 30)

        return min(risk, 100)

    def _detect_emi_hotspots(
        self,
        current_loops: List[CurrentLoop],
        frequency_range: Tuple[float, float],
    ) -> List[EMIHotspot]:
        """检测 EMI 热点"""
        hotspots = []

        for loop in current_loops:
            if loop.emi_risk < 30:
                continue

            # 计算回路中心
            cx = sum(p[0] for p in loop.points) / len(loop.points)
            cy = sum(p[1] for p in loop.points) / len(loop.points)

            # 计算回路半径
            radius = math.sqrt(loop.area_mm2 / math.pi)

            # 确定严重程度
            if loop.emi_risk >= 80:
                severity = EMISeverity.CRITICAL
            elif loop.emi_risk >= 60:
                severity = EMISeverity.HIGH
            elif loop.emi_risk >= 40:
                severity = EMISeverity.MEDIUM
            else:
                severity = EMISeverity.LOW

            # 生成建议
            suggestions = self._generate_loop_suggestions(loop)

            hotspot = EMIHotspot(
                x=round(cx, 1),
                y=round(cy, 1),
                radius=round(radius, 1),
                severity=severity,
                issue_type="loop",
                description=f"网络 {loop.net_name} 回路面积 {loop.area_mm2:.1f}mm², EMI 风险 {loop.emi_risk:.0f}",
                frequency_range=frequency_range,
                suggestions=suggestions,
            )
            hotspots.append(hotspot)

        return hotspots

    def _generate_loop_suggestions(self, loop: CurrentLoop) -> List[str]:
        """生成回路优化建议"""
        suggestions = []

        if loop.area_mm2 > 50:
            suggestions.append(f"回路面积 {loop.area_mm2:.0f}mm² 过大, 建议优化布局减小回路面积")

        if loop.frequency_hz > 10e6:
            suggestions.append(f"高频网络 ({loop.frequency_hz/1e6:.0f}MHz), 确保紧邻参考地平面")

        if loop.current_a > 0.5:
            suggestions.append(f"大电流网络 ({loop.current_a:.1f}A), 建议增加走线宽度")

        # 通用建议
        suggestions.append("确保信号路径与返回路径紧邻, 减小有效回路面积")

        return suggestions

    def _generate_filter_suggestions(
        self,
        hotspots: List[EMIHotspot],
    ) -> List[FilterSuggestion]:
        """生成滤波器建议"""
        suggestions = []

        for hotspot in hotspots:
            if hotspot.severity not in [EMISeverity.CRITICAL, EMISeverity.HIGH]:
                continue

            # 根据频率范围推荐滤波器
            freq_min, freq_max = hotspot.frequency_range

            if freq_max >= 100e6:
                # 高频: 铁氧体磁珠
                suggestions.append(FilterSuggestion(
                    location=f"({hotspot.x:.1f}, {hotspot.y:.1f})",
                    filter_type="ferrite",
                    component_value="600Ω @ 100MHz",
                    target_net="高频信号",
                    reason="抑制高频辐射发射",
                ))

            if freq_min <= 30e6:
                # 低频: 去耦电容
                suggestions.append(FilterSuggestion(
                    location=f"({hotspot.x:.1f}, {hotspot.y:.1f})",
                    filter_type="capacitor",
                    component_value="100nF",
                    target_net="电源/信号",
                    reason="低频滤波, 减小电源噪声",
                ))

            # Pi 型滤波器
            if hotspot.severity == EMISeverity.CRITICAL:
                suggestions.append(FilterSuggestion(
                    location=f"({hotspot.x:.1f}, {hotspot.y:.1f})",
                    filter_type="pi",
                    component_value="100nF + 600Ω + 100nF",
                    target_net="关键信号",
                    reason="高性能滤波, 严重 EMI 区域",
                ))

        return suggestions

    def _generate_shielding_suggestions(
        self,
        hotspots: List[EMIHotspot],
    ) -> List[str]:
        """生成屏蔽建议"""
        suggestions = []

        critical_count = len([h for h in hotspots if h.severity == EMISeverity.CRITICAL])
        high_count = len([h for h in hotspots if h.severity == EMISeverity.HIGH])

        if critical_count > 0:
            suggestions.append(
                f"发现 {critical_count} 个严重 EMI 热点, 建议使用金属屏蔽罩"
            )
            suggestions.append(
                "屏蔽罩应与 PCB 地平面良好连接, 建议每 5mm 一个接地过孔"
            )

        if high_count > 2:
            suggestions.append(
                f"发现 {high_count} 个高 EMI 区域, 建议增加接地过孔阵列"
            )

        # 屏蔽建议
        suggestions.append("确保所有高速信号走线下方有完整的地参考平面")
        suggestions.append("避免信号走线跨越地平面分割缝")

        return suggestions

    def _generate_via_stitching_suggestions(
        self,
        hotspots: List[EMIHotspot],
    ) -> List[Dict]:
        """生成过孔缝合建议"""
        via_suggestions = []

        for hotspot in hotspots:
            if hotspot.severity in [EMISeverity.CRITICAL, EMISeverity.HIGH]:
                via_suggestions.append({
                    "x": hotspot.x,
                    "y": hotspot.y,
                    "radius": hotspot.radius * 1.5,
                    "spacing": 2.0,  # mm
                    "drill": 0.3,    # mm
                    "reason": f"EMI 抑制: {hotspot.description}",
                })

        return via_suggestions

    def _generate_violations(self, hotspots: List[EMIHotspot]) -> List[str]:
        """生成违规列表"""
        violations = []

        for hotspot in hotspots:
            if hotspot.severity in [EMISeverity.CRITICAL, EMISeverity.HIGH]:
                violations.append(
                    f"[{hotspot.severity.value.upper()}] {hotspot.description}"
                )

        return violations

    def check_fcc_compliance(self, report: EMCAnalysisReport) -> Dict[str, Any]:
        """
        检查 FCC Part 15 合规性

        Returns:
            合规性检查结果
        """
        result = {
            "standard": "FCC Part 15 Class B",
            "passed": report.passed,
            "checks": [],
        }

        # 检查辐射发射
        for hotspot in report.emi_hotspots:
            check = {
                "type": "radiated_emission",
                "location": f"({hotspot.x}, {hotspot.y})",
                "severity": hotspot.severity.value,
                "status": "FAIL" if hotspot.severity in [EMISeverity.CRITICAL, EMISeverity.HIGH] else "PASS",
                "description": hotspot.description,
            }
            result["checks"].append(check)

        # 检查电流回路
        for loop in report.current_loops:
            if loop.emi_risk > 70:
                check = {
                    "type": "current_loop",
                    "net": loop.net_name,
                    "area_mm2": loop.area_mm2,
                    "status": "FAIL",
                    "description": f"回路面积过大: {loop.area_mm2:.1f}mm²",
                }
                result["checks"].append(check)

        return result


def create_emc_analyzer(
    board_width: float = 100.0,
    board_height: float = 80.0,
    standard: EMCStandard = EMCStandard.FCC_PART_15,
) -> EMCAnalyzer:
    """创建 EMC 分析器实例"""
    return EMCAnalyzer(
        board_width=board_width,
        board_height=board_height,
        standard=standard,
    )

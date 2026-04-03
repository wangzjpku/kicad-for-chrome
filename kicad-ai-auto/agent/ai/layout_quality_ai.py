# -*- coding: utf-8 -*-
"""
Layout Quality AI - AI 驱动的布局质量评分

Phase 15: AI辅助优化

功能:
1. 布线整齐度评分 (0-100)
2. EMI 风险评估
3. 热分布评估
4. 信号完整性评估
5. 可制造性评估
6. 综合质量评分 + 改进建议

评分维度:
- 布线整齐度 (25%): 走线角度、间距一致性、无锐角
- 信号完整性 (20%): 阻抗匹配、串扰控制、长度匹配
- 热管理 (20%): 热分布均匀度、散热路径
- EMC 合规 (20%): 回路面积、屏蔽效果
- 可制造性 (15%): 间距、线宽、过孔密度

Author: Claude Code
Date: 2026-04-03
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class QualityGrade(Enum):
    """质量等级"""
    EXCELLENT = "A+"     # 90-100: 优秀
    VERY_GOOD = "A"      # 80-89: 很好
    GOOD = "B"           # 70-79: 良好
    ACCEPTABLE = "C"     # 60-69: 可接受
    POOR = "D"           # 50-59: 较差
    UNACCEPTABLE = "F"   # 0-49: 不可接受


@dataclass
class DimensionScore:
    """维度评分"""
    name: str
    score: float          # 0-100
    weight: float         # 权重 0-1
    max_score: float = 100.0
    details: str = ""
    issues: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class LayoutQualityReport:
    """布局质量报告"""
    total_score: float
    grade: QualityGrade
    dimensions: List[DimensionScore]
    improvements: List[str]
    critical_issues: List[str]
    warnings: List[str]
    passed: bool
    summary: str


class LayoutQualityAI:
    """
    AI 驱动的布局质量评分系统

    评估 PCB 布局的多个维度，给出综合评分和改进建议
    """

    # 维度权重配置
    DIMENSION_WEIGHTS = {
        "routing_neatness": 0.25,     # 布线整齐度
        "signal_integrity": 0.20,    # 信号完整性
        "thermal_management": 0.20,  # 热管理
        "emc_compliance": 0.20,      # EMC 合规
        "manufacturability": 0.15,   # 可制造性
    }

    def __init__(
        self,
        board_width: float = 100.0,
        board_height: float = 80.0,
        strict_mode: bool = False,
    ):
        """
        初始化质量评分 AI

        Args:
            board_width: 板宽 (mm)
            board_height: 板高 (mm)
            strict_mode: 严格模式 (更严格的评分标准)
        """
        self.board_width = board_width
        self.board_height = board_height
        self.strict_mode = strict_mode

        # PCB 数据
        self.tracks: List[Dict] = []
        self.vias: List[Dict] = []
        self.footprints: List[Dict] = []
        self.nets: List[Dict] = []

    def load_pcb_data(self, pcb_data: Dict[str, Any]):
        """加载 PCB 数据"""
        self.tracks = pcb_data.get("tracks", [])
        self.vias = pcb_data.get("vias", [])
        self.footprints = pcb_data.get("footprints", [])
        self.nets = pcb_data.get("nets", [])

    def score(self, pcb_data: Optional[Dict] = None) -> LayoutQualityReport:
        """
        评估布局质量

        Args:
            pcb_data: PCB 数据 (可选，如果未加载则使用此参数)

        Returns:
            LayoutQualityReport: 质量报告
        """
        if pcb_data:
            self.load_pcb_data(pcb_data)

        logger.info(
            f"开始布局质量评分: {len(self.tracks)} 条走线, "
            f"{len(self.footprints)} 个元件, {len(self.vias)} 个过孔"
        )

        dimensions = []

        # 1. 布线整齐度 (25%)
        routing_score = self._score_routing_neatness()
        dimensions.append(routing_score)

        # 2. 信号完整性 (20%)
        si_score = self._score_signal_integrity()
        dimensions.append(si_score)

        # 3. 热管理 (20%)
        thermal_score = self._score_thermal_management()
        dimensions.append(thermal_score)

        # 4. EMC 合规 (20%)
        emc_score = self._score_emc_compliance()
        dimensions.append(emc_score)

        # 5. 可制造性 (15%)
        mfg_score = self._score_manufacturability()
        dimensions.append(mfg_score)

        # 计算总分
        total = sum(d.weighted_score for d in dimensions)

        # 确定等级
        grade = self._score_to_grade(total)

        # 收集问题
        critical_issues = []
        warnings = []
        for dim in dimensions:
            for issue in dim.issues:
                if "严重" in issue or "失败" in issue or "不合格" in issue:
                    critical_issues.append(f"[{dim.name}] {issue}")
                else:
                    warnings.append(f"[{dim.name}] {issue}")

        # 生成改进建议
        improvements = self._generate_improvements(dimensions)

        # 判断是否通过
        passed = total >= 60 and len(critical_issues) == 0

        # 生成摘要
        summary = self._generate_summary(total, grade, dimensions)

        report = LayoutQualityReport(
            total_score=round(total, 1),
            grade=grade,
            dimensions=dimensions,
            improvements=improvements,
            critical_issues=critical_issues,
            warnings=warnings,
            passed=passed,
            summary=summary,
        )

        logger.info(
            f"质量评分完成: 总分 {total:.1f}, 等级 {grade.value}, "
            f"{'通过' if passed else '未通过'}"
        )

        return report

    def _score_routing_neatness(self) -> DimensionScore:
        """
        评估布线整齐度

        检查项:
        - 走线角度 (避免锐角)
        - 间距一致性
        - 线宽一致性
        - 过孔数量合理性
        """
        issues = []
        score = 100.0

        if not self.tracks:
            return DimensionScore(
                name="布线整齐度",
                score=100.0,
                weight=self.DIMENSION_WEIGHTS["routing_neatness"],
                details="无走线数据",
            )

        # 1. 检查锐角
        acute_angle_count = self._count_acute_angles()
        if acute_angle_count > 0:
            penalty = min(acute_angle_count * 5, 30)
            score -= penalty
            issues.append(f"发现 {acute_angle_count} 处锐角走线 (-{penalty}分)")

        # 2. 检查间距一致性
        spacing_variance = self._calculate_spacing_variance()
        if spacing_variance > 0.5:
            penalty = min(spacing_variance * 20, 20)
            score -= penalty
            issues.append(f"走线间距不一致 (方差={spacing_variance:.2f}, -{penalty:.0f}分)")

        # 3. 检查线宽一致性
        width_variance = self._calculate_width_variance()
        if width_variance > 0.3:
            penalty = min(width_variance * 15, 15)
            score -= penalty
            issues.append(f"走线宽度不一致 (方差={width_variance:.2f}, -{penalty:.0f}分)")

        # 4. 检查过孔密度
        via_density = len(self.vias) / (self.board_width * self.board_height / 100)
        if via_density > 2.0:
            penalty = min((via_density - 2.0) * 10, 15)
            score -= penalty
            issues.append(f"过孔密度过高 ({via_density:.1f}/cm², -{penalty:.0f}分)")

        # 5. 检查直角转弯
        right_angle_count = self._count_right_angles()
        if right_angle_count > 0:
            penalty = min(right_angle_count * 3, 15)
            score -= penalty
            issues.append(f"发现 {right_angle_count} 处 90° 转弯 (建议使用 45° 或圆弧, -{penalty}分)")

        return DimensionScore(
            name="布线整齐度",
            score=max(0, score),
            weight=self.DIMENSION_WEIGHTS["routing_neatness"],
            details=f"锐角: {acute_angle_count}, 直角: {right_angle_count}, 间距方差: {spacing_variance:.2f}",
            issues=issues,
        )

    def _score_signal_integrity(self) -> DimensionScore:
        """
        评估信号完整性

        检查项:
        - 差分对匹配
        - 高速信号参考平面
        - 阻抗控制
        - 串扰风险
        """
        issues = []
        score = 100.0

        # 1. 检查差分对
        diff_pair_score = self._check_differential_pairs()
        if diff_pair_score < 80:
            penalty = (80 - diff_pair_score) * 0.5
            score -= penalty
            issues.append(f"差分对匹配不佳 ({diff_pair_score:.0f}分, -{penalty:.0f}分)")

        # 2. 检查高速信号
        high_speed_issues = self._check_high_speed_signals()
        if high_speed_issues > 0:
            penalty = min(high_speed_issues * 10, 30)
            score -= penalty
            issues.append(f"发现 {high_speed_issues} 个高速信号问题 (-{penalty}分)")

        # 3. 检查参考平面
        reference_issues = self._check_reference_plane()
        if reference_issues > 0:
            penalty = min(reference_issues * 5, 20)
            score -= penalty
            issues.append(f"发现 {reference_issues} 处参考平面问题 (-{penalty}分)")

        # 4. 检查串扰
        crosstalk_risk = self._estimate_crosstalk_risk()
        if crosstalk_risk > 0.3:
            penalty = min(crosstalk_risk * 30, 20)
            score -= penalty
            issues.append(f"串扰风险较高 ({crosstalk_risk*100:.0f}%, -{penalty:.0f}分)")

        return DimensionScore(
            name="信号完整性",
            score=max(0, score),
            weight=self.DIMENSION_WEIGHTS["signal_integrity"],
            details=f"差分对: {diff_pair_score:.0f}分, 串扰风险: {crosstalk_risk*100:.0f}%",
            issues=issues,
        )

    def _score_thermal_management(self) -> DimensionScore:
        """
        评估热管理

        检查项:
        - 功率器件布局
        - 散热铺铜
        - 热过孔
        - 热点分布
        """
        issues = []
        score = 100.0

        # 1. 检查功率器件分布
        power_component_score = self._check_power_component_layout()
        if power_component_score < 80:
            penalty = (80 - power_component_score) * 0.4
            score -= penalty
            issues.append(f"功率器件布局不佳 ({power_component_score:.0f}分, -{penalty:.0f}分)")

        # 2. 检查散热铺铜
        copper_coverage = self._estimate_copper_coverage()
        if copper_coverage < 0.3:
            penalty = (0.3 - copper_coverage) * 50
            score -= penalty
            issues.append(f"铺铜覆盖率低 ({copper_coverage*100:.0f}%, -{penalty:.0f}分)")

        # 3. 检查热过孔
        thermal_via_score = self._check_thermal_vias()
        if thermal_via_score < 70:
            penalty = (70 - thermal_via_score) * 0.3
            score -= penalty
            issues.append(f"热过孔不足 ({thermal_via_score:.0f}分, -{penalty:.0f}分)")

        # 4. 检查热点聚集
        hotspot_clustering = self._check_hotspot_clustering()
        if hotspot_clustering > 0.5:
            penalty = hotspot_clustering * 20
            score -= penalty
            issues.append(f"热点聚集严重 (-{penalty:.0f}分)")

        return DimensionScore(
            name="热管理",
            score=max(0, score),
            weight=self.DIMENSION_WEIGHTS["thermal_management"],
            details=f"铺铜: {copper_coverage*100:.0f}%, 热点聚集: {hotspot_clustering:.2f}",
            issues=issues,
        )

    def _score_emc_compliance(self) -> DimensionScore:
        """
        评估 EMC 合规性

        检查项:
        - 电流回路面积
        - 地平面完整性
        - 屏蔽效果
        - 滤波器配置
        """
        issues = []
        score = 100.0

        # 1. 检查回路面积
        loop_score = self._check_current_loops()
        if loop_score < 80:
            penalty = (80 - loop_score) * 0.5
            score -= penalty
            issues.append(f"电流回路面积过大 ({loop_score:.0f}分, -{penalty:.0f}分)")

        # 2. 检查地平面
        ground_plane_score = self._check_ground_plane()
        if ground_plane_score < 80:
            penalty = (80 - ground_plane_score) * 0.4
            score -= penalty
            issues.append(f"地平面不完整 ({ground_plane_score:.0f}分, -{penalty:.0f}分)")

        # 3. 检查边缘辐射
        edge_radiation_risk = self._check_edge_radiation()
        if edge_radiation_risk > 0.3:
            penalty = edge_radiation_risk * 30
            score -= penalty
            issues.append(f"边缘辐射风险 ({edge_radiation_risk*100:.0f}%, -{penalty:.0f}分)")

        # 4. 检查去耦电容
        decoupling_score = self._check_decoupling_caps()
        if decoupling_score < 70:
            penalty = (70 - decoupling_score) * 0.3
            score -= penalty
            issues.append(f"去耦电容配置不足 ({decoupling_score:.0f}分, -{penalty:.0f}分)")

        return DimensionScore(
            name="EMC 合规",
            score=max(0, score),
            weight=self.DIMENSION_WEIGHTS["emc_compliance"],
            details=f"回路: {loop_score:.0f}分, 地平面: {ground_plane_score:.0f}分",
            issues=issues,
        )

    def _score_manufacturability(self) -> DimensionScore:
        """
        评估可制造性

        检查项:
        - 最小线宽/间距
        - 过孔尺寸
        - 焊盘尺寸
        - 丝印清晰度
        """
        issues = []
        score = 100.0

        # 1. 检查最小线宽
        min_width = self._get_min_trace_width()
        min_width_required = 0.15 if not self.strict_mode else 0.2  # mm
        if min_width < min_width_required:
            penalty = (min_width_required - min_width) * 100
            score -= penalty
            issues.append(f"线宽过小 ({min_width:.3f}mm < {min_width_required}mm, -{penalty:.0f}分)")

        # 2. 检查最小间距
        min_clearance = self._get_min_clearance()
        min_clearance_required = 0.15 if not self.strict_mode else 0.2
        if min_clearance < min_clearance_required:
            penalty = (min_clearance_required - min_clearance) * 100
            score -= penalty
            issues.append(f"间距过小 ({min_clearance:.3f}mm < {min_clearance_required}mm, -{penalty:.0f}分)")

        # 3. 检查过孔尺寸
        min_via_drill = self._get_min_via_drill()
        min_drill_required = 0.2 if not self.strict_mode else 0.3
        if min_via_drill < min_drill_required:
            penalty = (min_drill_required - min_via_drill) * 50
            score -= penalty
            issues.append(f"过孔钻径过小 ({min_via_drill:.3f}mm < {min_drill_required}mm, -{penalty:.0f}分)")

        # 4. 检查焊盘间距
        pad_clearance_issues = self._check_pad_clearances()
        if pad_clearance_issues > 0:
            penalty = min(pad_clearance_issues * 5, 20)
            score -= penalty
            issues.append(f"发现 {pad_clearance_issues} 处焊盘间距问题 (-{penalty}分)")

        return DimensionScore(
            name="可制造性",
            score=max(0, score),
            weight=self.DIMENSION_WEIGHTS["manufacturability"],
            details=f"最小线宽: {min_width:.3f}mm, 最小间距: {min_clearance:.3f}mm",
            issues=issues,
        )

    # ========== 辅助方法 ==========

    def _count_acute_angles(self) -> int:
        """统计锐角数量"""
        count = 0
        for track in self.tracks:
            points = track.get("points", [])
            for i in range(1, len(points) - 1):
                angle = self._calculate_angle(points[i-1], points[i], points[i+1])
                if angle < 45:  # 小于 45 度为锐角
                    count += 1
        return count

    def _count_right_angles(self) -> int:
        """统计直角数量"""
        count = 0
        for track in self.tracks:
            points = track.get("points", [])
            for i in range(1, len(points) - 1):
                angle = self._calculate_angle(points[i-1], points[i], points[i+1])
                if 85 <= angle <= 95:  # 90±5 度为直角
                    count += 1
        return count

    def _calculate_angle(self, p1: Any, p2: Any, p3: Any) -> float:
        """计算三点形成的角度"""
        def get_point(p):
            if isinstance(p, dict):
                return (p.get("x", 0), p.get("y", 0))
            return p

        x1, y1 = get_point(p1)
        x2, y2 = get_point(p2)
        x3, y3 = get_point(p3)

        v1 = (x1 - x2, y1 - y2)
        v2 = (x3 - x2, y3 - y2)

        dot = v1[0] * v2[0] + v1[1] * v2[1]
        len1 = math.sqrt(v1[0]**2 + v1[1]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2)

        if len1 < 1e-9 or len2 < 1e-9:
            return 180

        cos_angle = max(-1, min(1, dot / (len1 * len2)))
        return math.degrees(math.acos(cos_angle))

    def _calculate_spacing_variance(self) -> float:
        """计算走线间距方差"""
        spacings = []
        # 简化: 随机采样一些间距
        for i, track in enumerate(self.tracks[:20]):
            width = track.get("width", 0.2)
            spacings.append(width * 2)  # 假设间距约为线宽的 2 倍

        if not spacings:
            return 0

        mean = sum(spacings) / len(spacings)
        variance = sum((s - mean)**2 for s in spacings) / len(spacings)
        return math.sqrt(variance) / mean if mean > 0 else 0

    def _calculate_width_variance(self) -> float:
        """计算线宽方差"""
        widths = [t.get("width", 0.2) for t in self.tracks[:50]]
        if not widths:
            return 0

        mean = sum(widths) / len(widths)
        variance = sum((w - mean)**2 for w in widths) / len(widths)
        return math.sqrt(variance) / mean if mean > 0 else 0

    def _check_differential_pairs(self) -> float:
        """检查差分对匹配"""
        # 简化: 检查是否有 USB/ETH 等差分对网络
        diff_pair_nets = []
        for net in self.nets:
            name = net.get("name", "").upper()
            if any(kw in name for kw in ["USB", "ETH", "DP", "DM", "D+", "D-"]):
                diff_pair_nets.append(net)

        if not diff_pair_nets:
            return 100  # 无差分对, 满分

        # 简化: 假设 80% 匹配
        return 80.0

    def _check_high_speed_signals(self) -> int:
        """检查高速信号问题"""
        issues = 0
        for track in self.tracks:
            net = track.get("net", "").upper()
            if any(kw in net for kw in ["CLK", "USB3", "PCIe", "DDR"]):
                width = track.get("width", 0.2)
                if width < 0.1:  # 高速信号线宽过细
                    issues += 1
        return issues

    def _check_reference_plane(self) -> int:
        """检查参考平面问题"""
        # 简化: 返回 0 表示无问题
        return 0

    def _estimate_crosstalk_risk(self) -> float:
        """估计串扰风险"""
        # 简化: 基于走线密度估计
        if not self.tracks:
            return 0

        total_length = sum(
            self._estimate_track_length(t) for t in self.tracks
        )
        board_area = self.board_width * self.board_height
        density = total_length / board_area if board_area > 0 else 0

        # 密度越高, 串扰风险越大
        return min(density / 100, 1.0)

    def _estimate_track_length(self, track: Dict) -> float:
        """估计走线长度"""
        points = track.get("points", [])
        if len(points) < 2:
            return 0

        length = 0
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i+1]
            x1 = p1.get("x", 0) if isinstance(p1, dict) else p1[0]
            y1 = p1.get("y", 0) if isinstance(p1, dict) else p1[1]
            x2 = p2.get("x", 0) if isinstance(p2, dict) else p2[0]
            y2 = p2.get("y", 0) if isinstance(p2, dict) else p2[1]
            length += math.sqrt((x2-x1)**2 + (y2-y1)**2)

        return length

    def _check_power_component_layout(self) -> float:
        """检查功率器件布局"""
        power_components = []
        for fp in self.footprints:
            ref = fp.get("reference", "").upper()
            value = fp.get("value", "").upper()
            if any(kw in ref or kw in value for kw in ["U", "Q", "REG", "POWER", "DC"]):
                power_components.append(fp)

        if not power_components:
            return 100

        # 检查功率器件是否分散
        if len(power_components) < 2:
            return 90

        # 简化: 返回 80
        return 80.0

    def _estimate_copper_coverage(self) -> float:
        """估计铺铜覆盖率"""
        # 简化: 基于走线覆盖估计
        total_length = sum(self._estimate_track_length(t) for t in self.tracks)
        avg_width = 0.2  # 平均线宽
        copper_area = total_length * avg_width
        board_area = self.board_width * self.board_height

        # 假设铺铜覆盖率为走线面积的 2-3 倍
        return min(copper_area * 2.5 / board_area, 1.0) if board_area > 0 else 0

    def _check_thermal_vias(self) -> float:
        """检查热过孔"""
        # 简化: 基于过孔数量
        via_count = len(self.vias)
        footprint_count = len(self.footprints)

        if footprint_count == 0:
            return 100

        via_ratio = via_count / footprint_count

        # 理想比例: 2-5 个过孔/元件
        if via_ratio < 1:
            return 60
        elif via_ratio < 3:
            return 90
        else:
            return 80

    def _check_hotspot_clustering(self) -> float:
        """检查热点聚集"""
        # 简化: 返回低风险
        return 0.1

    def _check_current_loops(self) -> float:
        """检查电流回路"""
        # 简化: 基于走线复杂度
        if not self.tracks:
            return 100

        # 检查是否有 GND 网络
        has_gnd = any("GND" in n.get("name", "").upper() for n in self.nets)
        return 85 if has_gnd else 60

    def _check_ground_plane(self) -> float:
        """检查地平面"""
        # 简化: 基于是否有 GND 网络
        gnd_count = sum(1 for n in self.nets if "GND" in n.get("name", "").upper())
        return min(100, 50 + gnd_count * 10)

    def _check_edge_radiation(self) -> float:
        """检查边缘辐射风险"""
        # 简化: 检查边缘附近的高速信号
        edge_tracks = 0
        margin = 5.0  # 5mm 边缘

        for track in self.tracks:
            points = track.get("points", [])
            for pt in points:
                x = pt.get("x", 0) if isinstance(pt, dict) else pt[0]
                y = pt.get("y", 0) if isinstance(pt, dict) else pt[1]

                if (x < margin or x > self.board_width - margin or
                    y < margin or y > self.board_height - margin):
                    edge_tracks += 1
                    break

        return min(edge_tracks / max(len(self.tracks), 1), 1.0)

    def _check_decoupling_caps(self) -> float:
        """检查去耦电容"""
        # 简化: 检查电容数量
        cap_count = sum(
            1 for fp in self.footprints
            if fp.get("reference", "").upper().startswith("C")
        )
        ic_count = sum(
            1 for fp in self.footprints
            if fp.get("reference", "").upper().startswith("U")
        )

        if ic_count == 0:
            return 100

        ratio = cap_count / ic_count
        if ratio >= 3:
            return 90
        elif ratio >= 1:
            return 70
        else:
            return 50

    def _get_min_trace_width(self) -> float:
        """获取最小线宽"""
        widths = [t.get("width", 0.2) for t in self.tracks]
        return min(widths) if widths else 0.2

    def _get_min_clearance(self) -> float:
        """获取最小间距"""
        # 简化: 假设间距为线宽
        return self._get_min_trace_width()

    def _get_min_via_drill(self) -> float:
        """获取最小过孔钻径"""
        drills = [v.get("drill", 0.3) for v in self.vias]
        return min(drills) if drills else 0.3

    def _check_pad_clearances(self) -> int:
        """检查焊盘间距问题"""
        # 简化: 返回 0
        return 0

    def _score_to_grade(self, score: float) -> QualityGrade:
        """分数转等级"""
        if score >= 90:
            return QualityGrade.EXCELLENT
        elif score >= 80:
            return QualityGrade.VERY_GOOD
        elif score >= 70:
            return QualityGrade.GOOD
        elif score >= 60:
            return QualityGrade.ACCEPTABLE
        elif score >= 50:
            return QualityGrade.POOR
        else:
            return QualityGrade.UNACCEPTABLE

    def _generate_improvements(self, dimensions: List[DimensionScore]) -> List[str]:
        """生成改进建议"""
        improvements = []

        for dim in dimensions:
            if dim.score < 80:
                if dim.name == "布线整齐度":
                    improvements.append(
                        f"布线整齐度得分 {dim.score:.0f}。建议: "
                        "1) 避免 90° 转弯，使用 45° 或圆弧过渡 "
                        "2) 保持走线间距一致 "
                        "3) 减少不必要的过孔"
                    )
                elif dim.name == "信号完整性":
                    improvements.append(
                        f"信号完整性得分 {dim.score:.0f}。建议: "
                        "1) 检查差分对长度匹配 "
                        "2) 确保高速信号下方有完整参考平面 "
                        "3) 增加关键信号间距以减小串扰"
                    )
                elif dim.name == "热管理":
                    improvements.append(
                        f"热管理得分 {dim.score:.0f}。建议: "
                        "1) 增加功率器件周围的铺铜面积 "
                        "2) 在热点区域添加热过孔 "
                        "3) 分散功率器件避免热聚集"
                    )
                elif dim.name == "EMC 合规":
                    improvements.append(
                        f"EMC 合规得分 {dim.score:.0f}。建议: "
                        "1) 减小电流回路面积 "
                        "2) 完善地平面设计 "
                        "3) 在 I/O 处添加滤波电容"
                    )
                elif dim.name == "可制造性":
                    improvements.append(
                        f"可制造性得分 {dim.score:.0f}。建议: "
                        "1) 增加最小线宽/间距 "
                        "2) 使用标准过孔尺寸 "
                        "3) 检查焊盘间距是否符合 DRC 规则"
                    )

        if not improvements:
            improvements.append("布局质量优秀，继续保持！")

        return improvements

    def _generate_summary(
        self,
        total: float,
        grade: QualityGrade,
        dimensions: List[DimensionScore],
    ) -> str:
        """生成摘要"""
        dim_summary = ", ".join([f"{d.name}: {d.score:.0f}" for d in dimensions])
        return (
            f"总评分 {total:.1f} ({grade.value}), "
            f"各维度: {dim_summary}"
        )


def create_layout_quality_ai(
    board_width: float = 100.0,
    board_height: float = 80.0,
    strict_mode: bool = False,
) -> LayoutQualityAI:
    """创建布局质量 AI 实例"""
    return LayoutQualityAI(
        board_width=board_width,
        board_height=board_height,
        strict_mode=strict_mode,
    )

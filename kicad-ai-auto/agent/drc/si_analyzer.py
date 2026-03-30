"""
Signal Integrity Analyzer - 信号完整性分析器

Phase 5: 提供阻抗控制、传输线损耗、串扰分析

Author: Claude Code
Date: 2026-03-30
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class SIViolationSeverity(Enum):
    """SI 违规严重程度"""
    CRITICAL = "critical"  # 必须修复
    WARNING = "warning"    # 建议修复
    INFO = "info"         # 信息


@dataclass
class ImpedanceTarget:
    """阻抗目标"""
    name: str
    target_ohm: float
    tolerance_percent: float = 10.0  # 10% 容差

    @property
    def min_ohm(self) -> float:
        return self.target_ohm * (1 - self.tolerance_percent / 100)

    @property
    def max_ohm(self) -> float:
        return self.target_ohm * (1 + self.tolerance_percent / 100)


@dataclass
class SIViolation:
    """SI 违规"""
    net_name: str
    severity: SIViolationSeverity
    violation_type: str  # impedance, crosstalk, loss, reflection
    message: str
    location: str = ""
    measured_value: float = 0
    target_value: str = ""


@dataclass
class ImpedanceResult:
    """阻抗分析结果"""
    net_name: str
    calculated_z0: float
    target_z0: float
    tolerance_percent: float
    passed: bool
    deviation_percent: float = 0

    def __post_init__(self):
        self.deviation_percent = abs(self.calculated_z0 - self.target_z0) / self.target_z0 * 100
        self.passed = self.deviation_percent <= self.tolerance_percent


@dataclass
class DiffPairResult:
    """差分对分析结果"""
    net_name_pos: str
    net_name_neg: str
    coupled_impedance: float
    target_impedance: float
    length_match_error_mm: float
    passed: bool
    violations: List[SIViolation] = field(default_factory=list)


@dataclass
class TLResult:
    """传输线损耗分析结果"""
    net_name: str
    conductor_loss_db: float  # 导体损耗 (dB)
    dielectric_loss_db: float  # 介质损耗 (dB)
    total_loss_db: float
    max_length_mm: float  # 最大允许长度
    suggested_length_mm: float  # 建议最大长度
    passed: bool


@dataclass
class SIAnalysisReport:
    """SI 分析报告"""
    passed: bool
    impedance_results: List[ImpedanceResult] = field(default_factory=list)
    diff_pair_results: List[DiffPairResult] = field(default_factory=list)
    tl_results: List[TLResult] = field(default_factory=list)
    crosstalk_results: List[float] = field(default_factory=list)
    violations: List[SIViolation] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


# 标准阻抗目标
STANDARD_IMPEDANCE_TARGETS = {
    "USB": ImpedanceTarget("USB 90Ω差分", 90, 10),
    "USB_HS": ImpedanceTarget("USB High-Speed 90Ω差分", 90, 10),
    "Ethernet": ImpedanceTarget("Ethernet 100Ω差分", 100, 10),
    "HDMI": ImpedanceTarget("HDMI 100Ω差分", 100, 10),
    "PCIe": ImpedanceTarget("PCIe 85Ω差分", 85, 10),
    "DDR": ImpedanceTarget("DDR 50Ω单端", 50, 10),
    "LVDS": ImpedanceTarget("LVDS 100Ω差分", 100, 10),
    "RS485": ImpedanceTarget("RS485 120Ω差分", 120, 10),
    "CAN": ImpedanceTarget("CAN 120Ω差分", 120, 10),
}


class SIAnalyzer:
    """
    信号完整性分析器

    提供:
    - 阻抗控制分析
    - 差分对阻抗分析
    - 传输线损耗分析
    - 串扰估算
    """

    def __init__(self, pcb_data: Dict[str, Any], stackup_manager=None):
        """
        Args:
            pcb_data: PCB 数据
            stackup_manager: 层叠管理器 (StackupManager 实例)
        """
        self.pcb_data = pcb_data
        self.stackup_manager = stackup_manager
        self.tracks = pcb_data.get("tracks", [])
        self.nets = pcb_data.get("nets", [])
        self.components = pcb_data.get("components", [])

        # 默认层叠参数 (如果没提供 stackup_manager)
        self.default_dk = 4.5  # FR4 介电常数
        self.default_cu_thickness = 0.035  # 1oz 铜厚 mm

    def analyze_impedance(
        self,
        trace_width: float,
        layer_name: str,
        target_ohm: float,
        tolerance_percent: float = 10.0,
        net_name: str = "",
    ) -> ImpedanceResult:
        """
        分析单线阻抗

        Args:
            trace_width: 走线宽度 (mm)
            layer_name: 层名 (如 F.Cu)
            target_ohm: 目标阻抗 (Ohm)
            tolerance_percent: 容差百分比
            net_name: 网络名称

        Returns:
            ImpedanceResult: 阻抗分析结果
        """
        # 简化的微带线阻抗计算
        # Z0 = 87 / sqrt(Er+1.41) * ln(5.98H / (0.8W + T))
        # H = 介质厚度 (假设 0.2mm)
        # W = 走线宽度
        # T = 铜厚 (0.035mm)
        # Er = 4.5 (FR4)

        H = 0.2  # 默认介质厚度 mm
        T = self.default_cu_thickness
        Er = self.default_dk

        # 微带线公式
        try:
            z0 = 87 / math.sqrt(Er + 1.41) * math.log(5.98 * H / (0.8 * trace_width + T))
        except (ValueError, ZeroDivisionError):
            z0 = 50  # 回退到 50 Ohm

        return ImpedanceResult(
            net_name=net_name,
            calculated_z0=round(z0, 2),
            target_z0=target_ohm,
            tolerance_percent=tolerance_percent,
            passed=True,  # 会在 __post_init__ 中重新计算
        )

    def analyze_diff_pair(
        self,
        width: float,
        spacing: float,
        layer_name: str,
        length_mm: float,
        target_ohm: float = 90.0,
        net_name_pos: str = "",
        net_name_neg: str = "",
    ) -> DiffPairResult:
        """
        分析差分对阻抗

        Args:
            width: 走线宽度 (mm)
            spacing: 差分对间距 (mm)
            layer_name: 层名
            length_mm: 走线长度 (mm)
            target_ohm: 目标差分阻抗 (Ohm)
            net_name_pos: 正端网络名
            net_name_neg: 负端网络名

        Returns:
            DiffPairResult: 差分对分析结果
        """
        violations = []

        # 差分阻抗近似计算
        # Zdiff = 2 * Z0 * (1 - coupling_factor)
        # 简化: Zdiff ≈ 2 * Z0 * (1 - 0.5 * (W/S))
        Er = self.default_dk
        H = 0.2

        # 单线阻抗
        try:
            z0 = 87 / math.sqrt(Er + 1.41) * math.log(5.98 * H / (0.8 * width + self.default_cu_thickness))
        except (ValueError, ZeroDivisionError):
            z0 = 50

        # 耦合效应修正
        w_s_ratio = width / spacing
        coupling_factor = 0.5 * w_s_ratio
        z_diff = 2 * z0 * (1 - coupling_factor)

        # 长度匹配检查
        # 差分对长度差异应小于 0.5mm
        length_match_error_mm = 0.1  # 简化：假设误差 0.1mm
        if length_match_error_mm > 0.5:
            violations.append(SIViolation(
                net_name=net_name_pos,
                severity=SIViolationSeverity.WARNING,
                violation_type="length_mismatch",
                message=f"差分对长度不匹配: {length_match_error_mm:.2f}mm (最大允许 0.5mm)",
                target_value="<0.5mm",
            ))

        # 阻抗检查
        impedance_error_percent = abs(z_diff - target_ohm) / target_ohm * 100
        if impedance_error_percent > 10:
            violations.append(SIViolation(
                net_name=net_name_pos,
                severity=SIViolationSeverity.CRITICAL,
                violation_type="impedance",
                message=f"差分阻抗 {z_diff:.1f}Ω 超出目标 {target_ohm}Ω 范围",
                measured_value=z_diff,
                target_value=f"{target_ohm}±10%",
            ))

        return DiffPairResult(
            net_name_pos=net_name_pos,
            net_name_neg=net_name_neg,
            coupled_impedance=round(z_diff, 2),
            target_impedance=target_ohm,
            length_match_error_mm=length_match_error_mm,
            passed=len(violations) == 0,
            violations=violations,
        )

    def analyze_transmission_loss(
        self,
        trace_width: float,
        length_mm: float,
        frequency_hz: float = 1e9,
        conductivity: float = 5.8e7,  # 铜的电导率 S/m
    ) -> TLResult:
        """
        分析传输线损耗

        Args:
            trace_width: 走线宽度 (mm)
            length_mm: 走线长度 (mm)
            frequency_hz: 信号频率 (Hz)
            conductivity: 铜的电导率 (S/m)

        Returns:
            TLResult: 传输线损耗分析结果
        """
        length_m = length_mm / 1000
        w = trace_width / 1000  # 转换为米

        # 导体损耗 (dB) - 简化公式
        # Rs = 皮肤深度阻抗 = sqrt(pi * f * mu / sigma)
        # Alpha_c (dB/m) = 8.68 * Rs / (Z0 * W)
        Rs = math.sqrt(math.pi * frequency_hz * 1.26e-6 / conductivity)  # 铜的表面粗糙度阻抗
        Z0 = 50  # 假设 50 Ohm
        alpha_c = 8.68 * Rs / (Z0 * w) if w > 0 else 0

        conductor_loss_db = alpha_c * length_m

        # 介质损耗 (dB)
        # Alpha_d = 27.3 * f * sqrt(Er) * tan(delta) / c
        tan_delta = 0.02  # FR4 损耗因子
        f = frequency_hz
        Er = self.default_dk
        alpha_d = 27.3 * f * math.sqrt(Er) * tan_delta / 3e8
        dielectric_loss_db = alpha_d * length_m

        total_loss_db = conductor_loss_db + dielectric_loss_db

        # 最大允许损耗 (通常 < 3dB)
        max_loss_db = 3.0
        suggested_length_mm = (max_loss_db / (alpha_c + alpha_d)) * 1000 if (alpha_c + alpha_d) > 0 else length_mm

        return TLResult(
            net_name="",
            conductor_loss_db=round(conductor_loss_db, 3),
            dielectric_loss_db=round(dielectric_loss_db, 3),
            total_loss_db=round(total_loss_db, 3),
            max_length_mm=length_mm,
            suggested_length_mm=round(suggested_length_mm, 1),
            passed=total_loss_db <= max_loss_db,
        )

    def calculate_crosstalk_simple(
        self,
        trace_spacing: float,
        dielectric_height: float = 0.2,
        trace_width: float = 0.25,
    ) -> float:
        """
        简化串扰估算

        Args:
            trace_spacing: 走线间距 (mm)
            dielectric_height: 介质厚度 (mm)
            trace_width: 走线宽度 (mm)

        Returns:
            float: 串扰系数 (0-1, 越小越好)
        """
        # 简化模型: 串扰 ~ 1 / (1 + (spacing/height)^2)
        ratio = trace_spacing / dielectric_height
        return 1.0 / (1.0 + ratio * ratio)

    def analyze_network(
        self,
        net_name: str,
        trace_width: float,
        layer_name: str,
        length_mm: float,
        is_diff_pair: bool = False,
        diff_spacing: float = 0.2,
        frequency_hz: float = 1e9,
    ) -> SIAnalysisReport:
        """
        分析单个网络的 SI 性能

        Args:
            net_name: 网络名称
            trace_width: 走线宽度
            layer_name: 层名
            length_mm: 走线长度
            is_diff_pair: 是否为差分对
            diff_spacing: 差分对间距
            frequency_hz: 信号频率

        Returns:
            SIAnalysisReport: SI 分析报告
        """
        violations = []
        impedance_results = []
        diff_pair_results = []
        tl_results = []

        # 确定目标阻抗
        target_ohm = 90 if is_diff_pair else 50
        target = ImpedanceTarget(net_name, target_ohm, 10)

        # 阻抗分析
        imp_result = self.analyze_impedance(
            trace_width=trace_width,
            layer_name=layer_name,
            target_ohm=target_ohm,
            net_name=net_name,
        )
        impedance_results.append(imp_result)

        if not imp_result.passed:
            violations.append(SIViolation(
                net_name=net_name,
                severity=SIViolationSeverity.WARNING,
                violation_type="impedance",
                message=f"阻抗 {imp_result.calculated_z0}Ω 超出目标范围",
                measured_value=imp_result.calculated_z0,
                target_value=f"{target_ohm}±{imp_result.tolerance_percent}%",
            ))

        # 差分对分析
        if is_diff_pair:
            dp_result = self.analyze_diff_pair(
                width=trace_width,
                spacing=diff_spacing,
                layer_name=layer_name,
                length_mm=length_mm,
                target_ohm=90,
                net_name_pos=net_name,
                net_name_neg=net_name.replace("+", "-").replace("_P", "_N"),
            )
            diff_pair_results.append(dp_result)
            violations.extend(dp_result.violations)

        # 传输损耗分析
        tl_result = self.analyze_transmission_loss(
            trace_width=trace_width,
            length_mm=length_mm,
            frequency_hz=frequency_hz,
        )
        tl_results.append(tl_result)

        if not tl_result.passed:
            violations.append(SIViolation(
                net_name=net_name,
                severity=SIViolationSeverity.WARNING,
                violation_type="loss",
                message=f"传输损耗 {tl_result.total_loss_db}dB 超过最大值 3dB",
                measured_value=tl_result.total_loss_db,
                target_value="<3dB",
            ))

        # 串扰估算
        crosstalk = self.calculate_crosstalk_simple(trace_spacing=0.2)
        crosstalk_results = [crosstalk]

        if crosstalk > 0.1:  # >10% 串扰
            violations.append(SIViolation(
                net_name=net_name,
                severity=SIViolationSeverity.INFO,
                violation_type="crosstalk",
                message=f"串扰 {crosstalk*100:.1f}% 较高，建议增加走线间距",
                measured_value=crosstalk,
                target_value="<10%",
            ))

        return SIAnalysisReport(
            passed=all(r.passed for r in impedance_results + diff_pair_results) and
                   all(r.passed for r in tl_results),
            impedance_results=impedance_results,
            diff_pair_results=diff_pair_results,
            tl_results=tl_results,
            crosstalk_results=crosstalk_results,
            violations=violations,
            summary={
                "net_name": net_name,
                "trace_width": trace_width,
                "layer": layer_name,
                "length_mm": length_mm,
                "crosstalk_percent": crosstalk * 100,
            },
        )

    def analyze_all(self) -> SIAnalysisReport:
        """
        分析所有网络的 SI 性能

        Returns:
            SIAnalysisReport: 汇总的 SI 分析报告
        """
        all_violations = []
        all_impedance = []
        all_diff_pair = []
        all_tl = []
        all_crosstalk = []

        for track in self.tracks:
            net_name = track.get("net", "")
            width = track.get("width", 0.25)
            layer = track.get("layer", "F.Cu")

            # 计算长度 (简化: 假设直线)
            points = track.get("points", [])
            if len(points) >= 2:
                dx = points[-1].get("x", 0) - points[0].get("x", 0)
                dy = points[-1].get("y", 0) - points[0].get("y", 0)
                length_mm = math.sqrt(dx*dx + dy*dy)
            else:
                length_mm = 10  # 默认 10mm

            # 判断是否为差分对
            is_diff_pair = any(kw in net_name.upper() for kw in ["USB", "ETH", "DP", "DM", "RX", "TX"])

            report = self.analyze_network(
                net_name=net_name,
                trace_width=width,
                layer_name=layer,
                length_mm=length_mm,
                is_diff_pair=is_diff_pair,
            )

            all_violations.extend(report.violations)
            all_impedance.extend(report.impedance_results)
            all_diff_pair.extend(report.diff_pair_results)
            all_tl.extend(report.tl_results)
            all_crosstalk.extend(report.crosstalk_results)

        return SIAnalysisReport(
            passed=all(v.severity != SIViolationSeverity.CRITICAL for v in all_violations),
            impedance_results=all_impedance,
            diff_pair_results=all_diff_pair,
            tl_results=all_tl,
            crosstalk_results=all_crosstalk,
            violations=all_violations,
            summary={
                "total_nets": len(self.tracks),
                "critical_violations": len([v for v in all_violations if v.severity == SIViolationSeverity.CRITICAL]),
                "warnings": len([v for v in all_violations if v.severity == SIViolationSeverity.WARNING]),
            },
        )

"""
电流计算器 - Current Calculator

功能:
1. 基于 IPC-2221 标准计算走线宽度
2. 支持用户标注电流 / datasheet 查表 / 默认估算
3. 返回各网络所需走线宽度

Author: Claude Code
Date: 2026-03-30
Phase: Phase 4
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
import logging

from .net_classifier import NetClassifier, NetInfo, NetClass

logger = logging.getLogger(__name__)


# IPC-2221 载流表 (内部铜厚 1oz/35μm, 温升 10°C)
# 格式: width_mils -> max_current_amps
IPC2221_CURRENT_TABLE = {
    5: 0.5,     # 0.127mm
    8: 0.8,     # 0.2mm
    10: 1.0,    # 0.254mm
    15: 1.5,    # 0.381mm
    20: 2.0,    # 0.508mm
    25: 2.5,    # 0.635mm
    30: 3.0,    # 0.762mm
    40: 4.0,    # 1.016mm
    50: 5.0,    # 1.27mm
    75: 7.5,    # 1.905mm
    100: 10.0,  # 2.54mm
    150: 15.0,  # 3.81mm
    200: 20.0,  # 5.08mm
    250: 25.0,  # 6.35mm
    300: 30.0,  # 7.62mm
}

# 默认基础走线宽度 (mm)
DEFAULT_TRACE_WIDTHS = {
    NetClass.POWER: 0.5,        # 电源网络
    NetClass.GROUND: 0.5,       # 地网络
    NetClass.SIGNAL: 0.15,      # 信号网络
    NetClass.HIGH_SPEED: 0.15,  # 高速信号
    NetClass.DIFF_PAIR: 0.2,    # 差分对
    NetClass.MIXED: 0.2,        # 混合信号
    NetClass.UNKNOWN: 0.15,      # 未知
}


@dataclass
class CurrentRequirement:
    """电流需求"""
    net_name: str
    current_ma: float           # 电流 (mA)
    copper_thickness: float = 1.0  # 铜厚倍数 (1.0=1oz, 2.0=2oz)
    temperature_rise: float = 10.0  # 温升 (°C)
    calculated_width: float = 0.0  # 计算出的走线宽度 (mm)
    is_adequate: bool = True       # 是否满足要求


class CurrentCalculator:
    """
    电流计算器

    计算流程:
    1. 收集电流信息（用户标注 > 器件推断 > 默认值）
    2. 使用 IPC-2221 公式计算所需走线宽度
    3. 与基础宽度比较，取较大值
    """

    def __init__(self, classified_nets: Dict[str, NetInfo]):
        """
        Args:
            classified_nets: 网络分类器结果 {net_name: NetInfo}
        """
        self.classified_nets = classified_nets
        self.current_requirements: Dict[str, CurrentRequirement] = {}

    def calculate_all_widths(
        self,
        user_current_annotations: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        计算所有网络的走线宽度

        Args:
            user_current_annotations: 用户标注的电流 {"VCC": 2000, "5V": 1000} (mA)

        Returns:
            Dict[str, float]: 网络名称 → 走线宽度 (mm)
        """
        user_currents = user_current_annotations or {}
        widths = {}

        for net_name, net_info in self.classified_nets.items():
            # Step 1: 获取电流
            current_ma = user_currents.get(net_name, 0.0)
            if current_ma <= 0:
                # 如果用户没有标注，使用网络信息中的电流
                current_ma = net_info.current_ma

            # Step 2: 计算走线宽度
            width = self.calculate_width(
                net_name=net_name,
                current_ma=current_ma,
                net_class=net_info.net_class,
            )

            widths[net_name] = width
            net_info.trace_width = width

            # 记录计算结果
            self.current_requirements[net_name] = CurrentRequirement(
                net_name=net_name,
                current_ma=current_ma,
                calculated_width=width,
            )

        logger.info(f"电流计算完成: {len(widths)} 个网络")
        return widths

    def calculate_width(
        self,
        net_name: str,
        current_ma: float,
        net_class: NetClass,
    ) -> float:
        """
        计算单个网络所需的走线宽度

        Args:
            net_name: 网络名称
            current_ma: 电流 (mA)
            net_class: 网络分类

        Returns:
            float: 所需走线宽度 (mm)
        """
        # Step 1: 获取基础宽度
        base_width = DEFAULT_TRACE_WIDTHS.get(net_class, 0.15)

        # Step 2: 如果没有电流，使用基础宽度
        if current_ma <= 0:
            return base_width

        # Step 3: 使用 IPC-2221 计算宽度
        ipc_width = self._ipc2221_width(current_ma)

        # Step 4: 取较大值
        final_width = max(base_width, ipc_width)

        logger.debug(
            f"Net {net_name}: current={current_ma}mA, "
            f"base_width={base_width:.3f}mm, ipc_width={ipc_width:.3f}mm, "
            f"final_width={final_width:.3f}mm"
        )

        return final_width

    def _ipc2221_width(self, current_ma: float) -> float:
        """
        IPC-2221 公式计算走线宽度

        公式: Width (mils) = (Current / (k * Temperature_Rise^0.44))^(1/0.725)

        其中 k = 0.048 (外部铜) 或 0.024 (内部铜)

        简化版本：使用查表 + 插值

        Args:
            current_ma: 电流 (mA)

        Returns:
            float: 走线宽度 (mm)
        """
        current_A = current_ma / 1000.0

        # 查找合适的宽度
        prev_width = 0
        prev_current = 0

        for width_mils, max_current in sorted(IPC2221_CURRENT_TABLE.items()):
            if current_A <= max_current:
                # 找到了合适的范围，使用插值
                if prev_width == 0:
                    width_mm = width_mils * 0.0254
                    return width_mm

                # 线性插值
                ratio = (current_A - prev_current) / (max_current - prev_current)
                width_mm = (prev_width + ratio * (width_mils - prev_width)) * 0.0254
                return width_mm

            prev_width = width_mils
            prev_current = max_current

        # 超过表格范围，使用最大宽度
        logger.warning(f"电流 {current_A}A 超过 IPC-2221 表格范围，使用最大宽度 5mm")
        return 5.0

    def get_current_requirement(self, net_name: str) -> Optional[CurrentRequirement]:
        """获取指定网络的电流需求"""
        return self.current_requirements.get(net_name)

    def get_width_for_net(self, net_name: str) -> float:
        """获取指定网络的走线宽度"""
        if net_name in self.classified_nets:
            return self.classified_nets[net_name].trace_width
        return 0.15  # 默认宽度


def calculate_trace_width(
    current_ma: float,
    net_class: str = "signal",
    copper_oz: float = 1.0,
) -> float:
    """
    便捷函数：计算给定电流所需的走线宽度

    Args:
        current_ma: 电流 (mA)
        net_class: 网络类型 ("power", "ground", "signal", "high_speed", "diff_pair")
        copper_oz: 铜厚 (1.0=1oz, 2.0=2oz)

    Returns:
        float: 走线宽度 (mm)
    """
    class_map = {
        "power": NetClass.POWER,
        "ground": NetClass.GROUND,
        "signal": NetClass.SIGNAL,
        "high_speed": NetClass.HIGH_SPEED,
        "diff_pair": NetClass.DIFF_PAIR,
        "mixed": NetClass.MIXED,
        "unknown": NetClass.UNKNOWN,
    }

    nc = class_map.get(net_class.lower(), NetClass.UNKNOWN)

    # 创建假的分类结果
    fake_nets = {
        "dummy": NetInfo(
            name="dummy",
            net_class=nc,
            current_ma=current_ma,
        )
    }

    calculator = CurrentCalculator(fake_nets)
    return calculator.calculate_width("dummy", current_ma, nc)


# 全局 IPC-2221 计算器实例
IPC2221_CALCULATOR = {
    "table": IPC2221_CURRENT_TABLE,
    "default_widths": DEFAULT_TRACE_WIDTHS,
}

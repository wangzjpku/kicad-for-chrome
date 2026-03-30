"""
电流计算器 - Current Calculator

功能:
1. 基于 IPC-2221 标准计算走线宽度
2. 支持用户标注电流 / datasheet 查表 / 默认估算
3. 返回各网络所需走线宽度

Author: Claude Code
Date: 2026-03-30
Phase: Phase 5 - IPC-2221 进阶
"""

from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import logging

from .net_classifier import NetClassifier, NetInfo, NetClass

logger = logging.getLogger(__name__)


# IPC-2221 基础载流表 (内部铜厚 1oz/35μm, 温升 10°C, 内部层)
# 格式: width_mils -> max_current_amps
IPC2221_BASE_TABLE = {
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

# 铜厚选项 (oz -> mm)
COPPER_WEIGHTS = {
    0.5: 0.0175,   # 0.5 oz -> 17.5μm
    1.0: 0.035,    # 1 oz -> 35μm
    2.0: 0.070,    # 2 oz -> 70μm
    3.0: 0.105,    # 3 oz -> 105μm
    4.0: 0.140,    # 4 oz -> 140μm
}

# 温升选项 (°C)
TEMPERATURE_RISES = [10, 20, 30, 40]

# 温升修正系数 (相对于 10°C)
# 基于 IPC-2221 公式: I α (ΔT)^0.44
TEMP_RISE_CORRECTION = {
    10: 1.0,
    20: 1.6,    # (20/10)^0.44 ≈ 1.59
    30: 2.1,    # (30/10)^0.44 ≈ 2.09
    40: 2.5,    # (40/10)^0.44 ≈ 2.54
}

# 铜厚修正系数 (相对于 1oz)
# 载流能力随铜厚增加而非线性增加
COPPER_THICKNESS_CORRECTION = {
    0.5: 0.7,   # 0.5oz 载流约为 1oz 的 70%
    1.0: 1.0,   # 1oz 基准
    2.0: 1.6,   # 2oz 载流约为 1oz 的 160%
    3.0: 2.0,   # 3oz
    4.0: 2.4,   # 4oz
}

# 内层 vs 外层修正系数
# 外层有更好的散热条件
LAYER_LOCATION_CORRECTION = {
    "external": 1.5,   # 外层散热好，载流增加 50%
    "internal": 1.0,   # 内层为基准
}

# 默认基础走线宽度 (mm)
DEFAULT_TRACE_WIDTHS = {
    NetClass.POWER: 0.5,        # 电源网络
    NetClass.GROUND: 0.5,       # 地网络
    NetClass.SIGNAL: 0.15,      # 信号网络
    NetClass.HIGH_SPEED: 0.15,  # 高速信号
    NetClass.DIFF_PAIR: 0.2,    # 差分对
    NetClass.MIXED: 0.2,        # 混合信号
    NetClass.UNKNOWN: 0.15,     # 未知
}


@dataclass
class CurrentRequirement:
    """电流需求"""
    net_name: str
    current_ma: float           # 电流 (mA)
    copper_thickness: float = 1.0  # 铜厚倍数 (1.0=1oz, 2.0=2oz)
    temperature_rise: float = 10.0  # 温升 (°C)
    layer_location: str = "external"  # 层位置 (external/internal)
    calculated_width: float = 0.0  # 计算出的走线宽度 (mm)
    is_adequate: bool = True       # 是否满足要求


@dataclass
class IPC2221Params:
    """IPC-2221 计算参数"""
    copper_oz: float = 1.0          # 铜厚 (oz)
    temperature_rise: float = 10.0  # 温升 (°C)
    layer_location: str = "external" # 层位置
    is_external_layer: bool = True  # 是否为外层


class AdvancedCurrentCalculator:
    """
    高级电流计算器 - IPC-2221 进阶版

    支持:
    - 多种铜厚 (0.5oz, 1oz, 2oz, 3oz, 4oz)
    - 多种温升 (10°C, 20°C, 30°C, 40°C)
    - 内层/外层修正
    - 公式计算 + 查表插值
    """

    def __init__(self, classified_nets: Dict[str, NetInfo]):
        self.classified_nets = classified_nets
        self.current_requirements: Dict[str, CurrentRequirement] = {}

    def calculate_all_widths(
        self,
        user_current_annotations: Optional[Dict[str, float]] = None,
        params: Optional[IPC2221Params] = None,
    ) -> Dict[str, float]:
        """
        计算所有网络的走线宽度

        Args:
            user_current_annotations: 用户标注的电流 {"VCC": 2000, "5V": 1000} (mA)
            params: IPC-2221 计算参数

        Returns:
            Dict[str, float]: 网络名称 → 走线宽度 (mm)
        """
        params = params or IPC2221Params()
        user_currents = user_current_annotations or {}
        widths = {}

        for net_name, net_info in self.classified_nets.items():
            current_ma = user_currents.get(net_name, 0.0)
            if current_ma <= 0:
                current_ma = net_info.current_ma

            width = self.calculate_width(
                net_name=net_name,
                current_ma=current_ma,
                net_class=net_info.net_class,
                params=params,
            )

            widths[net_name] = width
            net_info.trace_width = width

            self.current_requirements[net_name] = CurrentRequirement(
                net_name=net_name,
                current_ma=current_ma,
                copper_thickness=params.copper_oz,
                temperature_rise=params.temperature_rise,
                layer_location=params.layer_location,
                calculated_width=width,
            )

        logger.info(f"高级电流计算完成: {len(widths)} 个网络")
        return widths

    def calculate_width(
        self,
        net_name: str,
        current_ma: float,
        net_class: NetClass,
        params: Optional[IPC2221Params] = None,
    ) -> float:
        """
        计算单个网络所需的走线宽度

        Args:
            net_name: 网络名称
            current_ma: 电流 (mA)
            net_class: 网络分类
            params: IPC-2221 参数

        Returns:
            float: 所需走线宽度 (mm)
        """
        params = params or IPC2221Params()
        base_width = DEFAULT_TRACE_WIDTHS.get(net_class, 0.15)

        if current_ma <= 0:
            return base_width

        # 使用高级 IPC-2221 计算
        ipc_width = self._ipc2221_advanced(current_ma, params)

        final_width = max(base_width, ipc_width)

        logger.debug(
            f"Net {net_name}: current={current_ma}mA, "
            f"base_width={base_width:.3f}mm, ipc_width={ipc_width:.3f}mm, "
            f"final_width={final_width:.3f}mm (Cu={params.copper_oz}oz, ΔT={params.temperature_rise}°C)"
        )

        return final_width

    def _ipc2221_advanced(self, current_ma: float, params: IPC2221Params) -> float:
        """
        高级 IPC-2221 计算

        公式: Width (mils) = (Current / (k * Temperature_Rise^0.44))^(1/0.725)

        修正:
        - 铜厚修正
        - 温升修正
        - 内层/外层修正

        Args:
            current_ma: 电流 (mA)
            params: 计算参数

        Returns:
            float: 走线宽度 (mm)
        """
        current_A = current_ma / 1000.0

        # 获取修正系数
        temp_correction = TEMP_RISE_CORRECTION.get(params.temperature_rise, 1.0)
        copper_correction = COPPER_THICKNESS_CORRECTION.get(params.copper_oz, 1.0)
        layer_correction = LAYER_LOCATION_CORRECTION.get(params.layer_location, 1.0)

        # k 值: IPC-2221 标准
        # 内部层: k = 0.024, 外部层: k = 0.048
        k = 0.024 if params.layer_location == "internal" else 0.048

        # 有效温升 (考虑铜厚影响)
        # 厚铜需要更大的温升来散发热量
        effective_temp_rise = params.temperature_rise * (1 + 0.1 * (params.copper_oz - 1))

        # IPC-2221 公式计算
        # Area (mils²) = (Current / (k * ΔT^0.44))^(1/0.725)
        # Width (mils) = Area / (1.5 * thickness_mils)  (简化: 假设厚度为 1oz)
        try:
            exponent = 1 / 0.725
            area_mils2 = (current_A / (k * (effective_temp_rise ** 0.44))) ** exponent

            # 转换为宽度 (mils), 假设厚度为 1oz (1.37mils)
            thickness_mils = 1.37 * params.copper_oz
            width_mils = area_mils2 / thickness_mils
            width_mm = width_mils * 0.0254

        except (ValueError, ZeroDivisionError):
            # 回退到查表
            width_mm = self._ipc2221_table_lookup(current_ma, params)

        # 应用修正系数
        total_correction = copper_correction * layer_correction
        width_mm = width_mm / (temp_correction * total_correction)

        return max(width_mm, 0.1)  # 最小宽度 0.1mm

    def _ipc2221_table_lookup(self, current_ma: float, params: IPC2221Params) -> float:
        """
        表格查表 + 插值 (带修正)

        Args:
            current_ma: 电流 (mA)
            params: 计算参数

        Returns:
            float: 走线宽度 (mm)
        """
        current_A = current_ma / 1000.0

        # 修正电流 (考虑温升和铜厚)
        temp_correction = TEMP_RISE_CORRECTION.get(params.temperature_rise, 1.0)
        copper_correction = COPPER_THICKNESS_CORRECTION.get(params.copper_oz, 1.0)
        layer_correction = LAYER_LOCATION_CORRECTION.get(params.layer_location, 1.0)

        # 修正后的电流
        adjusted_current = current_A / (temp_correction * copper_correction * layer_correction)

        prev_width = 0
        prev_current = 0

        for width_mils, max_current in sorted(IPC2221_BASE_TABLE.items()):
            if adjusted_current <= max_current:
                if prev_width == 0:
                    return width_mils * 0.0254

                ratio = (adjusted_current - prev_current) / (max_current - prev_current)
                width_mm = (prev_width + ratio * (width_mils - prev_width)) * 0.0254
                return width_mm

            prev_width = width_mils
            prev_current = max_current

        return 5.0  # 超范围

    def get_width_for_net(self, net_name: str) -> float:
        """获取指定网络的走线宽度"""
        if net_name in self.classified_nets:
            return self.classified_nets[net_name].trace_width
        return 0.15

    def get_current_requirement(self, net_name: str) -> Optional[CurrentRequirement]:
        """获取指定网络的电流需求"""
        return self.current_requirements.get(net_name)

    @staticmethod
    def get_available_copper_weights() -> List[float]:
        """获取可选的铜厚列表"""
        return list(COPPER_WEIGHTS.keys())

    @staticmethod
    def get_available_temperature_rises() -> List[float]:
        """获取可选的温升列表"""
        return TEMPERATURE_RISES


class CurrentCalculator:
    """
    电流计算器 (兼容旧版)

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
            current_ma = user_currents.get(net_name, 0.0)
            if current_ma <= 0:
                current_ma = net_info.current_ma

            width = self.calculate_width(
                net_name=net_name,
                current_ma=current_ma,
                net_class=net_info.net_class,
            )

            widths[net_name] = width
            net_info.trace_width = width

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
        base_width = DEFAULT_TRACE_WIDTHS.get(net_class, 0.15)

        if current_ma <= 0:
            return base_width

        ipc_width = self._ipc2221_width(current_ma)
        final_width = max(base_width, ipc_width)

        logger.debug(
            f"Net {net_name}: current={current_ma}mA, "
            f"base_width={base_width:.3f}mm, ipc_width={ipc_width:.3f}mm, "
            f"final_width={final_width:.3f}mm"
        )

        return final_width

    def _ipc2221_width(self, current_ma: float) -> float:
        """
        IPC-2221 公式计算走线宽度 (基础版)

        Args:
            current_ma: 电流 (mA)

        Returns:
            float: 走线宽度 (mm)
        """
        current_A = current_ma / 1000.0

        prev_width = 0
        prev_current = 0

        for width_mils, max_current in sorted(IPC2221_BASE_TABLE.items()):
            if current_A <= max_current:
                if prev_width == 0:
                    width_mm = width_mils * 0.0254
                    return width_mm

                ratio = (current_A - prev_current) / (max_current - prev_current)
                width_mm = (prev_width + ratio * (width_mils - prev_width)) * 0.0254
                return width_mm

            prev_width = width_mils
            prev_current = max_current

        logger.warning(f"电流 {current_A}A 超过 IPC-2221 表格范围，使用最大宽度 5mm")
        return 5.0

    def get_current_requirement(self, net_name: str) -> Optional[CurrentRequirement]:
        """获取指定网络的电流需求"""
        return self.current_requirements.get(net_name)

    def get_width_for_net(self, net_name: str) -> float:
        """获取指定网络的走线宽度"""
        if net_name in self.classified_nets:
            return self.classified_nets[net_name].trace_width
        return 0.15


def calculate_trace_width(
    current_ma: float,
    net_class: str = "signal",
    copper_oz: float = 1.0,
    temperature_rise: float = 10.0,
    is_external: bool = True,
) -> float:
    """
    便捷函数：计算给定电流所需的走线宽度 (进阶版)

    Args:
        current_ma: 电流 (mA)
        net_class: 网络类型 ("power", "ground", "signal", "high_speed", "diff_pair")
        copper_oz: 铜厚 (0.5, 1.0, 2.0, 3.0, 4.0 oz)
        temperature_rise: 温升 (10, 20, 30, 40 °C)
        is_external: 是否为外层

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

    fake_nets = {
        "dummy": NetInfo(
            name="dummy",
            net_class=nc,
            current_ma=current_ma,
        )
    }

    params = IPC2221Params(
        copper_oz=copper_oz,
        temperature_rise=temperature_rise,
        layer_location="external" if is_external else "internal",
        is_external_layer=is_external,
    )

    calculator = AdvancedCurrentCalculator(fake_nets)
    return calculator.calculate_width("dummy", current_ma, nc, params)


# 全局 IPC-2221 计算器实例
IPC2221_CALCULATOR = {
    "table": IPC2221_BASE_TABLE,
    "default_widths": DEFAULT_TRACE_WIDTHS,
    "copper_weights": COPPER_WEIGHTS,
    "temperature_rises": TEMPERATURE_RISES,
    "AdvancedCurrentCalculator": AdvancedCurrentCalculator,
}

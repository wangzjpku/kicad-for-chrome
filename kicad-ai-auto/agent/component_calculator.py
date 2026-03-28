"""
参数计算器 - 电路参数计算

功能:
1. LED限流电阻计算
2. 晶振负载电容计算
3. 去耦电容选择
4. 分压电阻计算
5. 电源滤波电容计算
"""

import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


# 标准电阻值 (E24系列)
E24_SERIES = [
    1.0,
    1.1,
    1.2,
    1.3,
    1.5,
    1.6,
    1.8,
    2.0,
    2.2,
    2.4,
    2.7,
    3.0,
    3.3,
    3.6,
    3.9,
    4.3,
    4.7,
    5.1,
    5.6,
    6.2,
    6.8,
    7.5,
    8.2,
    9.1,
    10,
    11,
    12,
    13,
    15,
    16,
    18,
    20,
    22,
    24,
    27,
    30,
    33,
    36,
    39,
    43,
    47,
    51,
    56,
    62,
    68,
    75,
    82,
    91,
]

# E24 × 10^n 倍数
E24_MULTIPLIERS = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0]

# 标准电容值 (E12系列)
E12_SERIES = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]

E12_MULTIPLIERS = [1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0, 1000000.0]


@dataclass
class CalculationResult:
    """计算结果"""

    calculated_value: float
    standard_value: float
    unit: str
    formula: str
    warnings: List[str]
    alternatives: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calculated_value": self.calculated_value,
            "standard_value": self.standard_value,
            "unit": self.unit,
            "formula": self.formula,
            "warnings": self.warnings,
            "alternatives": self.alternatives,
        }


def find_nearest_standard(
    values: List[float], multipliers: List[float], target: float
) -> tuple:
    """查找最接近的标准值"""
    best_value = values[0] * multipliers[0]
    best_error = abs(target - best_value)

    for v in values:
        for m in multipliers:
            value = v * m
            error = abs(target - value)
            if error < best_error:
                best_error = error
                best_value = value

    # 找备选值
    alternatives = []
    for v in values:
        for m in multipliers:
            value = v * m
            if (
                abs(value - target) < best_error * 3
                and abs(value - best_value) > 0.01 * best_value
            ):
                alternatives.append(value)
                if len(alternatives) >= 3:
                    break
        if len(alternatives) >= 3:
            break

    return best_value, alternatives[:3]


def calculate_led_resistor(
    vcc: float, vf: float = 2.0, if_current: float = 10.0
) -> CalculationResult:
    """
    计算LED限流电阻

    Args:
        vcc: 电源电压 (V)
        vf: LED正向压降 (V), 默认2.0V
        if_current: LED工作电流 (mA), 默认10mA

    Returns:
        计算结果
    """
    if_current = if_current / 1000  # 转换为A

    # 基础计算
    resistance = (vcc - vf) / if_current
    power = (vcc - vf) * if_current

    warnings = []

    # 功率余量检查
    recommended_power = power * 2  # 100%余量
    if recommended_power < 0.125:
        recommended_power = 0.125
    elif recommended_power < 0.25:
        recommended_power = 0.25
    elif recommended_power < 0.5:
        recommended_power = 0.5
    else:
        recommended_power = 1.0

    # 封装选择
    if recommended_power <= 0.125:
        package = "0402"
    elif recommended_power <= 0.25:
        package = "0603"
    elif recommended_power <= 0.5:
        package = "0805"
    else:
        package = "1206"

    # 精度选择
    tolerance = "1%" if resistance > 1000 else "5%"

    # 标准值
    std_value, alternatives = find_nearest_standard(
        E24_SERIES, E24_MULTIPLIERS, resistance
    )

    # 实际功率
    actual_power = (vcc - vf) * (vcc - vf) / std_value
    if actual_power > recommended_power:
        warnings.append(f"警告: 实际功率 {actual_power:.3f}W 超过封装额定功率")

    formula = f"R = (Vcc - Vf) / If = ({vcc}V - {vf}V) / {if_current * 1000}mA = {resistance:.0f}Ω"

    return CalculationResult(
        calculated_value=resistance,
        standard_value=std_value,
        unit="Ω",
        formula=formula,
        warnings=warnings,
        alternatives=[f"{a:.1f}Ω" for a in alternatives],
    )


def calculate_crystal_load_capacitor(
    cl: float, c_internal: float = 5.0, c_stray: float = 3.0
) -> CalculationResult:
    """
    计算晶振负载电容

    Args:
        cl: 晶振负载电容 (pF)
        c_internal: MCU内部电容 (pF), 默认5pF
        c_stray: 杂散电容 (pF), 默认3pF

    Returns:
        计算结果

    Note:
        C1 = C2 = 2 × (CL - C_stray - C_internal)
    """
    # 计算所需电容
    c_calc = 2 * (cl - c_stray - c_internal)

    warnings = []
    if c_calc < 0:
        warnings.append("警告: 计算值为负, 内部电容可能已足够")
        c_calc = 0

    # 标准值
    std_value, alternatives = find_nearest_standard(E12_SERIES, E12_MULTIPLIERS, c_calc)

    # 实际负载电容
    actual_cl = (std_value * std_value) / (2 * c_stray + std_value)

    formula = f"C1 = C2 = 2 × (CL - C_stray - C_internal) = 2 × ({cl}pF - {c_stray}pF - {c_internal}pF) = {c_calc:.1f}pF"

    return CalculationResult(
        calculated_value=c_calc,
        standard_value=std_value,
        unit="pF",
        formula=formula,
        warnings=warnings,
        alternatives=[f"{a:.0f}pF" for a in alternatives],
    )


def calculate_decoupling_capacitor(
    vcc: float, current: float = 100.0
) -> Dict[str, Any]:
    """
    计算去耦电容

    Args:
        vcc: 电源电压 (V)
        current: 最大工作电流 (mA)

    Returns:
        推荐的电容组合
    """
    recommendations = {
        "high_frequency": {
            "value": 100,
            "unit": "nF",
            "package": "0402",
            "type": "X7R ceramic",
            "position": "靠近芯片电源引脚",
        },
        "bulk": {
            "value": 10,
            "unit": "μF",
            "package": "0805",
            "type": "X5R ceramic",
            "position": "电源入口",
        },
    }

    # 根据电流调整
    if current > 500:
        recommendations["bulk"]["value"] = 47
        recommendations["bulk"]["package"] = "1206"

    return recommendations


def calculate_voltage_divider(
    vin: float, vout: float, current: float = 1.0
) -> CalculationResult:
    """
    计算分压电阻

    Args:
        vin: 输入电压 (V)
        vout: 目标输出电压 (V)
        current: 分压电路电流 (mA)

    Returns:
        计算结果
    """
    if current < 0.1:
        current = 0.1  # 最小电流100μA

    current = current / 1000  # 转换为A

    # 总电阻
    r_total = vin / current

    # R2 = R1 × Vout / (Vin - Vout)
    # 假设R2 = 10kΩ
    r2 = 10000
    r1 = r2 * (vin - vout) / vout

    # 标准值
    std_r1, alt_r1 = find_nearest_standard(E24_SERIES, E24_MULTIPLIERS, r1)
    std_r2, alt_r2 = find_nearest_standard(E24_SERIES, E24_MULTIPLIERS, r2)

    # 实际输出电压
    vout_actual = vin * std_r2 / (std_r1 + std_r2)
    error_percent = abs(vout_actual - vout) / vout * 100

    warnings = []
    if error_percent > 5:
        warnings.append(f"警告: 输出电压误差 {error_percent:.1f}% 超过5%")

    formula = f"R1 = R2 × (Vin - Vout) / Vout = {r2}Ω × ({vin}V - {vout}V) / {vout}V = {r1:.0f}Ω"

    return CalculationResult(
        calculated_value=r1,
        standard_value=std_r1,
        unit="Ω",
        formula=formula,
        warnings=warnings,
        alternatives=[f"R1={a:.0f}Ω, R2={std_r2}Ω" for a in alt_r1],
    )


def calculate_power_input_capacitor(
    vin: float, iout: float, ripple: float = 100.0
) -> Dict[str, Any]:
    """
    计算电源输入滤波电容

    Args:
        vin: 输入电压 (V)
        iout: 输出电流 (mA)
        ripple: 允许纹波 (mVpp)

    Returns:
        推荐的电容
    """
    # 简化计算: C = I × dt / dV
    # 假设开关频率100kHz, dt = 10μs
    dt = 0.00001  # 10μs
    dv = ripple / 1000  # 转换为V
    i = iout / 1000  # 转换为A

    c_calc = i * dt / dv  # 法拉

    # 转换为μF
    c_calc = c_calc * 1000000

    # 标准值
    std_value, alternatives = find_nearest_standard(E12_SERIES, E12_MULTIPLIERS, c_calc)

    # 耐压选择
    voltage_rating = vin * 1.5
    if voltage_rating < 16:
        voltage_rating = 16
    elif voltage_rating < 25:
        voltage_rating = 25
    else:
        voltage_rating = 50

    return {
        "calculated": c_calc,
        "recommended": std_value,
        "unit": "μF",
        "voltage_rating": voltage_rating,
        "package": "0805" if std_value <= 47 else "1206",
        "alternatives": [f"{a:.1f}μF" for a in alternatives],
        "formula": f"C = I × dt / dV = {iout}mA × 10μs / {ripple}mV = {c_calc:.1f}μF",
    }


# ========== 便捷函数 ==========


def calculate_component_value(component_type: str, **params) -> Dict[str, Any]:
    """
    通用参数计算入口

    Args:
        component_type: 元件类型
            - "led_resistor": LED限流电阻
            - "crystal_cap": 晶振负载电容
            - "decoupling": 去耦电容
            - "voltage_divider": 分压电阻
            - "power_cap": 电源滤波电容
        **params: 相应参数

    Returns:
        计算结果字典
    """
    if component_type == "led_resistor":
        result = calculate_led_resistor(
            params.get("vcc", 3.3),
            params.get("vf", 2.0),
            params.get("if_current", 10.0),
        )
        return result.to_dict()

    elif component_type == "crystal_cap":
        result = calculate_crystal_load_capacitor(
            params.get("cl", 20.0),
            params.get("c_internal", 5.0),
            params.get("c_stray", 3.0),
        )
        return result.to_dict()

    elif component_type == "decoupling":
        return calculate_decoupling_capacitor(
            params.get("vcc", 3.3), params.get("current", 100.0)
        )

    elif component_type == "voltage_divider":
        result = calculate_voltage_divider(
            params.get("vin", 5.0), params.get("vout", 3.3), params.get("current", 1.0)
        )
        return result.to_dict()

    elif component_type == "power_cap":
        return calculate_power_input_capacitor(
            params.get("vin", 5.0),
            params.get("iout", 100.0),
            params.get("ripple", 100.0),
        )

    else:
        return {"error": f"Unknown component type: {component_type}"}


# ========== 测试 ==========
if __name__ == "__main__":
    # 测试LED电阻计算
    print("=== LED限流电阻计算 ===")
    result = calculate_led_resistor(5.0, 2.0, 10.0)
    print(f"计算值: {result.calculated_value:.0f}Ω")
    print(f"标准值: {result.standard_value:.0f}Ω")
    print(f"公式: {result.formula}")
    print()

    # 测试晶振电容计算
    print("=== 晶振负载电容计算 ===")
    result = calculate_crystal_load_capacitor(20.0)
    print(f"计算值: {result.calculated_value:.1f}pF")
    print(f"标准值: {result.standard_value:.0f}pF")
    print()

    # 测试去耦电容
    print("=== 去耦电容推荐 ===")
    result = calculate_decoupling_capacitor(3.3, 100)
    print(result)

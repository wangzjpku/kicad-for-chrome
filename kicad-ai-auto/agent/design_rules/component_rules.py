"""
元器件选型优化规则
Component Selection Optimization Rules

确保元器件选型合理：
- 电压/电流降额
- 封装选型
- 可靠性考虑
- 成本优化
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import re

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class DeratingSpec:
    """降额规格"""

    component_type: str
    parameter: str
    max_stress_pct: float  # 最大应力百分比
    recommended_stress_pct: float  # 推荐应力百分比
    reason: str


# ========== 降额标准 ==========

DERATING_RULES = [
    DeratingSpec("capacitor_ceramic", "voltage", 80, 50, "电解液干涸风险"),
    DeratingSpec("capacitor_electrolytic", "voltage", 80, 60, "电解液寿命"),
    DeratingSpec("capacitor_tantalum", "voltage", 50, 30, " tantalum易击穿"),
    DeratingSpec("resistor", "power", 70, 50, "温升影响寿命"),
    DeratingSpec("diode", "current", 70, 50, "热应力"),
    DeratingSpec("diode", "voltage_reverse", 70, 50, "瞬态过压"),
    DeratingSpec("mosfet", "voltage_ds", 80, 60, "开关尖峰"),
    DeratingSpec("mosfet", "current_d", 70, 50, "热应力"),
    DeratingSpec("bjt", "current_c", 70, 50, "热应力"),
    DeratingSpec("ic_digital", "voltage", 100, 90, "超出规格会损坏"),
    DeratingSpec("ic_analog", "voltage", 90, 80, "精度受影响"),
    DeratingSpec("inductor", "current", 80, 60, "磁饱和"),
    DeratingSpec("led", "current", 70, 50, "光衰和寿命"),
    DeratingSpec("fuse", "current", 100, 75, "避免误熔断"),
]

# ========== 封装选型建议 ==========

PACKAGE_RECOMMENDATIONS = {
    "resistor": {
        "0201": {"power_w": 0.05, "voltage_v": 25, "note": "超小型，手工焊接困难"},
        "0402": {"power_w": 0.063, "voltage_v": 50, "note": "常用小型"},
        "0603": {"power_w": 0.1, "voltage_v": 75, "note": "常用标准"},
        "0805": {"power_w": 0.125, "voltage_v": 150, "note": "常用大型"},
        "1206": {"power_w": 0.25, "voltage_v": 200, "note": "大功率"},
        "1210": {"power_w": 0.5, "voltage_v": 200, "note": "大功率"},
    },
    "capacitor_ceramic": {
        "0201": {"capacitance_max": "10nF", "voltage_max": 25, "note": "超小型"},
        "0402": {"capacitance_max": "100nF", "voltage_max": 50, "note": "常用小型"},
        "0603": {"capacitance_max": "1uF", "voltage_max": 50, "note": "常用标准"},
        "0805": {"capacitance_max": "10uF", "voltage_max": 50, "note": "常用大型"},
        "1206": {"capacitance_max": "22uF", "voltage_max": 25, "note": "大容量"},
        "1210": {"capacitance_max": "47uF", "voltage_max": 16, "note": "大容量"},
    },
    "mosfet_smd": {
        "SOT-23": {"power_w": 0.5, "current_a": 1, "note": "小信号"},
        "SOT-89": {"power_w": 1, "current_a": 3, "note": "中等功率"},
        "SOT-223": {"power_w": 2, "current_a": 5, "note": "大功率"},
        "DPAK": {"power_w": 5, "current_a": 10, "note": "功率MOS"},
        "D2PAK": {"power_w": 10, "current_a": 30, "note": "大功率MOS"},
        "TO-252": {"power_w": 5, "current_a": 15, "note": "常用功率"},
    },
}

# ========== 稳压器选型 ==========

REGULATOR_RECOMMENDATIONS = [
    {
        "model": "AMS1117-3.3",
        "type": "LDO",
        "voltage_in": "4.5-15V",
        "voltage_out": "3.3V",
        "current_max": "1A",
        "dropout": "1.3V",
        "note": "低成本常用",
    },
    {
        "model": "AMS1117-5.0",
        "type": "LDO",
        "voltage_in": "6.5-15V",
        "voltage_out": "5V",
        "current_max": "1A",
        "dropout": "1.3V",
        "note": "低成本常用",
    },
    {
        "model": "LM7805",
        "type": "LDO",
        "voltage_in": "7-35V",
        "voltage_out": "5V",
        "current_max": "1.5A",
        "dropout": "2V",
        "note": "经典线性稳压",
    },
    {
        "model": "LM317",
        "type": "LDO_ADJ",
        "voltage_in": "3-40V",
        "voltage_out": "1.2-37V",
        "current_max": "1.5A",
        "dropout": "2V",
        "note": "可调稳压",
    },
    {
        "model": "LM2596",
        "type": "BUCK",
        "voltage_in": "4.5-40V",
        "voltage_out": "3.3-35V",
        "current_max": "3A",
        "efficiency": "90%",
        "note": "常用DC-DC",
    },
    {
        "model": "MP1584",
        "type": "BUCK",
        "voltage_in": "4.5-28V",
        "voltage_out": "0.8-20V",
        "current_max": "3A",
        "efficiency": "95%",
        "note": "高效小型",
    },
    {
        "model": "MT3608",
        "type": "BOOST",
        "voltage_in": "2-24V",
        "voltage_out": "5-28V",
        "current_max": "2A",
        "efficiency": "93%",
        "note": "常用升压",
    },
]

# ========== MCU选型建议 ==========

MCU_RECOMMENDATIONS = {
    "simple_io": {"model": "ATtiny85", "note": "简单I/O控制，低成本"},
    "arduino_compat": {"model": "ATmega328P", "note": "Arduino兼容，生态丰富"},
    "wifi_iot": {"model": "ESP32-WROOM", "note": "WiFi+蓝牙，IoT首选"},
    "bluetooth": {"model": "ESP32-C3", "note": "蓝牙5.0，低成本"},
    "motor_control": {"model": "STM32F103", "note": "PWM丰富，电机控制"},
    "high_performance": {"model": "STM32F407", "note": "高性能，DSP功能"},
    "low_power": {"model": "STM32L0", "note": "超低功耗，电池供电"},
}


def get_component_rules() -> List[DesignRule]:
    """获取元器件选型规则"""
    return [
        DesignRule(
            id="COMPONENT_001",
            category=DesignCategory.COMPONENT,
            name="电容电压降额",
            description="电容工作电压必须有足够降额",
            check_function="check_capacitor_derating",
            fix_function="upgrade_capacitor",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="COMPONENT_002",
            category=DesignCategory.COMPONENT,
            name="电阻功率降额",
            description="电阻功耗必须有足够裕量",
            check_function="check_resistor_power",
            fix_function="upgrade_resistor",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="COMPONENT_003",
            category=DesignCategory.COMPONENT,
            name="封装选型",
            description="封装必须满足功率和电压要求",
            check_function="check_package_selection",
            fix_function="suggest_package",
            priority=2,
            auto_fix=False,
        ),
        DesignRule(
            id="COMPONENT_004",
            category=DesignCategory.COMPONENT,
            name="稳压器选型",
            description="稳压器必须满足电流和效率要求",
            check_function="check_regulator_selection",
            fix_function="suggest_regulator",
            priority=1,
            auto_fix=False,
        ),
        DesignRule(
            id="COMPONENT_005",
            category=DesignCategory.COMPONENT,
            name="MCU选型",
            description="MCU应匹配应用需求",
            check_function="check_mcu_selection",
            fix_function="suggest_mcu",
            priority=2,
            auto_fix=False,
        ),
    ]


def check_component(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查元器件选型"""
    issues = []
    components = circuit_data.get("components", [])
    parameters = circuit_data.get("parameters", [])

    if rule.id == "COMPONENT_001":
        issues.extend(_check_capacitor_derating(components, parameters))
    elif rule.id == "COMPONENT_002":
        issues.extend(_check_resistor_power(components))
    elif rule.id == "COMPONENT_003":
        issues.extend(_check_package_selection(components))
    elif rule.id == "COMPONENT_004":
        issues.extend(_check_regulator_selection(components, parameters))
    elif rule.id == "COMPONENT_005":
        issues.extend(_check_mcu_selection(components))

    return issues


def _parse_capacitor_value(model: str) -> Tuple[Optional[float], Optional[float]]:
    """解析电容值和电压值"""
    # 匹配如 "10uF 25V", "100nF", "4.7uF 16V" 等
    capacitance = None
    voltage = None

    # 提取电容值
    cap_match = re.search(r"(\d+\.?\d*)\s*(uF|nF|pF|uf|nf|pf)", model, re.I)
    if cap_match:
        value = float(cap_match.group(1))
        unit = cap_match.group(2).lower()
        if unit in ["uf", "uf"]:
            capacitance = value * 1e-6
        elif unit in ["nf", "nf"]:
            capacitance = value * 1e-9
        elif unit in ["pf", "pf"]:
            capacitance = value * 1e-12

    # 提取电压值
    volt_match = re.search(r"(\d+\.?\d*)\s*V", model, re.I)
    if volt_match:
        voltage = float(volt_match.group(1))

    return capacitance, voltage


def _parse_resistor_value(model: str) -> Tuple[Optional[float], Optional[float]]:
    """解析电阻值和功率值"""
    resistance = None
    power = None

    # 提取电阻值
    res_match = re.search(r"(\d+\.?\d*)\s*(kΩ|Ω|MΩ|k|ohm)", model, re.I)
    if res_match:
        value = float(res_match.group(1))
        unit = res_match.group(2).lower()
        if "k" in unit:
            resistance = value * 1000
        elif "m" in unit:
            resistance = value * 1000000
        else:
            resistance = value

    # 提取功率值
    pow_match = re.search(r"(\d+\.?\d*)\s*(W|w)", model)
    if pow_match:
        power = float(pow_match.group(1))

    return resistance, power


def _get_circuit_voltage(parameters: List[Dict]) -> float:
    """获取电路工作电压"""
    for param in parameters:
        key = param.get("key", "").lower()
        if "电压" in key or "voltage" in key:
            try:
                return float(param.get("value", 5))
            except:
                pass
    return 5.0  # 默认5V


def _check_capacitor_derating(
    components: List[Dict], parameters: List[Dict]
) -> List[DesignIssue]:
    """检查电容电压降额"""
    issues = []
    circuit_voltage = _get_circuit_voltage(parameters)

    for comp in components:
        name = comp.get("name", "").lower()
        model = comp.get("model", "")

        if "电容" in name or "capacitor" in name:
            _, cap_voltage = _parse_capacitor_value(model)

            if cap_voltage:
                # 计算应力比
                stress_ratio = (circuit_voltage / cap_voltage) * 100

                # 钽电容需要更严格降额
                if "tantalum" in model.lower() or "钽" in model.lower():
                    max_stress = 50
                elif (
                    "electrolytic" in comp.get("package", "").lower() or "电解" in name
                ):
                    max_stress = 80
                else:
                    max_stress = 80

                if stress_ratio > max_stress:
                    recommended_voltage = (
                        circuit_voltage / (max_stress / 100) * 1.2
                    )  # 留20%裕量
                    issues.append(
                        DesignIssue(
                            rule_id="COMPONENT_001",
                            category=DesignCategory.COMPONENT,
                            severity="warning",
                            message=f"电容 {model} 电压降额不足: {stress_ratio:.0f}% > {max_stress}%",
                            suggestion=f"建议使用 {recommended_voltage:.0f}V 以上耐压的电容",
                            auto_fixable=True,
                        )
                    )

    return issues


def _check_resistor_power(components: List[Dict]) -> List[DesignIssue]:
    """检查电阻功率"""
    issues = []

    # 常见封装功率限制
    package_power = {
        "0402": 0.063,
        "0603": 0.1,
        "0805": 0.125,
        "1206": 0.25,
        "1210": 0.5,
        "2010": 0.75,
        "2512": 1.0,
    }

    for comp in components:
        name = comp.get("name", "").lower()
        model = comp.get("model", "")
        package = comp.get("package", "").lower()

        if "电阻" in name or "resistor" in name:
            # 获取封装功率限制
            max_power = package_power.get(package, 0.125)

            # 简化检查：如果电阻值很小，可能是大电流应用
            resistance, rated_power = _parse_resistor_value(model)

            if rated_power and rated_power > max_power:
                issues.append(
                    DesignIssue(
                        rule_id="COMPONENT_002",
                        category=DesignCategory.COMPONENT,
                        severity="info",
                        message=f"电阻 {model} 功率规格与封装不匹配",
                        suggestion=f"建议使用更大封装如1206或1210",
                        auto_fixable=True,
                    )
                )

    return issues


def _check_package_selection(components: List[Dict]) -> List[DesignIssue]:
    """检查封装选型"""
    issues = []

    for comp in components:
        package = comp.get("package", "").lower()
        model = comp.get("model", "").lower()

        # 检查功率器件封装
        if any(x in model for x in ["7805", "7809", "7812", "lm317"]):
            if package != "to-220" and package != "dpak" and package != "d2pak":
                issues.append(
                    DesignIssue(
                        rule_id="COMPONENT_003",
                        category=DesignCategory.COMPONENT,
                        severity="warning",
                        message=f"功率器件 {comp.get('model', '')} 封装选型可能不当",
                        suggestion="功率器件建议使用TO-220、DPAK或D2PAK封装以利于散热",
                        auto_fixable=False,
                    )
                )

    return issues


def _check_regulator_selection(
    components: List[Dict], parameters: List[Dict]
) -> List[DesignIssue]:
    """检查稳压器选型"""
    issues = []

    # 获取电路参数
    input_voltage = 12.0
    output_voltage = 5.0
    output_current = 1.0

    for param in parameters:
        key = param.get("key", "").lower()
        value = param.get("value", "")
        try:
            if "输入" in key and "电压" in key:
                input_voltage = float(value)
            elif "输出" in key and "电压" in key:
                output_voltage = float(value)
            elif "输出" in key and "电流" in key:
                output_current = float(value)
        except:
            pass

    for comp in components:
        model = comp.get("model", "").lower()

        # 检查线性稳压器效率
        if any(x in model for x in ["7805", "7809", "7812", "1117"]):
            # 计算功耗
            dropout = 2.0 if "78" in model else 1.3
            if input_voltage - output_voltage > 3:
                power_loss = (input_voltage - output_voltage) * output_current
                efficiency = output_voltage / input_voltage * 100

                if power_loss > 2:
                    issues.append(
                        DesignIssue(
                            rule_id="COMPONENT_004",
                            category=DesignCategory.COMPONENT,
                            severity="warning",
                            message=f"线性稳压器 {comp.get('model', '')} 功耗过高: {power_loss:.1f}W",
                            suggestion=f"输入输出压差大({input_voltage - output_voltage:.0f}V)，建议改用DC-DC如LM2596/MP1584，效率可达90%+",
                            auto_fixable=False,
                        )
                    )

    return issues


def _check_mcu_selection(components: List[Dict]) -> List[DesignIssue]:
    """检查MCU选型"""
    issues = []

    # 检查是否有WiFi需求但用了非WiFi MCU
    has_wifi_requirement = False  # 需要从需求中获取

    for comp in components:
        model = comp.get("model", "").lower()

        # 检查是否使用了过时的MCU
        if "atmega328p" in model:
            # ATmega328P是经典选择，但如果需要WiFi就不合适
            pass

    return issues


def fix_component(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复元器件选型问题"""
    components = circuit_data.get("components", [])

    if rule.id == "COMPONENT_001":
        # 升级电容电压等级
        if "component_upgrades" not in circuit_data:
            circuit_data["component_upgrades"] = []
        circuit_data["component_upgrades"].append(
            {
                "original": issue.message,
                "suggestion": issue.suggestion,
            }
        )

    elif rule.id == "COMPONENT_004":
        # 稳压器优化建议
        if "design_recommendations" not in circuit_data:
            circuit_data["design_recommendations"] = []
        circuit_data["design_recommendations"].append(
            {
                "category": "power",
                "issue": issue.message,
                "suggestion": issue.suggestion,
            }
        )

    return circuit_data


def get_component_recommendations(requirements: Dict) -> Dict:
    """根据需求获取元器件推荐"""
    recommendations = {
        "mcu": None,
        "regulator": None,
        "notes": [],
    }

    # 检测功能需求
    has_wifi = requirements.get("wifi", False)
    has_bluetooth = requirements.get("bluetooth", False)
    has_motor = requirements.get("motor", False)
    low_power = requirements.get("low_power", False)

    # MCU推荐
    if has_wifi or has_bluetooth:
        recommendations["mcu"] = MCU_RECOMMENDATIONS["wifi_iot"]
        recommendations["notes"].append("ESP32支持WiFi和蓝牙，IoT首选")
    elif has_motor:
        recommendations["mcu"] = MCU_RECOMMENDATIONS["motor_control"]
        recommendations["notes"].append("STM32F103 PWM丰富，适合电机控制")
    elif low_power:
        recommendations["mcu"] = MCU_RECOMMENDATIONS["low_power"]
        recommendations["notes"].append("STM32L0超低功耗，适合电池供电")

    # 稳压器推荐
    input_v = requirements.get("input_voltage", 12)
    output_v = requirements.get("output_voltage", 5)
    current = requirements.get("current", 1)

    if input_v - output_v > 5 and current > 0.5:
        recommendations["regulator"] = {"model": "MP1584", "note": "高效DC-DC"}
        recommendations["notes"].append("压差大、电流大，建议用DC-DC")

    return recommendations

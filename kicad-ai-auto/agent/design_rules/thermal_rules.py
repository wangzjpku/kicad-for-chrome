"""
热设计分析规则
Thermal Design Analysis Rules

确保电路热设计合理：
- 热阻计算
- 散热片选型
- 热过孔设计
- 温度监测
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import math

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class ThermalSpec:
    """热设计规格"""

    component: str
    power_w: float  # 功耗 W
    tj_max_c: float  # 最大结温 °C
    theta_jc_c_w: float  # 结壳热阻 °C/W
    theta_cs_c_w: float  # 壳散热器热阻 °C/W (需要导热硅脂)
    theta_sa_c_w: float  # 散热器环境热阻 °C/W
    ambient_temp_c: float  # 环境温度 °C
    package: str  # 封装


@dataclass
class HeatSinkSpec:
    """散热片规格"""

    name: str
    thermal_resistance_c_w: float  # 热阻 °C/W
    volume_mm3: float  # 体积 mm³
    height_mm: float  # 高度 mm
    attachment: str  # 安装方式
    typical_use: str  # 典型应用


# ========== 常用封装热阻数据 ==========

PACKAGE_THERMAL_DATA = {
    # TO-220 (直插)
    "TO-220": {
        "theta_jc": 3.0,  # °C/W
        "theta_ja_no_heatsink": 65.0,  # 无散热器
        "max_power_no_heatsink": 2.0,  # W @ 25°C ambient
    },
    # TO-263 (D2PAK)
    "D2PAK": {
        "theta_jc": 2.0,
        "theta_ja_no_heatsink": 40.0,  # PCB散热
        "max_power_no_heatsink": 2.5,
    },
    # SOT-223
    "SOT-223": {
        "theta_jc": 15.0,
        "theta_ja_no_heatsink": 80.0,
        "max_power_no_heatsink": 0.8,
    },
    # SOT-89
    "SOT-89": {
        "theta_jc": 20.0,
        "theta_ja_no_heatsink": 100.0,
        "max_power_no_heatsink": 0.5,
    },
    # SOT-23
    "SOT-23": {
        "theta_jc": 80.0,
        "theta_ja_no_heatsink": 200.0,
        "max_power_no_heatsink": 0.25,
    },
    # QFN-48 (如ESP32)
    "QFN-48": {
        "theta_jc": 15.0,
        "theta_ja_no_heatsink": 45.0,  # 4层板
        "max_power_no_heatsink": 1.0,
    },
    # LQFP-64 (如STM32)
    "LQFP-64": {
        "theta_jc": 20.0,
        "theta_ja_no_heatsink": 55.0,
        "max_power_no_heatsink": 0.8,
    },
    # DIP-8
    "DIP-8": {
        "theta_jc": 40.0,
        "theta_ja_no_heatsink": 100.0,
        "max_power_no_heatsink": 0.5,
    },
}

# ========== 常用散热片数据 ==========

HEATSINK_CATALOG = [
    HeatSinkSpec(
        name="TO-220小型散热片",
        thermal_resistance_c_w=25.0,
        volume_mm3=5000,
        height_mm=20,
        attachment="夹片",
        typical_use="7805小电流 (<500mA)",
    ),
    HeatSinkSpec(
        name="TO-220中型散热片",
        thermal_resistance_c_w=15.0,
        volume_mm3=15000,
        height_mm=35,
        attachment="夹片/螺丝",
        typical_use="7805/L298 1-2A",
    ),
    HeatSinkSpec(
        name="TO-220大型散热片",
        thermal_resistance_c_w=8.0,
        volume_mm3=50000,
        height_mm=50,
        attachment="螺丝",
        typical_use="大功率 2-5A",
    ),
    HeatSinkSpec(
        name="DPAK散热片",
        thermal_resistance_c_w=20.0,
        volume_mm3=3000,
        height_mm=15,
        attachment="粘贴",
        typical_use="SMD功率器件",
    ),
]

# ========== 功率器件功耗估算 ==========

POWER_DEVICE_ESTIMATES = {
    # 线性稳压器
    "LM7805": {"power_w": 2.0, "note": "Vin=12V, I=0.5A"},
    "LM7809": {"power_w": 1.5, "note": "Vin=12V, I=0.3A"},
    "LM7812": {"power_w": 1.0, "note": "Vin=15V, I=0.2A"},
    "LM317": {"power_w": 2.0, "note": "可调，典型值"},
    "AMS1117-3.3": {"power_w": 1.0, "note": "Vin=5V, I=0.5A"},
    "AMS1117-5.0": {"power_w": 1.0, "note": "Vin=9V, I=0.3A"},
    # DC-DC (效率较高，功耗较低)
    "LM2596": {"power_w": 0.5, "note": "效率90%"},
    "MP1584": {"power_w": 0.3, "note": "效率95%"},
    "MT3608": {"power_w": 0.3, "note": "效率93%"},
    # 电机驱动
    "L298N": {"power_w": 5.0, "note": "2A双路，效率低"},
    "TB6612": {"power_w": 1.0, "note": "效率较高"},
    "DRV8833": {"power_w": 0.8, "note": "低电压应用"},
    # MOS驱动
    "IR2110": {"power_w": 0.5, "note": "驱动功耗"},
    "IR2104": {"power_w": 0.3, "note": "半桥驱动"},
}


def get_thermal_rules() -> List[DesignRule]:
    """获取热设计规则"""
    return [
        DesignRule(
            id="THERMAL_001",
            category=DesignCategory.THERMAL,
            name="功率器件热设计",
            description="功率器件必须有足够的热设计",
            check_function="check_power_device_thermal",
            fix_function="add_heatsink",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="THERMAL_002",
            category=DesignCategory.THERMAL,
            name="散热片选型",
            description="散热片热阻必须满足要求",
            check_function="check_heatsink_selection",
            fix_function="recommend_heatsink",
            priority=2,
            auto_fix=False,
        ),
        DesignRule(
            id="THERMAL_003",
            category=DesignCategory.THERMAL,
            name="热过孔设计",
            description="SMD功率器件需要热过孔",
            check_function="check_thermal_vias",
            fix_function="add_thermal_vias",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="THERMAL_004",
            category=DesignCategory.THERMAL,
            name="PCB散热面积",
            description="PCB必须有足够的散热面积",
            check_function="check_pcb_thermal",
            fix_function="increase_thermal_area",
            priority=3,
            auto_fix=True,
        ),
    ]


def check_thermal(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查热设计"""
    issues = []
    components = circuit_data.get("components", [])
    pcb_info = circuit_data.get("pcb_info", {})

    if rule.id == "THERMAL_001":
        issues.extend(_check_power_device_thermal(components, pcb_info))
    elif rule.id == "THERMAL_002":
        issues.extend(_check_heatsink_selection(components, pcb_info))
    elif rule.id == "THERMAL_003":
        issues.extend(_check_thermal_vias(components, pcb_info))
    elif rule.id == "THERMAL_004":
        issues.extend(_check_pcb_thermal(components, pcb_info))

    return issues


def calculate_junction_temperature(
    power_w: float,
    theta_jc: float,
    theta_cs: float,
    theta_sa: float,
    ambient_temp_c: float = 25.0,
) -> float:
    """
    计算结温

    Tj = Ta + P * (θjc + θcs + θsa)

    Args:
        power_w: 功耗 W
        theta_jc: 结壳热阻 °C/W
        theta_cs: 壳散热器热阻 °C/W
        theta_sa: 散热器环境热阻 °C/W
        ambient_temp_c: 环境温度 °C

    Returns:
        结温 °C
    """
    total_thermal_resistance = theta_jc + theta_cs + theta_sa
    temperature_rise = power_w * total_thermal_resistance
    return ambient_temp_c + temperature_rise


def calculate_required_heatsink(
    power_w: float,
    tj_max_c: float,
    theta_jc: float,
    theta_cs: float = 0.5,  # 导热硅脂
    ambient_temp_c: float = 40.0,  # 考虑温升
    safety_margin_c: float = 10.0,
) -> float:
    """
    计算所需散热片热阻

    Args:
        power_w: 功耗 W
        tj_max_c: 最大结温 °C
        theta_jc: 结壳热阻 °C/W
        theta_cs: 壳散热器热阻 °C/W
        ambient_temp_c: 环境温度 °C
        safety_margin_c: 安全裕量 °C

    Returns:
        所需散热片最大热阻 °C/W
    """
    # 目标结温 = 最大结温 - 安全裕量
    target_tj = tj_max_c - safety_margin_c

    # 允许的总热阻
    max_total_theta = (target_tj - ambient_temp_c) / power_w

    # 散热片热阻 = 总热阻 - 结壳热阻 - 壳散热器热阻
    required_theta_sa = max_total_theta - theta_jc - theta_cs

    return max(1.0, required_theta_sa)  # 最小1°C/W


def _check_power_device_thermal(
    components: List[Dict], pcb_info: Dict
) -> List[DesignIssue]:
    """检查功率器件热设计"""
    issues = []

    for comp in components:
        model = comp.get("model", "").upper()
        name = comp.get("name", "")

        # 检查是否是功率器件
        power_estimate = None
        for device_name, data in POWER_DEVICE_ESTIMATES.items():
            if device_name.upper() in model:
                power_estimate = data["power_w"]
                break

        if power_estimate and power_estimate > 0.5:
            # 获取封装热阻
            package = comp.get("package", "").upper()
            thermal_data = PACKAGE_THERMAL_DATA.get(
                package, PACKAGE_THERMAL_DATA.get("SOT-223", {})
            )

            # 计算无散热器时的结温
            theta_ja = thermal_data.get("theta_ja_no_heatsink", 80)
            max_power = thermal_data.get("max_power_no_heatsink", 1.0)

            if power_estimate > max_power:
                # 计算所需散热片热阻
                required_heatsink = calculate_required_heatsink(
                    power_w=power_estimate,
                    tj_max_c=125.0,
                    theta_jc=thermal_data.get("theta_jc", 15.0),
                )

                issues.append(
                    DesignIssue(
                        rule_id="THERMAL_001",
                        category=DesignCategory.THERMAL,
                        severity="warning",
                        message=f"功率器件 {model} 功耗{power_estimate}W超过封装限制{max_power}W",
                        suggestion=f"需要添加散热片(热阻≤{required_heatsink:.1f}°C/W)，或改用更大封装",
                        auto_fixable=True,
                    )
                )

            elif power_estimate > max_power * 0.7:
                issues.append(
                    DesignIssue(
                        rule_id="THERMAL_001",
                        category=DesignCategory.THERMAL,
                        severity="info",
                        message=f"功率器件 {model} 功耗接近封装极限",
                        suggestion="建议添加小型散热片或改善PCB散热",
                        auto_fixable=True,
                    )
                )

    return issues


def _check_heatsink_selection(
    components: List[Dict], pcb_info: Dict
) -> List[DesignIssue]:
    """检查散热片选型"""
    issues = []

    # 检查是否有散热片
    has_heatsink = any(
        "散热" in c.get("name", "") or "heatsink" in c.get("name", "").lower()
        for c in components
    )

    # 检查是否有需要散热片的器件
    has_power_device = any(
        any(
            x in c.get("model", "").upper()
            for x in ["7805", "7812", "7809", "L298", "2596"]
        )
        for c in components
    )

    if has_power_device and not has_heatsink:
        issues.append(
            DesignIssue(
                rule_id="THERMAL_002",
                category=DesignCategory.THERMAL,
                severity="info",
                message="检测到功率器件但未添加散热片",
                suggestion="根据功耗选择合适热阻的散热片",
                auto_fixable=False,
            )
        )

    return issues


def _check_thermal_vias(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查热过孔设计"""
    issues = []

    # 检查SMD功率器件
    smd_power_packages = ["D2PAK", "DPAK", "SOT-223", "QFN-48", "QFN-32"]

    for comp in components:
        package = comp.get("package", "").upper()

        if package in smd_power_packages or any(
            x in package for x in ["D2PAK", "DPAK", "SOT-223", "QFN"]
        ):
            # 检查是否有热过孔
            thermal_vias = pcb_info.get(f"thermal_vias_{comp.get('id', '')}", 0)

            if thermal_vias == 0:
                # 根据封装推荐热过孔数量
                via_recommendations = {
                    "D2PAK": 6,
                    "DPAK": 4,
                    "SOT-223": 2,
                    "QFN-48": 9,
                    "QFN-32": 4,
                }
                recommended_vias = via_recommendations.get(package, 4)

                issues.append(
                    DesignIssue(
                        rule_id="THERMAL_003",
                        category=DesignCategory.THERMAL,
                        severity="info",
                        message=f"SMD功率器件 {comp.get('model', '')} 缺少热过孔",
                        suggestion=f"在散热焊盘下添加{recommended_vias}个0.3mm热过孔连接到底层地平面",
                        auto_fixable=True,
                    )
                )

    return issues


def _check_pcb_thermal(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查PCB散热"""
    issues = []

    # 计算总功耗
    total_power = 0
    for comp in components:
        model = comp.get("model", "").upper()
        for device_name, data in POWER_DEVICE_ESTIMATES.items():
            if device_name.upper() in model:
                total_power += data["power_w"]

    # 获取PCB面积
    board_area_mm2 = pcb_info.get("board_area_mm2", 1000)  # 默认1000mm²

    # 经验值：100mm²/W
    required_area = total_power * 100

    if board_area_mm2 < required_area:
        issues.append(
            DesignIssue(
                rule_id="THERMAL_004",
                category=DesignCategory.THERMAL,
                severity="info",
                message=f"PCB散热面积可能不足: {board_area_mm2}mm² < {required_area}mm² (功耗{total_power}W)",
                suggestion="增加PCB面积、添加铺铜或增加层数以改善散热",
                auto_fixable=True,
            )
        )

    return issues


def fix_thermal(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复热设计问题"""
    if "thermal_design_notes" not in circuit_data:
        circuit_data["thermal_design_notes"] = []

    if rule.id == "THERMAL_001":
        circuit_data["thermal_design_notes"].append(
            {
                "category": "heatsink",
                "note": issue.suggestion,
                "priority": "high",
            }
        )

    elif rule.id == "THERMAL_003":
        circuit_data["thermal_design_notes"].append(
            {
                "category": "thermal_vias",
                "note": issue.suggestion,
                "priority": "medium",
            }
        )

    elif rule.id == "THERMAL_004":
        circuit_data["thermal_design_notes"].append(
            {
                "category": "pcb_thermal",
                "note": issue.suggestion,
                "priority": "medium",
            }
        )

    return circuit_data


def get_thermal_report(components: List[Dict], pcb_info: Dict) -> Dict:
    """生成热设计报告"""
    report = {
        "power_devices": [],
        "thermal_analysis": [],
        "recommendations": [],
        "total_power_w": 0,
    }

    for comp in components:
        model = comp.get("model", "").upper()
        package = comp.get("package", "").upper()

        for device_name, data in POWER_DEVICE_ESTIMATES.items():
            if device_name.upper() in model:
                power_w = data["power_w"]
                thermal_data = PACKAGE_THERMAL_DATA.get(package, {})

                report["power_devices"].append(
                    {
                        "component": model,
                        "package": package,
                        "power_w": power_w,
                        "theta_ja": thermal_data.get("theta_ja_no_heatsink", "N/A"),
                    }
                )

                report["total_power_w"] += power_w

                # 计算所需散热片
                if power_w > thermal_data.get("max_power_no_heatsink", 1.0):
                    required_heatsink = calculate_required_heatsink(
                        power_w=power_w,
                        tj_max_c=125.0,
                        theta_jc=thermal_data.get("theta_jc", 15.0),
                    )

                    report["thermal_analysis"].append(
                        {
                            "component": model,
                            "power_w": power_w,
                            "status": "需要散热片",
                            "required_heatsink_theta": f"{required_heatsink:.1f}°C/W",
                        }
                    )

                break

    # 总体建议
    if report["total_power_w"] > 5:
        report["recommendations"].append("总功耗较高，建议使用4层板改善散热")

    if report["total_power_w"] > 10:
        report["recommendations"].append("高功耗设计，考虑强制风冷")

    return report

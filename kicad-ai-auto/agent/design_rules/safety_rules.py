"""
PCB安全间距设计规则
PCB Safety Clearance Design Rules

确保PCB设计符合安规要求：
- 电气间隙 (Clearance)
- 爬电距离 (Creepage)
- 电压等级要求
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class SafetyClearance:
    """安全间距规格"""

    voltage_range_v: tuple  # 电压范围 (min, max)
    basic_clearance_mm: float  # 基本间隙 mm
    creepage_mm: float  # 爬电距离 mm
    pollution_degree: int  # 污染等级 1-3
    material_group: str  # 材料组别 I/II/IIIa/IIIb
    insulation_type: str  # 绝缘类型 functional/basic/reinforced


# ========== 安全间距标准 (基于IEC 60950-1 / IEC 62368-1) ==========

# 电气间隙标准 - 基本绝缘 (污染等级2)
CLEARANCE_BASIC = [
    SafetyClearance((0, 50), 0.1, 0.2, 2, "IIIa", "basic"),
    SafetyClearance((50, 100), 0.1, 0.4, 2, "IIIa", "basic"),
    SafetyClearance((100, 150), 0.5, 0.8, 2, "IIIa", "basic"),
    SafetyClearance((150, 300), 1.5, 1.5, 2, "IIIa", "basic"),
    SafetyClearance((300, 600), 3.0, 3.0, 2, "IIIa", "basic"),
    SafetyClearance((600, 1000), 5.5, 5.5, 2, "IIIa", "basic"),
]

# 电气间隙标准 - 加强绝缘 (双倍)
CLEARANCE_REINFORCED = [
    SafetyClearance((0, 50), 0.2, 0.4, 2, "IIIa", "reinforced"),
    SafetyClearance((50, 100), 0.2, 0.8, 2, "IIIa", "reinforced"),
    SafetyClearance((100, 150), 1.0, 1.6, 2, "IIIa", "reinforced"),
    SafetyClearance((150, 300), 3.0, 3.0, 2, "IIIa", "reinforced"),
    SafetyClearance((300, 600), 6.0, 6.0, 2, "IIIa", "reinforced"),
    SafetyClearance((600, 1000), 11.0, 11.0, 2, "IIIa", "reinforced"),
]

# 一次侧-二次侧隔离要求 (AC-DC电源)
PRIMARY_SECONDARY_CLEARANCE = SafetyClearance(
    voltage_range_v=(0, 250),
    basic_clearance_mm=6.0,  # 220V AC需要6mm以上
    creepage_mm=6.0,
    pollution_degree=2,
    material_group="IIIa",
    insulation_type="reinforced",
)

# 常用电压等级的安全间距速查
QUICK_REFERENCE = {
    "3.3V": {"clearance": 0.1, "creepage": 0.1, "note": "信号线"},
    "5V": {"clearance": 0.1, "creepage": 0.1, "note": "TTL逻辑"},
    "12V": {"clearance": 0.2, "creepage": 0.2, "note": "常用电源"},
    "24V": {"clearance": 0.5, "creepage": 0.5, "note": "工业控制"},
    "48V": {"clearance": 1.0, "creepage": 1.0, "note": "PoE/通信"},
    "110V": {"clearance": 2.0, "creepage": 2.5, "note": "AC低压"},
    "220V": {"clearance": 3.0, "creepage": 4.0, "note": "AC市电-基本绝缘"},
    "220V_ACDC": {"clearance": 6.0, "creepage": 6.0, "note": "AC-DC隔离-加强绝缘"},
    "380V": {"clearance": 4.0, "creepage": 5.0, "note": "三相电"},
}

# PCB线宽与载流能力 (IPC-2221)
CURRENT_CAPACITY = {
    # (线宽mil, 铜厚oz): 最大电流A (10°C温升)
    (10, 1): 0.5,
    (20, 1): 0.8,
    (50, 1): 1.5,
    (100, 1): 2.5,
    (200, 1): 4.0,
    (10, 2): 0.7,
    (20, 2): 1.2,
    (50, 2): 2.2,
    (100, 2): 3.5,
    (200, 2): 5.5,
}


def get_safety_rules() -> List[DesignRule]:
    """获取安全间距设计规则"""
    return [
        DesignRule(
            id="SAFETY_001",
            category=DesignCategory.SAFETY,
            name="基本电气间隙",
            description="PCB导体间距必须满足电压等级要求",
            check_function="check_basic_clearance",
            fix_function="increase_clearance",
            priority=1,
            auto_fix=False,
        ),
        DesignRule(
            id="SAFETY_002",
            category=DesignCategory.SAFETY,
            name="一次侧二次侧隔离",
            description="AC-DC电源初/次级间距必须>=6mm",
            check_function="check_primary_secondary",
            fix_function="increase_isolation",
            priority=1,
            auto_fix=False,
        ),
        DesignRule(
            id="SAFETY_003",
            category=DesignCategory.SAFETY,
            name="爬电距离",
            description="高压电路爬电距离必须足够",
            check_function="check_creepage",
            fix_function="increase_creepage",
            priority=1,
            auto_fix=False,
        ),
        DesignRule(
            id="SAFETY_004",
            category=DesignCategory.SAFETY,
            name="线宽载流能力",
            description="导线宽度必须满足电流要求",
            check_function="check_trace_width",
            fix_function="increase_trace_width",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="SAFETY_005",
            category=DesignCategory.SAFETY,
            name="散热焊盘",
            description="功率器件需要足够的散热面积",
            check_function="check_thermal_pad",
            fix_function="increase_thermal_pad",
            priority=2,
            auto_fix=True,
        ),
    ]


def check_safety(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查安全间距"""
    issues = []
    components = circuit_data.get("components", [])
    pcb_info = circuit_data.get("pcb_info", {})

    if rule.id == "SAFETY_001":
        issues.extend(_check_basic_clearance(components, pcb_info))
    elif rule.id == "SAFETY_002":
        issues.extend(_check_primary_secondary(components, pcb_info))
    elif rule.id == "SAFETY_003":
        issues.extend(_check_creepage(components, pcb_info))
    elif rule.id == "SAFETY_004":
        issues.extend(_check_trace_width(components, pcb_info))
    elif rule.id == "SAFETY_005":
        issues.extend(_check_thermal_pad(components, pcb_info))

    return issues


def get_clearance_for_voltage(voltage: float, insulation_type: str = "basic") -> float:
    """
    根据电压获取所需间隙

    Args:
        voltage: 工作电压 V
        insulation_type: 绝缘类型 basic/reinforced

    Returns:
        所需最小间隙 mm
    """
    clearances = (
        CLEARANCE_REINFORCED if insulation_type == "reinforced" else CLEARANCE_BASIC
    )

    for spec in clearances:
        if spec.voltage_range_v[0] <= voltage <= spec.voltage_range_v[1]:
            return spec.basic_clearance_mm

    # 超出范围，线性外推
    max_spec = clearances[-1]
    if voltage > max_spec.voltage_range_v[1]:
        # 简化外推：每100V增加1mm
        extra_v = voltage - max_spec.voltage_range_v[1]
        return max_spec.basic_clearance_mm + (extra_v / 100) * 1.0

    return 0.1  # 默认最小值


def _check_basic_clearance(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查基本电气间隙"""
    issues = []

    # 检查电路中是否有高压
    max_voltage = _estimate_max_voltage(components)

    if max_voltage >= 100:  # 100V以上需要特别关注
        min_clearance = get_clearance_for_voltage(max_voltage)

        # 获取PCB实际间隙
        actual_clearance = pcb_info.get("min_clearance_mm", 0.3)  # 默认0.3mm

        if actual_clearance < min_clearance:
            issues.append(
                DesignIssue(
                    rule_id="SAFETY_001",
                    category=DesignCategory.SAFETY,
                    severity="critical",
                    message=f"电气间隙不足: {actual_clearance}mm < {min_clearance}mm (电压{max_voltage}V)",
                    suggestion=f"将导体间距增加到至少{min_clearance}mm，建议使用开槽增加爬电距离",
                    auto_fixable=False,
                )
            )

    return issues


def _estimate_max_voltage(components: List[Dict]) -> float:
    """估算电路中最高电压"""
    max_v = 5.0  # 默认5V

    for comp in components:
        model = comp.get("model", "").lower()

        # 根据元件型号推断电压
        if "220v" in model or "220" in model:
            max_v = max(max_v, 220)
        elif "110v" in model or "110" in model:
            max_v = max(max_v, 110)
        elif "380v" in model or "380" in model:
            max_v = max(max_v, 380)
        elif "24v" in model:
            max_v = max(max_v, 24)
        elif "48v" in model:
            max_v = max(max_v, 48)
        elif "12v" in model:
            max_v = max(max_v, 12)

        # 检查变压器
        if "变压器" in comp.get("name", "") or "transformer" in model:
            max_v = max(max_v, 220)

    return max_v


def _check_primary_secondary(
    components: List[Dict], pcb_info: Dict
) -> List[DesignIssue]:
    """检查一次侧二次侧隔离"""
    issues = []

    # 检测是否是AC-DC电源
    has_transformer = any(
        "变压器" in c.get("name", "") or "transformer" in c.get("model", "").lower()
        for c in components
    )

    has_ac_input = any(
        "220v" in c.get("model", "").lower() or "ac" in c.get("name", "").lower()
        for c in components
    )

    if has_transformer or has_ac_input:
        # 获取初/次级间距
        isolation = pcb_info.get("primary_secondary_clearance_mm", 0)

        if isolation < PRIMARY_SECONDARY_CLEARANCE.basic_clearance_mm:
            issues.append(
                DesignIssue(
                    rule_id="SAFETY_002",
                    category=DesignCategory.SAFETY,
                    severity="critical",
                    message=f"一次侧二次侧隔离不足: {isolation}mm < {PRIMARY_SECONDARY_CLEARANCE.basic_clearance_mm}mm",
                    suggestion="增加初级和次级电路之间的距离，使用开槽或Y电容作为隔离",
                    auto_fixable=False,
                )
            )

    return issues


def _check_creepage(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查爬电距离"""
    issues = []

    max_voltage = _estimate_max_voltage(components)

    if max_voltage >= 150:  # 150V以上需要特别关注爬电距离
        min_creepage = (
            get_clearance_for_voltage(max_voltage) * 1.2
        )  # 爬电距离通常比间隙大

        actual_creepage = pcb_info.get("min_creepage_mm", 0.3)

        if actual_creepage < min_creepage:
            issues.append(
                DesignIssue(
                    rule_id="SAFETY_003",
                    category=DesignCategory.SAFETY,
                    severity="warning",
                    message=f"爬电距离可能不足: {actual_creepage}mm < {min_creepage:.1f}mm",
                    suggestion="在高电压区域添加开槽以增加爬电距离，或使用更高CTI值的PCB材料",
                    auto_fixable=False,
                )
            )

    return issues


def _check_trace_width(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查线宽载流能力"""
    issues = []

    # 检查大电流路径
    high_current_paths = pcb_info.get("high_current_paths", [])

    for path in high_current_paths:
        current_a = path.get("current_a", 0)
        width_mil = path.get("width_mil", 10)
        copper_oz = path.get("copper_oz", 1)

        # 获取该线宽允许的最大电流
        max_current = CURRENT_CAPACITY.get((width_mil, copper_oz), 0)

        if current_a > max_current:
            required_width = _get_required_trace_width(current_a, copper_oz)
            issues.append(
                DesignIssue(
                    rule_id="SAFETY_004",
                    category=DesignCategory.SAFETY,
                    severity="warning",
                    message=f"导线宽度过窄: {width_mil}mil不能承载{current_a}A电流",
                    suggestion=f"增加线宽至{required_width}mil以上，或使用更厚的铜箔",
                    auto_fixable=True,
                )
            )

    return issues


def _get_required_trace_width(current_a: float, copper_oz: int = 1) -> int:
    """获取所需线宽"""
    for (width, oz), max_current in sorted(CURRENT_CAPACITY.items()):
        if oz == copper_oz and max_current >= current_a:
            return width

    # 线性外推
    return int(current_a * 50)  # 粗略估计：1A约需50mil


def _check_thermal_pad(components: List[Dict], pcb_info: Dict) -> List[DesignIssue]:
    """检查散热焊盘"""
    issues = []

    # 检查功率器件
    for comp in components:
        model = comp.get("model", "").lower()
        name = comp.get("name", "").lower()

        # 识别功率器件
        is_power_device = any(
            x in model
            for x in [
                "7805",
                "7809",
                "7812",
                "7905",  # 线性稳压器
                "lm317",
                "lm337",
                "2596",
                "mp1584",
                "mt3608",  # DC-DC
                "l298",
                "tb6612",
                "drv88",  # 电机驱动
                "ir2110",
                "ir2104",  # MOS驱动
            ]
        )

        is_power_device = is_power_device or "功率" in name or "power" in name

        if is_power_device:
            # 检查是否有散热焊盘
            thermal_pad_area = pcb_info.get("thermal_pad_area_mm2", 0)

            # 根据功耗计算所需散热面积
            power_w = _estimate_power_dissipation(comp)
            required_area = power_w * 50  # 经验值：1W约需50mm²

            if thermal_pad_area < required_area:
                issues.append(
                    DesignIssue(
                        rule_id="SAFETY_005",
                        category=DesignCategory.SAFETY,
                        severity="warning",
                        message=f"{comp.get('name', '功率器件')}散热面积可能不足",
                        suggestion=f"增加散热焊盘面积至{required_area:.0f}mm²以上，或添加热过孔阵列",
                        auto_fixable=True,
                    )
                )

    return issues


def _estimate_power_dissipation(comp: Dict) -> float:
    """估算器件功耗"""
    model = comp.get("model", "").lower()

    # 线性稳压器功耗估计
    if "7805" in model:
        return 2.0  # 典型2W
    if "7812" in model:
        return 3.0
    if "lm317" in model:
        return 2.0

    # DC-DC效率较高，功耗较低
    if "2596" in model:
        return 1.0
    if "mp1584" in model:
        return 0.5

    # 电机驱动
    if "l298" in model:
        return 5.0  # 高功耗

    return 0.5  # 默认值


def fix_safety(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复安全间距问题"""
    if "pcb_design_notes" not in circuit_data:
        circuit_data["pcb_design_notes"] = []

    if rule.id == "SAFETY_001":
        circuit_data["pcb_design_notes"].append(
            {
                "category": "safety",
                "note": f"增加电气间隙: {issue.suggestion}",
                "priority": "critical",
            }
        )

    elif rule.id == "SAFETY_002":
        circuit_data["pcb_design_notes"].append(
            {
                "category": "safety",
                "note": "一次侧二次侧必须保持6mm以上间距，建议使用开槽",
                "priority": "critical",
            }
        )

    elif rule.id == "SAFETY_004":
        circuit_data["pcb_design_notes"].append(
            {
                "category": "safety",
                "note": f"增加电源线宽: {issue.suggestion}",
                "priority": "high",
            }
        )

    elif rule.id == "SAFETY_005":
        circuit_data["pcb_design_notes"].append(
            {
                "category": "safety",
                "note": f"增加散热设计: {issue.suggestion}",
                "priority": "high",
            }
        )

    return circuit_data


def get_safety_report(components: List[Dict], pcb_info: Dict) -> Dict:
    """生成安全间距报告"""
    max_voltage = _estimate_max_voltage(components)

    report = {
        "max_voltage_v": max_voltage,
        "clearance_requirements": {},
        "recommendations": [],
    }

    # 获取各级电压的间隙要求
    for voltage_str, specs in QUICK_REFERENCE.items():
        report["clearance_requirements"][voltage_str] = specs

    # 针对当前电路的建议
    if max_voltage >= 100:
        required_clearance = get_clearance_for_voltage(max_voltage)
        report["recommendations"].append(
            {
                "type": "clearance",
                "voltage": max_voltage,
                "required_mm": required_clearance,
                "note": f"电路中最高电压{max_voltage}V，需要{required_clearance}mm以上电气间隙",
            }
        )

    if max_voltage >= 220:
        report["recommendations"].append(
            {
                "type": "isolation",
                "note": "高压电路建议使用光耦或继电器隔离，并添加开槽增加爬电距离",
            }
        )

    return report

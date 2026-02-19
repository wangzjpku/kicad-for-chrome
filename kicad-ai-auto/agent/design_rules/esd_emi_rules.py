"""
ESD/EMI防护设计规则
ESD/EMI Protection Design Rules

确保电路具有足够的电磁兼容性：
- ESD防护 (静电放电)
- EMI滤波 (电磁干扰)
- 信号完整性
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class ESDProtection:
    """ESD防护规格"""

    protection_type: str  # tvs, zener, varistor, spark_gap
    component: str  # 推荐器件
    voltage: float  # 工作电压 V
    esd_rating_kv: float  # ESD耐受等级 kV
    capacitance_pf: float  # 电容 pF (影响信号)
    response_time_ns: float  # 响应时间 ns
    placement: str  # 放置位置


@dataclass
class EMIFilter:
    """EMI滤波器规格"""

    filter_type: str  # cmc, rc, lc, ferrite
    components: List[Dict]
    frequency_range: Tuple[float, float]  # Hz
    attenuation_db: float
    application: str  # power_line, signal_line, high_speed


# ========== ESD防护标准 ==========

ESD_PROTECTION_DEVICES = {
    # TVS二极管 (高速信号)
    "tvs_high_speed": ESDProtection(
        protection_type="tvs",
        component="TPD4E001 / PRTR5V0U2X",
        voltage=5.0,
        esd_rating_kv=15,
        capacitance_pf=0.5,
        response_time_ns=1,
        placement="紧靠连接器引脚",
    ),
    # TVS二极管 (通用I/O)
    "tvs_general": ESDProtection(
        protection_type="tvs",
        component="SMBJ5.0CA / P6KE6.8CA",
        voltage=5.0,
        esd_rating_kv=30,
        capacitance_pf=50,
        response_time_ns=1,
        placement="连接器入口处",
    ),
    # TVS二极管 (电源线)
    "tvs_power": ESDProtection(
        protection_type="tvs",
        component="SMBJ5.0A / 5KP5.0A",
        voltage=5.0,
        esd_rating_kv=30,
        capacitance_pf=1000,
        response_time_ns=1,
        placement="电源入口",
    ),
    # 压敏电阻 (高压)
    "varistor": ESDProtection(
        protection_type="varistor",
        component="TVR07470 / S07K470",
        voltage=300,
        esd_rating_kv=8,
        capacitance_pf=100,
        response_time_ns=25,
        placement="AC电源入口",
    ),
    # 稳压二极管 (低成本)
    "zener": ESDProtection(
        protection_type="zener",
        component="1N4733A (5.1V)",
        voltage=5.1,
        esd_rating_kv=2,
        capacitance_pf=50,
        response_time_ns=10,
        placement="I/O线路上",
    ),
}

# ========== EMI滤波标准 ==========

EMI_FILTER_CONFIGS = {
    # 电源线EMI滤波
    "power_line_input": EMIFilter(
        filter_type="cmc",
        components=[
            {"type": "fuse", "value": "1A", "note": "过流保护"},
            {"type": "cmc", "value": "10mH 1A", "note": "共模电感"},
            {"type": "capacitor_x", "value": "100nF 275VAC", "note": "X电容"},
            {"type": "capacitor_y", "value": "2.2nF 250VAC", "note": "Y电容"},
        ],
        frequency_range=(150000, 30000000),
        attenuation_db=40,
        application="power_line",
    ),
    # 信号线RC滤波
    "signal_rc": EMIFilter(
        filter_type="rc",
        components=[
            {"type": "resistor", "value": "100Ω", "note": "限流电阻"},
            {"type": "capacitor", "value": "100pF", "note": "滤波电容"},
        ],
        frequency_range=(1000000, 100000000),
        attenuation_db=20,
        application="signal_line",
    ),
    # 高速信号磁珠滤波
    "high_speed_ferrite": EMIFilter(
        filter_type="ferrite",
        components=[
            {"type": "ferrite_bead", "value": "600Ω @100MHz", "note": "磁珠"},
        ],
        frequency_range=(100000000, 1000000000),
        attenuation_db=20,
        application="high_speed",
    ),
    # USB信号滤波
    "usb_filter": EMIFilter(
        filter_type="cmc",
        components=[
            {"type": "usb_cmc", "value": "90Ω @100MHz", "note": "USB共模电感"},
            {"type": "esd_protection", "value": "TPD4E001", "note": "ESD保护"},
        ],
        frequency_range=(1000000, 480000000),
        attenuation_db=30,
        application="high_speed",
    ),
}

# ========== 接口ESD要求 ==========

INTERFACE_ESD_REQUIREMENTS = {
    "usb": {
        "esd_level": "IEC 61000-4-2 Level 4 (8kV接触/15kV空气)",
        "protection": "tvs_high_speed",
        "placement": "USB连接器D+/D-引脚",
    },
    "rs232": {
        "esd_level": "IEC 61000-4-2 Level 3 (6kV接触)",
        "protection": "tvs_general",
        "placement": "RS232收发器输入端",
    },
    "rs485": {
        "esd_level": "IEC 61000-4-2 Level 4 (8kV接触)",
        "protection": "tvs_general",
        "placement": "RS485收发器A/B线",
    },
    "ethernet": {
        "esd_level": "IEC 61000-4-2 Level 3 (6kV接触)",
        "protection": "ethernet_magjack",
        "placement": "网口变压器集成",
    },
    "gpio": {
        "esd_level": "IEC 61000-4-2 Level 2 (4kV接触)",
        "protection": "tvs_general",
        "placement": "连接器引脚",
    },
    "power_input": {
        "esd_level": "IEC 61000-4-2 Level 3 (6kV接触)",
        "protection": "tvs_power",
        "placement": "电源入口",
    },
}


def get_esd_emi_rules() -> List[DesignRule]:
    """获取ESD/EMI设计规则"""
    return [
        DesignRule(
            id="ESD_EMI_001",
            category=DesignCategory.ESD_EMI,
            name="接口ESD防护",
            description="所有外部接口必须有ESD防护",
            check_function="check_interface_esd",
            fix_function="add_esd_protection",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="ESD_EMI_002",
            category=DesignCategory.ESD_EMI,
            name="电源入口EMI滤波",
            description="电源入口必须有EMI滤波器",
            check_function="check_power_emi",
            fix_function="add_power_emi_filter",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="ESD_EMI_003",
            category=DesignCategory.ESD_EMI,
            name="信号线滤波",
            description="敏感信号线需要RC或磁珠滤波",
            check_function="check_signal_filter",
            fix_function="add_signal_filter",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="ESD_EMI_004",
            category=DesignCategory.ESD_EMI,
            name="TVS选型",
            description="TVS电压必须高于工作电压并留有裕量",
            check_function="check_tvs_selection",
            fix_function="optimize_tvs",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="ESD_EMI_005",
            category=DesignCategory.ESD_EMI,
            name="高速信号阻抗",
            description="高速差分信号需要阻抗匹配",
            check_function="check_impedance",
            fix_function="add_impedance_matching",
            priority=2,
            auto_fix=False,
        ),
    ]


def check_esd_emi(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查ESD/EMI防护"""
    issues = []
    components = circuit_data.get("components", [])

    if rule.id == "ESD_EMI_001":
        issues.extend(_check_interface_esd(components))
    elif rule.id == "ESD_EMI_002":
        issues.extend(_check_power_emi(components))
    elif rule.id == "ESD_EMI_003":
        issues.extend(_check_signal_filter(components))
    elif rule.id == "ESD_EMI_004":
        issues.extend(_check_tvs_selection(components))
    elif rule.id == "ESD_EMI_005":
        issues.extend(_check_impedance(components, circuit_data))

    return issues


def _detect_interfaces(components: List[Dict]) -> List[str]:
    """检测电路中的接口类型"""
    interfaces = []

    for comp in components:
        name = comp.get("name", "").lower()
        model = comp.get("model", "").lower()

        if "usb" in name or "usb" in model:
            interfaces.append("usb")
        if "rs232" in model or "max232" in model or "sp3232" in model:
            interfaces.append("rs232")
        if "rs485" in model or "max485" in model or "sp485" in model:
            interfaces.append("rs485")
        if "ethernet" in name or "lan" in name or "rtl8" in model:
            interfaces.append("ethernet")
        if "gpio" in name or "排针" in name:
            interfaces.append("gpio")

    return list(set(interfaces))


def _check_interface_esd(components: List[Dict]) -> List[DesignIssue]:
    """检查接口ESD防护"""
    issues = []

    interfaces = _detect_interfaces(components)

    # 检查是否有ESD保护器件
    has_esd_protection = any(
        any(
            x in c.get("name", "").lower() or x in c.get("model", "").lower()
            for x in ["tvs", "esd", "prtr", "tpd4", "smbj"]
        )
        for c in components
    )

    for interface in interfaces:
        if interface in INTERFACE_ESD_REQUIREMENTS:
            req = INTERFACE_ESD_REQUIREMENTS[interface]

            if not has_esd_protection:
                protection_type = req.get("protection", "tvs_general")
                protection = ESD_PROTECTION_DEVICES.get(
                    protection_type, ESD_PROTECTION_DEVICES["tvs_general"]
                )

                issues.append(
                    DesignIssue(
                        rule_id="ESD_EMI_001",
                        category=DesignCategory.ESD_EMI,
                        severity="warning",
                        message=f"{interface.upper()}接口缺少ESD防护",
                        suggestion=f"添加{protection.component} ({req['esd_level']})，放置于{req['placement']}",
                        auto_fixable=True,
                    )
                )

    return issues


def _check_power_emi(components: List[Dict]) -> List[DesignIssue]:
    """检查电源EMI滤波"""
    issues = []

    # 检测是否有电源输入
    has_power_input = any(
        "电源" in c.get("name", "") or "usb" in c.get("name", "").lower()
        for c in components
    )

    # 检查是否有EMI滤波器件
    has_cmc = any(
        "共模" in c.get("name", "") or "cmc" in c.get("name", "").lower()
        for c in components
    )

    has_ferrite = any(
        "磁珠" in c.get("name", "") or "ferrite" in c.get("name", "").lower()
        for c in components
    )

    if has_power_input and not (has_cmc or has_ferrite):
        issues.append(
            DesignIssue(
                rule_id="ESD_EMI_002",
                category=DesignCategory.ESD_EMI,
                severity="warning",
                message="电源入口缺少EMI滤波器",
                suggestion="添加共模电感或磁珠滤波器，配合X/Y电容使用",
                auto_fixable=True,
            )
        )

    return issues


def _check_signal_filter(components: List[Dict]) -> List[DesignIssue]:
    """检查信号线滤波"""
    issues = []

    # 检查是否有敏感信号线
    sensitive_signals = any(
        any(
            x in c.get("name", "").lower()
            for x in ["reset", "adc", "dac", "sens", "传感"]
        )
        for c in components
    )

    # 检查是否有滤波
    has_filter_cap = any(
        "电容" in c.get("name", "")
        and any(x in c.get("model", "").lower() for x in ["pf", "nf"])
        for c in components
    )

    if sensitive_signals and not has_filter_cap:
        issues.append(
            DesignIssue(
                rule_id="ESD_EMI_003",
                category=DesignCategory.ESD_EMI,
                severity="info",
                message="敏感信号线建议添加滤波",
                suggestion="在ADC/DAC/复位等敏感信号线上添加100pF-100nF滤波电容",
                auto_fixable=True,
            )
        )

    return issues


def _check_tvs_selection(components: List[Dict]) -> List[DesignIssue]:
    """检查TVS选型"""
    issues = []

    for comp in components:
        name = comp.get("name", "").lower()
        model = comp.get("model", "").lower()

        if "tvs" in name or "tvs" in model or "smbj" in model:
            # 检查TVS电压是否合适
            # 简化实现：检查是否包含电压值
            if "5.0" in model or "5v" in model:
                # 5V TVS, 检查电路是否有5V
                pass  # 合适

    return issues


def _check_impedance(components: List[Dict], circuit_data: Dict) -> List[DesignIssue]:
    """检查阻抗匹配"""
    issues = []

    # 检查高速信号
    pcb_info = circuit_data.get("pcb_info", {})
    high_speed_signals = pcb_info.get("high_speed_signals", [])

    for signal in high_speed_signals:
        freq_mhz = signal.get("frequency_mhz", 0)
        impedance = signal.get("impedance_ohm", 0)

        # USB/以太网等需要90-100Ω差分阻抗
        if freq_mhz >= 100 and impedance == 0:
            issues.append(
                DesignIssue(
                    rule_id="ESD_EMI_005",
                    category=DesignCategory.ESD_EMI,
                    severity="warning",
                    message=f"高速信号 {signal.get('name', 'unknown')} 缺少阻抗控制",
                    suggestion="使用差分对布线，控制90-100Ω差分阻抗，添加地平面参考",
                    auto_fixable=False,
                )
            )

    return issues


def fix_esd_emi(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复ESD/EMI问题"""
    components = circuit_data.get("components", [])

    if rule.id == "ESD_EMI_001":
        # 添加ESD保护器件
        new_components = _add_esd_protection(components)
        circuit_data["components"] = new_components

    elif rule.id == "ESD_EMI_002":
        # 添加电源EMI滤波
        new_components = _add_power_emi_filter(components)
        circuit_data["components"] = new_components

    elif rule.id == "ESD_EMI_003":
        # 添加信号滤波
        if "pcb_design_notes" not in circuit_data:
            circuit_data["pcb_design_notes"] = []
        circuit_data["pcb_design_notes"].append(
            {
                "category": "emi",
                "note": "在敏感信号线上添加100pF滤波电容",
                "priority": "medium",
            }
        )

    return circuit_data


def _add_esd_protection(components: List[Dict]) -> List[Dict]:
    """添加ESD保护器件"""
    interfaces = _detect_interfaces(components)

    max_id = max(
        (int(c.get("id", "comp-0").split("-")[1]) for c in components), default=0
    )
    new_components = []

    for interface in interfaces:
        if interface in INTERFACE_ESD_REQUIREMENTS:
            protection_type = INTERFACE_ESD_REQUIREMENTS[interface].get(
                "protection", "tvs_general"
            )
            protection = ESD_PROTECTION_DEVICES.get(protection_type)

            if protection:
                max_id += 1
                new_components.append(
                    {
                        "id": f"comp-{max_id}",
                        "name": f"{interface.upper()}_ESD保护",
                        "model": protection.component,
                        "package": "SOT-23"
                        if "tvs" in protection.protection_type
                        else "SMD",
                        "quantity": 1,
                        "auto_added": True,
                        "added_reason": f"为{interface}接口添加ESD防护",
                        "esd_rating_kv": protection.esd_rating_kv,
                    }
                )

    return components + new_components


def _add_power_emi_filter(components: List[Dict]) -> List[Dict]:
    """添加电源EMI滤波器"""
    max_id = max(
        (int(c.get("id", "comp-0").split("-")[1]) for c in components), default=0
    )

    # 添加磁珠
    max_id += 1
    ferrite = {
        "id": f"comp-{max_id}",
        "name": "电源滤波磁珠",
        "model": "600Ω @100MHz",
        "package": "0805",
        "quantity": 1,
        "auto_added": True,
        "added_reason": "电源入口EMI滤波",
    }

    return components + [ferrite]


def get_esd_emi_report(components: List[Dict]) -> Dict:
    """生成ESD/EMI报告"""
    interfaces = _detect_interfaces(components)

    report = {
        "detected_interfaces": interfaces,
        "esd_requirements": {},
        "emi_recommendations": [],
        "protection_devices": [],
    }

    for interface in interfaces:
        if interface in INTERFACE_ESD_REQUIREMENTS:
            req = INTERFACE_ESD_REQUIREMENTS[interface]
            protection = ESD_PROTECTION_DEVICES.get(
                req.get("protection", "tvs_general")
            )

            report["esd_requirements"][interface] = {
                "esd_level": req["esd_level"],
                "protection_device": protection.component if protection else "未指定",
                "placement": req["placement"],
            }

    # EMI建议
    if any(c in interfaces for c in ["usb", "ethernet"]):
        report["emi_recommendations"].append("高速接口建议使用共模电感和ESD保护组合")

    report["emi_recommendations"].append("所有外部连接器附近添加TVS二极管阵列")

    return report

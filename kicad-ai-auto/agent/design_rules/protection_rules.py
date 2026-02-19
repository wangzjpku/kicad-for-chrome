"""
保护电路设计规则
Protection Circuit Design Rules

确保电路具有完整的保护功能：
- 过压保护 (OVP)
- 过流保护 (OCP)
- 过温保护 (OTP)
- 反接保护
- 短路保护
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class ProtectionSpec:
    """保护规格"""

    protection_type: str  # ovp, ocp, otp, reverse, short
    component: str  # 推荐器件
    trigger_value: float  # 触发值
    response_time_us: float  # 响应时间 μs
    reset_type: str  # auto, manual
    cost_level: str  # low, medium, high


# ========== 过压保护器件 ==========

OVP_DEVICES = {
    # TVS二极管
    "tvs_5v": ProtectionSpec(
        protection_type="ovp",
        component="SMBJ5.0CA",
        trigger_value=6.4,  # V
        response_time_us=0.001,
        reset_type="auto",
        cost_level="low",
    ),
    "tvs_12v": ProtectionSpec(
        protection_type="ovp",
        component="SMBJ12CA",
        trigger_value=19.9,
        response_time_us=0.001,
        reset_type="auto",
        cost_level="low",
    ),
    "tvs_24v": ProtectionSpec(
        protection_type="ovp",
        component="SMBJ24CA",
        trigger_value=38.9,
        response_time_us=0.001,
        reset_type="auto",
        cost_level="low",
    ),
    # 稳压二极管
    "zener_5v1": ProtectionSpec(
        protection_type="ovp",
        component="1N4733A (5.1V)",
        trigger_value=5.1,
        response_time_us=10,
        reset_type="auto",
        cost_level="low",
    ),
    # 专用OVP IC
    "ovp_ic_5v": ProtectionSpec(
        protection_type="ovp",
        component="TPS2592 / NCP347",
        trigger_value=5.5,
        response_time_us=1,
        reset_type="auto",
        cost_level="medium",
    ),
}

# ========== 过流保护器件 ==========

OCP_DEVICES = {
    # 保险丝
    "fuse_500ma": ProtectionSpec(
        protection_type="ocp",
        component="保险丝 500mA",
        trigger_value=0.5,
        response_time_us=10000,  # 较慢
        reset_type="manual",
        cost_level="low",
    ),
    "fuse_1a": ProtectionSpec(
        protection_type="ocp",
        component="保险丝 1A",
        trigger_value=1.0,
        response_time_us=10000,
        reset_type="manual",
        cost_level="low",
    ),
    "fuse_2a": ProtectionSpec(
        protection_type="ocp",
        component="保险丝 2A",
        trigger_value=2.0,
        response_time_us=10000,
        reset_type="manual",
        cost_level="low",
    ),
    # PTC自恢复保险丝
    "ptc_500ma": ProtectionSpec(
        protection_type="ocp",
        component="PTC自恢复 500mA",
        trigger_value=0.5,
        response_time_us=100,
        reset_type="auto",
        cost_level="low",
    ),
    "ptc_1a": ProtectionSpec(
        protection_type="ocp",
        component="PTC自恢复 1A",
        trigger_value=1.0,
        response_time_us=100,
        reset_type="auto",
        cost_level="low",
    ),
    # 电子保险丝IC
    "efuse_1a": ProtectionSpec(
        protection_type="ocp",
        component="TPS2590 / LTC4365",
        trigger_value=1.0,
        response_time_us=1,
        reset_type="auto",
        cost_level="medium",
    ),
}

# ========== 过温保护器件 ==========

OTP_DEVICES = {
    # 热敏电阻NTC
    "ntc_10k": ProtectionSpec(
        protection_type="otp",
        component="NTC 10K 3950",
        trigger_value=85,  # °C
        response_time_us=1000,
        reset_type="auto",
        cost_level="low",
    ),
    # 温度开关
    "thermal_switch_85c": ProtectionSpec(
        protection_type="otp",
        component="温度开关 85°C",
        trigger_value=85,
        response_time_us=1000,
        reset_type="auto",
        cost_level="low",
    ),
    # 热电偶/温度传感器
    "temp_sensor": ProtectionSpec(
        protection_type="otp",
        component="DS18B20 / LM35",
        trigger_value=85,
        response_time_us=1000,
        reset_type="auto",
        cost_level="medium",
    ),
}

# ========== 反接保护器件 ==========

REVERSE_PROTECTION = {
    # 肖特基二极管
    "schottky_diode": ProtectionSpec(
        protection_type="reverse",
        component="SS34 (3A 40V)",
        trigger_value=0.3,  # V压降
        response_time_us=0.001,
        reset_type="auto",
        cost_level="low",
    ),
    # PMOS反向保护
    "pmos_protection": ProtectionSpec(
        protection_type="reverse",
        component="SI2301 (PMOS)",
        trigger_value=0.05,  # V压降
        response_time_us=0.1,
        reset_type="auto",
        cost_level="medium",
    ),
    # 桥式整流 (自动极性)
    "bridge_rectifier": ProtectionSpec(
        protection_type="reverse",
        component="MB6S 桥堆",
        trigger_value=1.0,  # V压降
        response_time_us=0.001,
        reset_type="auto",
        cost_level="low",
    ),
}

# ========== 应用场景保护需求 ==========

APPLICATION_PROTECTION_REQUIREMENTS = {
    "power_supply": {
        "required": ["ovp", "ocp"],
        "recommended": ["otp", "reverse"],
        "note": "电源必须有OVP和OCP",
    },
    "battery_charger": {
        "required": ["ovp", "ocp", "otp"],
        "recommended": ["reverse", "short"],
        "note": "充电电路必须有过压过流过温保护",
    },
    "motor_driver": {
        "required": ["ocp", "short"],
        "recommended": ["otp"],
        "note": "电机驱动需要短路和过流保护",
    },
    "usb_device": {
        "required": ["ovp", "ocp", "esd"],
        "recommended": ["reverse"],
        "note": "USB设备必须有ESD保护和限流",
    },
    "arduino_shield": {
        "required": ["ocp"],
        "recommended": ["ovp", "reverse"],
        "note": "Arduino扩展板建议有限流保护",
    },
    "iot_device": {
        "required": ["ovp", "ocp"],
        "recommended": ["otp", "reverse"],
        "note": "IoT设备需要完整保护",
    },
}


def get_protection_rules() -> List[DesignRule]:
    """获取保护电路规则"""
    return [
        DesignRule(
            id="PROTECTION_001",
            category=DesignCategory.PROTECTION,
            name="电源过压保护",
            description="电源输入必须有OVP",
            check_function="check_ovp",
            fix_function="add_ovp",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="PROTECTION_002",
            category=DesignCategory.PROTECTION,
            name="过流保护",
            description="电源/大电流路径必须有OCP",
            check_function="check_ocp",
            fix_function="add_ocp",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="PROTECTION_003",
            category=DesignCategory.PROTECTION,
            name="过温保护",
            description="功率电路建议有OTP",
            check_function="check_otp",
            fix_function="add_otp",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="PROTECTION_004",
            category=DesignCategory.PROTECTION,
            name="反接保护",
            description="直流电源输入应有反接保护",
            check_function="check_reverse_protection",
            fix_function="add_reverse_protection",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="PROTECTION_005",
            category=DesignCategory.PROTECTION,
            name="电池保护",
            description="电池电路必须有完整保护",
            check_function="check_battery_protection",
            fix_function="add_battery_protection",
            priority=1,
            auto_fix=True,
        ),
    ]


def check_protection(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查保护电路"""
    issues = []
    components = circuit_data.get("components", [])
    parameters = circuit_data.get("parameters", [])

    if rule.id == "PROTECTION_001":
        issues.extend(_check_ovp(components))
    elif rule.id == "PROTECTION_002":
        issues.extend(_check_ocp(components, parameters))
    elif rule.id == "PROTECTION_003":
        issues.extend(_check_otp(components))
    elif rule.id == "PROTECTION_004":
        issues.extend(_check_reverse_protection(components))
    elif rule.id == "PROTECTION_005":
        issues.extend(_check_battery_protection(components))

    return issues


def _detect_application_type(components: List[Dict], parameters: List[Dict]) -> str:
    """检测应用类型"""
    for comp in components:
        model = comp.get("model", "").lower()
        name = comp.get("name", "").lower()

        if "tp4056" in model or "xc4054" in model:
            return "battery_charger"
        if "l298" in model or "tb6612" in model or "drv88" in model:
            return "motor_driver"
        if "usb" in name:
            return "usb_device"
        if "7805" in model or "1117" in model or "2596" in model:
            return "power_supply"
        if "esp32" in model or "esp8266" in model:
            return "iot_device"

    return "power_supply"


def _has_protection_device(components: List[Dict], protection_type: str) -> bool:
    """检查是否有保护器件"""
    keywords = {
        "ovp": ["tvs", "zener", "稳压", "smbj", "p6ke", "1n47"],
        "ocp": ["保险", "fuse", "ptc", "自恢复", "efuse"],
        "otp": ["ntc", "温度", "thermal", "ds18b20", "lm35"],
        "reverse": ["肖特基", "schottky", "ss34", "pmos", "桥堆", "bridge"],
    }

    search_terms = keywords.get(protection_type, [])

    for comp in components:
        name = comp.get("name", "").lower()
        model = comp.get("model", "").lower()

        for term in search_terms:
            if term in name or term in model:
                return True

    return False


def _check_ovp(components: List[Dict]) -> List[DesignIssue]:
    """检查过压保护"""
    issues = []

    app_type = _detect_application_type(components, [])
    requirements = APPLICATION_PROTECTION_REQUIREMENTS.get(app_type, {})

    if "ovp" in requirements.get("required", []):
        if not _has_protection_device(components, "ovp"):
            # 根据电压选择推荐器件
            issues.append(
                DesignIssue(
                    rule_id="PROTECTION_001",
                    category=DesignCategory.PROTECTION,
                    severity="warning",
                    message="电源输入缺少过压保护(OVP)",
                    suggestion="添加TVS二极管(如SMBJ5.0CA)或稳压二极管，放置于电源入口",
                    auto_fixable=True,
                )
            )

    return issues


def _check_ocp(components: List[Dict], parameters: List[Dict]) -> List[DesignIssue]:
    """检查过流保护"""
    issues = []

    app_type = _detect_application_type(components, [])
    requirements = APPLICATION_PROTECTION_REQUIREMENTS.get(app_type, {})

    if "ocp" in requirements.get("required", []):
        if not _has_protection_device(components, "ocp"):
            # 获取电流需求
            current = 1.0  # 默认1A
            for param in parameters:
                if "电流" in param.get("key", ""):
                    try:
                        current = float(param.get("value", 1))
                    except:
                        pass

            # 推荐合适的保护器件
            if current <= 0.5:
                suggestion = "添加500mA PTC自恢复保险丝"
            elif current <= 1:
                suggestion = "添加1A PTC自恢复保险丝或保险丝"
            else:
                suggestion = f"添加{current:.1f}A保险丝或电子保险丝IC"

            issues.append(
                DesignIssue(
                    rule_id="PROTECTION_002",
                    category=DesignCategory.PROTECTION,
                    severity="warning",
                    message="电源/大电流路径缺少过流保护(OCP)",
                    suggestion=suggestion,
                    auto_fixable=True,
                )
            )

    return issues


def _check_otp(components: List[Dict]) -> List[DesignIssue]:
    """检查过温保护"""
    issues = []

    app_type = _detect_application_type(components, [])
    requirements = APPLICATION_PROTECTION_REQUIREMENTS.get(app_type, {})

    # 检查是否有功率器件
    has_power_device = any(
        any(x in c.get("model", "").lower() for x in ["7805", "l298", "2596", "ir2110"])
        for c in components
    )

    if has_power_device and not _has_protection_device(components, "otp"):
        if "otp" in requirements.get("required", []):
            issues.append(
                DesignIssue(
                    rule_id="PROTECTION_003",
                    category=DesignCategory.PROTECTION,
                    severity="warning",
                    message="功率电路缺少过温保护(OTP)",
                    suggestion="添加NTC热敏电阻或温度开关，监控功率器件温度",
                    auto_fixable=True,
                )
            )
        elif "otp" in requirements.get("recommended", []):
            issues.append(
                DesignIssue(
                    rule_id="PROTECTION_003",
                    category=DesignCategory.PROTECTION,
                    severity="info",
                    message="功率电路建议添加过温保护",
                    suggestion="可添加温度传感器实现软件保护",
                    auto_fixable=True,
                )
            )

    return issues


def _check_reverse_protection(components: List[Dict]) -> List[DesignIssue]:
    """检查反接保护"""
    issues = []

    # 检查是否有直流电源输入
    has_dc_input = any(
        "usb" in c.get("name", "").lower() or "电源" in c.get("name", "")
        for c in components
    )

    if has_dc_input and not _has_protection_device(components, "reverse"):
        issues.append(
            DesignIssue(
                rule_id="PROTECTION_004",
                category=DesignCategory.PROTECTION,
                severity="info",
                message="直流电源输入缺少反接保护",
                suggestion="添加肖特基二极管(SS34)或PMOS实现反接保护",
                auto_fixable=True,
            )
        )

    return issues


def _check_battery_protection(components: List[Dict]) -> List[DesignIssue]:
    """检查电池保护"""
    issues = []

    # 检查是否有电池充电电路
    has_battery_charger = any(
        "tp4056" in c.get("model", "").lower() or "充电" in c.get("name", "")
        for c in components
    )

    if has_battery_charger:
        # 检查保护是否完整
        has_protection_ic = any(
            "fs8205" in c.get("model", "").lower()
            or "dw01" in c.get("model", "").lower()
            for c in components
        )

        if not has_protection_ic:
            issues.append(
                DesignIssue(
                    rule_id="PROTECTION_005",
                    category=DesignCategory.PROTECTION,
                    severity="warning",
                    message="电池电路缺少保护板",
                    suggestion="添加DW01+FS8205电池保护板，实现过充过放过流保护",
                    auto_fixable=True,
                )
            )

    return issues


def fix_protection(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复保护电路问题"""
    components = circuit_data.get("components", [])

    max_id = max(
        (int(c.get("id", "comp-0").split("-")[1]) for c in components), default=0
    )
    new_components = []

    if rule.id == "PROTECTION_001":
        # 添加TVS
        max_id += 1
        new_components.append(
            {
                "id": f"comp-{max_id}",
                "name": "过压保护TVS",
                "model": "SMBJ5.0CA",
                "package": "SMB",
                "quantity": 1,
                "auto_added": True,
                "added_reason": "电源输入过压保护",
            }
        )

    elif rule.id == "PROTECTION_002":
        # 添加PTC
        max_id += 1
        new_components.append(
            {
                "id": f"comp-{max_id}",
                "name": "过流保护PTC",
                "model": "PPTC 1A",
                "package": "1206",
                "quantity": 1,
                "auto_added": True,
                "added_reason": "电源输入过流保护",
            }
        )

    elif rule.id == "PROTECTION_004":
        # 添加反接保护二极管
        max_id += 1
        new_components.append(
            {
                "id": f"comp-{max_id}",
                "name": "反接保护二极管",
                "model": "SS34",
                "package": "SMA",
                "quantity": 1,
                "auto_added": True,
                "added_reason": "电源反接保护",
            }
        )

    elif rule.id == "PROTECTION_005":
        # 添加电池保护器件
        max_id += 1
        new_components.append(
            {
                "id": f"comp-{max_id}",
                "name": "电池保护IC",
                "model": "DW01+FS8205",
                "package": "SOT-23+TSSOP-8",
                "quantity": 1,
                "auto_added": True,
                "added_reason": "锂电池过充过放保护",
            }
        )

    circuit_data["components"] = components + new_components
    return circuit_data


def get_protection_report(components: List[Dict], parameters: List[Dict]) -> Dict:
    """生成保护电路报告"""
    app_type = _detect_application_type(components, parameters)
    requirements = APPLICATION_PROTECTION_REQUIREMENTS.get(app_type, {})

    report = {
        "application_type": app_type,
        "requirements": requirements,
        "current_protection": {},
        "missing_protection": [],
        "recommendations": [],
    }

    # 检查现有保护
    for p_type in ["ovp", "ocp", "otp", "reverse"]:
        has_protection = _has_protection_device(components, p_type)
        report["current_protection"][p_type] = has_protection

        required = p_type in requirements.get("required", [])
        recommended = p_type in requirements.get("recommended", [])

        if not has_protection:
            if required:
                report["missing_protection"].append(
                    {
                        "type": p_type,
                        "level": "required",
                    }
                )
            elif recommended:
                report["missing_protection"].append(
                    {
                        "type": p_type,
                        "level": "recommended",
                    }
                )

    # 生成建议
    protection_names = {
        "ovp": "过压保护",
        "ocp": "过流保护",
        "otp": "过温保护",
        "reverse": "反接保护",
    }

    for missing in report["missing_protection"]:
        p_type = missing["type"]
        level = missing["level"]

        if p_type == "ovp":
            report["recommendations"].append(
                f"[{'必须' if level == 'required' else '建议'}] 添加TVS二极管(如SMBJ5.0CA)实现{protection_names[p_type]}"
            )
        elif p_type == "ocp":
            report["recommendations"].append(
                f"[{'必须' if level == 'required' else '建议'}] 添加PTC自恢复保险丝实现{protection_names[p_type]}"
            )
        elif p_type == "otp":
            report["recommendations"].append(
                f"[{'必须' if level == 'required' else '建议'}] 添加NTC热敏电阻或温度开关实现{protection_names[p_type]}"
            )
        elif p_type == "reverse":
            report["recommendations"].append(
                f"[{'必须' if level == 'required' else '建议'}] 添加肖特基二极管实现{protection_names[p_type]}"
            )

    return report

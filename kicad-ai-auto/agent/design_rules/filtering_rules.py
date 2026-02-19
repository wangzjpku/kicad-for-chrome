"""
电源滤波设计规则
Power Supply Filtering Design Rules

设计合适的电源滤波电路：
- 输入滤波（EMI/反灌抑制）
- 级间滤波
- 输出滤波（纹波抑制）
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import math

from . import DesignRule, DesignIssue, DesignCategory

logger = logging.getLogger(__name__)


@dataclass
class FilterStage:
    """滤波级"""

    stage_type: str  # input, interstage, output
    topology: str  # pi, lc, rc, clc
    components: List[Dict]
    cutoff_freq_hz: float
    attenuation_db: float
    purpose: str


@dataclass
class PowerSupplySpec:
    """电源规格"""

    input_voltage_min: float
    input_voltage_max: float
    output_voltage: float
    output_current_max: float
    ripple_req_mv: float
    noise_req_mv: float
    response_time_us: float


# ========== 滤波器设计规则 ==========

FILTER_TOPOLOGIES = {
    "pi_filter": {
        "description": "π型滤波器 - 高频噪声抑制",
        "components": [
            {"type": "capacitor", "position": "input", "typical_value": "10uF"},
            {"type": "inductor", "position": "middle", "typical_value": "10uH"},
            {"type": "capacitor", "position": "output", "typical_value": "10uF"},
        ],
        "attenuation_db_per_decade": 40,
        "typical_cutoff": "10kHz-100kHz",
    },
    "lc_filter": {
        "description": "LC滤波器 - 中频噪声抑制",
        "components": [
            {"type": "inductor", "position": "series", "typical_value": "100uH"},
            {"type": "capacitor", "position": "shunt", "typical_value": "100uF"},
        ],
        "attenuation_db_per_decade": 40,
        "typical_cutoff": "1kHz-10kHz",
    },
    "rc_filter": {
        "description": "RC滤波器 - 低频噪声抑制",
        "components": [
            {"type": "resistor", "position": "series", "typical_value": "10Ω"},
            {"type": "capacitor", "position": "shunt", "typical_value": "100uF"},
        ],
        "attenuation_db_per_decade": 20,
        "typical_cutoff": "100Hz-1kHz",
    },
    "clc_filter": {
        "description": "CLC滤波器 - 高性能滤波",
        "components": [
            {"type": "capacitor", "position": "input", "typical_value": "100uF"},
            {"type": "inductor", "position": "series", "typical_value": "1mH"},
            {"type": "capacitor", "position": "output", "typical_value": "100uF"},
        ],
        "attenuation_db_per_decade": 60,
        "typical_cutoff": "100Hz-1kHz",
    },
    "common_mode_choke": {
        "description": "共模电感 - EMI抑制",
        "components": [
            {"type": "cmc", "position": "series", "typical_value": "10mH"},
            {"type": "capacitor", "position": "x_cap", "typical_value": "100nF"},
            {"type": "capacitor", "position": "y_cap", "typical_value": "2.2nF"},
        ],
        "attenuation_db_per_decade": 40,
        "typical_cutoff": "150kHz-30MHz",
    },
}

# 电源类型与推荐滤波配置
POWER_SUPPLY_FILTER_CONFIGS = {
    "linear_regulator": {
        "description": "线性稳压器 (7805, AMS1117等)",
        "input_filter": FilterStage(
            stage_type="input",
            topology="rc",
            components=[
                {
                    "type": "capacitor",
                    "value": "10uF",
                    "voltage": "25V",
                    "package": "0805",
                },
            ],
            cutoff_freq_hz=1000,
            attenuation_db=20,
            purpose="输入纹波抑制",
        ),
        "output_filter": FilterStage(
            stage_type="output",
            topology="rc",
            components=[
                {
                    "type": "capacitor",
                    "value": "10uF",
                    "voltage": "10V",
                    "package": "0805",
                },
                {
                    "type": "capacitor",
                    "value": "100nF",
                    "voltage": "16V",
                    "package": "0603",
                },
            ],
            cutoff_freq_hz=10000,
            attenuation_db=20,
            purpose="输出纹波抑制和高频去耦",
        ),
    },
    "buck_converter": {
        "description": "降压变换器 (LM2596, MP1584等)",
        "input_filter": FilterStage(
            stage_type="input",
            topology="pi",
            components=[
                {
                    "type": "capacitor",
                    "value": "10uF",
                    "voltage": "25V",
                    "package": "1206",
                },
                {
                    "type": "inductor",
                    "value": "10uH",
                    "current": "3A",
                    "package": "SMD",
                },
                {
                    "type": "capacitor",
                    "value": "47uF",
                    "voltage": "25V",
                    "package": "electrolytic",
                },
            ],
            cutoff_freq_hz=100000,
            attenuation_db=40,
            purpose="输入纹波和开关噪声抑制",
        ),
        "output_filter": FilterStage(
            stage_type="output",
            topology="lc",
            components=[
                {
                    "type": "capacitor",
                    "value": "100uF",
                    "voltage": "10V",
                    "package": "electrolytic",
                },
                {
                    "type": "capacitor",
                    "value": "10uF",
                    "voltage": "10V",
                    "package": "1206",
                },
            ],
            cutoff_freq_hz=10000,
            attenuation_db=40,
            purpose="输出纹波抑制",
        ),
    },
    "boost_converter": {
        "description": "升压变换器 (MT3608, XL6009等)",
        "input_filter": FilterStage(
            stage_type="input",
            topology="lc",
            components=[
                {
                    "type": "capacitor",
                    "value": "100uF",
                    "voltage": "10V",
                    "package": "electrolytic",
                },
            ],
            cutoff_freq_hz=1000,
            attenuation_db=20,
            purpose="输入电流平滑",
        ),
        "output_filter": FilterStage(
            stage_type="output",
            topology="pi",
            components=[
                {
                    "type": "capacitor",
                    "value": "47uF",
                    "voltage": "35V",
                    "package": "electrolytic",
                },
                {
                    "type": "inductor",
                    "value": "10uH",
                    "current": "2A",
                    "package": "SMD",
                },
                {
                    "type": "capacitor",
                    "value": "47uF",
                    "voltage": "35V",
                    "package": "electrolytic",
                },
            ],
            cutoff_freq_hz=100000,
            attenuation_db=40,
            purpose="输出纹波抑制",
        ),
    },
    "flyback": {
        "description": "反激电源 (UC3842等)",
        "input_filter": FilterStage(
            stage_type="input",
            topology="common_mode_choke",
            components=[
                {"type": "fuse", "value": "1A", "package": "axial"},
                {"type": "cmc", "value": "10mH", "current": "1A", "package": "THT"},
                {
                    "type": "capacitor_x",
                    "value": "100nF",
                    "voltage": "275VAC",
                    "package": "X2",
                },
                {"type": "varistor", "value": "275V", "package": "SMD"},
            ],
            cutoff_freq_hz=150000,
            attenuation_db=40,
            purpose="EMI滤波和浪涌保护",
        ),
        "output_filter": FilterStage(
            stage_type="output",
            topology="clc",
            components=[
                {
                    "type": "capacitor",
                    "value": "470uF",
                    "voltage": "16V",
                    "package": "electrolytic",
                },
                {
                    "type": "inductor",
                    "value": "100uH",
                    "current": "5A",
                    "package": "toroid",
                },
                {
                    "type": "capacitor",
                    "value": "470uF",
                    "voltage": "16V",
                    "package": "electrolytic",
                },
            ],
            cutoff_freq_hz=100,
            attenuation_db=60,
            purpose="输出纹波抑制",
        ),
    },
}


def get_filtering_rules() -> List[DesignRule]:
    """获取滤波设计规则"""
    return [
        DesignRule(
            id="FILTERING_001",
            category=DesignCategory.FILTERING,
            name="电源输入滤波",
            description="电源输入必须有适当的滤波电路",
            check_function="check_input_filter",
            fix_function="add_input_filter",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="FILTERING_002",
            category=DesignCategory.FILTERING,
            name="稳压器输出滤波",
            description="稳压器输出需要足够的大容量电容",
            check_function="check_output_filter",
            fix_function="add_output_filter",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="FILTERING_003",
            category=DesignCategory.FILTERING,
            name="开关电源滤波",
            description="开关电源需要LC/π型滤波",
            check_function="check_switching_filter",
            fix_function="add_switching_filter",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="FILTERING_004",
            category=DesignCategory.FILTERING,
            name="多级滤波",
            description="高要求电源需要多级滤波",
            check_function="check_multistage_filter",
            fix_function="add_multistage_filter",
            priority=2,
            auto_fix=False,
        ),
    ]


def check_filtering(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查滤波设计"""
    issues = []
    components = circuit_data.get("components", [])

    if rule.id == "FILTERING_001":
        issues.extend(_check_input_filter(components))
    elif rule.id == "FILTERING_002":
        issues.extend(_check_output_filter(components))
    elif rule.id == "FILTERING_003":
        issues.extend(_check_switching_filter(components))
    elif rule.id == "FILTERING_004":
        issues.extend(_check_multistage_filter(components))

    return issues


def _detect_power_supply_type(components: List[Dict]) -> Optional[str]:
    """检测电源类型"""
    for comp in components:
        model = comp.get("model", "").lower()

        # 线性稳压器
        if any(
            x in model
            for x in [
                "7805",
                "7809",
                "7812",
                "7905",
                "lm317",
                "lm337",
                "1117",
                "lt1086",
            ]
        ):
            return "linear_regulator"

        # 降压变换器
        if any(x in model for x in ["2596", "mp1584", "mp2307", "tps56", "lm267"]):
            return "buck_converter"

        # 升压变换器
        if any(x in model for x in ["mt3608", "xl6009", "sx1308", "lm2577"]):
            return "boost_converter"

        # 反激电源
        if any(
            x in model for x in ["uc3842", "uc3843", "uc3844", "uc3845", "top2", "lnk3"]
        ):
            return "flyback"

    return None


def _check_input_filter(components: List[Dict]) -> List[DesignIssue]:
    """检查输入滤波"""
    issues = []

    power_type = _detect_power_supply_type(components)
    if not power_type:
        return issues

    # 检查是否有输入电容
    has_input_cap = any(
        "电容" in c.get("name", "") and "输入" not in c.get("name", "").lower()
        for c in components
    )

    if not has_input_cap:
        config = POWER_SUPPLY_FILTER_CONFIGS.get(power_type)
        if config:
            issues.append(
                DesignIssue(
                    rule_id="FILTERING_001",
                    category=DesignCategory.FILTERING,
                    severity="critical",
                    message=f"{config.get('description', '电源')}缺少输入滤波电路",
                    suggestion=_get_input_filter_suggestion(power_type),
                    auto_fixable=True,
                )
            )

    return issues


def _get_input_filter_suggestion(power_type: str) -> str:
    """获取输入滤波建议"""
    suggestions = {
        "linear_regulator": "在输入端添加10uF以上电解电容和100nF陶瓷电容",
        "buck_converter": "在输入端添加π型滤波器：10uF陶瓷电容 + 10uH电感 + 47uF电解电容",
        "boost_converter": "在输入端添加100uF以上电解电容以平滑输入电流",
        "flyback": "在输入端添加EMI滤波器：保险丝 + 共模电感 + X电容 + 压敏电阻",
    }
    return suggestions.get(power_type, "添加适当的输入滤波电容")


def _check_output_filter(components: List[Dict]) -> List[DesignIssue]:
    """检查输出滤波"""
    issues = []

    power_type = _detect_power_supply_type(components)
    if not power_type:
        return issues

    # 检查是否有输出电容
    has_output_cap = any(
        "电容" in c.get("name", "") or "输出" in c.get("name", "").lower()
        for c in components
    )

    # 检查大容量电容
    has_bulk_cap = any(
        any(
            x in c.get("model", "").lower() for x in ["47uf", "100uf", "220uf", "470uf"]
        )
        for c in components
    )

    if not has_output_cap or (
        power_type in ["buck_converter", "boost_converter", "flyback"]
        and not has_bulk_cap
    ):
        config = POWER_SUPPLY_FILTER_CONFIGS.get(power_type)
        if config:
            issues.append(
                DesignIssue(
                    rule_id="FILTERING_002",
                    category=DesignCategory.FILTERING,
                    severity="warning",
                    message=f"{config.get('description', '电源')}输出滤波不足",
                    suggestion=_get_output_filter_suggestion(power_type),
                    auto_fixable=True,
                )
            )

    return issues


def _get_output_filter_suggestion(power_type: str) -> str:
    """获取输出滤波建议"""
    suggestions = {
        "linear_regulator": "在输出端添加10uF陶瓷电容和100nF去耦电容",
        "buck_converter": "在输出端添加100uF电解电容 + 10uF陶瓷电容",
        "boost_converter": "在输出端添加π型滤波器：47uF电解电容 + 10uH电感 + 47uF电解电容",
        "flyback": "在输出端添加CLC滤波器：470uF电解电容 + 100uH电感 + 470uF电解电容",
    }
    return suggestions.get(power_type, "添加适当的输出滤波电容")


def _check_switching_filter(components: List[Dict]) -> List[DesignIssue]:
    """检查开关电源滤波"""
    issues = []

    power_type = _detect_power_supply_type(components)
    if power_type not in ["buck_converter", "boost_converter", "flyback"]:
        return issues

    # 检查是否有电感（开关电源必须有）
    has_inductor = any(
        "电感" in c.get("name", "") or "inductor" in c.get("name", "").lower()
        for c in components
    )

    if not has_inductor:
        issues.append(
            DesignIssue(
                rule_id="FILTERING_003",
                category=DesignCategory.FILTERING,
                severity="critical",
                message="开关电源缺少滤波电感",
                suggestion="添加适当的LC或π型滤波电感",
                auto_fixable=True,
            )
        )

    return issues


def _check_multistage_filter(components: List[Dict]) -> List[DesignIssue]:
    """检查多级滤波"""
    issues = []

    power_type = _detect_power_supply_type(components)
    if power_type != "flyback":
        return issues

    # 反激电源需要EMI滤波器
    has_cmc = any(
        "共模" in c.get("name", "") or "cmc" in c.get("name", "").lower()
        for c in components
    )

    has_x_cap = any(
        "x电容" in c.get("name", "").lower() or "x2" in c.get("model", "").lower()
        for c in components
    )

    if not (has_cmc and has_x_cap):
        issues.append(
            DesignIssue(
                rule_id="FILTERING_004",
                category=DesignCategory.FILTERING,
                severity="warning",
                message="反激电源缺少EMI滤波器",
                suggestion="添加共模电感和X电容组成的EMI滤波器",
                auto_fixable=False,
            )
        )

    return issues


def fix_filtering(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复滤波问题"""
    components = circuit_data.get("components", [])

    if rule.id in ["FILTERING_001", "FILTERING_002", "FILTERING_003"]:
        power_type = _detect_power_supply_type(components)
        if power_type:
            new_components = _add_filter_components(components, power_type, rule.id)
            circuit_data["components"] = new_components

    return circuit_data


def _add_filter_components(
    components: List[Dict], power_type: str, rule_id: str
) -> List[Dict]:
    """添加滤波元件"""
    config = POWER_SUPPLY_FILTER_CONFIGS.get(power_type)
    if not config:
        return components

    max_id = max(
        (int(c.get("id", "comp-0").split("-")[1]) for c in components), default=0
    )
    new_components = []

    if rule_id == "FILTERING_001" and "input_filter" in config:
        filter_stage = config["input_filter"]
        for comp in filter_stage.components:
            max_id += 1
            new_components.append(
                {
                    "id": f"comp-{max_id}",
                    "name": f"输入滤波{comp['type']}",
                    "model": comp.get("value", ""),
                    "package": comp.get("package", "0805"),
                    "quantity": 1,
                    "auto_added": True,
                    "added_reason": f"为{config.get('description', '电源')}添加输入滤波",
                }
            )

    elif rule_id == "FILTERING_002" and "output_filter" in config:
        filter_stage = config["output_filter"]
        for comp in filter_stage.components:
            max_id += 1
            new_components.append(
                {
                    "id": f"comp-{max_id}",
                    "name": f"输出滤波{comp['type']}",
                    "model": comp.get("value", ""),
                    "package": comp.get("package", "0805"),
                    "quantity": 1,
                    "auto_added": True,
                    "added_reason": f"为{config.get('description', '电源')}添加输出滤波",
                }
            )

    return components + new_components


def calculate_filter_components(
    cutoff_freq_hz: float,
    source_impedance_ohm: float,
    load_impedance_ohm: float,
    required_attenuation_db: float,
) -> Dict:
    """
    计算滤波器元件值

    Args:
        cutoff_freq_hz: 截止频率
        source_impedance_ohm: 源阻抗
        load_impedance_ohm: 负载阻抗
        required_attenuation_db: 所需衰减量 dB

    Returns:
        推荐的元件值
    """
    # 计算LC值
    # fc = 1 / (2 * pi * sqrt(L * C))

    # 选择阻抗比例
    r_ratio = math.sqrt(source_impedance_ohm * load_impedance_ohm)

    # 计算LC乘积
    lc_product = 1.0 / ((2 * math.pi * cutoff_freq_hz) ** 2)

    # 根据阻抗比例分配L和C
    l_value = r_ratio * math.sqrt(lc_product)
    c_value = math.sqrt(lc_product) / r_ratio

    return {
        "cutoff_frequency_hz": cutoff_freq_hz,
        "inductor_h": l_value,
        "capacitor_f": c_value,
        "inductor_uh": l_value * 1e6,
        "capacitor_uf": c_value * 1e6,
        "attenuation_per_decade_db": 40 if l_value > 0 and c_value > 0 else 20,
    }

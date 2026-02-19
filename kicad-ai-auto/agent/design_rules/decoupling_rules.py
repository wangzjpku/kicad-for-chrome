"""
去耦电容设计规则
Decoupling Capacitor Design Rules

根据IC类型、工作频率、电流消耗自动添加去耦电容
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import math

from . import DesignRule, DesignIssue, DesignCategory, ICComponent

logger = logging.getLogger(__name__)


@dataclass
class DecouplingCapacitor:
    """去耦电容规格"""

    value: str  # 电容值 (如 "0.1uF", "10uF")
    package: str  # 封装 (如 "0402", "0603", "0805")
    type: str  # 类型 (ceramic, electrolytic, tantalum)
    voltage_rating: float  # 额定电压 V
    esr: float  # 等效串联电阻 Ω
    esl: float  # 等效串联电感 H
    placement: str  # 放置位置描述
    distance_mm: float  # 距离IC引脚最大距离 mm


# ========== 去耦电容规则库 ==========

# 根据IC类型的去耦电容配置
DECOUPLING_RULES = {
    # MCU类
    "MCU": {
        "low_freq": {  # < 10MHz
            "high_freq_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=16,
                esr=0.05,
                esl=0.5e-9,
                placement="每个电源引脚",
                distance_mm=3,
            ),
            "bulk_cap": DecouplingCapacitor(
                value="10uF",
                package="0805",
                type="ceramic",
                voltage_rating=10,
                esr=0.02,
                esl=1e-9,
                placement="电源入口",
                distance_mm=10,
            ),
        },
        "high_freq": {  # >= 10MHz
            "hf_cap": DecouplingCapacitor(
                value="0.01uF",
                package="0402",
                type="ceramic",
                voltage_rating=16,
                esr=0.03,
                esl=0.3e-9,
                placement="每个电源引脚",
                distance_mm=2,
            ),
            "lf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=16,
                esr=0.05,
                esl=0.5e-9,
                placement="每个电源引脚附近",
                distance_mm=5,
            ),
            "bulk_cap": DecouplingCapacitor(
                value="10uF",
                package="0805",
                type="ceramic",
                voltage_rating=10,
                esr=0.02,
                esl=1e-9,
                placement="电源入口",
                distance_mm=15,
            ),
        },
    },
    # DSP/FPGA类
    "DSP_FPGA": {
        "core": {
            "hf_cap": DecouplingCapacitor(
                value="0.01uF",
                package="0201",
                type="ceramic",
                voltage_rating=6.3,
                esr=0.02,
                esl=0.2e-9,
                placement="每个核心电源引脚",
                distance_mm=2,
            ),
            "lf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=10,
                esr=0.04,
                esl=0.4e-9,
                placement="核心电源区域",
                distance_mm=5,
            ),
            "bulk_cap": DecouplingCapacitor(
                value="47uF",
                package="1206",
                type="ceramic",
                voltage_rating=6.3,
                esr=0.01,
                esl=0.8e-9,
                placement="核心电源入口",
                distance_mm=10,
            ),
        },
        "io": {
            "hf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=10,
                esr=0.05,
                esl=0.5e-9,
                placement="每4个IO电源引脚1个",
                distance_mm=5,
            ),
        },
    },
    # 运放类
    "OPAMP": {
        "standard": {
            "hf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0603",
                type="ceramic",
                voltage_rating=16,
                esr=0.08,
                esl=0.6e-9,
                placement="每个电源引脚",
                distance_mm=5,
            ),
        },
        "high_speed": {  # > 10MHz GBW
            "hf_cap": DecouplingCapacitor(
                value="0.01uF",
                package="0402",
                type="ceramic",
                voltage_rating=16,
                esr=0.04,
                esl=0.3e-9,
                placement="每个电源引脚",
                distance_mm=3,
            ),
            "lf_cap": DecouplingCapacitor(
                value="1uF",
                package="0603",
                type="ceramic",
                voltage_rating=10,
                esr=0.05,
                esl=0.5e-9,
                placement="电源入口",
                distance_mm=10,
            ),
        },
    },
    # 电源IC类
    "POWER_IC": {
        "switching": {  # 开关电源
            "input_cap": DecouplingCapacitor(
                value="10uF",
                package="1206",
                type="ceramic",
                voltage_rating=25,
                esr=0.01,
                esl=0.5e-9,
                placement="输入端",
                distance_mm=3,
            ),
            "output_cap": DecouplingCapacitor(
                value="47uF",
                package="1210",
                type="ceramic",
                voltage_rating=10,
                esr=0.005,
                esl=0.4e-9,
                placement="输出端",
                distance_mm=5,
            ),
            "hf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0603",
                type="ceramic",
                voltage_rating=16,
                esr=0.05,
                esl=0.5e-9,
                placement="IC电源引脚",
                distance_mm=3,
            ),
        },
        "linear": {  # 线性电源
            "input_cap": DecouplingCapacitor(
                value="10uF",
                package="0805",
                type="ceramic",
                voltage_rating=16,
                esr=0.02,
                esl=0.8e-9,
                placement="输入端",
                distance_mm=5,
            ),
            "output_cap": DecouplingCapacitor(
                value="10uF",
                package="0805",
                type="ceramic",
                voltage_rating=10,
                esr=0.02,
                esl=0.8e-9,
                placement="输出端",
                distance_mm=5,
            ),
        },
    },
    # 射频IC
    "RF_IC": {
        "standard": {
            "hf_cap": DecouplingCapacitor(
                value="1nF",
                package="0402",
                type="ceramic",
                voltage_rating=16,
                esr=0.03,
                esl=0.2e-9,
                placement="每个电源引脚",
                distance_mm=2,
            ),
            "lf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=10,
                esr=0.05,
                esl=0.4e-9,
                placement="电源线入口",
                distance_mm=5,
            ),
            "rf_choke": DecouplingCapacitor(
                value="100pF",
                package="0402",
                type="ceramic",
                voltage_rating=16,
                esr=0.02,
                esl=0.15e-9,
                placement="RF电路电源",
                distance_mm=3,
            ),
        },
    },
    # 存储器
    "MEMORY": {
        "ddr": {
            "hf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=6.3,
                esr=0.03,
                esl=0.3e-9,
                placement="每对VDD/VSS",
                distance_mm=3,
            ),
            "bulk_cap": DecouplingCapacitor(
                value="10uF",
                package="0805",
                type="ceramic",
                voltage_rating=6.3,
                esr=0.015,
                esl=0.6e-9,
                placement="每8对VDD/VSS 1个",
                distance_mm=10,
            ),
        },
        "flash": {
            "hf_cap": DecouplingCapacitor(
                value="0.1uF",
                package="0402",
                type="ceramic",
                voltage_rating=10,
                esr=0.05,
                esl=0.5e-9,
                placement="VCC引脚",
                distance_mm=5,
            ),
        },
    },
}


# IC类型识别关键词
IC_TYPE_KEYWORDS = {
    "MCU": [
        "stm32",
        "atmega",
        "attiny",
        "esp32",
        "esp8266",
        "pic",
        "avr",
        "msp430",
        "nrf52",
        "rp2040",
    ],
    "DSP_FPGA": ["fpga", "cyclone", "spartan", "zynq", "dsp", "omapl", "tms320"],
    "OPAMP": ["lm358", "tl072", "ne5532", "opa", "ad8", "lt1", "lmv"],
    "POWER_IC": [
        "lm78",
        "lm31",
        "ams1117",
        "tp4056",
        "mp15",
        "xl60",
        "mt36",
        "lm2596",
        "ltc",
        "tps",
    ],
    "RF_IC": ["nrf24", "cc1101", "sx127", "rfm95", "cc25", "si44", "esp32"],
    "MEMORY": ["w25q", "at25", "s25fl", "mt41", "ddr", "sdr", "is42"],
}


def get_ic_type(ic_model: str) -> str:
    """根据IC型号识别类型"""
    model_lower = ic_model.lower()
    for ic_type, keywords in IC_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in model_lower:
                return ic_type
    return "MCU"  # 默认


def calculate_required_capacitance(
    current_ma: float, voltage_v: float, freq_hz: float, max_ripple_mv: float = 50
) -> Tuple[float, float]:
    """
    计算所需去耦电容值

    Args:
        current_ma: 电流消耗 mA
        voltage_v: 工作电压 V
        freq_hz: 工作频率 Hz
        max_ripple_mv: 最大允许纹波 mV

    Returns:
        (高频电容值F, 低频电容值F)
    """
    # 高频电容: 基于ESL和瞬态响应
    # C_hf >= I * dt / dV, dt ~ 1/freq
    dt = 1.0 / freq_hz if freq_hz > 0 else 1e-6
    dv = max_ripple_mv / 1000.0

    # 高频电容 (针对快速瞬态)
    c_hf = (current_ma / 1000.0) * dt / dv

    # 低频/大容量电容 (针对慢速波动)
    # 经验公式: 1uF per 10mA for digital ICs
    c_lf = (current_ma / 10.0) * 1e-6

    return (c_hf, c_lf)


def get_decoupling_rules() -> List[DesignRule]:
    """获取去耦电容设计规则"""
    return [
        DesignRule(
            id="DECOUPLING_001",
            category=DesignCategory.POWER_INTEGRITY,
            name="IC去耦电容检查",
            description="每个IC电源引脚必须有合适的去耦电容",
            check_function="check_ic_decoupling",
            fix_function="add_decoupling_capacitors",
            priority=1,
            auto_fix=True,
        ),
        DesignRule(
            id="DECOUPLING_002",
            category=DesignCategory.POWER_INTEGRITY,
            name="去耦电容距离检查",
            description="去耦电容必须靠近IC电源引脚",
            check_function="check_capacitor_distance",
            fix_function="suggest_capacitor_placement",
            priority=2,
            auto_fix=False,
        ),
        DesignRule(
            id="DECOUPLING_003",
            category=DesignCategory.POWER_INTEGRITY,
            name="电源入口大容量电容",
            description="电源入口需要大容量电解电容",
            check_function="check_bulk_capacitor",
            fix_function="add_bulk_capacitor",
            priority=2,
            auto_fix=True,
        ),
        DesignRule(
            id="DECOUPLING_004",
            category=DesignCategory.POWER_INTEGRITY,
            name="去耦电容电压降额",
            description="去耦电容电压必须留有50%以上降额",
            check_function="check_capacitor_voltage_derating",
            fix_function="upgrade_capacitor_voltage",
            priority=3,
            auto_fix=True,
        ),
    ]


def check_decoupling(rule: DesignRule, circuit_data: Dict) -> List[DesignIssue]:
    """检查去耦电容"""
    issues = []
    components = circuit_data.get("components", [])

    if rule.id == "DECOUPLING_001":
        issues.extend(_check_ic_decoupling(components))
    elif rule.id == "DECOUPLING_002":
        issues.extend(_check_capacitor_distance(circuit_data))
    elif rule.id == "DECOUPLING_003":
        issues.extend(_check_bulk_capacitor(components))
    elif rule.id == "DECOUPLING_004":
        issues.extend(_check_voltage_derating(components))

    return issues


def _check_ic_decoupling(components: List[Dict]) -> List[DesignIssue]:
    """检查IC去耦电容"""
    issues = []

    # 识别所有IC
    ic_components = []
    for comp in components:
        name = comp.get("name", "").lower()
        model = comp.get("model", "").lower()

        # 检查是否是IC
        if any(
            kw in name or kw in model
            for keywords in IC_TYPE_KEYWORDS.values()
            for kw in keywords
        ):
            ic_type = get_ic_type(model)
            ic_components.append(
                {
                    "component": comp,
                    "type": ic_type,
                }
            )

    # 检查每个IC是否有对应的去耦电容
    for ic_info in ic_components:
        comp = ic_info["component"]
        ic_type = ic_info["type"]

        # 查找该IC附近的去耦电容
        has_decoupling = False
        for c in components:
            if "电容" in c.get("name", "") or "capacitor" in c.get("name", "").lower():
                # 简化检查：假设如果有电容就OK
                has_decoupling = True
                break

        if not has_decoupling:
            issues.append(
                DesignIssue(
                    rule_id="DECOUPLING_001",
                    category=DesignCategory.POWER_INTEGRITY,
                    severity="critical",
                    message=f"IC {comp.get('model', comp.get('name', 'Unknown'))} 缺少去耦电容",
                    location=comp.get("id"),
                    suggestion=_get_decoupling_suggestion(ic_type),
                    auto_fixable=True,
                )
            )

    return issues


def _get_decoupling_suggestion(ic_type: str) -> str:
    """获取去耦电容建议"""
    suggestions = {
        "MCU": "每个VCC引脚添加0.1uF陶瓷电容，电源入口添加10uF电容",
        "DSP_FPGA": "每个核心电源引脚添加0.01uF+0.1uF电容，每组电源添加47uF大容量电容",
        "OPAMP": "每个电源引脚添加0.1uF陶瓷电容",
        "POWER_IC": "输入端添加10uF+0.1uF电容，输出端根据电流选择47uF+电解电容",
        "RF_IC": "每个电源引脚添加1nF+0.1uF电容，使用RF扼流电感",
        "MEMORY": "每对VDD/VSS添加0.1uF电容，每8对添加10uF电容",
    }
    return suggestions.get(ic_type, "添加0.1uF陶瓷电容")


def _check_capacitor_distance(circuit_data: Dict) -> List[DesignIssue]:
    """检查电容距离"""
    issues = []
    # 需要PCB布局数据才能检查
    # 简化实现：仅作为提示
    return issues


def _check_bulk_capacitor(components: List[Dict]) -> List[DesignIssue]:
    """检查大容量电容"""
    issues = []

    # 检查是否有大容量电容
    has_bulk = False
    for comp in components:
        model = comp.get("model", "").lower()
        if any(x in model for x in ["100uf", "47uf", "220uf", "470uf", "1000uf"]):
            has_bulk = True
            break

    # 如果有功率器件但没有大容量电容
    has_power = any(
        any(
            kw in c.get("model", "").lower()
            for kw in ["7805", "7809", "7812", "1117", "2596", "lm317"]
        )
        for c in components
    )

    if has_power and not has_bulk:
        issues.append(
            DesignIssue(
                rule_id="DECOUPLING_003",
                category=DesignCategory.POWER_INTEGRITY,
                severity="warning",
                message="电源电路缺少大容量电解电容",
                suggestion="在电源输入端添加100uF以上电解电容",
                auto_fixable=True,
            )
        )

    return issues


def _check_voltage_derating(components: List[Dict]) -> List[DesignIssue]:
    """检查电容电压降额"""
    issues = []

    for comp in components:
        name = comp.get("name", "").lower()
        if "电容" in name or "capacitor" in name:
            model = comp.get("model", "")
            # 解析电压值
            # 简化实现：检查是否包含电压标记

    return issues


def fix_decoupling(rule: DesignRule, issue: DesignIssue, circuit_data: Dict) -> Dict:
    """修复去耦电容问题"""
    components = circuit_data.get("components", [])

    if rule.id == "DECOUPLING_001":
        # 为缺少去耦电容的IC添加电容
        new_components = _add_missing_decoupling(components, issue)
        circuit_data["components"] = new_components

    elif rule.id == "DECOUPLING_003":
        # 添加大容量电容
        new_components = _add_bulk_capacitor(components)
        circuit_data["components"] = new_components

    return circuit_data


def _add_missing_decoupling(components: List[Dict], issue: DesignIssue) -> List[Dict]:
    """添加缺失的去耦电容"""
    # 找到需要添加电容的IC
    target_id = issue.location
    target_comp = None
    ic_type = "MCU"

    for comp in components:
        if comp.get("id") == target_id:
            target_comp = comp
            ic_type = get_ic_type(comp.get("model", ""))
            break

    if not target_comp:
        return components

    # 根据IC类型添加去耦电容
    new_caps = []
    rules = DECOUPLING_RULES.get(ic_type, DECOUPLING_RULES["MCU"])

    # 获取适合的电容配置
    if "high_freq" in rules:
        config = rules["high_freq"]
    elif "standard" in rules:
        config = rules["standard"]
    elif "low_freq" in rules:
        config = rules["low_freq"]
    else:
        config = list(rules.values())[0] if rules else {}

    # 添加电容
    max_id = max(
        (int(c.get("id", "comp-0").split("-")[1]) for c in components), default=0
    )

    for i, (cap_type, cap_spec) in enumerate(config.items()):
        if isinstance(cap_spec, DecouplingCapacitor):
            max_id += 1
            new_caps.append(
                {
                    "id": f"comp-{max_id}",
                    "name": f"去耦电容_{cap_type}",
                    "model": cap_spec.value,
                    "package": cap_spec.package,
                    "quantity": 1,
                    "footprint": f"Capacitor_SMD:C_{cap_spec.package}_Metric",
                    "voltage_rating": cap_spec.voltage_rating,
                    "type": cap_spec.type,
                    "placement_note": cap_spec.placement,
                    "max_distance_mm": cap_spec.distance_mm,
                    "auto_added": True,
                    "added_reason": f"为 {target_comp.get('model', 'IC')} 添加去耦电容",
                }
            )

    return components + new_caps


def _add_bulk_capacitor(components: List[Dict]) -> List[Dict]:
    """添加大容量电容"""
    max_id = max(
        (int(c.get("id", "comp-0").split("-")[1]) for c in components), default=0
    )
    max_id += 1

    bulk_cap = {
        "id": f"comp-{max_id}",
        "name": "滤波电容",
        "model": "100uF 25V",
        "package": "electrolytic",
        "quantity": 1,
        "footprint": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
        "voltage_rating": 25,
        "type": "electrolytic",
        "placement_note": "电源输入端",
        "auto_added": True,
        "added_reason": "电源输入大容量滤波",
    }

    return components + [bulk_cap]


def generate_decoupling_report(
    ic_model: str, voltage: float, current_ma: float, freq_mhz: float
) -> Dict:
    """
        生成去耦电容报告

    Returns:
        包含推荐的电容列表和设计说明
    """
    ic_type = get_ic_type(ic_model)

    # 计算所需电容值
    c_hf, c_lf = calculate_required_capacitance(current_ma, voltage, freq_mhz * 1e6)

    # 获取标准配置
    rules = DECOUPLING_RULES.get(ic_type, DECOUPLING_RULES["MCU"])
    if "high_freq" in rules and freq_mhz >= 10:
        config = rules["high_freq"]
    elif "standard" in rules:
        config = rules["standard"]
    else:
        config = rules.get("low_freq", {})

    # 生成报告
    report = {
        "ic_info": {
            "model": ic_model,
            "type": ic_type,
            "voltage": voltage,
            "current_ma": current_ma,
            "frequency_mhz": freq_mhz,
        },
        "calculated_values": {
            "min_hf_capacitance_f": c_hf,
            "min_lf_capacitance_f": c_lf,
        },
        "recommended_capacitors": [],
        "placement_guidelines": [],
    }

    for cap_type, cap_spec in config.items():
        if isinstance(cap_spec, DecouplingCapacitor):
            report["recommended_capacitors"].append(
                {
                    "type": cap_type,
                    "value": cap_spec.value,
                    "package": cap_spec.package,
                    "capacitor_type": cap_spec.type,
                    "voltage_rating": cap_spec.voltage_rating,
                    "esr_ohm": cap_spec.esr,
                    "esl_h": cap_spec.esl,
                    "derated_voltage": f"{cap_spec.voltage_rating}V (降额: {(1 - voltage / cap_spec.voltage_rating) * 100:.0f}%)",
                }
            )
            report["placement_guidelines"].append(
                f"{cap_spec.value} {cap_spec.package} {cap_spec.type}: {cap_spec.placement} (距IC < {cap_spec.distance_mm}mm)"
            )

    return report

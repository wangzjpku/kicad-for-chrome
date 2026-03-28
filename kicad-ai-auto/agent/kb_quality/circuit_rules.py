# -*- coding: utf-8 -*-
"""
电路连接规则知识库

定义元件引脚之间的连接关系，支持功能驱动的自动连线。

规则类型:
1. 电源连接规则 - 定义电源流向
2. 信号连接规则 - 定义信号类型匹配
3. 拓扑连接规则 - 定义电路拓扑模式
4. 元件特定规则 - 特定元件的连接要求
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re


class ConnectionType(Enum):
    """连接类型"""
    POWER_FLOW = "power_flow"        # 电源流向
    SIGNAL_MATCH = "signal_match"    # 信号匹配
    TOPOLOGY = "topology"            # 拓扑连接
    DIRECT = "direct"                # 直接连接


class TopologyType(Enum):
    """电路拓扑类型"""
    SERIES = "series"                # 串联
    PARALLEL = "parallel"            # 并联
    CASCADE = "cascade"              # 级联
    BRIDGE = "bridge"                # 桥接
    FEEDBACK = "feedback"            # 反馈


@dataclass
class PinConnectionRule:
    """引脚连接规则"""
    source_pin_pattern: str          # 源引脚名称正则
    source_pin_types: List[str]      # 源引脚类型列表
    target_pin_pattern: str          # 目标引脚名称正则
    target_pin_types: List[str]      # 目标引脚类型列表
    net_name_template: str           # 网络名模板
    description: str = ""
    priority: int = 1                # 优先级，数字越小优先级越高


@dataclass
class ComponentConnectionRule:
    """元件间连接规则"""
    source_component: str            # 源元件类型/名称
    target_component: str            # 目标元件类型/名称
    connection_type: ConnectionType
    pin_rules: List[PinConnectionRule] = field(default_factory=list)
    topology: Optional[TopologyType] = None


@dataclass
class CircuitPattern:
    """电路模式"""
    name: str
    description: str
    components: List[str]            # 元件类型列表
    connections: List[Tuple[str, str, str]]  # (comp1_pin, comp2_pin, net_name)
    topology: TopologyType


# ─────────────────────────────────────────────────────────────
# 全局电源连接规则
# ─────────────────────────────────────────────────────────────

POWER_CONNECTION_RULES: List[PinConnectionRule] = [
    # 电源输入 -> 电源输入 (并联)
    PinConnectionRule(
        source_pin_pattern=r"VCC|VDD|VIN|\+5V|\+3V3|5V|3V3",
        source_pin_types=["power_in"],
        target_pin_pattern=r"VCC|VDD|VIN|V_BATT",
        target_pin_types=["power_in"],
        net_name_template="{VCC_NET}",
        description="电源并联连接",
        priority=1,
    ),
    # 电源输出 -> 电源输入 (级联)
    PinConnectionRule(
        source_pin_pattern=r"VOUT|VO|OUTPUT",
        source_pin_types=["power_out"],
        target_pin_pattern=r"VCC|VDD|VIN",
        target_pin_types=["power_in"],
        net_name_template="VOUT_{source_ref}",
        description="稳压器输出到下级输入",
        priority=1,
    ),
    # 电源输出 -> 电容正极
    PinConnectionRule(
        source_pin_pattern=r"VOUT|VO|OUTPUT",
        source_pin_types=["power_out"],
        target_pin_pattern=r"\+|1|POS",
        target_pin_types=["passive"],
        net_name_template="VOUT_{source_ref}",
        description="电源输出到滤波电容",
        priority=2,
    ),
    # VCC -> 电阻 (限流)
    PinConnectionRule(
        source_pin_pattern=r"VCC|VDD|\+5V|\+3V3",
        source_pin_types=["power_in", "power_out"],
        target_pin_pattern=r"1|A|ANODE|\+",
        target_pin_types=["passive"],
        net_name_template="{VCC_NET}",
        description="电源通过限流电阻",
        priority=3,
    ),
    # GND -> 电容负极/电阻/二极管阴极
    PinConnectionRule(
        source_pin_pattern=r"GND|VSS|GROUND",
        source_pin_types=["power_in", "gnd"],
        target_pin_pattern=r"2|-|NEG|K|CATHODE",
        target_pin_types=["passive"],
        net_name_template="GND",
        description="接地连接",
        priority=1,
    ),
]


# ─────────────────────────────────────────────────────────────
# 信号连接规则
# ─────────────────────────────────────────────────────────────

SIGNAL_CONNECTION_RULES: List[PinConnectionRule] = [
    # UART: TX -> RX
    PinConnectionRule(
        source_pin_pattern=r"TX|TXD|UART_TX|TX_\w+",
        source_pin_types=["output"],
        target_pin_pattern=r"RX|RXD|UART_RX|RX_\w+",
        target_pin_types=["input"],
        net_name_template="UART_TX_{source_ref}",
        description="UART发送端连接接收端",
        priority=1,
    ),
    # UART: RX -> TX (反向)
    PinConnectionRule(
        source_pin_pattern=r"RX|RXD|UART_RX",
        source_pin_types=["input"],
        target_pin_pattern=r"TX|TXD|UART_TX",
        target_pin_types=["output"],
        net_name_template="UART_RX_{source_ref}",
        description="UART接收端连接发送端",
        priority=1,
    ),
    # I2C: SDA <-> SDA (双向)
    PinConnectionRule(
        source_pin_pattern=r"SDA|SDA_\w+",
        source_pin_types=["bidirectional"],
        target_pin_pattern=r"SDA|SDA_\w+",
        target_pin_types=["bidirectional", "input", "output"],
        net_name_template="I2C_SDA",
        description="I2C数据线",
        priority=1,
    ),
    # I2C: SCL -> SCL (时钟)
    PinConnectionRule(
        source_pin_pattern=r"SCL|SCL_\w+",
        source_pin_types=["output", "bidirectional"],
        target_pin_pattern=r"SCL|SCL_\w+",
        target_pin_types=["input", "bidirectional"],
        net_name_template="I2C_SCL",
        description="I2C时钟线",
        priority=1,
    ),
    # SPI: MOSI -> MOSI
    PinConnectionRule(
        source_pin_pattern=r"MOSI|SDO|DO",
        source_pin_types=["output"],
        target_pin_pattern=r"MOSI|SDI|DI|SI",
        target_pin_types=["input"],
        net_name_template="SPI_MOSI",
        description="SPI主出从入",
        priority=1,
    ),
    # SPI: MISO -> MISO
    PinConnectionRule(
        source_pin_pattern=r"MISO|SDI",
        source_pin_types=["input"],
        target_pin_pattern=r"MISO|SDO",
        target_pin_types=["output"],
        net_name_template="SPI_MISO",
        description="SPI主入从出",
        priority=1,
    ),
    # SPI: SCK -> SCK
    PinConnectionRule(
        source_pin_pattern=r"SCK|SCLK|CLK",
        source_pin_types=["output"],
        target_pin_pattern=r"SCK|SCLK|CLK",
        target_pin_types=["input"],
        net_name_template="SPI_SCK",
        description="SPI时钟",
        priority=1,
    ),
    # SPI: CS/NSS -> CS
    PinConnectionRule(
        source_pin_pattern=r"CS|NSS|SS|CS_\w+",
        source_pin_types=["output"],
        target_pin_pattern=r"CS|NSS|SS",
        target_pin_types=["input"],
        net_name_template="SPI_CS_{target_ref}",
        description="SPI片选",
        priority=2,
    ),
    # PWM 输出
    PinConnectionRule(
        source_pin_pattern=r"PWM|PWM_\w+",
        source_pin_types=["output"],
        target_pin_pattern=r"IN|INPUT|PWM_IN",
        target_pin_types=["input"],
        net_name_template="PWM_{source_ref}",
        description="PWM信号",
        priority=2,
    ),
    # ADC 输入
    PinConnectionRule(
        source_pin_pattern=r"ADC|AIN|ADC_\w+",
        source_pin_types=["input"],
        target_pin_pattern=r"OUT|OUTPUT|SIG|SENSE",
        target_pin_types=["output"],
        net_name_template="ADC_{source_ref}",
        description="ADC输入信号",
        priority=2,
    ),
]


# ─────────────────────────────────────────────────────────────
# 元件特定连接规则
# ─────────────────────────────────────────────────────────────

COMPONENT_SPECIFIC_RULES: Dict[str, List[PinConnectionRule]] = {
    "LM7805": [
        PinConnectionRule(
            source_pin_pattern=r"VIN|INPUT",
            source_pin_types=["power_in"],
            target_pin_pattern=r"VCC|VDD|\+5V|\+3V3",
            target_pin_types=["power_in"],
            net_name_template="VIN_RAW",
            description="7805输入接电源",
        ),
        PinConnectionRule(
            source_pin_pattern=r"VOUT|OUTPUT",
            source_pin_types=["power_out"],
            target_pin_pattern=r"\+|1|VCC",
            target_pin_types=["passive", "power_in"],
            net_name_template="VOUT_5V",
            description="7805输出5V",
        ),
    ],
    "AMS1117": [
        PinConnectionRule(
            source_pin_pattern=r"VOUT|OUTPUT",
            source_pin_types=["power_out"],
            target_pin_pattern=r"\+|1|VCC",
            target_pin_types=["passive", "power_in"],
            net_name_template="VOUT_{chip_model}",
            description="AMS1117输出",
        ),
    ],
    "CH340": [
        PinConnectionRule(
            source_pin_pattern=r"TXD|TX",
            source_pin_types=["output"],
            target_pin_pattern=r"RX|RXD",
            target_pin_types=["input"],
            net_name_template="UART_TX_CH340",
            description="CH340 TX接MCU RX",
        ),
        PinConnectionRule(
            source_pin_pattern=r"RXD|RX",
            source_pin_types=["input"],
            target_pin_pattern=r"TX|TXD",
            target_pin_types=["output"],
            net_name_template="UART_RX_CH340",
            description="CH340 RX接MCU TX",
        ),
    ],
    "STM32F103": [
        PinConnectionRule(
            source_pin_pattern=r"OSC_IN|OSCIN",
            source_pin_types=["input"],
            target_pin_pattern=r"OUT|OUTPUT",
            target_pin_types=["output"],
            net_name_template="OSC_IN",
            description="晶振输入",
        ),
        PinConnectionRule(
            source_pin_pattern=r"OSC_OUT|OSCOUT",
            source_pin_types=["output"],
            target_pin_pattern=r"IN|INPUT",
            target_pin_types=["input"],
            net_name_template="OSC_OUT",
            description="晶振输出",
        ),
    ],
}


# ─────────────────────────────────────────────────────────────
# 电路模式定义
# ─────────────────────────────────────────────────────────────

CIRCUIT_PATTERNS: Dict[str, CircuitPattern] = {
    "rc_filter": CircuitPattern(
        name="rc_filter",
        description="RC低通滤波器",
        components=["resistor", "capacitor"],
        connections=[
            ("2", "1", "RC_FILTER"),  # R.2 -> C.1
        ],
        topology=TopologyType.SERIES,
    ),
    "r_led_series": CircuitPattern(
        name="r_led_series",
        description="电阻限流LED",
        components=["resistor", "LED"],
        connections=[
            ("2", "A", "R_LED"),  # R.2 -> LED.A
        ],
        topology=TopologyType.SERIES,
    ),
    "decoupling_cap": CircuitPattern(
        name="decoupling_cap",
        description="去耦电容",
        components=["capacitor"],
        connections=[
            ("1", "VCC", "VCC"),  # C.+ -> VCC
            ("2", "GND", "GND"),  # C.- -> GND
        ],
        topology=TopologyType.PARALLEL,
    ),
    "voltage_divider": CircuitPattern(
        name="voltage_divider",
        description="电阻分压器",
        components=["resistor", "resistor"],
        connections=[
            ("2", "1", "V_DIV_MID"),  # R1.2 -> R2.1
        ],
        topology=TopologyType.SERIES,
    ),
    "power_supply_chain": CircuitPattern(
        name="power_supply_chain",
        description="电源供电链",
        components=["regulator", "capacitor", "capacitor"],
        connections=[
            ("VOUT", "1", "VOUT_REG"),  # Reg.VOUT -> Cin.+
            ("VOUT", "1", "VOUT_REG"),  # Reg.VOUT -> Cout.+
        ],
        topology=TopologyType.CASCADE,
    ),
    "spi_bus": CircuitPattern(
        name="spi_bus",
        description="SPI总线",
        components=["mcu", "spi_device"],
        connections=[
            ("MOSI", "MOSI", "SPI_MOSI"),
            ("MISO", "MISO", "SPI_MISO"),
            ("SCK", "SCK", "SPI_SCK"),
            ("CS", "CS", "SPI_CS"),
        ],
        topology=TopologyType.BRIDGE,
    ),
    "i2c_bus": CircuitPattern(
        name="i2c_bus",
        description="I2C总线",
        components=["mcu", "i2c_device"],
        connections=[
            ("SDA", "SDA", "I2C_SDA"),
            ("SCL", "SCL", "I2C_SCL"),
        ],
        topology=TopologyType.BRIDGE,
    ),
    "uart_link": CircuitPattern(
        name="uart_link",
        description="UART连接",
        components=["device1", "device2"],
        connections=[
            ("TX", "RX", "UART_TX"),
            ("RX", "TX", "UART_RX"),
        ],
        topology=TopologyType.BRIDGE,
    ),
}


# ─────────────────────────────────────────────────────────────
# 连接规则引擎
# ─────────────────────────────────────────────────────────────

class ConnectionRuleEngine:
    """连接规则引擎"""

    def __init__(self):
        self.power_rules = POWER_CONNECTION_RULES
        self.signal_rules = SIGNAL_CONNECTION_RULES
        self.component_rules = COMPONENT_SPECIFIC_RULES
        self.patterns = CIRCUIT_PATTERNS

    def find_matching_rules(
        self,
        source_pin: Dict[str, Any],
        target_pin: Dict[str, Any],
        source_component: Optional[Dict] = None,
        target_component: Optional[Dict] = None,
    ) -> List[PinConnectionRule]:
        """
        查找匹配的连接规则

        Args:
            source_pin: 源引脚信息 {"name": str, "type": str}
            target_pin: 目标引脚信息 {"name": str, "type": str}
            source_component: 源元件信息 (可选)
            target_component: 目标元件信息 (可选)

        Returns:
            匹配的连接规则列表，按优先级排序
        """
        matches = []

        # 检查元件特定规则
        if source_component:
            comp_model = source_component.get("model", "").upper()
            for model_key, rules in self.component_rules.items():
                if model_key.upper() in comp_model:
                    for rule in rules:
                        if self._rule_matches(rule, source_pin, target_pin):
                            matches.append(rule)

        # 检查电源规则
        for rule in self.power_rules:
            if self._rule_matches(rule, source_pin, target_pin):
                matches.append(rule)

        # 检查信号规则
        for rule in self.signal_rules:
            if self._rule_matches(rule, source_pin, target_pin):
                matches.append(rule)

        # 按优先级排序
        matches.sort(key=lambda r: r.priority)

        return matches

    def _rule_matches(
        self,
        rule: PinConnectionRule,
        source_pin: Dict[str, Any],
        target_pin: Dict[str, Any],
    ) -> bool:
        """检查规则是否匹配"""
        source_name = source_pin.get("name", "")
        source_type = source_pin.get("type", "")
        target_name = target_pin.get("name", "")
        target_type = target_pin.get("type", "")

        # 检查源引脚
        name_match = bool(re.search(rule.source_pin_pattern, source_name, re.IGNORECASE))
        type_match = source_type in rule.source_pin_types

        if not (name_match and type_match):
            return False

        # 检查目标引脚
        name_match = bool(re.search(rule.target_pin_pattern, target_name, re.IGNORECASE))
        type_match = target_type in rule.target_pin_types

        return name_match and type_match

    def get_net_name(
        self,
        rule: PinConnectionRule,
        source_ref: str,
        target_ref: str,
        chip_model: str = "",
    ) -> str:
        """
        根据规则生成网络名

        Args:
            rule: 连接规则
            source_ref: 源元件参考编号
            target_ref: 目标元件参考编号
            chip_model: 芯片型号

        Returns:
            网络名
        """
        net_name = rule.net_name_template.format(
            source_ref=source_ref,
            target_ref=target_ref,
            chip_model=chip_model,
            VCC_NET="VCC",
        )
        return net_name

    def find_circuit_pattern(self, component_types: List[str]) -> Optional[CircuitPattern]:
        """
        根据元件类型查找电路模式

        Args:
            component_types: 元件类型列表

        Returns:
            匹配的电路模式，如果没有匹配则返回None
        """
        for pattern in self.patterns.values():
            if self._pattern_matches(pattern, component_types):
                return pattern
        return None

    def _pattern_matches(self, pattern: CircuitPattern, component_types: List[str]) -> bool:
        """检查电路模式是否匹配"""
        pattern_types = pattern.components
        if len(component_types) != len(pattern_types):
            return False

        # 检查所有必需类型是否存在
        for pt in pattern_types:
            if not any(pt in ct.lower() for ct in component_types):
                return False

        return True


# 全局规则引擎实例
_rule_engine: Optional[ConnectionRuleEngine] = None


def get_connection_rule_engine() -> ConnectionRuleEngine:
    """获取全局连接规则引擎实例"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = ConnectionRuleEngine()
    return _rule_engine


def check_pin_compatibility(
    pin1: Dict[str, Any],
    pin2: Dict[str, Any],
    comp1: Optional[Dict] = None,
    comp2: Optional[Dict] = None,
) -> Tuple[bool, Optional[str]]:
    """
    检查两个引脚是否兼容（可以连接）

    Args:
        pin1: 引脚1信息
        pin2: 引脚2信息
        comp1: 元件1信息 (可选)
        comp2: 元件2信息 (可选)

    Returns:
        (是否兼容, 建议网络名)
    """
    engine = get_connection_rule_engine()

    # 尝试双向匹配
    rules = engine.find_matching_rules(pin1, pin2, comp1, comp2)
    if rules:
        best_rule = rules[0]
        net_name = engine.get_net_name(
            best_rule,
            comp1.get("reference", "") if comp1 else "",
            comp2.get("reference", "") if comp2 else "",
            comp1.get("model", "") if comp1 else "",
        )
        return True, net_name

    # 反向匹配
    rules = engine.find_matching_rules(pin2, pin1, comp2, comp1)
    if rules:
        best_rule = rules[0]
        net_name = engine.get_net_name(
            best_rule,
            comp2.get("reference", "") if comp2 else "",
            comp1.get("reference", "") if comp1 else "",
            comp2.get("model", "") if comp2 else "",
        )
        return True, net_name

    return False, None


def suggest_connections(
    components: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    为元件列表建议连接

    Args:
        components: 元件列表，每个包含 pins 和 reference

    Returns:
        建议的连接列表
    """
    engine = get_connection_rule_engine()
    suggestions = []

    # 收集所有引脚
    all_pins = []
    for comp in components:
        for pin in comp.get("pins", []):
            all_pins.append({
                "comp": comp,
                "pin": pin,
            })

    # 检查所有引脚对
    for i, pin_info1 in enumerate(all_pins):
        for pin_info2 in all_pins[i + 1 :]:
            compatible, net_name = check_pin_compatibility(
                pin_info1["pin"],
                pin_info2["pin"],
                pin_info1["comp"],
                pin_info2["comp"],
            )
            if compatible:
                suggestions.append({
                    "from": f"{pin_info1['comp'].get('reference', '')}.{pin_info1['pin'].get('name', '')}",
                    "to": f"{pin_info2['comp'].get('reference', '')}.{pin_info2['pin'].get('name', '')}",
                    "net": net_name,
                })

    return suggestions

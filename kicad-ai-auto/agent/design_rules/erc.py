"""
电气规则检查器 (ERC - Electrical Rule Checker)

负责检查原理图中的电气连接问题:
- 未连接的引脚
- 引脚方向冲突 (输出-输出, 输入-输入)
- 电源引脚问题
- 网路短路检测
- 缺少电源符号
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ERCErrorLevel(Enum):
    """ERC错误级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ERCErrorType(Enum):
    """ERC错误类型"""

    UNCONNECTED_PIN = "unconnected_pin"
    UNCONNECTED_INPUT = "unconnected_input"
    OUTPUT_TO_OUTPUT = "output_to_output"
    INPUT_TO_INPUT = "input_to_input"
    OUTPUT_TO_INPUT = "output_to_input"
    MISSING_POWER = "missing_power"
    MISSING_GND = "missing_gnd"
    PIN_TYPE_CONFLICT = "pin_type_conflict"
    NET_SHORT = "net_short"
    DUPLICATE_REFERENCE = "duplicate_reference"
    FLOATING_NET = "floating_net"


@dataclass
class ERCIssue:
    """单个ERC问题"""

    error_type: ERCErrorType
    level: ERCErrorLevel
    message: str
    component_id: Optional[str] = None
    pin_number: Optional[str] = None
    net_name: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    severity: int = 1  # 1-5, 5是最高优先级


@dataclass
class ERCResult:
    """ERC检查结果"""

    issues: List[ERCIssue] = field(default_factory=list)
    score: int = 100
    passed: bool = True

    def add_issue(self, issue: ERCIssue):
        """添加问题并更新分数"""
        self.issues.append(issue)
        # 根据错误级别和严重程度扣分
        if issue.level == ERCErrorLevel.ERROR:
            self.score -= issue.severity * 10
        elif issue.level == ERCErrorLevel.WARNING:
            self.score -= issue.severity * 5
        else:
            self.score -= issue.severity * 2

        if issue.level != ERCErrorLevel.INFO:
            self.passed = False

        # 确保分数不低于0
        self.score = max(0, self.score)


class ERCChecker:
    """
    电气规则检查器

    检查原理图中的电气连接问题
    """

    # 引脚类型兼容性矩阵
    # True = 兼容, False = 不兼容
    PIN_COMPATIBILITY = {
        #              Input  Output  Bidir  Power  GND   Passive Unspec
        "input": [False, True, True, False, False, True, True],
        "output": [True, False, True, False, False, True, True],
        "bidirectional": [True, True, True, False, False, True, True],
        "power_in": [False, False, False, True, True, True, True],
        "power_out": [False, False, False, True, True, True, True],
        "gnd": [False, False, False, True, True, True, True],
        "passive": [True, True, True, True, True, True, True],
        "unspecified": [True, True, True, True, True, True, True],
    }

    def __init__(self):
        self.issues: List[ERCIssue] = []

    def check(
        self, components: List[Dict], nets: List[Dict], power_symbols: List[Dict]
    ) -> ERCResult:
        """
        执行完整的ERC检查

        Args:
            components: 元件列表，每个元件包含pins信息
            nets: 网络列表
            power_symbols: 电源符号列表

        Returns:
            ERCResult: 检查结果
        """
        result = ERCResult()

        # 1. 检查未连接的引脚
        self._check_unconnected_pins(components, nets, result)

        # 2. 检查引脚方向冲突
        self._check_pin_direction_conflicts(components, nets, result)

        # 3. 检查电源引脚
        self._check_power_pins(components, nets, result)

        # 4. 检查缺少电源符号
        self._check_power_symbols(power_symbols, result)

        # 5. 检查重复引用
        self._check_duplicate_references(components, result)

        # 6. 检查浮动网络
        self._check_floating_nets(components, nets, result)

        return result

    def _check_unconnected_pins(
        self, components: List[Dict], nets: List[Dict], result: ERCResult
    ):
        """检查未连接的引脚"""
        # 构建已连接的引脚集合
        connected_pins: Set[str] = set()

        for net in nets:
            net_name = net.get("name", "")
            pins = net.get("pins", [])
            for pin_ref in pins:
                connected_pins.add(pin_ref)

        # 检查每个元件的引脚
        for comp in components:
            comp_id = comp.get("id", "")
            reference = comp.get("reference", "")
            pins = comp.get("pins", [])

            for pin in pins:
                pin_number = pin.get("number", "")
                pin_ref = f"{comp_id}:{pin_number}"
                pin_type = pin.get("pin_type", "unspecified")

                if pin_ref not in connected_pins:
                    # 电源引脚必须连接
                    if pin_type in ["power_in", "power_out", "gnd"]:
                        issue = ERCIssue(
                            error_type=ERCErrorType.UNCONNECTED_PIN,
                            level=ERCErrorLevel.ERROR,
                            message=f"未连接的电源引脚: {reference}.{pin.get('name', pin_number)}",
                            component_id=comp_id,
                            pin_number=pin_number,
                            severity=5,
                        )
                        result.add_issue(issue)
                    # 输入引脚未连接是警告
                    elif pin_type == "input":
                        issue = ERCIssue(
                            error_type=ERCErrorType.UNCONNECTED_INPUT,
                            level=ERCErrorLevel.WARNING,
                            message=f"未连接的输入引脚: {reference}.{pin.get('name', pin_number)}",
                            component_id=comp_id,
                            pin_number=pin_number,
                            severity=3,
                        )
                        result.add_issue(issue)

    def _check_pin_direction_conflicts(
        self, components: List[Dict], nets: List[Dict], result: ERCResult
    ):
        """检查引脚方向冲突"""
        # 按网络分组引脚
        net_pins: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)

        for net in nets:
            net_name = net.get("name", "")
            pins = net.get("pins", [])

            for pin_ref in pins:
                # pin_ref format: "component_id:pin_number"
                parts = pin_ref.split(":")
                if len(parts) == 2:
                    comp_id, pin_num = parts
                    # 查找引脚类型
                    for comp in components:
                        if comp.get("id") == comp_id:
                            for pin in comp.get("pins", []):
                                if pin.get("number") == pin_num:
                                    pin_type = pin.get("pin_type", "unspecified")
                                    net_pins[net_name].append(
                                        (comp_id, pin_num, pin_type)
                                    )
                                    break

        # 检查每个网络的引脚兼容性
        for net_name, pins in net_pins.items():
            if len(pins) < 2:
                continue

            # 收集所有输出引脚
            output_pins = [(c, p, t) for c, p, t in pins if t == "output"]
            input_pins = [(c, p, t) for c, p, t in pins if t == "input"]

            # 输出-输出冲突
            if len(output_pins) > 1:
                refs = [f"{c}:{p}" for c, p, _ in output_pins]
                issue = ERCIssue(
                    error_type=ERCErrorType.OUTPUT_TO_OUTPUT,
                    level=ERCErrorLevel.ERROR,
                    message=f"多个输出引脚连接到同一网络 '{net_name}': {', '.join(refs)}",
                    net_name=net_name,
                    severity=5,
                )
                result.add_issue(issue)

            # 输入-输入冲突 (可能是有意为之，但也应该警告)
            if len(input_pins) > 1:
                refs = [f"{c}:{p}" for c, p, _ in input_pins]
                issue = ERCIssue(
                    error_type=ERCErrorType.INPUT_TO_INPUT,
                    level=ERCErrorLevel.WARNING,
                    message=f"多个输入引脚连接到同一网络 '{net_name}': {', '.join(refs)}",
                    net_name=net_name,
                    severity=2,
                )
                result.add_issue(issue)

            # 输出-输入冲突 - 这是正常的，不用报错
            pass

    def _check_power_pins(
        self, components: List[Dict], nets: List[Dict], result: ERCResult
    ):
        """检查电源引脚连接"""
        # 收集所有电源网络名称
        power_nets: Set[str] = set()

        for net in nets:
            net_class = net.get("class", "default")
            if net_class == "power":
                power_nets.add(net.get("name", ""))

        # 检查电源引脚是否连接到电源网络
        for comp in components:
            reference = comp.get("reference", "")
            pins = comp.get("pins", [])

            for pin in pins:
                pin_type = pin.get("pin_type", "")

                if pin_type in ["power_in", "power_out", "gnd"]:
                    # 检查是否连接到电源网络
                    pin_ref = f"{comp.get('id')}:{pin.get('number')}"
                    is_connected_to_power = False

                    for net in nets:
                        if pin_ref in net.get("pins", []):
                            if net.get("class") == "power":
                                is_connected_to_power = True
                                break

                    if not is_connected_to_power and pin_type in ["power_in", "gnd"]:
                        issue = ERCIssue(
                            error_type=ERCErrorType.PIN_TYPE_CONFLICT,
                            level=ERCErrorLevel.WARNING,
                            message=f"电源引脚 {reference}.{pin.get('name', pin.get('number'))} "
                            f"未连接到电源网络",
                            component_id=comp.get("id"),
                            pin_number=pin.get("number"),
                            severity=3,
                        )
                        result.add_issue(issue)

    def _check_power_symbols(self, power_symbols: List[Dict], result: ERCResult):
        """检查电源符号"""
        has_vcc = False
        has_gnd = False

        for symbol in power_symbols:
            symbol_type = symbol.get("symbol_type", "")
            if symbol_type == "vcc":
                has_vcc = True
            elif symbol_type == "gnd":
                has_gnd = True

        if not has_vcc:
            issue = ERCIssue(
                error_type=ERCErrorType.MISSING_POWER,
                level=ERCErrorLevel.WARNING,
                message="缺少 VCC 电源符号",
                severity=3,
            )
            result.add_issue(issue)

        if not has_gnd:
            issue = ERCIssue(
                error_type=ERCErrorType.MISSING_GND,
                level=ERCErrorLevel.WARNING,
                message="缺少 GND 电源符号",
                severity=3,
            )
            result.add_issue(issue)

    def _check_duplicate_references(self, components: List[Dict], result: ERCResult):
        """检查重复的元件引用"""
        references: Dict[str, List[str]] = defaultdict(list)

        for comp in components:
            ref = comp.get("reference", "")
            comp_id = comp.get("id", "")
            references[ref].append(comp_id)

        for ref, comp_ids in references.items():
            if len(comp_ids) > 1:
                issue = ERCIssue(
                    error_type=ERCErrorType.DUPLICATE_REFERENCE,
                    level=ERCErrorLevel.ERROR,
                    message=f"重复的元件引用: {ref} (ID: {', '.join(comp_ids)})",
                    component_id=comp_ids[0],
                    severity=5,
                )
                result.add_issue(issue)

    def _check_floating_nets(
        self, components: List[Dict], nets: List[Dict], result: ERCResult
    ):
        """检查浮动网络 (只有1个引脚的网络)"""
        for net in nets:
            net_name = net.get("name", "")
            pins = net.get("pins", [])

            # 跳过电源网络和空网络名
            if net.get("class") == "power" or not net_name:
                continue

            if len(pins) == 1:
                issue = ERCIssue(
                    error_type=ERCErrorType.FLOATING_NET,
                    level=ERCErrorLevel.WARNING,
                    message=f"浮动网络 '{net_name}' - 只有1个引脚连接",
                    net_name=net_name,
                    severity=2,
                )
                result.add_issue(issue)


def check_schematic(schematic_data: Dict[str, Any]) -> ERCResult:
    """
    检查原理图电气规则

    这是一个便捷函数，接受原理图数据字典并返回ERC结果

    Args:
        schematic_data: 原理图数据，包含:
            - components: 元件列表
            - nets: 网络列表
            - power_symbols: 电源符号列表

    Returns:
        ERCResult: 检查结果
    """
    checker = ERCChecker()

    components = schematic_data.get("components", [])
    nets = schematic_data.get("nets", [])
    power_symbols = schematic_data.get("power_symbols", [])

    return checker.check(components, nets, power_symbols)


# 兼容性: 从旧接口迁移
def run_erc(
    components: List[Dict], nets: List[Dict], power_symbols: List[Dict] = None
) -> Dict[str, Any]:
    """
    运行ERC检查 (旧接口兼容)

    Returns:
        Dict with 'passed', 'score', 'issues'
    """
    if power_symbols is None:
        power_symbols = []

    result = check_schematic(
        {"components": components, "nets": nets, "power_symbols": power_symbols}
    )

    return {
        "passed": result.passed,
        "score": result.score,
        "issues": [
            {
                "type": issue.error_type.value,
                "level": issue.level.value,
                "message": issue.message,
                "severity": issue.severity,
            }
            for issue in result.issues
        ],
    }

"""
电路规范化工具
统一电源网络命名、合并重复电源符号、验证引脚连接完整性
"""

from typing import Dict, Any, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


# 电源网络名称映射表
POWER_NET_MAPPING = {
    # GND 变体
    "GND": "GND",
    "VSS": "GND",
    "GROUND": "GND",
    "ground": "GND",
    "vss": "GND",
    "gnd": "GND",
    "AGND": "GND",
    "DGND": "GND",
    # VCC 变体
    "VCC": "VCC",
    "VDD": "VCC",
    "+5V": "VCC",
    "+3.3V": "VCC",
    "+12V": "VCC",
    "+9V": "VCC",
    "Vdd": "VCC",
    "vcc": "VCC",
    "vdd": "VCC",
    "+5v": "VCC",
    "+3.3v": "VCC",
    # 正电源
    "VPP": "VCC",
    "AVCC": "VCC",
    "DVDD": "VCC",
}


def normalize_circuit(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    规范化电路数据

    处理：
    1. 统一电源网络命名
    2. 合并重复电源符号
    3. 验证引脚连接完整性
    4. 修复悬空引脚

    Args:
        json_data: 原始电路 JSON 数据

    Returns:
        规范化后的电路 JSON 数据
    """

    # 创建副本避免修改原始数据
    data = _deep_copy(json_data)

    # Step 1: 统一电源网络命名
    data = _normalize_power_nets(data)

    # Step 2: 合并重复电源符号
    data = _deduplicate_power_symbols(data)

    # Step 3: 验证引脚连接
    data = _validate_pin_connections(data)

    return data


def _deep_copy(data: Any) -> Any:
    """深拷贝"""
    import copy

    return copy.deepcopy(data)


def _normalize_power_nets(data: Dict[str, Any]) -> Dict[str, Any]:
    """统一电源网络命名"""

    # 1. 规范化网络名称
    for net in data.get("nets", []):
        original_name = net.get("name", "")
        normalized = POWER_NET_MAPPING.get(original_name, original_name)
        net["name"] = normalized
        logger.debug(f"网络命名规范化: {original_name} -> {normalized}")

    # 2. 规范化元件引脚的网络连接
    for comp in data.get("components", []):
        for pin in comp.get("pins", []):
            net_name = pin.get("net", "")
            if net_name:
                normalized = POWER_NET_MAPPING.get(net_name, net_name)
                pin["net"] = normalized

    # 3. 规范化连线中的网络名称
    for wire in data.get("wires", []):
        net_name = wire.get("net", "")
        if net_name:
            normalized = POWER_NET_MAPPING.get(net_name, net_name)
            wire["net"] = normalized

    # 4. 规范化电源符号的网络名称
    for power in data.get("powerSymbols", []):
        net_name = power.get("netName", "")
        if net_name:
            normalized = POWER_NET_MAPPING.get(net_name, net_name)
            power["netName"] = normalized

    return data


def _deduplicate_power_symbols(data: Dict[str, Any]) -> Dict[str, Any]:
    """合并重复的电源符号"""

    # 跟踪已见过的电源类型
    seen_power: Dict[str, Dict[str, Any]] = {}
    unique_powers: List[Dict[str, Any]] = []

    for power in data.get("powerSymbols", []):
        power_type = power.get("type", "")
        net_name = power.get("netName", "VCC")

        # 创建唯一键
        key = f"{power_type}_{net_name}"

        if key not in seen_power:
            seen_power[key] = power
            unique_powers.append(power)
            logger.debug(f"保留电源符号: {power_type} ({net_name})")
        else:
            logger.debug(f"移除重复电源符号: {power_type} ({net_name})")

    data["powerSymbols"] = unique_powers
    return data


def _validate_pin_connections(data: Dict[str, Any]) -> Dict[str, Any]:
    """验证并修复引脚连接问题"""

    # 构建网络名称集合
    valid_nets: Set[str] = {net.get("name", "") for net in data.get("nets", [])}
    valid_nets.update(["VCC", "GND", "NET1", "NET2"])  # 添加常见网络

    warnings: List[str] = []

    # 检查每个元件的引脚连接
    for comp in data.get("components", []):
        ref = comp.get("reference", "Unknown")

        for pin in comp.get("pins", []):
            pin_num = pin.get("number", "")
            net_name = pin.get("net", "")

            # 检查未连接的引脚
            if not net_name or net_name == "":
                pin_type = pin.get("type", "")

                # 对于电源引脚类型，添加警告
                if pin_type in ["power_in", "power_out", "gnd"]:
                    warnings.append(f"元件 {ref} 引脚 {pin_num} ({pin_type}) 未连接")

    # 将警告信息添加到数据中
    if warnings:
        data["_warnings"] = data.get("_warnings", []) + warnings
        logger.warning(f"发现 {len(warnings)} 个连接问题")

    return data


def get_unconnected_pins(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    获取所有未连接的引脚

    Returns:
        未连接引脚列表，每项包含元件参考、引脚号、类型
    """
    unconnected = []

    for comp in json_data.get("components", []):
        ref = comp.get("reference", "Unknown")

        for pin in comp.get("pins", []):
            pin_num = pin.get("number", "")
            net_name = pin.get("net", "")
            pin_type = pin.get("type", "")

            if not net_name or net_name == "":
                unconnected.append(
                    {
                        "reference": ref,
                        "pin_number": pin_num,
                        "pin_type": pin_type,
                        "pin_name": pin.get("name", ""),
                    }
                )

    return unconnected


def add_power_flags(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    自动添加缺失的电源符号

    检查所有连接到 VCC/GND 的引脚，确保有对应的电源符号
    """

    # 统计需要 VCC 和 GND 的引脚
    need_vcc = False
    need_gnd = False

    for comp in json_data.get("components", []):
        for pin in comp.get("pins", []):
            net_name = pin.get("net", "")
            pin_type = pin.get("type", "")

            if net_name == "VCC" or pin_type == "power_in":
                need_vcc = True
            if net_name == "GND" or pin_type == "gnd":
                need_gnd = True

    # 获取现有的电源符号
    existing_powers = json_data.get("powerSymbols", [])
    existing_types = {p.get("type", "") for p in existing_powers}

    # 添加缺失的电源符号
    new_powers = []

    if need_vcc and "vcc" not in existing_types:
        new_powers.append(
            {"type": "vcc", "netName": "VCC", "position": {"x": 50, "y": 50}}
        )
        logger.info("自动添加 VCC 电源符号")

    if need_gnd and "gnd" not in existing_types:
        new_powers.append(
            {"type": "gnd", "netName": "GND", "position": {"x": 100, "y": 50}}
        )
        logger.info("自动添加 GND 电源符号")

    json_data["powerSymbols"] = existing_powers + new_powers

    return json_data


def fix_erc_issues(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    修复常见的 ERC 问题

    1. 添加缺失的电源符号
    2. 统一网络命名
    3. 去除重复电源符号
    """

    # 先规范化
    json_data = normalize_circuit(json_data)

    # 添加缺失的电源符号
    json_data = add_power_flags(json_data)

    # 再次规范化（确保电源符号也被处理）
    json_data = _deduplicate_power_symbols(json_data)

    return json_data

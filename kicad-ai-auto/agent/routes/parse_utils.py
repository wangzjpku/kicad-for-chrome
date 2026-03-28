"""
AI路由解析工具函数
从用户消息中解析出操作意图和参数
"""

import re
from typing import Optional, Dict, Any, Tuple


def parse_reference(message: str) -> Optional[str]:
    """从消息中解析元件引用号

    支持格式: R1, C3, U5, LED1, etc.

    Args:
        message: 用户消息

    Returns:
        元件引用号，如 'R1'，未找到返回 None
    """
    # 匹配常见元件引用格式
    patterns = [
        r"([A-Z]+[0-9]+)",  # R1, C3, U5 (without word boundary for Chinese text compatibility)
        r"元件[：:]?\s*([A-Z]+[0-9]+)",  # 元件:R1 or 元件R1
        r"删除([A-Z]+[0-9]+)",  # 删除R1
        r"修改([A-Z]+[0-9]+)",  # 修改R1
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def parse_position(message: str) -> Optional[Dict[str, float]]:
    """从消息中解析位置坐标

    支持格式: "(100, 200)", "100,200", "x=100 y=200"

    Args:
        message: 用户消息

    Returns:
        {'x': float, 'y': float}，未找到返回 None
    """
    # 尝试匹配 (x, y) 格式
    match = re.search(r"\((\d+)[,\s]+(\d+)\)", message)
    if match:
        return {"x": float(match.group(1)), "y": float(match.group(2))}

    # 尝试匹配 x=100 y=200 格式（支持各种空格格式）
    x_match = re.search(r"x\s*[=:]\s*(\d+\.?\d*)", message, re.IGNORECASE)
    y_match = re.search(r"y\s*[=:]\s*(\d+\.?\d*)", message, re.IGNORECASE)
    if x_match and y_match:
        return {"x": float(x_match.group(1)), "y": float(y_match.group(1))}

    # 尝试匹配 "150, 200" 格式（无x/y标签）
    match = re.search(r"(\d+\.?\d*)\s*[,\s]\s*(\d+\.?\d*)", message)
    if match:
        return {"x": float(match.group(1)), "y": float(match.group(2))}

    return None


def parse_value(message: str) -> Optional[str]:
    """从消息中解析元件值

    支持格式: "10k欧姆", "100uF", "5V"

    Args:
        message: 用户消息

    Returns:
        元件值字符串，未找到返回 None
    """
    # 匹配电阻值
    resistor_match = re.search(r"(\d+\.?\d*)[kKmM]?\s*[ΩoO]?", message)
    if resistor_match:
        return resistor_match.group(1) + "Ω"

    # 匹配电容值
    cap_match = re.search(r"(\d+\.?\d*)\s*[uU]n[pP]?[fF]?", message)
    if cap_match:
        return cap_match.group(1) + "uF"

    # 匹配电压值
    volt_match = re.search(r"(\d+\.?\d*)\s*[vV]", message)
    if volt_match:
        return volt_match.group(1) + "V"

    return None


def parse_package(message: str) -> Optional[str]:
    """从消息中解析封装类型

    支持格式: "0805", "SOT-23", "DIP-8"

    Args:
        message: 用户消息

    Returns:
        封装类型，未找到返回 None
    """
    # 使用更灵活的匹配，支持中英文混合（如"0805电阻"或"DIP-8芯片"）
    patterns = [
        r"(0\d{3})",  # 0402, 0603, 0805, 1206
        r"(SOT-23|SOT-223|SOT-89)",
        r"(DIP-\d+|SOIC-\d+)",
        r"(QFN-\d+|TSSOP-\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def parse_net_name(message: str) -> Optional[str]:
    """从消息中解析网络名称

    Args:
        message: 用户消息

    Returns:
        网络名称，未找到返回 None
    """
    patterns = [
        r"网络[：:]([A-Za-z0-9_]+)",
        r"Net[：:]([A-Za-z0-9_]+)",
        r"连接到([A-Za-z0-9_]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def parse_chip_model(message: str) -> Optional[str]:
    """从消息中解析芯片型号

    Args:
        message: 用户消息

    Returns:
        芯片型号，未找到返回 None
    """
    common_chips = [
        "STM32F103",
        "STM32F405",
        "STM32F401",
        "ATmega328",
        "ATtiny85",
        "ATtiny1614",
        "ESP32",
        "ESP8266",
        "AMS1117",
        "LM7805",
        "LM317",
        "CH340",
        "CP2102",
        "FT232",
        "NE555",
        "LM358",
    ]

    for chip in common_chips:
        if chip.lower() in message.lower():
            return chip

    return None


def detect_operation_type(message: str) -> str:
    """检测操作类型

    Args:
        message: 用户消息

    Returns:
        操作类型: 'add', 'delete', 'modify', 'move', 'connect', 'query'
    """
    message_lower = message.lower()

    if any(kw in message_lower for kw in ["添加", "加", "新增", "add", "create"]):
        return "add"
    elif any(kw in message_lower for kw in ["删除", "去掉", "remove", "delete", "del"]):
        return "delete"
    elif any(
        kw in message_lower for kw in ["修改", "改变", "modify", "change", "update"]
    ):
        return "modify"
    elif any(kw in message_lower for kw in ["移动", "移到", "move"]):
        return "move"
    elif any(kw in message_lower for kw in ["连接", "接线", "connect", "wire"]):
        return "connect"
    elif any(
        kw in message_lower for kw in ["查询", "查找", "找", "query", "find", "search"]
    ):
        return "query"

    return "unknown"


def detect_component_type(message: str) -> Optional[str]:
    """检测元件类型

    Args:
        message: 用户消息

    Returns:
        元件类型: 'resistor', 'capacitor', 'ic', 'led', 'connector', etc.
    """
    message_lower = message.lower()

    # 按优先级检查（更具体的关键词在前）
    # 使用单词边界匹配，避免单字符误匹配
    if re.search(r"\b(resistor|res)\b", message_lower) or "电阻" in message_lower:
        return "resistor"
    elif re.search(r"\b(capacitor|cap)\b", message_lower) or "电容" in message_lower:
        return "capacitor"
    elif (
        re.search(r"\b(ic|mcu)\b", message_lower)
        or "芯片" in message_lower
        or "单片机" in message_lower
    ):
        return "ic"
    elif "led" in message_lower or "发光" in message_lower or "灯" in message_lower:
        return "led"
    elif (
        re.search(r"\b(connector|conn)\b", message_lower)
        or "连接器" in message_lower
        or "接口" in message_lower
        or "usb" in message_lower
    ):
        return "connector"
    elif re.search(r"\b(diode)\b", message_lower) or "二极管" in message_lower:
        return "diode"
    elif re.search(r"\b(crystal|xtal)\b", message_lower) or "晶振" in message_lower:
        return "crystal"
    elif re.search(r"\b(inductor|ind)\b", message_lower) or "电感" in message_lower:
        return "inductor"

    return None

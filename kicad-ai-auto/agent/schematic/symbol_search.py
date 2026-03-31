"""
Symbol Search Engine - 符号搜索引擎

Phase 6: 提供原理图符号搜索功能

功能:
- 按名称、描述、封装搜索符号
- 支持模糊匹配
- 搜索结果缓存
- 按类别过滤

Author: Claude Code
Date: 2026-03-30
"""

import re
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SymbolCategory(Enum):
    """符号类别"""
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    CONNECTOR = "connector"
    IC = "ic"
    POWER = "power"
    GROUND = "ground"
    TRANSISTOR = "transistor"
    MOSFET = "mosfet"
    DIODE = "diode"
    LED = "led"
    SWITCH = "switch"
    SENSOR = "sensor"
    MCU = "mcu"
    INTERFACE = "interface"
    CRYSTAL = "crystal"
    RELAY = "relay"
    FUSE = "fuse"
    OTHER = "other"


@dataclass
class SymbolInfo:
    """符号信息"""
    name: str                    # 符号名称 (如 "STM32F103C8")
    library: str                  # 符号库 (如 "MCU_ST")
    description: str              # 描述
    keywords: List[str]           # 关键词
    package: str                  # 封装
    pin_count: int               # 引脚数
    category: SymbolCategory     # 类别
    datasheet: str = ""          # 数据手册 URL
    manufacturer: str = ""        # 制造商


@dataclass
class SearchResult:
    """搜索结果"""
    symbols: List[SymbolInfo]
    total: int
    page: int
    page_size: int
    query: str


@dataclass
class SearchFilters:
    """搜索过滤条件"""
    category: Optional[SymbolCategory] = None
    library: Optional[str] = None
    package: Optional[str] = None
    pin_count_min: Optional[int] = None
    pin_count_max: Optional[int] = None
    manufacturer: Optional[str] = None


# 预定义符号库 (示例，实际从 KiCad 库读取)
PREDEFINED_SYMBOLS: List[SymbolInfo] = [
    # 电阻
    SymbolInfo("R", "Device", "Resistor", ["resistor", "r"], "0402", 2, SymbolCategory.RESISTOR),
    SymbolInfo("R_POT", "Device", "Potentiometer", ["potentiometer", "variable resistor"], "POT", 3, SymbolCategory.RESISTOR),
    SymbolInfo("R_SMD", "Device", "SMD Resistor", ["smd", "resistor", "r"], "0805", 2, SymbolCategory.RESISTOR),

    # 电容
    SymbolInfo("C", "Device", "Capacitor", ["capacitor", "c"], "0402", 2, SymbolCategory.CAPACITOR),
    SymbolInfo("C_Polarized", "Device", "Polarized Capacitor", ["capacitor", "polarized", "electrolytic"], "CAP-POL", 2, SymbolCategory.CAPACITOR),
    SymbolInfo("C_SMD", "Device", "SMD Capacitor", ["smd", "capacitor", "c"], "0805", 2, SymbolCategory.CAPACITOR),

    # 电感
    SymbolInfo("L", "Device", "Inductor", ["inductor", "l"], "0805", 2, SymbolCategory.INDUCTOR),
    SymbolInfo("L_SMD", "Device", "SMD Inductor", ["smd", "inductor", "l"], "0806", 2, SymbolCategory.INDUCTOR),

    # 连接器
    SymbolInfo("USB_B", "Connector", "USB Type-B", ["usb", "connector", "type-b"], "USB-B", 4, SymbolCategory.CONNECTOR),
    SymbolInfo("USB_C", "Connector", "USB Type-C", ["usb", "connector", "type-c"], "USB-C", 24, SymbolCategory.CONNECTOR),
    SymbolInfo("JACK", "Connector", "DC Jack", ["dc", "jack", "power"], "DC-JACK", 3, SymbolCategory.CONNECTOR),
    SymbolInfo("PinHeader", "Connector", "Pin Header", ["pin", "header", "connector"], "1x4", 4, SymbolCategory.CONNECTOR),

    # IC - MCU
    SymbolInfo("STM32F103C8", "MCU_ST", "STM32F103C8T6 ARM Cortex-M3", ["stm32", "mcu", "arm", "cortex"], "LQFP-48", 48, SymbolCategory.MCU),
    SymbolInfo("STM32F401CC", "MCU_ST", "STM32F401CCU6 ARM Cortex-M4", ["stm32", "mcu", "arm", "cortex"], "UFQFPN-48", 48, SymbolCategory.MCU),
    SymbolInfo("ATMEGA328P", "MCU_Microchip", "ATmega328P AVR MCU", ["atmega", "avr", "mcu", "arduino"], "TQFP-32", 32, SymbolCategory.MCU),
    SymbolInfo("ESP32", "MCU_Espressif", "ESP32 WiFi+BT MCU", ["esp32", "wifi", "bluetooth", "mcu"], "QFN-48", 48, SymbolCategory.MCU),
    SymbolInfo("RP2040", "MCU_Raspberry", "Raspberry Pi RP2040", ["rp2040", "raspberry", "mcu", "pico"], "QFN-56", 56, SymbolCategory.MCU),
    SymbolInfo("CH340C", "Interface_USB", "USB to Serial CH340C", ["ch340", "usb", "serial", "uart"], "SOP-16", 16, SymbolCategory.INTERFACE),

    # IC - 接口
    SymbolInfo("MAX232", "Interface_USB", "RS232 Transceiver", ["max232", "rs232", "serial"], "SOIC-16", 16, SymbolCategory.INTERFACE),
    SymbolInfo("MAX485", "Interface_RS485", "RS485 Transceiver", ["max485", "rs485", "serial"], "SOIC-8", 8, SymbolCategory.INTERFACE),
    SymbolInfo("CP2102", "Interface_USB", "USB to UART Bridge", ["cp2102", "usb", "uart", "bridge"], "QFN-28", 28, SymbolCategory.INTERFACE),
    SymbolInfo("TPD4E001", "Interface_USB", "USB ESD Protection", ["esd", "tvs", "usb", "protection"], "SOT-23", 5, SymbolCategory.INTERFACE),

    # IC - 电源
    SymbolInfo("AMS1117-3.3", "Power", "3.3V LDO Regulator", ["ldo", "regulator", "3.3v", "power"], "SOT-223", 3, SymbolCategory.POWER),
    SymbolInfo("LM7805", "Power", "5V Linear Regulator", ["lm7805", "regulator", "5v", "power"], "TO-220", 3, SymbolCategory.POWER),
    SymbolInfo("LD1117", "Power", "Low Dropout Regulator", ["ld1117", "ldo", "regulator"], "SOT-223", 3, SymbolCategory.POWER),
    SymbolInfo("MT3608", "Power", "DC-DC Boost Converter", ["mt3608", "boost", "dc-dc", "power"], "SOT-23-6", 6, SymbolCategory.POWER),

    # 二极管
    SymbolInfo("D", "Device", "Diode", ["diode", "d", "pn junction"], "DO-35", 2, SymbolCategory.DIODE),
    SymbolInfo("D_Schottky", "Device", "Schottky Diode", ["schottky", "diode", "d"], "SOD-123", 2, SymbolCategory.DIODE),
    SymbolInfo("D_Zener", "Device", "Zener Diode", ["zener", "diode", "d"], "DO-35", 2, SymbolCategory.DIODE),
    SymbolInfo("LED", "Device", "LED", ["led", "light", "emitting diode"], "0805", 2, SymbolCategory.LED),
    SymbolInfo("LED_RGB", "Device", "RGB LED", ["rgb", "led", "light"], "5mm", 4, SymbolCategory.LED),

    # 晶体管
    SymbolInfo("Q_NPN", "Device", "NPN Transistor", ["npn", "transistor", "bjt"], "TO-92", 3, SymbolCategory.TRANSISTOR),
    SymbolInfo("Q_PNP", "Device", "PNP Transistor", ["pnp", "transistor", "bjt"], "TO-92", 3, SymbolCategory.TRANSISTOR),
    SymbolInfo("Q_NMOS", "Device", "N-Channel MOSFET", ["nmos", "mosfet", "fet"], "TO-92", 3, SymbolCategory.MOSFET),
    SymbolInfo("Q_PMOS", "Device", "P-Channel MOSFET", ["pmos", "mosfet", "fet"], "TO-92", 3, SymbolCategory.MOSFET),

    # 开关
    SymbolInfo("SW_Push", "Device", "Push Button", ["switch", "push", "button"], "SW_PUSH", 2, SymbolCategory.SWITCH),
    SymbolInfo("SW_Tact", "Device", "Tactile Switch", ["switch", "tactile", "button"], "SMD-6x6", 4, SymbolCategory.SWITCH),
    SymbolInfo("SW_Rotary", "Device", "Rotary Switch", ["switch", "rotary", "dip"], "DIP-6", 7, SymbolCategory.SWITCH),

    # 传感器
    SymbolInfo("DHT11", "Sensor", "Temperature & Humidity Sensor", ["dht11", "temperature", "humidity", "sensor"], "THT-4", 4, SymbolCategory.SENSOR),
    SymbolInfo("BMP280", "Sensor", "Barometric Pressure Sensor", ["bmp280", "pressure", "barometric", "sensor"], "LGA-8", 8, SymbolCategory.SENSOR),
    SymbolInfo("MPU6050", "Sensor", "6-Axis Accelerometer/Gyroscope", ["mpu6050", "imu", "accelerometer", "gyroscope"], "QFN-24", 24, SymbolCategory.SENSOR),

    # 晶振
    SymbolInfo("Crystal", "Device", "Crystal Oscillator", ["crystal", "oscillator", "xtal"], "HC-49", 2, SymbolCategory.CRYSTAL),
    SymbolInfo("Crystal_SMD", "Device", "SMD Crystal", ["crystal", "smd", "oscillator"], "3225", 2, SymbolCategory.CRYSTAL),

    # 其他
    SymbolInfo("GND", "Power", "Ground", ["gnd", "ground", "power"], "THT", 1, SymbolCategory.GROUND),
    SymbolInfo("PWR_FLAG", "Power", "Power Flag", ["power", "flag"], "THT", 1, SymbolCategory.POWER),
    SymbolInfo("Fuse", "Device", "Fuse", ["fuse", "protection"], "RUE", 2, SymbolCategory.FUSE),
    SymbolInfo("Relay", "Device", "Electromechanical Relay", ["relay", "switch"], "DIP-5", 5, SymbolCategory.RELAY),
]


class SymbolSearchEngine:
    """
    符号搜索引擎

    支持:
    - 模糊匹配
    - 关键词搜索
    - 类别过滤
    - 分页
    """

    def __init__(self, symbols: Optional[List[SymbolInfo]] = None):
        """
        Args:
            symbols: 符号列表 (默认使用预定义符号)
        """
        self.symbols = symbols or PREDEFINED_SYMBOLS
        self._build_index()

    def _build_index(self):
        """构建搜索索引"""
        self._name_index: Dict[str, List[int]] = {}  # name -> symbol indices
        self._keyword_index: Dict[str, List[int]] = {}  # keyword -> symbol indices
        self._category_index: Dict[SymbolCategory, List[int]] = {}  # category -> symbol indices

        for idx, symbol in enumerate(self.symbols):
            # 名称索引
            name_lower = symbol.name.lower()
            for i in range(len(name_lower)):
                prefix = name_lower[:i+1]
                if prefix not in self._name_index:
                    self._name_index[prefix] = []
                self._name_index[prefix].append(idx)

            # 关键词索引
            for keyword in symbol.keywords:
                kw_lower = keyword.lower()
                if kw_lower not in self._keyword_index:
                    self._keyword_index[kw_lower] = []
                self._keyword_index[kw_lower].append(idx)

            # 类别索引
            if symbol.category not in self._category_index:
                self._category_index[symbol.category] = []
            self._category_index[symbol.category].append(idx)

    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResult:
        """
        搜索符号

        Args:
            query: 搜索词
            filters: 过滤条件
            page: 页码 (从 1 开始)
            page_size: 每页数量

        Returns:
            SearchResult: 搜索结果
        """
        filters = filters or SearchFilters()
        query_lower = query.lower().strip()

        # 收集匹配的索引
        matched_indices: set = set()

        if query_lower:
            # 名称匹配
            for prefix, indices in self._name_index.items():
                if query_lower in prefix:
                    matched_indices.update(indices)

            # 关键词匹配
            for kw, indices in self._keyword_index.items():
                if query_lower in kw:
                    matched_indices.update(indices)

            # 描述匹配 (模糊)
            for idx, symbol in enumerate(self.symbols):
                if query_lower in symbol.description.lower():
                    matched_indices.add(idx)
        else:
            # 无搜索词，返回所有
            matched_indices = set(range(len(self.symbols)))

        # 应用过滤
        if filters.category:
            cat_indices = set(self._category_index.get(filters.category, []))
            matched_indices &= cat_indices

        if filters.library:
            lib_lower = filters.library.lower()
            matched_indices = {
                idx for idx in matched_indices
                if lib_lower in self.symbols[idx].library.lower()
            }

        if filters.package:
            pkg_lower = filters.package.lower()
            matched_indices = {
                idx for idx in matched_indices
                if pkg_lower in self.symbols[idx].package.lower()
            }

        if filters.pin_count_min is not None:
            matched_indices = {
                idx for idx in matched_indices
                if self.symbols[idx].pin_count >= filters.pin_count_min
            }

        if filters.pin_count_max is not None:
            matched_indices = {
                idx for idx in matched_indices
                if self.symbols[idx].pin_count <= filters.pin_count_max
            }

        # 转换为结果
        matched_list = sorted(list(matched_indices))
        total = len(matched_list)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_indices = matched_list[start:end]

        result_symbols = [self.symbols[idx] for idx in page_indices]

        return SearchResult(
            symbols=result_symbols,
            total=total,
            page=page,
            page_size=page_size,
            query=query,
        )

    def get_by_name(self, name: str) -> Optional[SymbolInfo]:
        """根据名称获取符号"""
        name_lower = name.lower()
        for symbol in self.symbols:
            if symbol.name.lower() == name_lower:
                return symbol
        return None

    def get_by_category(self, category: SymbolCategory) -> List[SymbolInfo]:
        """根据类别获取符号"""
        indices = self._category_index.get(category, [])
        return [self.symbols[idx] for idx in indices]

    def get_categories(self) -> List[SymbolCategory]:
        """获取所有类别"""
        return list(SymbolCategory)

    def get_libraries(self) -> List[str]:
        """获取所有符号库"""
        return sorted(set(symbol.library for symbol in self.symbols))


# 全局搜索引擎实例
_symbol_search_engine: Optional[SymbolSearchEngine] = None


def get_symbol_search_engine() -> SymbolSearchEngine:
    """获取符号搜索引擎单例"""
    global _symbol_search_engine
    if _symbol_search_engine is None:
        _symbol_search_engine = SymbolSearchEngine()
    return _symbol_search_engine


def search_symbols(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    便捷函数：搜索符号

    Args:
        query: 搜索词
        filters: 过滤条件
        page: 页码
        page_size: 每页数量

    Returns:
        Dict: 搜索结果
    """
    engine = get_symbol_search_engine()

    search_filters = None
    if filters:
        category = None
        if filters.get("category"):
            try:
                category = SymbolCategory(filters["category"])
            except ValueError:
                pass

        search_filters = SearchFilters(
            category=category,
            library=filters.get("library"),
            package=filters.get("package"),
            pin_count_min=filters.get("pin_count_min"),
            pin_count_max=filters.get("pin_count_max"),
            manufacturer=filters.get("manufacturer"),
        )

    result = engine.search(query, search_filters, page, page_size)

    return {
        "symbols": [
            {
                "name": s.name,
                "library": s.library,
                "description": s.description,
                "keywords": s.keywords,
                "package": s.package,
                "pin_count": s.pin_count,
                "category": s.category.value,
                "datasheet": s.datasheet,
                "manufacturer": s.manufacturer,
            }
            for s in result.symbols
        ],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "query": result.query,
    }

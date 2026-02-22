#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KiCad 符号库解析器 v1.0

功能：
1. 解析 .kicad_sym 文件格式
2. 提取符号图形数据（矩形、线、圆、多边形等）
3. 提取引脚信息（编号、名称、位置、方向）
4. 提供符号搜索接口
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 符号库根目录
SYMBOL_LIBS_ROOT = Path(__file__).parent.parent.parent / "kicad-symbols"


@dataclass
class SymbolPin:
    """符号引脚"""

    number: str
    name: str
    position: Dict[str, float]  # {x, y}
    length: float = 1.27
    direction: int = 0  # 角度，0=右，90=上，180=左，270=下
    pin_type: str = (
        "passive"  # passive, input, output, bidirectional, power_in, power_out
    )


@dataclass
class SymbolGraphic:
    """符号图形元素"""

    type: str  # rectangle, polyline, circle, arc, text
    points: List[Dict[str, float]] = field(default_factory=list)
    start: Optional[Dict[str, float]] = None
    end: Optional[Dict[str, float]] = None
    center: Optional[Dict[str, float]] = None
    radius: float = 0
    stroke_width: float = 0.254
    fill_type: str = "none"
    text: str = ""


@dataclass
class KiCadSymbol:
    """KiCad 符号"""

    library: str  # 库名 (如 Device)
    name: str  # 符号名 (如 R)
    full_name: str  # 完整名称 (如 Device:R)
    reference: str = ""  # 参考编号前缀 (如 R)
    value: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    footprint_filters: List[str] = field(default_factory=list)
    graphics: List[SymbolGraphic] = field(default_factory=list)
    pins: List[SymbolPin] = field(default_factory=list)
    unit_count: int = 1  # 单元数量


class SymbolLibParser:
    """KiCad 符号库解析器"""

    def __init__(self):
        self._libs_cache: Dict[str, Dict[str, KiCadSymbol]] = {}
        self._build_libs_cache()

    def _build_libs_cache(self):
        """构建符号库缓存"""
        if not SYMBOL_LIBS_ROOT.exists():
            logger.warning(f"符号库目录不存在: {SYMBOL_LIBS_ROOT}")
            return

        for lib_dir in SYMBOL_LIBS_ROOT.iterdir():
            if lib_dir.is_dir() and lib_dir.name.endswith(".kicad_symdir"):
                lib_name = lib_dir.name.replace(".kicad_symdir", "")
                self._libs_cache[lib_name] = {}

                for sym_file in lib_dir.glob("*.kicad_sym"):
                    try:
                        symbol = self._parse_symbol_file(sym_file, lib_name)
                        if symbol:
                            self._libs_cache[lib_name][symbol.name] = symbol
                    except Exception as e:
                        logger.debug(f"解析符号文件失败 {sym_file}: {e}")

        total_symbols = sum(len(lib) for lib in self._libs_cache.values())
        logger.info(
            f"已加载 {len(self._libs_cache)} 个符号库, 共 {total_symbols} 个符号"
        )

    def _parse_symbol_file(
        self, file_path: Path, lib_name: str
    ) -> Optional[KiCadSymbol]:
        """解析单个符号文件"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            symbol_name = file_path.stem

            # 提取属性
            reference = self._extract_property(content, "Reference") or symbol_name[0]
            value = self._extract_property(content, "Value") or symbol_name
            description = self._extract_property(content, "Description") or ""
            keywords = self._extract_property(content, "ki_keywords") or ""
            footprint_filters = self._extract_property(content, "ki_fp_filters") or ""

            # 解析图形元素
            graphics = self._parse_graphics(content)

            # 解析引脚
            pins = self._parse_pins(content)

            return KiCadSymbol(
                library=lib_name,
                name=symbol_name,
                full_name=f"{lib_name}:{symbol_name}",
                reference=reference,
                value=value,
                description=description,
                keywords=keywords.split() if keywords else [],
                footprint_filters=footprint_filters.split()
                if footprint_filters
                else [],
                graphics=graphics,
                pins=pins,
            )
        except Exception as e:
            logger.warning(f"解析符号文件失败 {file_path}: {e}")
            return None

    def _extract_property(self, content: str, prop_name: str) -> Optional[str]:
        """提取属性值"""
        pattern = rf'\(property\s+"{prop_name}"\s+"([^"]*)"'
        match = re.search(pattern, content)
        return match.group(1) if match else None

    def _parse_graphics(self, content: str) -> List[SymbolGraphic]:
        """解析图形元素"""
        graphics = []

        # 解析矩形
        rect_pattern = r"\(rectangle\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)"
        for match in re.finditer(rect_pattern, content):
            graphics.append(
                SymbolGraphic(
                    type="rectangle",
                    start={"x": float(match.group(1)), "y": float(match.group(2))},
                    end={"x": float(match.group(3)), "y": float(match.group(4))},
                )
            )

        # 解析多边形/折线
        poly_pattern = r"\(polyline\s+\(pts\s+((?:\s*\([-\d.]+\s+[-\d.]+\))+)\s*\)"
        for match in re.finditer(poly_pattern, content):
            pts_str = match.group(1)
            points = []
            pt_pattern = r"\(([-\d.]+)\s+([-\d.]+)\)"
            for pt_match in re.finditer(pt_pattern, pts_str):
                points.append(
                    {"x": float(pt_match.group(1)), "y": float(pt_match.group(2))}
                )
            if points:
                graphics.append(SymbolGraphic(type="polyline", points=points))

        # 解析圆
        circle_pattern = (
            r"\(circle\s+\(center\s+([-\d.]+)\s+([-\d.]+)\)\s+\(radius\s+([-\d.]+)\)"
        )
        for match in re.finditer(circle_pattern, content):
            graphics.append(
                SymbolGraphic(
                    type="circle",
                    center={"x": float(match.group(1)), "y": float(match.group(2))},
                    radius=float(match.group(3)),
                )
            )

        # 解析弧
        arc_pattern = r"\(arc\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(mid\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)"
        for match in re.finditer(arc_pattern, content):
            graphics.append(
                SymbolGraphic(
                    type="arc",
                    start={"x": float(match.group(1)), "y": float(match.group(2))},
                    end={"x": float(match.group(5)), "y": float(match.group(6))},
                    center={"x": float(match.group(3)), "y": float(match.group(4))},
                )
            )

        return graphics

    def _parse_pins(self, content: str) -> List[SymbolPin]:
        """解析引脚"""
        pins = []

        # 匹配引脚定义
        pin_pattern = r"\(pin\s+(\w+)\s+(?:line|tri_state)\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)\s+\(length\s+([-\d.]+)\)"
        for match in re.finditer(pin_pattern, content):
            pin_type = match.group(1)
            x = float(match.group(2))
            y = float(match.group(3))
            rotation = int(float(match.group(4)))
            length = float(match.group(5))

            # 在附近查找引脚编号和名称
            pin_end = match.end()
            remaining = content[pin_end : pin_end + 500]

            number_match = re.search(r'\(number\s+"([^"]+)"', remaining)
            name_match = re.search(r'\(name\s+"([^"]*)"', remaining)

            pin_number = number_match.group(1) if number_match else "?"
            pin_name = name_match.group(1) if name_match else ""

            pins.append(
                SymbolPin(
                    number=pin_number,
                    name=pin_name,
                    position={"x": x, "y": y},
                    length=length,
                    direction=rotation,
                    pin_type=pin_type,
                )
            )

        return pins

    def get_symbol(self, lib_name: str, symbol_name: str) -> Optional[KiCadSymbol]:
        """获取指定符号"""
        return self._libs_cache.get(lib_name, {}).get(symbol_name)

    def search_symbols(self, keyword: str, limit: int = 20) -> List[KiCadSymbol]:
        """搜索符号"""
        results = []
        keyword_lower = keyword.lower()

        for lib_name, symbols in self._libs_cache.items():
            for symbol in symbols.values():
                # 匹配名称
                if keyword_lower in symbol.name.lower():
                    results.append(symbol)
                # 匹配描述
                elif keyword_lower in symbol.description.lower():
                    results.append(symbol)
                # 匹配关键词
                elif any(keyword_lower in kw.lower() for kw in symbol.keywords):
                    results.append(symbol)

                if len(results) >= limit:
                    return results

        return results

    def find_symbol_for_component(
        self, component_name: str, component_model: str = ""
    ) -> Optional[KiCadSymbol]:
        """
        根据元件名称/型号查找合适的符号

        Args:
            component_name: 元件名称 (如 "电阻", "LED", "单片机")
            component_model: 元件型号 (如 "LM7805", "STM32F103")

        Returns:
            匹配的符号，如果没有匹配则返回默认符号
        """
        name_lower = component_name.lower()
        model_lower = component_model.lower() if component_model else ""

        # 元件名称到符号库的映射
        symbol_mappings = {
            # 电阻
            "电阻": ("Device", "R"),
            "resistor": ("Device", "R"),
            "res": ("Device", "R"),
            # 电容
            "电容": ("Device", "C"),
            "capacitor": ("Device", "C"),
            "cap": ("Device", "C"),
            "滤波电容": ("Device", "C_Polarized"),
            "电解电容": ("Device", "C_Polarized"),
            # 电感
            "电感": ("Device", "L"),
            "inductor": ("Device", "L"),
            # LED
            "led": ("Device", "LED"),
            "发光": ("Device", "LED"),
            "灯": ("Device", "LED"),
            # 二极管
            "二极管": ("Device", "D"),
            "diode": ("Device", "D"),
            # 晶振
            "晶振": ("Device", "Crystal"),
            "crystal": ("Device", "Crystal"),
            # 三极管/MOSFET
            "三极管": ("Device", "Q_NPN"),
            "mosfet": ("Device", "Q_NMOS"),
            "transistor": ("Device", "Q_NPN"),
            # 连接器
            "连接器": ("Connector", "Conn_01x02_Pin"),
            "接口": ("Connector", "Conn_01x02_Pin"),
            "usb": ("Connector", "USB_B_Micro"),
            # 开关
            "开关": ("Switch", "SW_SPST"),
            "按键": ("Switch", "SW_Push"),
            "button": ("Switch", "SW_Push"),
            # 电源
            "vcc": ("Power", "VCC"),
            "gnd": ("Power", "GND"),
            "电源": ("Power", "VCC"),
        }

        # 特定型号映射（按优先级排序，精确匹配在前）
        # 注意：KiCad符号库中AMS1117-5.0表示5V输出（不是5.0V）
        model_symbol_mappings = {
            "lm7805": ("Regulator_Linear", "LM7805_TO220"),
            "lm7812": ("Regulator_Linear", "LM7812_TO220"),
            "ams1117-5v": ("Regulator_Linear", "AMS1117-5.0"),
            "ams1117-5.0": ("Regulator_Linear", "AMS1117-5.0"),
            "ams1117-3.3": ("Regulator_Linear", "AMS1117-3.3"),
            "ams1117": ("Regulator_Linear", "AMS1117-3.3"),  # 默认3.3V
            "esp32": ("RF_Module", "ESP32-WROOM-32"),
            "esp8266": ("RF_Module", "ESP-12E"),
            "stm32f103": ("MCU_ST_STM32F1", "STM32F103C8Tx"),
            "atmega328": ("MCU_Microchip_ATmega", "ATmega328P-PU"),
            "attiny85": ("MCU_Microchip_ATtiny", "ATtiny85-20PU"),
            "ch340": ("Interface_USB", "CH340G"),
            "cp2102": ("Interface_USB", "CP2102"),
        }

        # 优先匹配型号
        for model_key, (lib, sym) in model_symbol_mappings.items():
            if model_key in model_lower:
                symbol = self.get_symbol(lib, sym)
                if symbol:
                    return symbol

        # 匹配元件名称
        for name_key, (lib, sym) in symbol_mappings.items():
            if name_key in name_lower:
                symbol = self.get_symbol(lib, sym)
                if symbol:
                    return symbol

        # 搜索符号库
        search_results = self.search_symbols(component_name, limit=5)
        if search_results:
            return search_results[0]

        # 返回默认符号 (通用IC)
        return (
            self.get_symbol("Device", "R")
            or list(self._libs_cache.get("Device", {}).values())[0]
            if self._libs_cache.get("Device")
            else None
        )

    def list_available_libraries(self) -> List[str]:
        """列出所有可用的符号库"""
        return list(self._libs_cache.keys())

    def get_library_symbols(self, lib_name: str) -> List[KiCadSymbol]:
        """获取指定库中的所有符号"""
        return list(self._libs_cache.get(lib_name, {}).values())


# 全局实例
_parser = None


def get_symbol_parser() -> SymbolLibParser:
    """获取全局符号解析器实例"""
    global _parser
    if _parser is None:
        _parser = SymbolLibParser()
    return _parser


def find_symbol(
    component_name: str, component_model: str = ""
) -> Optional[KiCadSymbol]:
    """便捷函数：查找符号"""
    return get_symbol_parser().find_symbol_for_component(
        component_name, component_model
    )


def symbol_to_dict(symbol: KiCadSymbol) -> Dict[str, Any]:
    """将符号转换为字典格式（用于API响应）"""
    return {
        "library": symbol.library,
        "name": symbol.name,
        "full_name": symbol.full_name,
        "reference": symbol.reference,
        "value": symbol.value,
        "description": symbol.description,
        "keywords": symbol.keywords,
        "footprint_filters": symbol.footprint_filters,
        "graphics": [
            {
                "type": g.type,
                "points": g.points,
                "start": g.start,
                "end": g.end,
                "center": g.center,
                "radius": g.radius,
                "stroke_width": g.stroke_width,
                "fill_type": g.fill_type,
            }
            for g in symbol.graphics
        ],
        "pins": [
            {
                "number": p.number,
                "name": p.name,
                "position": p.position,
                "length": p.length,
                "direction": p.direction,
                "pin_type": p.pin_type,
            }
            for p in symbol.pins
        ],
        "unit_count": symbol.unit_count,
    }


if __name__ == "__main__":
    # 测试
    parser = SymbolLibParser()

    print("=" * 60)
    print("KiCad 符号库解析器测试")
    print("=" * 60)

    # 列出可用库
    print(f"\n可用符号库: {len(parser.list_available_libraries())} 个")
    for lib in parser.list_available_libraries()[:10]:
        print(f"  - {lib}")

    # 搜索符号
    print("\n搜索 'LED':")
    results = parser.search_symbols("LED", limit=5)
    for sym in results:
        print(f"  {sym.full_name}: {sym.description}")

    # 查找元件符号
    print("\n查找元件符号:")
    test_cases = [
        ("电阻", ""),
        ("电容", ""),
        ("LED", ""),
        ("单片机", "STM32F103"),
        ("稳压芯片", "LM7805"),
    ]

    for name, model in test_cases:
        symbol = parser.find_symbol_for_component(name, model)
        if symbol:
            print(f"  {name} ({model}) -> {symbol.full_name}")
        else:
            print(f"  {name} ({model}) -> 未找到")

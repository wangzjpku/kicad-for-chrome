# -*- coding: utf-8 -*-
"""
Altium Designer 原理图解析器

解析 AD 导出的原理图 XML 文件，提取引件信息用于知识库数据校验和入库。
支持格式:
    - XML 格式 (.SchDoc, .SchLib 导出 XML)
    - OutJob 导出格式
    - Altium Library Compiler 导出
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedComponent:
    """解析出的元件"""

    designator: str      # 位号 (R1, C1, U1, etc.)
    comment: str         # 注释/值 (10k, 100nF, STM32F103, etc.)
    footprint: str       # 封装
    lib_ref: str         # 库中名称
    source_library: str   # 来源库
    pins: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedNet:
    """解析出的网络"""

    name: str
    wire_count: int = 0
    pins: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ParsedSchematic:
    """解析出的原理图"""

    filename: str
    components: List[ParsedComponent] = field(default_factory=list)
    nets: List[ParsedNet] = field(default_factory=list)
    sheet_size: str = ""
    errors: List[str] = field(default_factory=list)


class AltiumSchParser:
    """
    Altium Designer 原理图解析器。

    使用方法:
        parser = AltiumSchParser()
        result = parser.parse("path/to/design.SchDoc")
        print(f"Found {len(result.components)} components")
    """

    # Altium XML 命名空间
    NS = {
        "altium": "http://www.altium.com/studio/2006/schematic_xml",
        "sch": "http://www.altium.com/studio/2006/schematic_xml",
    }

    # AD 封装 → KiCad 封装完整路径映射
    FOOTPRINT_MAP: Dict[str, str] = {
        # 无源元件
        "0603": "Capacitor_SMD:C_0603_1608Metric",
        "0805": "Capacitor_SMD:C_0805_2012Metric",
        "1206": "Capacitor_SMD:C_1206_3216Metric",
        "0402": "Capacitor_SMD:C_0402_1005Metric",
        "R0603": "Resistor_SMD:R_0603_1608Metric",
        "R0805": "Resistor_SMD:R_0805_2012Metric",
        "R1206": "Resistor_SMD:R_1206_3216Metric",
        "CAP-0603": "Capacitor_SMD:C_0603_1608Metric",
        "CAP-0805": "Capacitor_SMD:C_0805_2012Metric",
        "RES-0603": "Resistor_SMD:R_0603_1608Metric",
        "RES-0805": "Resistor_SMD:R_0805_2012Metric",
        # IC 封装
        "SOP-8": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "SOP-16": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "TSSOP-28": "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm",
        "QFN-32": "Package_DFN:QFN-32_5x5mm_P0.5mm",
        "LQFP-48": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
        "LQFP-64": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
        "DIP-8": "Package_THT:DIP-8_W7.62mm",
        "DIP-14": "Package_THT:DIP-14_W7.62mm",
        "DIP-16": "Package_THT:DIP-16_W7.62mm",
        "DIP-28": "Package_THT:DIP-28_W7.62mm",
        "SOT-23": "Package_TO_SOT_SMD:SOT-23",
        "SOT-223": "Package_TO_SOT_SMD:SOT-223",
        "TO-92": "Package_TO_SOT_THT:TO-92",
        "BGA-64": "BGA-64_5x5mm_P0.8mm",
    }

    # AD 符号 → KiCad 符号库映射 (库名, 符号名)
    SYMBOL_MAP: Dict[str, tuple] = {
        # MCU
        "STM32F103C8T6": ("MCU_ST_STM32F1", "STM32F103C8Tx"),
        "STM32F103RCT6": ("MCU_ST_STM32F1", "STM32F103RCTx"),
        "STM32F401CCU6": ("MCU_ST_STM32F4", "STM32F401CCUx"),
        "STM32F405RGT6": ("MCU_ST_STM32F4", "STM32F405RGTx"),
        "STM32F407VGT6": ("MCU_ST_STM32F4", "STM32F407VGTx"),
        "ATmega328P": ("MCU_Microchip_ATmega", "ATmega328P-A"),
        "ATmega2560": ("MCU_Microchip_ATmega", "ATmega2560"),
        "ATtiny85": ("MCU_Microchip_ATtiny", "ATtiny85-20P"),
        # 无线模块
        "ESP8266": ("RF_Module", "ESP-WROOM-01"),
        "ESP32-WROOM-32": ("RF_Module", "ESP32-WROOM-32"),
        "ESP32-C3-WROOM-02": ("RF_Module", "ESP32-C3-WROOM-02"),
        "ESP32-S3-WROOM-1": ("RF_Module", "ESP32-S3-WROOM-1"),
        "ESP32-S3": ("MCU_Espressif", "ESP32-S3"),
        # USB接口
        "CH340G": ("Interface_USB", "CH340G"),
        "CH340C": ("Interface_USB", "CH340C"),
        "CH340E": ("Interface_USB", "CH340E"),
        "CP2102": ("Interface_USB", "CP2102N-Axx-xQFN20"),
        "FT232RL": ("Interface_USB", "FT232RL"),
        "USB2512": ("custom", "N/A"),
        # 线性稳压
        "AMS1117-3.3": ("Regulator_Linear", "AMS1117-3.3"),
        "AMS1117-5.0": ("Regulator_Linear", "AMS1117-5.0"),
        "LM7805": ("Regulator_Linear", "LM7805_TO220"),
        "LM317": ("Regulator_Linear", "LM317L_TO92"),
        "ME6211-3.3": ("Regulator_Linear", "ME6211C33M5"),
        # 运放
        "LM358": ("Amplifier_Signal", "LM358"),
        "LM358P": ("Amplifier_Operational", "LM358"),
        "LM324": ("Amplifier_Signal", "LM324"),
        "NE555": ("Timer", "NE555D"),
        # 存储器
        "W25Q128": ("Memory_Flash", "W25Q128JVE"),
        "W25Q32": ("Memory_Flash", "W25Q32JVSS"),
        "AT24C256": ("Memory_EEPROM", "CAT24C256"),
        # 接口芯片
        "MAX485": ("Interface_UART", "MAX485E"),
        "SP3485": ("custom", "N/A"),
        "ULN2803": ("Transistor_Array", "ULN2803A"),
        "74HC595": ("74xx", "74HC595"),
        "74HC165": ("74xx", "74HC165"),
        "CD4051": ("Analog_Switch", "CD4051B"),
        "CD4066": ("Analog_Switch", "CD4066BE"),
        "PCF8574": ("Interface_Expansion", "PCF8574T"),
        # 传感器
        "MAX31865": ("Sensor_Temperature", "MAX31865xAP"),
        "MPU6050": ("custom", "N/A"),
        "DHT22": ("custom", "N/A"),
        "BME280": ("custom", "N/A"),
        "DS18B20": ("Sensor_Temperature", "DS18B20"),
        "BMP280": ("Sensor_Pressure", "BMP280"),
        # 时钟
        "DS3231": ("RTC", "DS3231"),
        "DS1302": ("RTC", "DS1302"),
        # 电源管理
        "TP4056": ("Battery_Management", "TP4056-42-ESOP8"),
        "IP5306": ("custom", "N/A"),
        # 马达驱动
        "L298N": ("Driver_Motor", "L298"),
        "DRV8833": ("Driver_Motor", "DRV8833"),
        # 电流检测
        "ACS712": ("Sensor_Current", "ACS712xLCTR-05B"),
    }

    def __init__(self):
        self._sch_lib_map: Dict[str, Dict[str, str]] = {}

    def parse(self, filepath: str) -> ParsedSchematic:
        path = Path(filepath)
        if not path.exists():
            return ParsedSchematic(
                filename=str(filepath),
                errors=[f"File not found: {filepath}"],
            )

        result = ParsedSchematic(filename=str(filepath))

        try:
            tree = ET.parse(str(path))
            root = tree.getroot()
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            return result

        root_tag = root.tag.lower() if root.tag else ""

        if "schematic_document" in root_tag or "design" in root_tag:
            self._parse_ad_xml(root, result)
        elif "library" in root_tag:
            self._parse_schlib_xml(root, result)
        else:
            self._parse_generic_xml(root, result)

        logger.info(f"AltiumSchParser: {len(result.components)} components, "
                    f"{len(result.nets)} nets parsed from {path.name}")
        return result

    def parse_from_string(self, xml_content: str) -> ParsedSchematic:
        result = ParsedSchematic(filename="<string>")

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            return result

        root_tag = root.tag.lower() if root.tag else ""
        if "schematic" in root_tag or "schematic_document" in root_tag or "design" in root_tag:
            self._parse_ad_xml(root, result)
        elif "library" in root_tag:
            self._parse_schlib_xml(root, result)
        else:
            self._parse_generic_xml(root, result)

        logger.info(f"AltiumSchParser (string): {len(result.components)} components parsed")
        return result

    def _parse_ad_xml(self, root: ET.Element, result: ParsedSchematic) -> None:
        for comp_elem in root.iter():
            if self._is_component(comp_elem):
                comp = self._extract_component(comp_elem)
                if comp:
                    result.components.append(comp)

        for net_elem in root.iter():
            if self._is_net(net_elem):
                net = self._extract_net(net_elem)
                if net:
                    result.nets.append(net)

    def _parse_schlib_xml(self, root: ET.Element, result: ParsedSchematic) -> None:
        for sym in root.iter():
            if self._is_symbol(sym):
                comp = ParsedComponent(
                    designator="",
                    comment=sym.attrib.get("name", ""),
                    footprint="",
                    lib_ref=sym.attrib.get("name", ""),
                    source_library="Altium",
                )
                self._extract_symbol_pins(sym, comp)
                if comp.pins:
                    result.components.append(comp)

    def _parse_generic_xml(self, root: ET.Element, result: ParsedSchematic) -> None:
        # 方式1: 递归查找 <Component> 元素（支持嵌套结构）
        found_any = False
        for comp_elem in root.iter():
            if comp_elem.tag.lower() in ("component", "part"):
                comp = self._extract_component(comp_elem)
                if comp and (comp.designator or comp.lib_ref):
                    result.components.append(comp)
                    found_any = True

        if found_any:
            return

        # 方式2: 降级为正则匹配（适用于扁平 BOM 格式）
        xml_str = ET.tostring(root, encoding="unicode")

        designator_pattern = r"<Designator>([^<]+)</Designator>"
        comment_pattern = r"<Comment>([^<]+)</Comment>"
        footprint_pattern = r"<Footprint>([^<]+)</Footprint>"
        lib_ref_pattern = r"<LibRef>([^<]+)</LibRef>"

        designators = re.findall(designator_pattern, xml_str)
        comments = re.findall(comment_pattern, xml_str)
        footprints = re.findall(footprint_pattern, xml_str)
        lib_refs = re.findall(lib_ref_pattern, xml_str)

        count = min(len(designators), len(comments))
        for i in range(count):
            fp = footprints[i] if i < len(footprints) else ""
            lib = lib_refs[i] if i < len(lib_refs) else ""

            comp = ParsedComponent(
                designator=designators[i],
                comment=comments[i],
                footprint=self._map_footprint(fp),
                lib_ref=lib,
                source_library="Altium",
            )
            result.components.append(comp)

    def _is_component(self, elem: ET.Element) -> bool:
        tag = elem.tag.lower()
        if "pin" in tag:
            return False  # Pin 元素不是元件
        if tag == "components" or tag == "parts":
            return False  # 复数容器不是元件
        return any(k in tag for k in ["component", "part", "componentinst", "partinst"])

    def _is_net(self, elem: ET.Element) -> bool:
        tag = elem.tag.lower()
        return "net" in tag and "wire" not in tag

    def _is_symbol(self, elem: ET.Element) -> bool:
        tag = elem.tag.lower()
        return "symbol" in tag or "pin" in tag

    def _extract_component(self, elem: ET.Element) -> Optional[ParsedComponent]:
        try:
            designator = self._get_text(elem, ["designator", "Designator", "Ref"])
            comment = self._get_text(elem, ["comment", "Comment", "Value"])
            footprint = self._get_text(elem, ["footprint", "Footprint", "PCBFOOTPRINT"])
            lib_ref = self._get_text(elem, ["libref", "LibRef", "PartType"])
            source_lib = self._get_text(elem, ["sourcelibrary", "SourceLibrary"])

            if not designator and not lib_ref:
                return None

            comp = ParsedComponent(
                designator=designator or "",
                comment=comment or "",
                footprint=self._map_footprint(footprint or ""),
                lib_ref=lib_ref or "",
                source_library=source_lib or "Altium",
            )

            self._extract_pins_from_element(elem, comp)
            return comp
        except Exception as e:
            logger.debug(f"Failed to extract component: {e}")
            return None

    def _extract_symbol_pins(self, sym_elem: ET.Element, comp: ParsedComponent) -> None:
        for pin in sym_elem.iter():
            pin_num = pin.attrib.get("number", "") or pin.attrib.get("Number", "")
            pin_name = pin.attrib.get("name", "") or pin.attrib.get("Name", "")
            pin_type = pin.attrib.get("type", "") or pin.attrib.get("ElectricalType", "")

            if pin_num:
                comp.pins.append({
                    "number": pin_num,
                    "name": pin_name,
                    "type": self._map_pin_type(pin_type),
                })

    def _extract_pins_from_element(self, elem: ET.Element, comp: ParsedComponent) -> None:
        for pin in elem.iter():
            if self._is_pin(pin):
                pin_num = pin.attrib.get("number", "") or pin.attrib.get("Number", "")
                pin_name = pin.attrib.get("name", "") or pin.attrib.get("Name", "")
                pin_type = pin.attrib.get("type", "") or pin.attrib.get("ElectricalType", "")
                net = pin.attrib.get("net", "") or self._get_text(pin, ["net", "Net"])

                if pin_num:
                    comp.pins.append({
                        "number": pin_num,
                        "name": pin_name,
                        "type": self._map_pin_type(pin_type),
                        "net": net,
                    })

    def _extract_net(self, elem: ET.Element) -> Optional[ParsedNet]:
        name = elem.attrib.get("name", "") or self._get_text(elem, ["name", "Name"])
        if not name:
            return None

        net = ParsedNet(name=name)
        for pin in elem.iter():
            designator = pin.attrib.get("component", "") or self._get_text(pin, ["component"])
            pin_num = pin.attrib.get("pin", "") or pin.attrib.get("Pin", "")
            if designator and pin_num:
                net.pins.append({"designator": designator, "pin_num": pin_num})

        return net

    def _get_text(self, elem: ET.Element, keys: List[str]) -> str:
        for key in keys:
            found = elem.find(f".//{key}")
            if found is not None and found.text:
                return found.text.strip()
        return ""

    def _is_pin(self, elem: ET.Element) -> bool:
        tag = elem.tag.lower()
        return "pin" in tag and "number" in elem.attrib

    def _map_footprint(self, ad_footprint: str) -> str:
        """将 AD 封装名称映射到 KiCad 标准格式 (库:封装名)"""
        if not ad_footprint:
            return ""
        ad_footprint = ad_footprint.strip()

        # 精确匹配
        if ad_footprint in self.FOOTPRINT_MAP:
            return self.FOOTPRINT_MAP[ad_footprint]
        # 前缀匹配
        for ad_name, kicad_name in self.FOOTPRINT_MAP.items():
            if ad_footprint.startswith(ad_name):
                return kicad_name
        # 保持原始值（可能需要手动映射）
        return ad_footprint

    def _map_pin_type(self, ad_type: str) -> str:
        mapping = {
            "input": "input",
            "output": "output",
            "bidirectional": "bidirectional",
            "tri-state": "tri_state",
            "passive": "passive",
            "power": "power_in",
            "power_in": "power_in",
            "powerinput": "power_in",
            "opentcollector": "open_collector",
            "open_collector": "open_collector",
            "no connect": "no_connect",
            "nc": "no_connect",
            "unspecified": "unspecified",
            "pushed": "pushed",
            "free": "free",
            "mechanical": "mechanical",
            "wiper": "passive",
            "connector": "connector",
        }
        return mapping.get(ad_type.lower(), "unspecified")

    def _map_symbol_to_kicad(self, lib_ref: str) -> tuple:
        """
        将 AD 符号名映射到 KiCad 符号库。

        Returns:
            (symbol_library, symbol_name) 元组
        """
        if not lib_ref:
            return ("", "")

        lib_ref_clean = lib_ref.strip()

        # 精确匹配
        if lib_ref_clean in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[lib_ref_clean]

        # 前缀匹配（AD 符号可能带后缀如 _0, -1 等）
        for ad_name, (klib, ksym) in self.SYMBOL_MAP.items():
            if ad_name in lib_ref_clean or lib_ref_clean in ad_name:
                return (klib, ksym)

        # 启发式匹配
        upper = lib_ref_clean.upper()
        if "STM32" in upper:
            return ("MCU_ST_STM32F1", "STM32F103C8Tx")
        if "ESP32" in upper:
            if "S3" in upper:
                return ("MCU_Espressif", "ESP32-S3")
            if "C3" in upper:
                return ("RF_Module", "ESP32-C3-WROOM-02")
            return ("RF_Module", "ESP32-WROOM-32")
        if "ESP8266" in upper:
            return ("RF_Module", "ESP-WROOM-01")
        if "CH340" in upper:
            return ("Interface_USB", "CH340C")
        if "CP210" in upper:
            return ("Interface_USB", "CP2102N-Axx-xQFN20")
        if "AMS1117" in upper:
            return ("Regulator_Linear", "AMS1117-3.3")
        if "LM7805" in upper:
            return ("Regulator_Linear", "LM7805_TO220")
        if "LM317" in upper:
            return ("Regulator_Linear", "LM317L_TO92")
        if "LM358" in upper:
            return ("Amplifier_Operational", "LM358")
        if "NE555" in upper:
            return ("Timer", "NE555D")
        if "ATMEGA" in upper:
            return ("MCU_Microchip_ATmega", "ATmega328P-A")
        if "ATTINY" in upper:
            return ("MCU_Microchip_ATtiny", "ATtiny85-20P")
        if "74HC" in upper:
            num = re.search(r"74HC(\d+)", upper)
            if num:
                return ("74xx", f"74HC{num.group(1)}")
        if "W25Q" in upper:
            return ("Memory_Flash", "W25Q128JVE")
        if "AT24C" in upper:
            return ("Memory_EEPROM", "CAT24C256")
        if "USB" in upper:
            return ("Interface_USB", "CH340C")

        # 未知符号，标记为 custom
        return ("custom", "N/A")

    # ─── 导入到 component_db.json ─────────────────────────────────

    def to_kb_format(self, parsed: ParsedSchematic) -> List[Dict[str, Any]]:
        """
        将解析结果转换为 component_db.json 格式。

        仅适用于 IC 类元件（需要封装和引脚定义）。
        阻容等无源元件直接忽略。
        """
        results: List[Dict[str, Any]] = []
        seen: set = set()

        for comp in parsed.components:
            # 跳过无源元件
            designator_prefix = re.match(r"^([A-Z]+)", comp.designator)
            if designator_prefix:
                prefix = designator_prefix.group(1)
                if prefix in ("R", "C", "L", "D", "J", "JP", "X", "Y", "Q", "TP"):
                    continue

            # 去重
            key = comp.lib_ref or comp.comment
            if not key or key in seen:
                continue
            seen.add(key)

            # 映射符号到 KiCad
            symbol_lib, symbol_name = self._map_symbol_to_kicad(comp.lib_ref)

            entry: Dict[str, Any] = {
                "name": key,
                "category": self._infer_category(comp.comment),
                "manufacturer": "",
                "status": "active",
                "description": comp.comment,
                "symbol_library": symbol_lib,
                "symbol_name": symbol_name,
                "footprint": comp.footprint,
                "datasheet_url": "",
                "source": "altium",
                "lcsc_part": comp.properties.get("LCSC", ""),
                "pins": [
                    {
                        "number": str(p["number"]),
                        "name": p.get("name", ""),
                        "type": p.get("type", "unspecified"),
                        "description": "",
                    }
                    for p in comp.pins if p.get("number")
                ],
            }

            results.append(entry)

        return results

    def _infer_category(self, comment: str) -> str:
        """根据注释推断类别"""
        comment_lower = comment.lower()
        if "stm32" in comment_lower:
            return "mcu"
        if "esp32" in comment_lower or "esp8266" in comment_lower or "wifi" in comment_lower:
            return "wireless"
        if "ldo" in comment_lower or "regulator" in comment_lower or "dc-dc" in comment_lower:
            return "power"
        if "usb" in comment_lower:
            return "usb"
        if "amplifier" in comment_lower or "opamp" in comment_lower:
            return "amplifier"
        if "memory" in comment_lower or "eeprom" in comment_lower or "flash" in comment_lower:
            return "memory"
        if "sensor" in comment_lower or "dht" in comment_lower or "bme" in comment_lower:
            return "sensor"
        if "74hc" in comment_lower or "74" in comment_lower:
            return "driver"
        if "rtc" in comment_lower or "ds" in comment_lower:
            return "rtc"
        return "unknown"

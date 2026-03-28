# -*- coding: utf-8 -*-
"""
嘉立创 EDA 解析器

解析嘉立创 EDA (LCEDA Pro / EasyEDA) 导出的 JSON 项目文件，
提取引件、封装、网络连接信息，并转换为 component_db.json 格式。

支持的导出格式:
    - JSON 格式 (.json 导出)
    - 立创 EDA 标准格式
    - LCEDA Pro JSON 格式
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class JLDParsedComponent:
    """解析出的元件（嘉立创格式）"""

    id: str
    designator: str
    value: str
    footprint: str
    symbol: str
    pins: List[Dict[str, Any]] = field(default_factory=list)
    x: float = 0
    y: float = 0
    rotation: float = 0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JLDParsedNet:
    """解析出的网络（嘉立创格式）"""

    name: str
    pins: List[Dict[str, str]] = field(default_factory=list)  # [{component_id, pin_index}]


@dataclass
class JLDParsedProject:
    """解析出的嘉立创 EDA 项目"""

    filename: str
    project_name: str
    components: List[JLDParsedComponent] = field(default_factory=list)
    nets: List[JLDParsedNet] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class JLCEdaParser:
    """
    嘉立创 EDA 项目解析器。

    使用方法:
        parser = JLCEdaParser()
        result = parser.parse("path/to/project.json")
        print(f"Found {len(result.components)} components")
    """

    # 嘉立创封装 → KiCad 封装映射（完整版）
    FOOTPRINT_MAP: Dict[str, str] = {
        # SMD 无源
        "0603": "Capacitor_SMD:C_0603_1608Metric",
        "0402": "Capacitor_SMD:C_0402_1005Metric",
        "0805": "Capacitor_SMD:C_0805_2012Metric",
        "1206": "Capacitor_SMD:C_1206_3216Metric",
        "R0603": "Resistor_SMD:R_0603_1608Metric",
        "R0402": "Resistor_SMD:R_0402_1005Metric",
        "R0805": "Resistor_SMD:R_0805_2012Metric",
        "R1206": "Resistor_SMD:R_1206_3216Metric",
        # SMD 有源
        "SOT-23": "Package_TO_SOT_SMD:SOT-23",
        "SOT-23-5": "Package_TO_SOT_SMD:SOT-23-5",
        "SOT-23-6": "Package_TO_SOT_SMD:SOT-23-6",
        "SOT-223": "Package_TO_SOT_SMD:SOT-223",
        "SOT-223-3": "Package_TO_SOT_SMD:SOT-223",
        "SOT-223-4": "Package_TO_SOT_SMD:SOT-223-4",
        "SOT-323": "Package_TO_SOT_SMD:SOT-323",
        "SOT23": "Package_TO_SOT_SMD:SOT-23",
        "SOT23-5": "Package_TO_SOT_SMD:SOT-23-5",
        "SOT353": "Package_TO_SOT_SMD:SOT-353",
        "SOT-363": "Package_TO_SOT_SMD:SOT-363",
        "TSSOP-8": "Package_SO:TSSOP-8_3x3mm_P0.65mm",
        "TSSOP-14": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        "TSSOP-16": "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
        "TSSOP-20": "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
        "TSSOP-24": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
        "TSSOP-28": "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm",
        "TSSOP-32": "Package_SO:TSSOP-32_6.1x8mm_P0.65mm",
        "TSSOP-48": "Package_SO:TSSOP-48_6.1x12.5mm_P0.5mm",
        "QFN-16": "Package_DFN:QFN-16_3x3mm_P0.5mm",
        "QFN-20": "Package_DFN:QFN-20_4x4mm_P0.5mm",
        "QFN-24": "Package_DFN:QFN-24_4x4mm_P0.5mm",
        "QFN-28": "Package_DFN:QFN-28_4x5mm_P0.5mm",
        "QFN-32": "Package_DFN:QFN-32_5x5mm_P0.5mm",
        "QFN-48": "Package_DFN:QFN-48_6x6mm_P0.4mm",
        "QFN-64": "Package_DFN:QFN-64_9x9mm_P0.5mm",
        "LQFP-32": "Package_QFP:LQFP-32_7x7mm_P0.8mm",
        "LQFP-44": "Package_QFP:LQFP-44_10x10mm_P0.8mm",
        "LQFP-48": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
        "LQFP-64": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
        "LQFP-80": "Package_QFP:LQFP-80_12x12mm_P0.5mm",
        "LQFP-100": "Package_QFP:LQFP-100_14x14mm_P0.5mm",
        "HTSSOP-28": "Package_SO:HTSSOP-28_4.4x9.7mm_P0.65mm",
        "HTSSOP-32": "Package_SO:HTSSOP-32_6.1x8mm_P0.65mm",
        "ETSSOP-16": "Package_SO:ETSSOP-16_4.4x5mm_P0.5mm",
        "ETSSOP-20": "Package_SO:ETSSOP-20_4.4x6.5mm_P0.5mm",
        "VFQFPN-20": "Package_DFN:VFQFPN-20_4x4mm_P0.5mm",
        "VFQFPN-28": "Package_DFN:VFQFPN-28_4x5mm_P0.5mm",
        "VQFN-48": "Package_DFN:VQFN-48_6x6mm_P0.4mm",
        "WQFN-24": "Package_DFN:WQFN-24_4x4mm_P0.4mm",
        "WQFN-32": "Package_DFN:WQFN-32_5x5mm_P0.5mm",
        "BGA-36": "Package_BGA:BGA-36_4x4mm_P0.5mm",
        "BGA-48": "Package_BGA:BGA-48_6x6mm_P0.5mm",
        "BGA-64": "Package_BGA:BGA-64_5x5mm_P0.5mm",
        # SOIC
        "SOIC-8": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "SOIC-14": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
        "SOIC-16": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "SOIC-18": "Package_SO:SOIC-18_3.9x11.6mm_P1.27mm",
        "SOIC-20": "Package_SO:SOIC-20_3.9x13mm_P1.27mm",
        "SOIC-24": "Package_SO:SOIC-24_3.9x15.4mm_P1.27mm",
        "SOIC-28": "Package_SO:SOIC-28_3.9x17.9mm_P1.27mm",
        "MSOP-8": "Package_SO:MSOP-8_3x3mm_P0.65mm",
        "MSOP-10": "Package_SO:MSOP-10_3x3mm_P0.5mm",
        "MSOP-12": "Package_SO:MSOP-12_3x4mm_P0.5mm",
        "TSSOP-8_3x3mm": "Package_SO:TSSOP-8_3x3mm_P0.65mm",
        # DIP / THT
        "DIP-8": "Package_THT:DIP-8_W7.62mm",
        "DIP-14": "Package_THT:DIP-14_W7.62mm",
        "DIP-16": "Package_THT:DIP-16_W7.62mm",
        "DIP-18": "Package_THT:DIP-18_W7.62mm",
        "DIP-20": "Package_THT:DIP-20_W7.62mm",
        "DIP-24": "Package_THT:DIP-24_W7.62mm",
        "DIP-28": "Package_THT:DIP-28_W7.62mm",
        "DIP-32": "Package_THT:DIP-32_W15.24mm",
        "DIP-40": "Package_THT:DIP-40_W15.24mm",
        "SOP-8_3.9x4.9mm_P1.27mm": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "SOP-16_3.9x9.9mm_P1.27mm": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "TSSOP-28_4.4x9.7mm_P0.65mm": "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm",
        "QFN-32_5x5mm_P0.5mm": "Package_DFN:QFN-32_5x5mm_P0.5mm",
        "LQFP-48_7x7mm_P0.5mm": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
        "LQFP-64_10x10mm_P0.5mm": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
        # RF模块
        "ESP32-WROOM-32": "RF_Module:ESP32-WROOM-32",
        "ESP32-S3-WROOM-1": "RF_Module:ESP32-S3-WROOM-1",
        "ESP32-C3-WROOM-02": "RF_Module:ESP32-C3-WROOM-02",
        "ESP8266": "RF_Module:ESP8266",
        # 接插件
        "USB-C": "Connector_USB:USB_Type_C_Receptacle",
        "USB-Type-C": "Connector_USB:USB_Type_C_Receptacle",
        "TYPE-C-16P": "Connector_USB:USB_Type_C_Receptacle",
        "USB-A": "Connector_USB:USB_Type_A",
        "USB-MICRO": "Connector_USB:USB_Micro-B",
        "HDR-1X4": "Connector_PinHeader_1.27mm:PinHeader_1x4_P1.27mm",
        "HDR-1X6": "Connector_PinHeader_1.27mm:PinHeader_1x6_P1.27mm",
        "CONN-SMA-K": "Connector_Coaxial:SMA_Jack",
    }

    # 嘉立创符号 → KiCad (symbol_library, symbol_name) 映射
    # 使用经过 component_db.json 验证的 KiCad 官方符号数据
    SYMBOL_MAP: Dict[str, tuple] = {
        # USB桥接
        "CH340C": ("Interface_USB", "CH340C"),
        "CH340G": ("Interface_USB", "CH340G"),
        "CH340E": ("Interface_USB", "CH340E"),
        "CH340T": ("Interface_USB", "CH340T"),
        "CH341T": ("Interface_USB", "CH341T"),
        "FT232RL": ("Interface_USB", "FT232RL"),
        "CP2102": ("Interface_UART", "CP2102-GMR"),
        # USB连接器
        "TYPE-C": ("Connector_USB", "USB_C_Receptacle"),
        "USB-C": ("Connector_USB", "USB_C_Receptacle"),
        # LTE/通信模组 (custom，无KiCad对应符号)
        "ML307C": ("custom", "ML307C"),
        "ML307": ("custom", "ML307"),
        # DC-DC降压
        "JW5359": ("custom", "JW5359"),
        "SY8088": ("custom", "SY8088"),
        "SY8089": ("custom", "SY8089"),
        # 线性稳压
        "AMS1117-3.3": ("Regulator_Linear", "AMS1117-3.3"),
        "AMS1117-5.0": ("Regulator_Linear", "AMS1117-5.0"),
        "AMS1117": ("Regulator_Linear", "AMS1117"),
        "LDO": ("Regulator_Linear", "Regulator_Linear"),
        "HT7333": ("Regulator_Linear", "HT7333"),
        "ME6211": ("Regulator_Linear", "ME6211C33M5"),
        "ME6217C33M5G": ("Regulator_Linear", "ME6217C33M5G"),
        "ME6217": ("Regulator_Linear", "ME6217C33M5G"),
        # STM32
        "STM32F103C8T6": ("MCU_ST_STM32F1", "STM32F103C8Tx"),
        "STM32F103RCT6": ("MCU_ST_STM32F1", "STM32F103RCTx"),
        "STM32F103RBT6": ("MCU_ST_STM32F1", "STM32F103RBTx"),
        "STM32F103VCT6": ("MCU_ST_STM32F1", "STM32F103VCTx"),
        "STM32F401CCU6": ("MCU_ST_STM32F4", "STM32F401CCUx"),
        "STM32F401CEU6": ("MCU_ST_STM32F4", "STM32F401CEUx"),
        "STM32F405RGT6": ("MCU_ST_STM32F4", "STM32F405RGTx"),
        "STM32F411CEU6": ("MCU_ST_STM32F4", "STM32F411CEUx"),
        "STM32F429ZIT6": ("MCU_ST_STM32F4", "STM32F429ZITx"),
        "STM32F103zet6": ("MCU_ST_STM32F1", "STM32F103ZETx"),
        "STM32F103VET6": ("MCU_ST_STM32F1", "STM32F103VETx"),
        # ESP
        "ESP32-WROOM-32": ("RF_Module", "ESP32-WROOM-32"),
        "ESP32-S3-WROOM-1": ("RF_Module", "ESP32-S3-WROOM-1"),
        "ESP32-C3-WROOM-02": ("RF_Module", "ESP32-C3-WROOM-02"),
        "ESP32-C3": ("RF_Module", "ESP32-C3-MINI-1"),
        "ESP8266": ("RF_Module", "ESP8266"),
        "ESP32-S3": ("RF_Module", "ESP32-S3-MINI-1"),
        # ESP32S3 variant (no dash in BOM name)
        "ESP32S3": ("RF_Module", "ESP32-S3-WROOM-1"),
        "ESP32S3-N16R8": ("RF_Module", "ESP32-S3-WROOM-1"),
        # ATmega
        "ATmega328P": ("MCU_Microchip_ATmega", "ATmega328P-A"),
        "ATmega2560": ("MCU_Microchip_ATmega", "ATmega2560"),
        "ATmega168PA": ("MCU_Microchip_ATmega", "ATmega168P-A"),
        "ATtiny85": ("MCU_Microchip_ATtiny", "ATtiny85"),
        "ATtiny84A": ("MCU_Microchip_ATtiny", "ATtiny84A"),
        # 运放
        "LM358": ("Amplifier_Operational", "LM358"),
        "LM358P": ("Amplifier_Operational", "LM358"),
        "LM324": ("Amplifier_Operational", "LM324"),
        "LM324P": ("Amplifier_Operational", "LM324"),
        "TL072": ("Amplifier_Operational", "TL072"),
        "TL074": ("Amplifier_Operational", "TL074"),
        "NE5532": ("Amplifier_Operational", "NE5532"),
        "MCP6002": ("Amplifier_Operational", "MCP6002"),
        "MCP6004": ("Amplifier_Operational", "MCP6004"),
        "OPA2350": ("Amplifier_Operational", "OPA2350"),
        # 555定时器
        "NE555": ("Timer", "NE555"),
        "LM555": ("Timer", "NE555"),
        # 逻辑芯片
        "74HC595": ("Logic_74xx", "74HC595"),
        "74HC165": ("Logic_74xx", "74HC165"),
        "74HC245": ("Logic_74xx", "74HC245"),
        "74HC573": ("Logic_74xx", "74HC573"),
        "74HC125": ("Logic_74xx", "74HC125"),
        "74HC126": ("Logic_74xx", "74HC126"),
        "74LS00": ("Logic_74xx", "74LS00"),
        "74HC04": ("Logic_74xx", "74HC04"),
        "74HC08": ("Logic_74xx", "74HC08"),
        "74HC32": ("Logic_74xx", "74HC32"),
        "74HC86": ("Logic_74xx", "74HC86"),
        "74HC14": ("Logic_74xx", "74HC14"),
        "74HC4067": ("Logic_74xx", "74HC4067"),
        "CD4051": ("Logic_CMOS_4000", "CD4051B"),
        "CD4053": ("Logic_CMOS_4000", "CD4053B"),
        "CD4066": ("Logic_CMOS_4000", "CD4066B"),
        "CD4094": ("Logic_CMOS_4000", "CD4094B"),
        "MC14067": ("Logic_CMOS_4000", "MC14067B"),
        # 存储器
        "W25Q128": ("Memory_Flash", "W25Q128"),
        "W25Q64": ("Memory_Flash", "W25Q64"),
        "W25Q256": ("Memory_Flash", "W25Q256"),
        "W25C256": ("Memory_Flash", "W25C256"),
        "AT24C256": ("Memory_EEPROM", "24C256"),
        "AT24C512": ("Memory_EEPROM", "24C512"),
        "W25Q32": ("Memory_Flash", "W25Q32"),
        # RS485/RS232
        "MAX485": ("Interface_UART", "MAX485"),
        "MAX232": ("Interface_UART", "MAX232"),
        "SP3485": ("Interface_UART", "SP3485"),
        "SN65HVD230": ("Interface_UART", "SN65HVD230"),
        # 传感器
        "DHT11": ("Sensor_Custom", "DHT11"),
        "DHT22": ("Sensor_Custom", "DHT22"),
        "BMP280": ("Sensor_Pressure", "BMP280"),
        "MPU6050": ("Sensor_Custom", "MPU6050"),
        "MPU9250": ("Sensor_Custom", "MPU9250"),
        "ADS1115": ("ADC", "ADS1115"),
        "ADS1015": ("ADC", "ADS1115"),
        "ACS712": ("Sensor_Current", "ACS712"),
        # RTC
        "DS3231": ("Timer_RTC", "DS3231"),
        "PCF8563": ("Timer_RTC", "PCF8563"),
        "DS1307": ("Timer_RTC", "DS1307"),
        # 显示
        "OLED-0.96": ("Display", "OLED_0.96inch"),
        "OLED_0.96": ("Display", "OLED_0.96inch"),
        "LCD1602": ("Display", "LCD-16X2"),
        "HD44780": ("Display", "LCD-16X2"),
        # 分立
        "SS8050": ("Transistor_BJT", "SS8050"),
        "SS8550": ("Transistor_BJT", "SS8550"),
        "2N3904": ("Transistor_BJT", "2N3904"),
        "2N3906": ("Transistor_BJT", "2N3906"),
        "S8550": ("Transistor_BJT", "S8550"),
        "S8050": ("Transistor_BJT", "S8050"),
        "S9013": ("Transistor_BJT", "S9013"),
        "S9014": ("Transistor_BJT", "S9014"),
        "S9018": ("Transistor_BJT", "S9018"),
        "IRF540N": ("Transistor_FET", "IRF540N"),
        "IRF9540N": ("Transistor_FET", "IRF9540N"),
        "AO3400": ("Transistor_FET", "AO3400"),
        "AO3401": ("Transistor_FET", "AO3401"),
        "SI2302": ("Transistor_FET", "SI2302"),
        "SI2301": ("Transistor_FET", "SI2301"),
        "IRL540N": ("Transistor_FET", "IRL540N"),
        "AMS1117-1.8": ("Regulator_Linear", "AMS1117-1.8"),
        "AMS1117-2.5": ("Regulator_Linear", "AMS1117-2.5"),
        "AMS1117-1.2": ("Regulator_Linear", "AMS1117-1.2"),
        "LM317": ("Regulator_Linear", "LM317"),
        "LM7805": ("Regulator_Linear", "LM7805"),
        "LM7809": ("Regulator_Linear", "LM7809"),
        "LM7812": ("Regulator_Linear", "LM7812"),
        "LM7905": ("Regulator_Linear", "LM7905"),
        "LM1117-3.3": ("Regulator_Linear", "LM1117-3.3"),
        "LM1117-5.0": ("Regulator_Linear", "LM1117-5.0"),
        "TPS63020": ("Regulator_Switching", "TPS63020"),
        # ULN
        "ULN2803": ("Transistor_Array", "ULN2803"),
        # 光耦
        "PC817": ("Isolator", "PC817x"),
        "PC817B": ("Isolator", "PC817x"),
        "6N137": ("Isolator", "6N137"),
        "EL357N": ("Isolator", "EL357N"),
        # MOSFET驱动
        "IR2110": ("Driver_FET", "IR2110"),
        "IR2104": ("Driver_FET", "IR2104"),
        # LoRa
        "LoRa-Ra-01": ("RF_Module", "Ai-Thinker-Ra-01"),
        "Ra-02": ("RF_Module", "Ai-Thinker-Ra-01"),
        "SX1278": ("RF_Module", "SX1278"),
        "SX1276": ("RF_Module", "SX1276"),
        # GPS
        "NEO-6M": ("GPS_Module", "NEO-6M"),
        "NEO-7M": ("GPS_Module", "NEO-7M"),
        # SIM
        "SIM800L": ("RF_GSM", "SIM800L"),
        "SIM800C": ("RF_GSM", "SIM800L"),
        "SIM900A": ("RF_GSM", "SIM900A"),
        # 显示驱动
        "MAX7219": ("Driver_LED", "MAX7219"),
        "TM1637": ("Driver_LED", "TM1637"),
        "HT1621": ("Driver_LCD", "HT1621"),
        # 充电
        "TP4056": ("Battery_Management", "TP4056"),
        "IP5306": ("Battery_Management", "IP5306"),
        # 温度
        "DS18B20": ("Sensor_Temperature", "DS18B20"),
        "MAX31865": ("Sensor_Temperature", "MAX31865"),
        "MAX6675": ("Sensor_Temperature", "MAX6675"),
        "LM75": ("Sensor_Temperature", "LM75"),
        "NTC-10K": ("Resistor", "NTC"),
        # 电流检测
        "INA219": ("Sensor_Current", "INA219"),
        "INA226": ("Sensor_Current", "INA226"),
        # 编码器
        "EC11": ("Mechanical", "EC11"),
        # DI/O
        "74HC4052": ("Logic_74xx", "74HC4052"),
        "74HC4051": ("Logic_74xx", "74HC4051"),
        "CD4052": ("Logic_CMOS_4000", "CD4052B"),
        # CAN
        "MCP2515": ("CAN", "MCP2515"),
        "SN65HVD230": ("CAN", "SN65HVD230"),
        # 接口
        "CP2104": ("Interface_UART", "CP2104-GMR"),
        "MAX3232": ("Interface_UART", "MAX3232"),
    }

    # 无源元件前缀（跳过不入库）
    PASSIVE_PREFIXES = frozenset(
        ("R", "C", "L", "D", "J", "JP", "X", "Y", "Q", "TP", "CN", "P", "F", "RN", "RB", "L1", "L2")
    )

    def parse(self, filepath: str) -> JLDParsedProject:
        """解析嘉立创 EDA JSON 项目文件。"""
        path = Path(filepath)
        if not path.exists():
            return JLDParsedProject(
                filename=str(filepath),
                project_name="",
                errors=[f"File not found: {filepath}"],
            )

        result = JLDParsedProject(filename=str(filepath), project_name=path.stem)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
            return result

        if not isinstance(data, dict):
            result.errors.append("JSON root must be an object")
            return result

        format_type = self._detect_format(data)
        logger.info(f"Detected LCEDA format: {format_type}")

        if format_type == "standard":
            self._parse_standard_format(data, result)
        elif format_type == "lcsc":
            self._parse_lcsc_format(data, result)
        elif format_type == "kicad_export":
            self._parse_kicad_export(data, result)
        else:
            self._parse_generic_format(data, result)

        logger.info(f"JLCEdaParser: {len(result.components)} components, "
                    f"{len(result.nets)} nets parsed from {path.name}")
        return result

    def parse_from_string(self, json_content: Any) -> JLDParsedProject:
        """从 JSON 字符串/对象解析嘉立创 EDA 项目。"""
        result = JLDParsedProject(filename="<string>", project_name="unknown")

        try:
            if isinstance(json_content, str):
                data = json.loads(json_content)
            else:
                data = json_content
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
            return result

        if not isinstance(data, dict):
            result.errors.append("JSON root must be an object")
            return result

        format_type = self._detect_format(data)
        logger.info(f"JLCEdaParser (string): detected format {format_type}")

        if format_type == "standard":
            self._parse_standard_format(data, result)
        elif format_type == "lcsc":
            self._parse_lcsc_format(data, result)
        elif format_type == "kicad_export":
            self._parse_kicad_export(data, result)
        else:
            self._parse_generic_format(data, result)

        return result

    def _detect_format(self, data: Dict) -> str:
        """识别 JSON 格式类型"""
        keys = set(data.keys())
        if "schematic" in keys or "Schematic" in keys:
            return "standard"
        if "components" in keys or "bom" in keys:
            return "lcsc"
        if "kicad" in keys or "board" in keys:
            return "kicad_export"
        return "generic"

    def _parse_standard_format(self, data: Dict, result: JLDParsedProject) -> None:
        """解析嘉立创标准格式"""
        proj = data.get("project", data.get("Project", {}))
        result.project_name = proj.get("title", proj.get("name", ""))
        result.metadata = {
            "version": proj.get("version", ""),
            "source": "LCEDA_Standard",
        }

        comps = data.get("schematic", {}).get("components", [])
        if not comps:
            comps = data.get("components", [])
        for comp_data in comps:
            comp = self._extract_lcd_component(comp_data)
            if comp:
                result.components.append(comp)

        nets = data.get("schematic", {}).get("nets", [])
        for net_data in nets:
            net = self._extract_lcd_net(net_data)
            if net:
                result.nets.append(net)

    def _parse_lcsc_format(self, data: Dict, result: JLDParsedProject) -> None:
        """解析 LCSC BOM 导出格式"""
        comps = data.get("components", data.get("bom", []))
        for item in comps:
            if isinstance(item, dict):
                comp = JLDParsedComponent(
                    id=str(item.get("Id", "")),
                    designator=str(item.get("Designator", item.get("位号", ""))),
                    value=str(item.get("Value", item.get("值", ""))),
                    footprint=str(item.get("Footprint", item.get("封装", ""))),
                    symbol=str(item.get("Symbol", item.get("符号", ""))),
                    properties=dict(item),
                )
                comp.footprint = self._map_footprint(comp.footprint)
                result.components.append(comp)

    def _parse_kicad_export(self, data: Dict, result: JLDParsedProject) -> None:
        """解析 KiCad 导出格式（已转换为 JSON）"""
        comps = data.get("components", data.get("board", {}).get("components", []))
        for comp_data in comps:
            comp = self._extract_lcd_component(comp_data)
            if comp:
                result.components.append(comp)

    def _parse_generic_format(self, data: Dict, result: JLDParsedProject) -> None:
        """通用 JSON 解析（尝试常见键名）"""
        for key in ["parts", "symbols", "devices", "components"]:
            items = data.get(key, [])
            if isinstance(items, list) and items:
                for item in items:
                    if isinstance(item, dict):
                        comp = self._extract_lcd_component(item)
                        if comp:
                            result.components.append(comp)
                if result.components:
                    break

    def _extract_lcd_component(self, data: Dict) -> Optional[JLDParsedComponent]:
        """从 JSON 数据提取引件"""
        try:
            designator = str(data.get("designator", data.get("Designator", data.get("ref", ""))))
            if not designator:
                return None

            return JLDParsedComponent(
                id=str(data.get("id", data.get("Id", ""))),
                designator=designator,
                value=str(data.get("value", data.get("Value", data.get("comment", "")))),
                footprint=self._map_footprint(str(data.get("footprint", data.get("Footprint", "")))),
                symbol=str(data.get("symbol", data.get("Symbol", data.get("lib", "")))),
                x=float(data.get("x", 0)),
                y=float(data.get("y", 0)),
                rotation=float(data.get("rotation", data.get("rot", 0))),
                properties=dict(data),
            )
        except Exception as e:
            logger.debug(f"Failed to extract component: {e}")
            return None

    def _extract_lcd_net(self, data: Dict) -> Optional[JLDParsedNet]:
        """从 JSON 数据提取网络"""
        name = str(data.get("name", data.get("Name", "")))
        if not name:
            return None

        net = JLDParsedNet(name=name)
        for pin in data.get("pins", data.get("connections", [])):
            if isinstance(pin, dict):
                net.pins.append({
                    "component_id": str(pin.get("component", pin.get("ref", ""))),
                    "pin_index": str(pin.get("pin", pin.get("pin_num", ""))),
                })

        return net

    def _map_footprint(self, lcd_footprint: str) -> str:
        """将嘉立创封装映射到 KiCad 标准格式"""
        if not lcd_footprint:
            return ""

        # 精确匹配
        if lcd_footprint in self.FOOTPRINT_MAP:
            return self.FOOTPRINT_MAP[lcd_footprint]

        # 前缀匹配
        for lcd_name, kicad_name in self.FOOTPRINT_MAP.items():
            if lcd_name.lower() in lcd_footprint.lower() or lcd_footprint.lower() in lcd_name.lower():
                return kicad_name

        # 嘉立创格式通常是 "Package:Footprint"，提取 Footprint 部分
        if ":" in lcd_footprint:
            _, fp = lcd_footprint.split(":", 1)
            if fp in self.FOOTPRINT_MAP:
                return self.FOOTPRINT_MAP[fp]

        return lcd_footprint

    def _map_symbol_to_kicad(self, lcd_symbol: str) -> tuple:
        """将嘉立创符号映射到 KiCad (symbol_library, symbol_name)"""
        if not lcd_symbol:
            return ("", "")

        lcd_clean = lcd_symbol.strip()

        # 精确匹配
        if lcd_clean in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[lcd_clean]

        # 前缀匹配（STM32, ESP32, ATmega 等）
        for lcd_name, kicad_pair in self.SYMBOL_MAP.items():
            if lcd_name.upper() in lcd_clean.upper() or lcd_clean.upper() in lcd_name.upper():
                return kicad_pair

        # 通用前缀智能推断
        upper_sym = lcd_clean.upper()
        if "STM32F103" in upper_sym:
            return ("MCU_ST_STM32F1", "STM32F103C8Tx")
        if "STM32F4" in upper_sym:
            return ("MCU_ST_STM32F4", "STM32F401CCUx")
        if "STM32" in upper_sym:
            return ("MCU_ST_STM32F1", "STM32F103C8Tx")
        if "ESP32-S3" in upper_sym:
            return ("RF_Module", "ESP32-S3-WROOM-1")
        if "ESP32-C3" in upper_sym:
            return ("RF_Module", "ESP32-C3-WROOM-02")
        if "ESP32" in upper_sym:
            return ("RF_Module", "ESP32-WROOM-32")
        if "CH340" in upper_sym:
            return ("Interface_USB", lcd_clean)
        if "AMS1117" in upper_sym:
            return ("Regulator_Linear", lcd_clean)
        if "LM358" in upper_sym:
            return ("Amplifier_Operational", "LM358")
        if "LM324" in upper_sym:
            return ("Amplifier_Operational", "LM324")
        if "NE555" in upper_sym:
            return ("Timer", "NE555")
        if "74HC" in upper_sym:
            return ("Logic_74xx", lcd_clean)
        if "CD40" in upper_sym:
            return ("Logic_CMOS_4000", lcd_clean + "B")
        if "ATMEGA" in upper_sym:
            return ("MCU_Microchip_ATmega", lcd_clean)
        if "ATTINY" in upper_sym:
            return ("MCU_Microchip_ATtiny", lcd_clean)

        # 无法识别 → custom
        return ("custom", lcd_clean)

    # ─── 导入到 component_db.json ─────────────────────────────────

    def to_kb_format(self, parsed: JLDParsedProject) -> List[Dict[str, Any]]:
        """将解析结果转换为 component_db.json 格式"""
        results: List[Dict[str, Any]] = []
        seen: set = set()

        for comp in parsed.components:
            # 跳过无源元件
            if comp.designator:
                prefix = "".join(c for c in comp.designator if c.isalpha())
                if prefix in self.PASSIVE_PREFIXES:
                    continue

            # 使用芯片型号名（而非JLC符号名）作为键和映射依据
            chip_name = comp.value or comp.symbol
            if not chip_name:
                continue

            # key = 芯片型号，确保同名芯片不重复入库
            if chip_name in seen:
                continue
            seen.add(chip_name)

            # 使用芯片型号（而非JLC符号名）进行KiCad映射
            symbol_lib, symbol_name = self._map_symbol_to_kicad(chip_name)

            entry: Dict[str, Any] = {
                "name": chip_name,
                "category": self._infer_category(chip_name),
                "manufacturer": "",
                "status": "active",
                "description": chip_name,
                "symbol_library": symbol_lib,
                "symbol_name": symbol_name,
                "footprint": comp.footprint,
                "datasheet_url": "",
                "source": "lcsc",
                "lcsc_part": str(comp.properties.get("LCSC", "")),
                "pins": [],
            }

            results.append(entry)

        return results

    def _infer_category(self, value: str) -> str:
        """根据值推断类别"""
        v = value.upper()
        if "STM32" in v:
            return "mcu"
        if "ESP32" in v or "ESP8266" in v:
            return "wireless"
        if "ATTINY" in v or "ATMEGA" in v:
            return "mcu"
        if "LDO" in v or "REGULATOR" in v or "AMS1117" in v or "LM7805" in v or "LM317" in v or "LM1117" in v:
            return "power"
        if "USB" in v or "CH340" in v or "FT232" in v:
            return "usb"
        if "LM358" in v or "LM324" in v or "OPAMP" in v or "TL072" in v or "NE5532" in v:
            return "amplifier"
        if "EEPROM" in v or "FLASH" in v or "MEMORY" in v or "W25Q" in v or "AT24C" in v:
            return "memory"
        if "485" in v or "232" in v or "UART" in v or "CP210" in v or "SP34" in v:
            return "communication"
        if "DHT" in v or "BMP" in v or "MPU" in v or "ADS" in v or "SENSOR" in v or "ACS" in v or "INA" in v or "DS18" in v or "MAX318" in v or "LM75" in v:
            return "sensor"
        if "OLED" in v or "LCD" in v:
            return "display"
        if "DS323" in v or "PCF8563" in v or "DS1307" in v:
            return "rtc"
        if "LoRa" in v or "Ra-0" in v or "SX127" in v:
            return "wireless"
        if "NE555" in v or "555" in v:
            return "timer"
        if "74HC" in v or "CD40" in v or "74LS" in v:
            return "logic"
        if "SIM800" in v or "SIM900" in v:
            return "wireless"
        if "GPS" in v or "NEO-6" in v or "NEO-7" in v:
            return "gps"
        if "ULN" in v or "IRF" in v or "S8050" in v or "SS8050" in v or "AO340" in v or "IR2110" in v or "IR2104" in v:
            return "driver"
        if "TP4056" in v or "IP5306" in v:
            return "power"
        if "PC817" in v or "6N137" in v:
            return "isolator"
        if "MAX7219" in v or "TM1637" in v:
            return "display"
        if "NEO-6" in v:
            return "gps"
        if "EC11" in v:
            return "mechanical"
        if "MCP2515" in v or "HVD230" in v:
            return "can"
        return "unknown"

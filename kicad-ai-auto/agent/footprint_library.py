"""
KiCad 封装库管理器
提供封装库查询、符号到封装的映射、以及默认封装 fallback 功能
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# ========== 常用封装映射表 ==========
# 当 AI 无法找到合适封装时使用这些默认值
# 格式: {元件类型: {关键词: 封装名}}

DEFAULT_FOOTPRINT_MAPPING = {
    # 电阻
    "resistor": {
        "0603": "Resistor_SMD:R_0603_1608Metric",
        "0805": "Resistor_SMD:R_0805_2012Metric",
        "1206": "Resistor_SMD:R_1206_3216Metric",
        "0402": "Resistor_SMD:R_0402_1005Metric",
        "default": "Resistor_SMD:R_0603_1608Metric",
    },
    # 电容
    "capacitor": {
        "0603": "Capacitor_SMD:C_0603_1608Metric",
        "0805": "Capacitor_SMD:C_0805_2012Metric",
        "1206": "Capacitor_SMD:C_1206_3216Metric",
        "0402": "Capacitor_SMD:C_0402_1005Metric",
        "electrolytic": "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
        "ceramic": "Capacitor_SMD:C_0603_1608Metric",
        "default": "Capacitor_SMD:C_0603_1608Metric",
    },
    # 电感
    "inductor": {
        "0603": "Inductor_SMD:L_0603_1608Metric",
        "0805": "Inductor_SMD:L_0805_2012Metric",
        "1206": "Inductor_SMD:L_1206_3216Metric",
        "power": "Inductor_SMD:LR2012",
        "default": "Inductor_SMD:L_0603_1608Metric",
    },
    # 二极管
    "diode": {
        "sod123": "Diode_SMD:D_SOD-123",
        "sod323": "Diode_SMD:D_SOD-323",
        "default": "Diode_SMD:D_SOD-123",
    },
    # LED
    "led": {
        "0603": "LED_SMD:LED_0603_1608Metric",
        "0805": "LED_SMD:LED_0805_2012Metric",
        "5mm": "LED_THT:LED_D5.0mm-3_Flat",
        "3mm": "LED_THT:LED_D3.0mm-3",
        "default": "LED_SMD:LED_0603_1608Metric",
    },
    # 三极管
    "transistor": {
        "sot23": "Package_TO_SOT_SMD:SOT-23",
        "sot89": "Package_TO_SOT_SMD:SOT-89-3",
        "sot223": "Package_TO_SOT_SMD:SOT-223-3",
        "to220": "Package_THT:TO-220_Vertical",
        "default": "Package_TO_SOT_SMD:SOT-23",
    },
    # MOS管
    "mosfet": {
        "sot23": "Package_TO_SOT_SMD:SOT-23",
        "sot223": "Package_TO_SOT_SMD:SOT-223-3",
        "dfn": "Package_DFN_QFN:DFN-8_2x2mm_P0.5mm",
        "default": "Package_TO_SOT_SMD:SOT-23",
    },
    # 集成电路
    "ic": {
        "soic8": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "soic16": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "tssop": "Package_SO:TSSOP-8_3.0x3.0mm_P0.65mm",
        "qfn": "Package_DFN_QFN:QFN-32_5x5mm_P0.5mm",
        "dfn": "Package_DFN_QFN:DFN-8_2x2mm_P0.5mm",
        "bga": "Package_BGA:BGA-9_3x3mm",
        "dip": "Package_DIP:DIP-8_W7.62mm",
        "default": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    },
    # 稳压器
    "regulator": {
        "sot23": "Package_TO_SOT_SMD:SOT-23",
        "sot89": "Package_TO_SOT_SMD:SOT-89-3",
        "to252": "Package_TO_SOT_SMD:TO-252-2",
        "default": "Package_TO_SOT_SMD:SOT-23",
    },
    # 连接器
    "connector": {
        "pinheader": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "pinheader2": "Connector_PinHeader_2.54mm:PinHeader_2x02_P2.54mm_Vertical",
        "jumper": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "usb": "Connector_USB:USB-Micro-B",
        "default": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    },
    # 开关
    "switch": {
        "push": "Switch_THT:SW_Push_1P1T_6x6mm_H9.5mm",
        "dip": "Switch_THT:SW_DIP_x1_W7.62mm_Slide",
        "default": "Switch_THT:SW_Push_1P1T_6x6mm_H9.5mm",
    },
    # 晶振
    "crystal": {
        "3225": "Crystal_SMD:Crystal_SMD_3225-4Pin_3.2x2.5mm",
        "5032": "Crystal_SMD:Crystal_SMD_5032-2Pin_5.0x3.2mm",
        "插件": "Crystal:Crystal_HC49_SMD",
        "default": "Crystal_SMD:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    },
    # 电池座
    "battery": {
        "cr2032": "BatteryHolder:Keystone_3000_1x12mm",
        "default": "BatteryHolder:Keystone_3000_1x12mm",
    },
    # 保险丝
    "fuse": {
        "1206": "Fuse:Fuse_1206_3216Metric",
        "default": "Fuse:Fuse_1206_3216Metric",
    },
    # 继电器
    "relay": {
        "5v": "Relay_THT:Relay_5V_SRD-05VDC-SL-C",
        "default": "Relay_THT:Relay_5V_SRD-05VDC-SL-C",
    },
    # 光耦
    "optocoupler": {
        "dip4": "Package_DIP:DIP-4_W7.62mm",
        "sop4": "Package_SO:SOP-4_3.9x4.9mm_P1.27mm",
        "default": "Package_DIP:DIP-4_W7.62mm",
    },
    # 蜂鸣器
    "buzzer": {
        "passive": "Buzzer_Beeper:Buzzer_12x9.5RM7.6",
        "default": "Buzzer_Beeper:Buzzer_12x9.5RM7.6",
    },
    # 麦克风
    "microphone": {
        "electret": "Microphone:MIC_CMA-4544PF-W",
        "default": "Microphone:MIC_CMA-4544PF-W",
    },
    # 电位器
    "potentiometer": {
        "trim": "Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical",
        "normal": "Potentiometer_THT:Potentiometer_Alps_RK16_12mm",
        "default": "Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical",
    },
    # 传感器
    "sensor": {
        "temp": "Package_TO_SOT_SMD:SOT-23",
        "default": "Package_TO_SOT_SMD:SOT-23",
    },
    # 模块 - 常用传感器模块封装
    "module": {
        "rcwl-0516": "Module:RCWL-0516",  # 微波雷达模块
        "hc-sr04": "Module:HC-SR04",  # 超声波模块
        "hc-sr501": "Module:HC-SR501",  # 人体红外模块
        "dht11": "Module:DHT11",  # 温湿度模块
        "dht22": "Module:DHT22",  # 温湿度模块
        "ds18b20": "Package_TO_SOT_SMD:SOT-23",  # 温度传感器
        "mq-2": "Module:MQ-2",  # 气体传感器
        "mq-135": "Module:MQ-135",  # 气体传感器
        "gyro": "Module:GY-521",  # 陀螺仪模块
        "accelerometer": "Module:ADXL345",  # 加速度计
        "oled": "Module:OLED_0.96",  # OLED显示屏
        "ssd1306": "Module:OLED_0.96",  # SSD1306 OLED
        "esp32": "Module:ESP32_DEVKIT",  # ESP32开发板
        "arduino": "Module:Arduino_Nano",  # Arduino Nano
        "stm32": "Module:STM32_BLUEPILL",  # STM32开发板
        "default": "Module:Generic_Module",  # 默认模块
    },
    # 显示屏
    "display": {
        "oled": "Module:OLED_0.96",
        "lcd1602": "Display:LCD_16x2",
        "lcd2004": "Display:LCD_20x4",
        "tft": "Display:ST7789_240x240",
        "default": "Module:Generic_Module",
    },
    # 无线模块
    "wireless": {
        "esp8266": "Module:ESP8266",
        "esp32": "Module:ESP32_DEVKIT",
        "nrf24l01": "Module:NRF24L01",
        "bluetooth": "Module:HC-05",
        "zigbee": "Module:CC2530",
        "lora": "Module:LoRa_RFM95",
        "default": "Module:Generic_Module",
    },
}


# ========== 符号到封装的推荐映射 ==========
# 基于 KiCad 内置符号库的推荐封装

SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS = {
    # Device 库
    "R": "Resistor_SMD:R_0603_1608Metric",
    "C": "Capacitor_SMD:C_0603_1608Metric",
    "L": "Inductor_SMD:L_0603_1608Metric",
    "D": "Diode_SMD:D_SOD-123",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "LED_Small": "LED_SMD:LED_0402_1005Metric",
    "Fuse": "Fuse:Fuse_1206_3216Metric",
    "Ferrite_Bead": "Inductor_SMD:L_0603_1608Metric",
    "TVS": "Diode_SMD:D_SOD-123",
    "Varistor": "Varistor:Varistor_D7mm",
    "Thermistor": "Resistor_SMD:R_0603_1608Metric",
    "Potentiometer": "Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical",
    "Crystal": "Crystal_SMD:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Buzzer": "Buzzer_Beeper:Buzzer_12x9.5RM7.6",
    "Speaker": "Buzzer_Beeper:Buzzer_12x9.5RM7.6",
    "Microphone": "Microphone:MIC_CMA-4544PF-W",
    "Battery": "BatteryHolder:Keystone_3000_1x12mm",
    # Transistor 库
    "Q_NPN": "Package_TO_SOT_SMD:SOT-23",
    "Q_PNP": "Package_TO_SOT_SMD:SOT-23",
    "Q_NMOS": "Package_TO_SOT_SMD:SOT-23",
    "Q_PMOS": "Package_TO_SOT_SMD:SOT-23",
    "Q_NPN_BEC": "Package_TO_SOT_SMD:SOT-23",
    "Q_PNP_BEC": "Package_TO_SOT_SMD:SOT-23",
    # Connector 库
    "J": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "J_TerminalBlock": "TerminalBlock:TerminalBlock_P5.0mm",
    "USB_B": "Connector_USB:USB-B-Micro",
    "USB_C": "Connector_USB:USB-C_Micro",
    "Jack": "Connector_Audio:Jack_3.5mm_PJ311ST04",
    # Switch 库
    "SW_Push": "Switch_THT:SW_Push_1P1T_6x6mm_H9.5mm",
    "SW_DIP": "Switch_THT:SW_DIP_x1_W7.62mm_Slide",
    "SW_Slide": "Switch_THT:SW_Slide_1P1T_P2.54mm",
    # Integrated_Circuit 库 (常用 IC)
    "555": "Package_DIP:DIP-8_W7.62mm",
    "NE555": "Package_DIP:DIP-8_W7.62mm",
    "LM7805": "Package_TO_SOT_SMD:SOT-223-3",
    "LM317": "Package_TO_SOT_SMD:SOT-223-3",
    "AMS1117": "Package_TO_SOT_SMD:SOT-223-3",
    "ATmega328P": "Package_DIP:DIP-28_W7.62mm",
    "ESP32": "Package_DFN_QFN:QFN-48_6x6mm_P0.4mm",
    "STM32": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
    # OpAmp 库
    "LM358": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "LM358P": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "TL072": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    # Power 库
    "LM2596": "Package_TO_SOT_SMD:SOT-223-3",
    "MT3608": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    # Relay 库
    "Relay_5V": "Relay_THT:Relay_5V_SRD-05VDC-SL-C",
    "Relay_12V": "Relay_THT:Relay_12V_SRD-05VDC-SL-C",
    # Optocoupler 库
    "PC817": "Package_DIP:DIP-4_W7.62mm",
    "6N137": "Package_SO:SOP-8_3.9x4.9mm_P1.27mm",
}


def get_default_footprint(component_type: str, package: str = None) -> str:
    """
    获取默认封装

    Args:
        component_type: 元件类型 (resistor, capacitor, ic 等)
        package: 封装大小 (0603, 0805, soic8 等)

    Returns:
        封装名称字符串
    """
    component_type = component_type.lower()

    if component_type in DEFAULT_FOOTPRINT_MAPPING:
        mapping = DEFAULT_FOOTPRINT_MAPPING[component_type]

        if package:
            package_lower = package.lower()
            # 尝试精确匹配
            if package_lower in mapping:
                return mapping[package_lower]
            # 尝试部分匹配
            for key in mapping:
                if key in package_lower or package_lower in key:
                    return mapping[key]

        return mapping.get("default", mapping.get("", "Resistor_SMD:R_0603_1608Metric"))

    # 未知类型返回通用电阻封装
    return "Resistor_SMD:R_0603_1608Metric"


def get_footprint_by_keyword(keyword: str) -> Optional[str]:
    """
    根据关键词搜索封装

    Args:
        keyword: 关键词 (例如: "0805 resistor", "soic8 ic")

    Returns:
        封装名称或 None
    """
    keyword_lower = keyword.lower()

    # 先在推荐表中查找
    for symbol, footprint in SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS.items():
        if keyword_lower in symbol.lower():
            return footprint

    # 在映射表中查找
    for component_type, mapping in DEFAULT_FOOTPRINT_MAPPING.items():
        if component_type in keyword_lower:
            for package, footprint in mapping.items():
                if package in keyword_lower or keyword_lower in package:
                    return footprint
            return mapping.get("default")

    return None


def find_best_footprint(
    component_name: str, component_value: str = None, package: str = None
) -> str:
    """
    根据元件信息找到最佳封装

    Args:
        component_name: 元件名称/型号 (例如: "R", "ATmega328P", "LM7805")
        component_value: 元件值 (例如: "10K", "1uF")
        package: 封装 (例如: "0805", "DIP-8")

    Returns:
        推荐的封装名称
    """
    # 1. 首先检查符号推荐表
    if component_name in SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS:
        return SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS[component_name]

    # 2. 尝试模糊匹配
    for symbol, footprint in SYMBOL_TO_FOOTPRINT_RECOMMENDATIONS.items():
        if (
            symbol.lower() in component_name.lower()
            or component_name.lower() in symbol.lower()
        ):
            return footprint

    # 3. 根据 package 参数获取默认封装
    if package:
        # 推断元件类型
        component_type = infer_component_type(component_name, component_value)
        footprint = get_default_footprint(component_type, package)
        if footprint:
            return footprint

    # 4. 根据元件名称推断类型
    component_type = infer_component_type(component_name, component_value)
    return get_default_footprint(component_type)


def infer_component_type(component_name: str, component_value: str = None) -> str:
    """
    根据元件名称和值推断元件类型

    Returns:
        元件类型字符串
    """
    name_lower = component_name.lower()
    value_lower = component_value.lower() if component_value else ""

    # IC 判断
    ics = [
        "atmega",
        "stm32",
        "esp32",
        "pic",
        "attiny",
        "arduino",
        "运放",
        "放大器",
        "lm358",
        "lm324",
        "tl072",
        "ne555",
        "稳压",
        "7805",
        "1117",
        "2596",
        "ch340",
        "cp2102",
        "ft232",
        "晶圆",
        "chip",
    ]
    if any(ic in name_lower for ic in ics):
        return "ic"

    # 电阻判断
    if name_lower.startswith("r") or "电阻" in name_lower:
        return "resistor"

    # 电容判断
    if name_lower.startswith("c") or "电容" in name_lower:
        # 检查是否是电解电容
        if (
            "电解" in name_lower
            or "electrolytic" in name_lower
            or "polar" in name_lower
        ):
            return "capacitor"
        return "capacitor"

    # 电感判断
    if name_lower.startswith("l") or "电感" in name_lower:
        return "inductor"

    # 二极管判断
    if name_lower.startswith("d") or "二极管" in name_lower or "diode" in name_lower:
        if "led" in name_lower or "灯" in name_lower:
            return "led"
        return "diode"

    # LED 判断
    if "led" in name_lower or "灯" in name_lower:
        return "led"

    # 三极管/MOS判断
    if name_lower.startswith("q") or "三极管" in name_lower or "晶体管" in name_lower:
        if "mos" in name_lower or "mosfet" in name_lower:
            return "mosfet"
        return "transistor"

    # 连接器判断
    if (
        name_lower.startswith("j")
        or "连接器" in name_lower
        or "connector" in name_lower
    ):
        if "usb" in name_lower:
            return "connector"
        if "header" in name_lower or "排针" in name_lower:
            return "connector"
        return "connector"

    # 开关判断
    if name_lower.startswith("sw") or "开关" in name_lower or "switch" in name_lower:
        return "switch"

    # 晶振判断
    if name_lower.startswith("y") or "晶振" in name_lower or "crystal" in name_lower:
        return "crystal"

    # 电池座
    if "bt" in name_lower or "电池" in name_lower or "battery" in name_lower:
        return "battery"

    # 保险丝
    if name_lower.startswith("f") or "保险丝" in name_lower or "fuse" in name_lower:
        return "fuse"

    # 继电器
    if "继电器" in name_lower or "relay" in name_lower:
        return "relay"

    # 光耦
    if "光耦" in name_lower or "optocoupler" in name_lower or "pc817" in name_lower:
        return "optocoupler"

    # 蜂鸣器
    if "蜂鸣器" in name_lower or "buzzer" in name_lower or "蜂" in name_lower:
        return "buzzer"

    # 麦克风
    if "麦克" in name_lower or "mic" in name_lower or "microphone" in name_lower:
        return "microphone"

    # 电位器
    if "电位器" in name_lower or "pot" in name_lower or "potentiometer" in name_lower:
        return "potentiometer"

    # 传感器
    if "传感器" in name_lower or "sensor" in name_lower or "温度" in name_lower:
        return "sensor"

    # 稳压器
    if "稳压" in name_lower or "regulator" in name_lower or "7805" in name_lower:
        return "regulator"

    # 模块判断 - 常用传感器和无线模块
    modules = [
        "rcwl",  # 微波雷达模块
        "hc-sr04",
        "hc_sr04",  # 超声波模块
        "hc-sr501",
        "hc_sr501",  # 人体红外模块
        "dht11",
        "dht22",  # 温湿度模块
        "ds18b20",  # 温度传感器
        "mq-2",
        "mq2",
        "mq-135",
        "mq135",  # 气体传感器
        "gyro",
        "gy-521",
        "mpu6050",  # 陀螺仪模块
        "accelerometer",
        "adxl345",  # 加速度计
        "oled",
        "ssd1306",  # OLED显示屏
        "esp32",
        "esp8266",  # ESP系列
        "arduino",  # Arduino
        "stm32",  # STM32
        "bluetooth",
        "hc-05",
        "hc-06",  # 蓝牙模块
        "nrf24l01",  # 无线模块
        "lora",
        "rfm95",
        "rfm96",  # LoRa模块
        "zigbee",
        "cc2530",  # ZigBee模块
        "ch340",
        "cp2102",
        "ft232",  # USB转串口模块
        "module",  # 通用模块
        "超声波",  # 超声波
        "雷达",
        "radar",  # 雷达模块
    ]
    if any(m in name_lower for m in modules):
        if "oled" in name_lower or "ssd1306" in name_lower:
            return "display"
        if (
            "esp32" in name_lower
            or "esp8266" in name_lower
            or "arduino" in name_lower
            or "stm32" in name_lower
        ):
            return "module"
        if "bluetooth" in name_lower or "hc-05" in name_lower or "hc-06" in name_lower:
            return "wireless"
        if (
            "nrf" in name_lower
            or "lora" in name_lower
            or "rfm" in name_lower
            or "zigbee" in name_lower
        ):
            return "wireless"
        return "module"

    # 默认返回电阻
    return "resistor"


class FootprintLibraryManager:
    """
    KiCad 封装库管理器
    从 KiCad 安装目录读取封装库
    """

    def __init__(self, kicad_footprint_dir: str = None):
        """
        初始化封装库管理器

        Args:
            kicad_footprint_dir: KiCad 封装库目录
                                 如果为 None，会自动检测系统中的 KiCad 目录
        """
        self.footprint_dirs = []
        self.footprints = {}  # {库名: [封装列表]}

        if kicad_footprint_dir:
            self._scan_directory(kicad_footprint_dir)
        else:
            self._auto_detect_footprint_dirs()

    def _auto_detect_footprint_dirs(self):
        """自动检测 KiCad 封装库目录"""
        import platform

        system = platform.system()

        if system == "Windows":
            base_dirs = [
                r"C:\Program Files\KiCad\9.0\share\kicad\footprints",
                r"C:\Program Files\KiCad\8.0\share\kicad\footprints",
                r"C:\Program Files (x86)\KiCad\9.0\share\kicad\footprints",
            ]
        elif system == "Darwin":
            base_dirs = [
                "/Applications/KiCad.app/Contents/SharedSupport/footprints",
                "/Library/Application Support/kicad/footprints",
            ]
        else:  # Linux
            base_dirs = [
                "/usr/share/kicad/footprints",
                "/usr/local/share/kicad/footprints",
                os.path.expanduser("~/.local/share/kicad/footprints"),
            ]

        for dir_path in base_dirs:
            if os.path.exists(dir_path):
                logger.info(f"Found KiCad footprint directory: {dir_path}")
                self._scan_directory(dir_path)

    def _scan_directory(self, dir_path: str):
        """扫描目录获取封装列表"""
        if not os.path.exists(dir_path):
            return

        self.footprint_dirs.append(dir_path)

        # 扫描 .pretty 目录
        for entry in os.listdir(dir_path):
            entry_path = os.path.join(dir_path, entry)
            if os.path.isdir(entry_path) and entry.endswith(".pretty"):
                library_name = entry[:-7]  # 去掉 .pretty 后缀
                self.footprints[library_name] = self._scan_pretty_library(entry_path)

    def _scan_pretty_library(self, lib_path: str) -> List[Dict[str, str]]:
        """
        扫描 .pretty 库目录

        Returns:
            封装列表，每个封装包含 name, path 等信息
        """
        footprints = []

        for entry in os.listdir(lib_path):
            if entry.endswith(".kicad_mod"):
                footprint_name = entry[:-10]  # 去掉 .kicad_mod
                footprints.append(
                    {
                        "name": footprint_name,
                        "path": os.path.join(lib_path, entry),
                        "library": os.path.basename(os.path.dirname(lib_path)),
                    }
                )

        return footprints

    def get_all_footprints(self) -> List[str]:
        """获取所有封装名称"""
        all_names = []
        for library, footprint_list in self.footprints.items():
            for fp in footprint_list:
                # 返回格式: Library:FootprintName
                all_names.append(f"{library}:{fp['name']}")
        return all_names

    def search_footprints(self, keyword: str) -> List[str]:
        """
        搜索封装

        Args:
            keyword: 关键词

        Returns:
            匹配的封装列表
        """
        keyword_lower = keyword.lower()
        results = []

        for library, footprint_list in self.footprints.items():
            for fp in footprint_list:
                if keyword_lower in fp["name"].lower():
                    results.append(f"{library}:{fp['name']}")

        return results

    def get_libraries(self) -> List[str]:
        """获取所有库名称"""
        return list(self.footprints.keys())

    def get_footprints_by_library(self, library: str) -> List[str]:
        """获取指定库的封装"""
        if library in self.footprints:
            return [f"{library}:{fp['name']}" for fp in self.footprints[library]]
        return []


# 全局实例
_footprint_library_manager: Optional[FootprintLibraryManager] = None


def get_footprint_library_manager() -> FootprintLibraryManager:
    """获取封装库管理器单例"""
    global _footprint_library_manager
    if _footprint_library_manager is None:
        _footprint_library_manager = FootprintLibraryManager()
    return _footprint_library_manager

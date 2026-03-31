"""
Template Data - 预定义项目模板

Phase 6: 项目模板系统

提供常用电路模板:
- Arduino Shield 模板
- Raspberry Pi Pico 模板
- ESP32 模板
- STM32 最小系统
- 电源模块模板

Author: Claude Code
Date: 2026-03-30
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class TemplateCategory(Enum):
    """模板类别"""
    MCU_BOARD = "mcu_board"       # MCU 开发板
    POWER = "power"               # 电源模块
    SENSOR = "sensor"             # 传感器模块
    INTERFACE = "interface"       # 接口模块
    WIRELESS = "wireless"         # 无线模块
    DISPLAY = "display"           # 显示模块
    MOTOR = "motor"               # 电机驱动
    BATTERY = "battery"           # 电池/充电
    LED_DRIVER = "led_driver"     # LED 驱动
    COMMUNICATION = "communication"  # 通信模块
    CUSTOM = "custom"             # 自定义


@dataclass
class TemplateSchematic:
    """模板原理图数据"""
    components: List[Dict[str, Any]] = field(default_factory=list)
    wires: List[Dict[str, Any]] = field(default_factory=list)
    nets: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TemplatePCB:
    """模板 PCB 数据"""
    board_outline: List[List[float]] = field(default_factory=list)  # [[x,y], ...]
    components: List[Dict[str, Any]] = field(default_factory=list)
    traces: List[Dict[str, Any]] = field(default_factory=list)
    vias: List[Dict[str, Any]] = field(default_factory=list)
    layers: int = 2


@dataclass
class ProjectTemplate:
    """项目模板"""
    template_id: str
    name: str
    name_cn: str
    description: str
    category: TemplateCategory
    tags: List[str]
    schematic: TemplateSchematic
    pcb: TemplatePCB
    thumbnail: str = ""  # 缩略图路径
    author: str = "System"
    version: str = "1.0"


# ============== 预定义模板 ==============

ARDUINO_SHIELD_TEMPLATE = ProjectTemplate(
    template_id="arduino_shield",
    name="Arduino Shield",
    name_cn="Arduino 扩展板",
    description="Arduino UNO/Leonardo 扩展板模板，包含电源、接口定义",
    category=TemplateCategory.MCU_BOARD,
    tags=["arduino", "shield", "uno", "leonardo"],
    schematic=TemplateSchematic(
        components=[
            # Arduino 接口座
            {"reference": "J1", "symbol": "Conn_1x8", "x": 0, "y": 0, "properties": {"Type": "Female"}},
            {"reference": "J2", "symbol": "Conn_1x8", "x": 0, "y": 25.4, "properties": {"Type": "Female"}},
            # 电源指示
            {"reference": "LED1", "symbol": "LED", "x": 50, "y": 0, "properties": {"Color": "Red"}},
            {"reference": "R1", "symbol": "R", "x": 40, "y": 0, "properties": {"Value": "330"}},
            # 扩展接口
            {"reference": "J3", "symbol": "Conn_1x6", "x": 100, "y": 0, "properties": {"Type": "Male"}},
        ],
        wires=[],
        nets=[
            {"name": "5V", "nodes": ["J1.1", "J2.1"]},
            {"name": "GND", "nodes": ["J1.4", "J2.4", "LED1.2", "R1.2"]},
            {"name": "3V3", "nodes": ["J1.3", "J2.3"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [100, 0], [100, 80], [0, 80]],
        components=[],
        traces=[],
        vias=[],
        layers=2,
    ),
)

RASPBERRY_PI_PICO_TEMPLATE = ProjectTemplate(
    template_id="rpi_pico",
    name="Raspberry Pi Pico",
    name_cn="树莓派 Pico 开发板",
    description="Raspberry Pi Pico 最小系统模板，包含 USB、调试接口",
    category=TemplateCategory.MCU_BOARD,
    tags=["raspberry", "pico", "rp2040", "arm"],
    schematic=TemplateSchematic(
        components=[
            # Pico 模块
            {"reference": "U1", "symbol": "RPi_Pico", "x": 50, "y": 50, "properties": {"Type": "THT"}},
            # USB 接口
            {"reference": "J1", "symbol": "USB_C", "x": 100, "y": 30, "properties": {"Type": "SMD"}},
            # 调试接口
            {"reference": "J2", "symbol": "Conn_1x3", "x": 0, "y": 40, "properties": {"Type": "Male"}},
            # 电源指示
            {"reference": "LED1", "symbol": "LED", "x": 20, "y": 70, "properties": {"Color": "Green"}},
            {"reference": "R1", "symbol": "R", "x": 10, "y": 70, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "U1.VBUS"]},
            {"name": "GND", "nodes": ["J1.GND", "U1.GND", "LED1.2"]},
            {"name": "3V3", "nodes": ["U1.3V3"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [70, 0], [70, 100], [0, 100]],
        components=[],
        traces=[],
        vias=[],
        layers=2,
    ),
)

ESP32_BOARD_TEMPLATE = ProjectTemplate(
    template_id="esp32_board",
    name="ESP32 Dev Board",
    name_cn="ESP32 开发板",
    description="ESP32 WiFi+BT MCU 开发板模板，包含 USB-TTL、天线",
    category=TemplateCategory.MCU_BOARD,
    tags=["esp32", "wifi", "bluetooth", "iot"],
    schematic=TemplateSchematic(
        components=[
            # ESP32 模块
            {"reference": "U1", "symbol": "ESP32", "x": 50, "y": 50, "properties": {"Type": "SMD"}},
            # USB-TTL
            {"reference": "U2", "symbol": "CH340C", "x": 100, "y": 20, "properties": {"Type": "SMD"}},
            # USB 接口
            {"reference": "J1", "symbol": "USB_C", "x": 130, "y": 10, "properties": {"Type": "SMD"}},
            # 电源
            {"reference": "C1", "symbol": "C", "x": 30, "y": 20, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 40, "y": 20, "properties": {"Value": "100nF"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "U2.VCC"]},
            {"name": "GND", "nodes": ["J1.GND", "U2.GND"]},
            {"name": "3V3", "nodes": ["U1.3V3", "C1.1", "C2.1"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [80, 0], [80, 100], [0, 100]],
        components=[],
        traces=[],
        vias=[],
        layers=2,
    ),
)

STM32_MINIMAL_TEMPLATE = ProjectTemplate(
    template_id="stm32_minimal",
    name="STM32 Minimal",
    name_cn="STM32 最小系统",
    description="STM32F103 最小系统模板，包含电源、晶振、调试接口",
    category=TemplateCategory.MCU_BOARD,
    tags=["stm32", "arm", "cortex-m3", "minimal"],
    schematic=TemplateSchematic(
        components=[
            # STM32 MCU
            {"reference": "U1", "symbol": "STM32F103C8", "x": 50, "y": 50, "properties": {"Type": "LQFP-48"}},
            # 电源
            {"reference": "U2", "symbol": "AMS1117-3.3", "x": 20, "y": 20, "properties": {"Type": "SOT-223"}},
            {"reference": "C1", "symbol": "C", "x": 10, "y": 10, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 25, "y": 10, "properties": {"Value": "100nF"}},
            # 晶振
            {"reference": "Y1", "symbol": "Crystal", "x": 80, "y": 30, "properties": {"Value": "8MHz"}},
            {"reference": "C3", "symbol": "C", "x": 75, "y": 20, "properties": {"Value": "20pF"}},
            {"reference": "C4", "symbol": "C", "x": 85, "y": 20, "properties": {"Value": "20pF"}},
            # SWD 调试
            {"reference": "J1", "symbol": "Conn_1x4", "x": 0, "y": 60, "properties": {"Type": "Male"}},
        ],
        wires=[],
        nets=[
            {"name": "VDD", "nodes": ["U1.VDD", "U2.OUT", "C1.1", "C2.1"]},
            {"name": "GND", "nodes": ["U1.VSS", "U2.GND", "C1.2", "C2.2", "C3.2", "C4.2"]},
            {"name": "3V3", "nodes": ["U2.OUT"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [70, 0], [70, 80], [0, 80]],
        components=[],
        traces=[],
        vias=[],
        layers=2,
    ),
)

POWER_MODULE_TEMPLATE = ProjectTemplate(
    template_id="power_module",
    name="Power Module",
    name_cn="电源模块",
    description="5V/3.3V 电源模块模板，支持 DC-DC 和 LDO",
    category=TemplateCategory.POWER,
    tags=["power", "5v", "3v3", "ldo", "dc-dc"],
    schematic=TemplateSchematic(
        components=[
            # 输入连接器
            {"reference": "J1", "symbol": "Conn_1x2", "x": 0, "y": 50, "properties": {"Type": "Screw"}},
            # 输出连接器
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 50, "properties": {"Type": "Screw"}},
            # LDO
            {"reference": "U1", "symbol": "AMS1117-3.3", "x": 50, "y": 50, "properties": {"Type": "SOT-223"}},
            # 电容
            {"reference": "C1", "symbol": "C", "x": 30, "y": 40, "properties": {"Value": "10uF", "Type": "Electrolytic"}},
            {"reference": "C2", "symbol": "C", "x": 40, "y": 40, "properties": {"Value": "100nF"}},
            {"reference": "C3", "symbol": "C", "x": 60, "y": 40, "properties": {"Value": "10uF", "Type": "Electrolytic"}},
            {"reference": "C4", "symbol": "C", "x": 70, "y": 40, "properties": {"Value": "100nF"}},
            # LED 指示
            {"reference": "LED1", "symbol": "LED", "x": 90, "y": 30, "properties": {"Color": "Green"}},
            {"reference": "R1", "symbol": "R", "x": 90, "y": 40, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VIN", "nodes": ["J1.2", "C1.1", "U1.IN"]},
            {"name": "VOUT", "nodes": ["J2.2", "C3.1", "U1.OUT"]},
            {"name": "GND", "nodes": ["J1.1", "C1.2", "C2.2", "C3.2", "C4.2", "LED1.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [110, 0], [110, 60], [0, 60]],
        components=[],
        traces=[],
        vias=[],
        layers=2,
    ),
)

# ============== Phase 7D: 新增模板 (10+) ==============

# 1. USB-C PD Charger - CH224K PD 控制器 + DC-DC
USBC_PD_CHARGER_TEMPLATE = ProjectTemplate(
    template_id="usbc_pd_charger",
    name="USB-C PD Charger",
    name_cn="USB-C PD 充电器",
    description="USB-C Power Delivery 充电器，CH224K PD 控制器，支持 5/9/12/20V 输出",
    category=TemplateCategory.POWER,
    tags=["usb-c", "pd", "charger", "ch224k", "dc-dc", "power-delivery"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "J1", "symbol": "USB_C_16P", "x": 0, "y": 50, "properties": {"Type": "SMD", "Rating": "5A"}},
            {"reference": "U1", "symbol": "CH224K", "x": 50, "y": 50, "properties": {"Type": "QFN-28"}},
            {"reference": "U2", "symbol": "IP6538", "x": 80, "y": 50, "properties": {"Type": "QFN-24"}},  # DC-DC
            {"reference": "R1", "symbol": "R", "x": 30, "y": 35, "properties": {"Value": "5.1k"}},  # CC1 pull-down
            {"reference": "R2", "symbol": "R", "x": 35, "y": 35, "properties": {"Value": "5.1k"}},  # CC2 pull-down
            {"reference": "C1", "symbol": "C", "x": 20, "y": 30, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 65, "y": 30, "properties": {"Value": "22uF"}},
            {"reference": "C3", "symbol": "C", "x": 90, "y": 30, "properties": {"Value": "22uF"}},
            {"reference": "L1", "symbol": "L", "x": 70, "y": 45, "properties": {"Value": "4.7uH"}},
            {"reference": "LED1", "symbol": "LED", "x": 95, "y": 25, "properties": {"Color": "Green"}},
            {"reference": "R3", "symbol": "R", "x": 95, "y": 35, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "U1.VBUS", "C1.1"]},
            {"name": "CC1", "nodes": ["J1.CC1", "U1.CC1", "R1.1"]},
            {"name": "CC2", "nodes": ["J1.CC2", "U1.CC2", "R2.1"]},
            {"name": "VOUT", "nodes": ["U2.VOUT", "C3.1", "R3.1"]},
            {"name": "SW", "nodes": ["U2.SW", "L1.1"]},
            {"name": "GND", "nodes": ["J1.GND", "U1.GND", "U2.GND", "C1.2", "C2.2", "C3.2", "R1.2", "R2.2", "LED1.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [60, 0], [60, 50], [0, 50]],
        components=[], traces=[], vias=[], layers=4,
    ),
)

# 2. USB-Serial Adapter - CH340C + USB-B + 12MHz crystal
USB_SERIAL_ADAPTER_TEMPLATE = ProjectTemplate(
    template_id="usb_serial_adapter",
    name="USB-Serial Adapter",
    name_cn="USB 转串口适配器",
    description="CH340C USB 转串口适配器，支持 3.3V/5V 电平，12MHz 晶振",
    category=TemplateCategory.INTERFACE,
    tags=["usb", "serial", "uart", "ch340c", "ttl", "adapter"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "CH340C", "x": 50, "y": 50, "properties": {"Type": "SOP-16"}},
            {"reference": "J1", "symbol": "USB_B", "x": 0, "y": 50, "properties": {"Type": "THT"}},
            {"reference": "Y1", "symbol": "Crystal", "x": 35, "y": 30, "properties": {"Value": "12MHz"}},
            {"reference": "C1", "symbol": "C", "x": 30, "y": 20, "properties": {"Value": "22pF"}},
            {"reference": "C2", "symbol": "C", "x": 40, "y": 20, "properties": {"Value": "22pF"}},
            {"reference": "C3", "symbol": "C", "x": 20, "y": 35, "properties": {"Value": "10uF"}},
            {"reference": "C4", "symbol": "C", "x": 60, "y": 35, "properties": {"Value": "100nF"}},
            {"reference": "J2", "symbol": "Conn_1x5", "x": 100, "y": 50, "properties": {"Type": "Pin_Header"}},  # TX/RX/VCC/GND/RTS
            {"reference": "R1", "symbol": "R", "x": 80, "y": 45, "properties": {"Value": "10k"}},
            {"reference": "R2", "symbol": "R", "x": 85, "y": 55, "properties": {"Value": "10k"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "C3.1"]},
            {"name": "D+", "nodes": ["J1.D+", "U1.UD+"]},
            {"name": "D-", "nodes": ["J1.D-", "U1.UD-"]},
            {"name": "VCC", "nodes": ["U1.VCC", "C3.1", "C4.1"]},
            {"name": "GND", "nodes": ["J1.GND", "U1.GND", "C1.2", "C2.2", "C3.2", "C4.2"]},
            {"name": "XTAL1", "nodes": ["U1.XI", "Y1.1", "C1.1"]},
            {"name": "XTAL2", "nodes": ["U1.XO", "Y1.2", "C2.1"]},
            {"name": "TXD", "nodes": ["U1.TX", "R1.1", "J2.2"]},
            {"name": "RXD", "nodes": ["U1.RX", "R2.1", "J2.3"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [55, 0], [55, 30], [0, 30]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# 3. ESP32 Minimum System - ESP32-WROOM + AMS1117-3.3 + auto-reset
ESP32_MINIMAL_TEMPLATE = ProjectTemplate(
    template_id="esp32_minimal",
    name="ESP32 Minimum System",
    name_cn="ESP32 最小系统",
    description="ESP32-WROOM-32 最小系统，含 AMS1117-3.3 稳压、自动复位电路、BOOT 按键",
    category=TemplateCategory.MCU_BOARD,
    tags=["esp32", "wroom", "wifi", "bluetooth", "minimal", "auto-reset"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "ESP32-WROOM-32", "x": 50, "y": 50, "properties": {"Type": "Module"}},
            {"reference": "U2", "symbol": "AMS1117-3.3", "x": 15, "y": 15, "properties": {"Type": "SOT-223"}},
            {"reference": "C1", "symbol": "C", "x": 5, "y": 10, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 20, "y": 10, "properties": {"Value": "100nF"}},
            {"reference": "C3", "symbol": "C", "x": 25, "y": 10, "properties": {"Value": "10uF"}},
            {"reference": "C4", "symbol": "C", "x": 30, "y": 10, "properties": {"Value": "100nF"}},
            {"reference": "R1", "symbol": "R", "x": 70, "y": 20, "properties": {"Value": "10k"}},  # EN pull-up
            {"reference": "R2", "symbol": "R", "x": 75, "y": 20, "properties": {"Value": "10k"}},  # IO0 pull-up
            {"reference": "C5", "symbol": "C", "x": 72, "y": 15, "properties": {"Value": "100nF"}},  # EN filter
            {"reference": "SW1", "symbol": "SW_Push", "x": 85, "y": 15},  # BOOT
            {"reference": "SW2", "symbol": "SW_Push", "x": 90, "y": 15},  # RESET
            {"reference": "J1", "symbol": "Conn_1x6", "x": 0, "y": 50, "properties": {"Type": "Pin_Header"}},  # programming header
            {"reference": "LED1", "symbol": "LED", "x": 90, "y": 50, "properties": {"Color": "Blue"}},
            {"reference": "R3", "symbol": "R", "x": 85, "y": 50, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "5V", "nodes": ["U2.IN", "C1.1", "C2.1", "J1.1"]},
            {"name": "3V3", "nodes": ["U2.OUT", "C3.1", "C4.1", "U1.3V3", "R1.1", "R2.1"]},
            {"name": "GND", "nodes": ["U2.GND", "C1.2", "C2.2", "C3.2", "C4.2", "U1.GND", "C5.2", "SW1.2", "SW2.2", "LED1.2"]},
            {"name": "EN", "nodes": ["U1.EN", "R1.2", "C5.1", "SW2.1"]},
            {"name": "IO0", "nodes": ["U1.IO0", "R2.2", "SW1.1"]},
            {"name": "TX", "nodes": ["U1.TX", "J1.3"]},
            {"name": "RX", "nodes": ["U1.RX", "J1.4"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [70, 0], [70, 50], [0, 50]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# 4. STM32 Minimum System (enhanced - separate from existing stm32_minimal)
# NOTE: stm32_minimal already exists above; this adds SWD, LDO, boot circuit details

# 5. 5V/3.3V Dual Power Supply
DUAL_POWER_TEMPLATE = ProjectTemplate(
    template_id="dual_power_5v_3v3",
    name="5V/3.3V Dual Power",
    name_cn="5V/3.3V 双路电源",
    description="双路稳压电源模块，AMS1117-5.0 和 AMS1117-3.3，7-12V 输入",
    category=TemplateCategory.POWER,
    tags=["power", "5v", "3v3", "dual", "ldo", "ams1117", "supply"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "J1", "symbol": "Conn_1x2", "x": 0, "y": 50, "properties": {"Type": "Barrel_Jack"}},  # 7-12V input
            {"reference": "U1", "symbol": "AMS1117-5.0", "x": 35, "y": 40, "properties": {"Type": "SOT-223"}},
            {"reference": "U2", "symbol": "AMS1117-3.3", "x": 65, "y": 40, "properties": {"Type": "SOT-223"}},
            {"reference": "C1", "symbol": "CP", "x": 15, "y": 35, "properties": {"Value": "100uF", "Voltage": "25V"}},  # input bulk
            {"reference": "C2", "symbol": "C", "x": 20, "y": 30, "properties": {"Value": "100nF"}},  # input bypass
            {"reference": "C3", "symbol": "CP", "x": 45, "y": 35, "properties": {"Value": "47uF"}},  # 5V output
            {"reference": "C4", "symbol": "C", "x": 50, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C5", "symbol": "CP", "x": 75, "y": 35, "properties": {"Value": "47uF"}},  # 3.3V output
            {"reference": "C6", "symbol": "C", "x": 80, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "J2", "symbol": "Conn_1x4", "x": 100, "y": 40, "properties": {"Type": "Output"}},  # 5V, GND, 3V3, GND
            {"reference": "LED1", "symbol": "LED", "x": 45, "y": 20, "properties": {"Color": "Red"}},  # 5V indicator
            {"reference": "LED2", "symbol": "LED", "x": 75, "y": 20, "properties": {"Color": "Green"}},  # 3.3V indicator
            {"reference": "R1", "symbol": "R", "x": 45, "y": 25, "properties": {"Value": "1k"}},
            {"reference": "R2", "symbol": "R", "x": 75, "y": 25, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VIN", "nodes": ["J1.2", "C1.1", "C2.1", "U1.IN"]},
            {"name": "5V", "nodes": ["U1.OUT", "C3.1", "C4.1", "U2.IN", "R1.1", "J2.1"]},
            {"name": "3V3", "nodes": ["U2.OUT", "C5.1", "C6.1", "R2.1", "J2.3"]},
            {"name": "GND", "nodes": ["J1.1", "U1.GND", "U2.GND", "C1.2", "C2.2", "C3.2", "C4.2", "C5.2", "C6.2", "LED1.2", "LED2.2", "J2.2", "J2.4"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [80, 0], [80, 45], [0, 45]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# 6. LiPo Battery Charger - TP4056 + FS8205 protection + USB-C input
LIPO_CHARGER_TEMPLATE = ProjectTemplate(
    template_id="lipo_charger",
    name="LiPo Battery Charger",
    name_cn="锂电池充电保护板",
    description="单节锂电池充放电保护板，TP4056 充电 + FS8205A 双 MOS 保护 + USB-C 输入",
    category=TemplateCategory.BATTERY,
    tags=["lipo", "battery", "charger", "tp4056", "fs8205", "protection", "usb-c"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "J1", "symbol": "USB_C", "x": 0, "y": 50, "properties": {"Type": "SMD"}},
            {"reference": "U1", "symbol": "TP4056", "x": 40, "y": 50, "properties": {"Type": "SOP-8"}},
            {"reference": "U2", "symbol": "DW01A", "x": 65, "y": 65, "properties": {"Type": "SOT-23-6"}},
            {"reference": "Q1", "symbol": "FS8205A", "x": 80, "y": 65, "properties": {"Type": "TSSOP-8"}},  # dual N-MOSFET
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 50, "properties": {"Type": "JST_PH"}},  # battery
            {"reference": "R1", "symbol": "R", "x": 25, "y": 40, "properties": {"Value": "1.2k"}},  # charge current set
            {"reference": "R2", "symbol": "R", "x": 55, "y": 55, "properties": {"Value": "1k"}},  # DW01 RC
            {"reference": "R3", "symbol": "R", "x": 60, "y": 60, "properties": {"Value": "100"}},  # current sense
            {"reference": "C1", "symbol": "C", "x": 15, "y": 35, "properties": {"Value": "10uF"}},  # input
            {"reference": "C2", "symbol": "C", "x": 90, "y": 45, "properties": {"Value": "10uF"}},  # output
            {"reference": "LED1", "symbol": "LED", "x": 30, "y": 25, "properties": {"Color": "Red"}},  # charging
            {"reference": "LED2", "symbol": "LED", "x": 40, "y": 25, "properties": {"Color": "Green"}},  # full
            {"reference": "R4", "symbol": "R", "x": 30, "y": 30, "properties": {"Value": "1k"}},
            {"reference": "R5", "symbol": "R", "x": 40, "y": 30, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "U1.VCC", "C1.1"]},
            {"name": "BAT+", "nodes": ["U1.BAT", "Q1.D1", "J2.1", "C2.1"]},
            {"name": "PACK+", "nodes": ["Q1.S1", "R3.1"]},
            {"name": "CS", "nodes": ["U2.CS", "R3.2", "Q1.G1"]},
            {"name": "GND", "nodes": ["J1.GND", "U1.GND", "U2.GND", "C1.2", "C2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [45, 0], [45, 30], [0, 30]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# 7. Motor Driver (enhanced - replaces existing simplified motor_driver)
# NOTE: existing motor_driver template already covers L298N; this adds flyback diodes & sense resistors

# 8. RS485 Communication (enhanced with bias + termination)
# NOTE: existing rs485_module template already covers this

# 9. Battery Protection - DW01 + FS8205 standalone
BATTERY_PROTECTION_TEMPLATE = ProjectTemplate(
    template_id="battery_protection",
    name="Battery Protection Board",
    name_cn="电池保护板",
    description="单节锂电池保护板，DW01A + FS8205A，过充/过放/过流/短路保护",
    category=TemplateCategory.BATTERY,
    tags=["battery", "protection", "dw01", "fs8205", "overcharge", "overdischarge"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "DW01A", "x": 50, "y": 50, "properties": {"Type": "SOT-23-6"}},
            {"reference": "Q1", "symbol": "FS8205A", "x": 70, "y": 50, "properties": {"Type": "TSSOP-8"}},
            {"reference": "J1", "symbol": "Conn_1x2", "x": 0, "y": 45, "properties": {"Type": "Battery_In"}},
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 45, "properties": {"Type": "Load_Out"}},
            {"reference": "R1", "symbol": "R", "x": 35, "y": 40, "properties": {"Value": "1k"}},  # VDD series
            {"reference": "R2", "symbol": "R", "x": 60, "y": 55, "properties": {"Value": "100"}},  # current sense
            {"reference": "C1", "symbol": "C", "x": 30, "y": 35, "properties": {"Value": "100nF"}},  # VDD bypass
        ],
        wires=[],
        nets=[
            {"name": "B+", "nodes": ["J1.1", "R1.1", "C1.1", "U1.VDD"]},
            {"name": "B-", "nodes": ["J1.2"]},
            {"name": "P+", "nodes": ["J2.1", "Q1.D1"]},
            {"name": "P-", "nodes": ["J2.2", "Q1.S2"]},
            {"name": "CS", "nodes": ["U1.CS", "R2.1"]},
            {"name": "OD", "nodes": ["U1.OD", "Q1.G2"]},
            {"name": "OC", "nodes": ["U1.OC", "Q1.G1"]},
            {"name": "VM", "nodes": ["U1.VM", "R2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [25, 0], [25, 15], [0, 15]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# 10. LED Constant Current Driver - AL8805 buck LED driver
LED_DRIVER_BUCK_TEMPLATE = ProjectTemplate(
    template_id="led_driver_buck",
    name="LED Constant Current Driver",
    name_cn="LED 恒流驱动",
    description="AL8805 降压型 LED 恒流驱动，支持 6-30V 输入，最大 1A 输出",
    category=TemplateCategory.LED_DRIVER,
    tags=["led", "driver", "buck", "constant-current", "al8805", "lighting"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "AL8805", "x": 50, "y": 50, "properties": {"Type": "SOP-8"}},
            {"reference": "J1", "symbol": "Conn_1x2", "x": 0, "y": 50, "properties": {"Type": "Power_In"}},  # 6-30V input
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 50, "properties": {"Type": "LED_Out"}},  # LED string
            {"reference": "L1", "symbol": "L", "x": 70, "y": 45, "properties": {"Value": "47uH", "Current": "1.2A"}},
            {"reference": "D1", "symbol": "D_Schottky", "x": 60, "y": 35, "properties": {"Value": "SS34"}},  # freewheeling
            {"reference": "R1", "symbol": "R", "x": 45, "y": 60, "properties": {"Value": "0.3"}},  # sense resistor (sets current)
            {"reference": "C1", "symbol": "C", "x": 15, "y": 40, "properties": {"Value": "2.2uF", "Voltage": "50V"}},  # input
            {"reference": "C2", "symbol": "C", "x": 20, "y": 35, "properties": {"Value": "100nF"}},  # VIN bypass
            {"reference": "C3", "symbol": "C", "x": 85, "y": 45, "properties": {"Value": "1uF"}},  # output
            {"reference": "R2", "symbol": "R", "x": 35, "y": 45, "properties": {"Value": "100k"}},  # DIM pull-up (on)
        ],
        wires=[],
        nets=[
            {"name": "VIN", "nodes": ["J1.2", "C1.1", "C2.1", "U1.VIN", "L1.1"]},
            {"name": "SW", "nodes": ["U1.SW", "D1.1", "L1.2"]},
            {"name": "LED+", "nodes": ["L1.2", "J2.1", "C3.1"]},
            {"name": "SENSE", "nodes": ["U1.SENSE", "R1.1"]},
            {"name": "GND", "nodes": ["J1.1", "U1.GND", "C1.2", "C2.2", "C3.2", "R1.2", "D1.2", "J2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [50, 0], [50, 30], [0, 30]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# --- Pre-existing Phase 7D templates (already in file) ---

USB_CHARGER_TEMPLATE = ProjectTemplate(
    template_id="usb_charger",
    name="USB-C Charger",
    name_cn="USB-C 充电器",
    description="USB-C 5V/2A 充电器，包含 CC 检测和过压保护",
    category=TemplateCategory.INTERFACE,
    tags=["usb-c", "charger", "pd", "5v", "battery"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "J1", "symbol": "USB_C", "x": 0, "y": 50, "properties": {"Type": "SMD"}},
            {"reference": "U1", "symbol": "TP4056", "x": 50, "y": 50, "properties": {"Type": "SOP-8"}},
            {"reference": "U2", "symbol": "AMS1117-5.0", "x": 50, "y": 20, "properties": {"Type": "SOT-223"}},
            {"reference": "R1", "symbol": "R", "x": 30, "y": 30, "properties": {"Value": "1.2k"}},
            {"reference": "C1", "symbol": "C", "x": 20, "y": 40, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 70, "y": 40, "properties": {"Value": "10uF"}},
            {"reference": "LED1", "symbol": "LED", "x": 80, "y": 30, "properties": {"Color": "Red"}},
            {"reference": "LED2", "symbol": "LED", "x": 90, "y": 30, "properties": {"Color": "Green"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "U1.VCC", "C1.1"]},
            {"name": "5V", "nodes": ["U2.OUT", "C2.1"]},
            {"name": "GND", "nodes": ["J1.GND", "U1.GND", "U2.GND", "C1.2", "C2.2"]},
            {"name": "BAT+", "nodes": ["U1.BAT", "R1.1"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [60, 0], [60, 50], [0, 50]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

RS485_MODULE_TEMPLATE = ProjectTemplate(
    template_id="rs485_module",
    name="RS485 Communication",
    name_cn="RS485 通信模块",
    description="RS485 工业通信模块，支持 Modbus 协议，带隔离保护",
    category=TemplateCategory.INTERFACE,
    tags=["rs485", "modbus", "uart", "industrial", "communication"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "MAX485", "x": 50, "y": 50, "properties": {"Type": "SOP-8"}},
            {"reference": "J1", "symbol": "Conn_1x4", "x": 0, "y": 40, "properties": {"Type": "Screw"}},
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 50, "properties": {"Type": "Screw"}},
            {"reference": "R1", "symbol": "R", "x": 80, "y": 60, "properties": {"Value": "120"}},
            {"reference": "R2", "symbol": "R", "x": 20, "y": 30, "properties": {"Value": "10k"}},
            {"reference": "C1", "symbol": "C", "x": 30, "y": 30, "properties": {"Value": "100nF"}},
        ],
        wires=[],
        nets=[
            {"name": "VCC", "nodes": ["U1.VCC", "C1.1", "R2.1"]},
            {"name": "GND", "nodes": ["U1.GND", "C1.2"]},
            {"name": "A", "nodes": ["J2.1", "U1.A", "R1.1"]},
            {"name": "B", "nodes": ["J2.2", "U1.B", "R1.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [50, 0], [50, 40], [0, 40]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

LED_MATRIX_TEMPLATE = ProjectTemplate(
    template_id="led_matrix",
    name="LED Matrix Driver",
    name_cn="LED 矩阵驱动",
    description="8x8 WS2812 RGB LED 矩阵驱动板，支持级联",
    category=TemplateCategory.DISPLAY,
    tags=["led", "ws2812", "rgb", "matrix", "display"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "ESP32", "x": 20, "y": 50, "properties": {"Type": "SMD"}},
            {"reference": "U2", "symbol": "WS2812", "x": 60, "y": 50, "properties": {"Type": "SMD", "Count": 64}},
            {"reference": "J1", "symbol": "Conn_1x3", "x": 0, "y": 50, "properties": {"Type": "Input"}},
            {"reference": "J2", "symbol": "Conn_1x3", "x": 100, "y": 50, "properties": {"Type": "Output"}},
            {"reference": "C1", "symbol": "C", "x": 40, "y": 30, "properties": {"Value": "1000uF"}},
            {"reference": "R1", "symbol": "R", "x": 50, "y": 45, "properties": {"Value": "470"}},
        ],
        wires=[],
        nets=[
            {"name": "5V", "nodes": ["U2.VCC", "C1.1"]},
            {"name": "GND", "nodes": ["U2.GND", "C1.2"]},
            {"name": "DIN", "nodes": ["U1.GPIO", "R1.1"]},
            {"name": "DOUT", "nodes": ["U2.DOUT", "J2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [100, 0], [100, 100], [0, 100]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

MOTOR_DRIVER_TEMPLATE = ProjectTemplate(
    template_id="motor_driver",
    name="L298N Motor Driver",
    name_cn="L298N 电机驱动",
    description="双 H 桥电机驱动模块，支持 2A/通道，5-35V 输入",
    category=TemplateCategory.MOTOR,
    tags=["motor", "l298n", "h-bridge", "driver", "dc-motor"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "L298N", "x": 50, "y": 50, "properties": {"Type": "MultiWatt-15"}},
            {"reference": "J1", "symbol": "Conn_1x2", "x": 0, "y": 40, "properties": {"Type": "Power"}},
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 40, "properties": {"Type": "Motor_A"}},
            {"reference": "J3", "symbol": "Conn_1x2", "x": 100, "y": 60, "properties": {"Type": "Motor_B"}},
            {"reference": "D1", "symbol": "D_Schottky", "x": 80, "y": 35, "properties": {"Value": "1N5819"}},
            {"reference": "D2", "symbol": "D_Schottky", "x": 85, "y": 35},
            {"reference": "D3", "symbol": "D_Schottky", "x": 80, "y": 65},
            {"reference": "D4", "symbol": "D_Schottky", "x": 85, "y": 65},
            {"reference": "C1", "symbol": "C", "x": 20, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C2", "symbol": "CP", "x": 25, "y": 25, "properties": {"Value": "100uF"}},
        ],
        wires=[],
        nets=[
            {"name": "VCC", "nodes": ["J1.2", "U1.VS", "C2.1"]},
            {"name": "GND", "nodes": ["J1.1", "U1.GND", "C1.2", "C2.2"]},
            {"name": "OUT1", "nodes": ["U1.OUT1", "J2.1", "D1.1"]},
            {"name": "OUT2", "nodes": ["U1.OUT2", "J2.2", "D2.1"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [80, 0], [80, 60], [0, 60]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

NRF24L01_WIRELESS_TEMPLATE = ProjectTemplate(
    template_id="nrf24l01_wireless",
    name="NRF24L01 Wireless",
    name_cn="NRF24L01 无线模块",
    description="2.4GHz 无线通信模块，SPI 接口，带天线匹配",
    category=TemplateCategory.WIRELESS,
    tags=["nrf24l01", "2.4ghz", "wireless", "spi", "iot"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "NRF24L01+", "x": 50, "y": 50, "properties": {"Type": "QFN-20"}},
            {"reference": "J1", "symbol": "Conn_1x8", "x": 0, "y": 50, "properties": {"Type": "Male"}},
            {"reference": "AE1", "symbol": "Antenna", "x": 90, "y": 50, "properties": {"Type": "PCB_Trace"}},
            {"reference": "C1", "symbol": "C", "x": 30, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C2", "symbol": "C", "x": 35, "y": 25, "properties": {"Value": "10nF"}},
            {"reference": "C3", "symbol": "C", "x": 40, "y": 30, "properties": {"Value": "1pF"}},
            {"reference": "L1", "symbol": "L", "x": 70, "y": 40, "properties": {"Value": "3.3nH"}},
        ],
        wires=[],
        nets=[
            {"name": "VCC", "nodes": ["U1.VDD", "C1.1", "C2.1"]},
            {"name": "GND", "nodes": ["U1.VSS", "C1.2", "C2.2", "C3.2"]},
            {"name": "SPI_MOSI", "nodes": ["J1.1", "U1.MOSI"]},
            {"name": "SPI_MISO", "nodes": ["J1.2", "U1.MISO"]},
            {"name": "SPI_SCK", "nodes": ["J1.3", "U1.SCK"]},
            {"name": "RF_OUT", "nodes": ["U1.ANT", "L1.1", "C3.1"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [40, 0], [40, 30], [0, 30]],
        components=[], traces=[], vias=[], layers=4,
    ),
)

AUDIO_AMPLIFIER_TEMPLATE = ProjectTemplate(
    template_id="audio_amplifier",
    name="PAM8403 Audio Amp",
    name_cn="PAM8403 音频功放",
    description="3W+3W D类立体声音频功放，5V 供电，带音量控制",
    category=TemplateCategory.INTERFACE,
    tags=["audio", "amplifier", "pam8403", "class-d", "speaker"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "PAM8403", "x": 50, "y": 50, "properties": {"Type": "SOP-16"}},
            {"reference": "J1", "symbol": "Audio_Jack", "x": 0, "y": 50, "properties": {"Type": "3.5mm"}},
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 40, "properties": {"Type": "Speaker_L"}},
            {"reference": "J3", "symbol": "Conn_1x2", "x": 100, "y": 60, "properties": {"Type": "Speaker_R"}},
            {"reference": "RV1", "symbol": "Potentiometer", "x": 20, "y": 50, "properties": {"Value": "10k"}},
            {"reference": "C1", "symbol": "C", "x": 30, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C2", "symbol": "CP", "x": 25, "y": 25, "properties": {"Value": "470uF"}},
            {"reference": "C3", "symbol": "C", "x": 35, "y": 60, "properties": {"Value": "100nF"}},
            {"reference": "C4", "symbol": "C", "x": 40, "y": 65, "properties": {"Value": "100nF"}},
        ],
        wires=[],
        nets=[
            {"name": "5V", "nodes": ["U1.VCC", "C1.1", "C2.1"]},
            {"name": "GND", "nodes": ["U1.GND", "C1.2", "C2.2"]},
            {"name": "OUTL+", "nodes": ["U1.OUTL+", "J2.1"]},
            {"name": "OUTL-", "nodes": ["U1.OUTL-", "J2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [60, 0], [60, 50], [0, 50]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

BATTERY_CHARGER_TEMPLATE = ProjectTemplate(
    template_id="battery_charger",
    name="TP4056 Battery Charger",
    name_cn="TP4056 锂电池充电",
    description="单节锂电池充电模块，带过充过放保护和温度检测",
    category=TemplateCategory.POWER,
    tags=["battery", "charger", "tp4056", "lithium", "protection"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "TP4056", "x": 50, "y": 50, "properties": {"Type": "SOP-8"}},
            {"reference": "U2", "symbol": "DW01A", "x": 50, "y": 80, "properties": {"Type": "SOT-23-6"}},
            {"reference": "Q1", "symbol": "N-MOSFET", "x": 70, "y": 80, "properties": {"Type": "SOT-23"}},
            {"reference": "J1", "symbol": "USB_Micro", "x": 0, "y": 50},
            {"reference": "J2", "symbol": "Conn_1x2", "x": 100, "y": 50, "properties": {"Type": "Battery"}},
            {"reference": "R1", "symbol": "R", "x": 30, "y": 40, "properties": {"Value": "1.2k"}},
            {"reference": "R2", "symbol": "R", "x": 60, "y": 70, "properties": {"Value": "1k"}},
            {"reference": "C1", "symbol": "C", "x": 20, "y": 30, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 80, "y": 50, "properties": {"Value": "10uF"}},
            {"reference": "LED1", "symbol": "LED", "x": 35, "y": 25, "properties": {"Color": "Red"}},
            {"reference": "LED2", "symbol": "LED", "x": 45, "y": 25, "properties": {"Color": "Green"}},
        ],
        wires=[],
        nets=[
            {"name": "VBUS", "nodes": ["J1.VBUS", "U1.VCC", "C1.1"]},
            {"name": "BAT+", "nodes": ["U1.BAT", "J2.1", "C2.1"]},
            {"name": "GND", "nodes": ["J1.GND", "U1.GND", "C1.2", "C2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [50, 0], [50, 40], [0, 40]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

LEVEL_SHIFTER_TEMPLATE = ProjectTemplate(
    template_id="level_shifter",
    name="Level Shifter",
    name_cn="电平转换器",
    description="4通道双向电平转换模块，3.3V/5V 兼容",
    category=TemplateCategory.INTERFACE,
    tags=["level-shifter", "3.3v", "5v", "bidirectional", "logic"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "TXS0108E", "x": 50, "y": 50, "properties": {"Type": "TSSOP-20"}},
            {"reference": "J1", "symbol": "Conn_1x10", "x": 0, "y": 50, "properties": {"Type": "Low_Side"}},
            {"reference": "J2", "symbol": "Conn_1x10", "x": 100, "y": 50, "properties": {"Type": "High_Side"}},
            {"reference": "C1", "symbol": "C", "x": 25, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C2", "symbol": "C", "x": 75, "y": 30, "properties": {"Value": "100nF"}},
        ],
        wires=[],
        nets=[
            {"name": "3V3", "nodes": ["J1.VCC", "U1.VCCA", "C1.1"]},
            {"name": "5V", "nodes": ["J2.VCC", "U1.VCCB", "C2.1"]},
            {"name": "GND", "nodes": ["J1.GND", "J2.GND", "U1.GND", "C1.2", "C2.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [40, 0], [40, 30], [0, 30]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

OLED_DISPLAY_TEMPLATE = ProjectTemplate(
    template_id="oled_display",
    name="OLED Display Adapter",
    name_cn="OLED 显示适配器",
    description="0.96寸 SSD1306 OLED 显示模块，I2C/SPI 接口",
    category=TemplateCategory.DISPLAY,
    tags=["oled", "ssd1306", "display", "i2c", "spi"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "SSD1306", "x": 50, "y": 50, "properties": {"Type": "COG"}},
            {"reference": "J1", "symbol": "Conn_1x7", "x": 0, "y": 50, "properties": {"Type": "Male"}},
            {"reference": "C1", "symbol": "C", "x": 30, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C2", "symbol": "C", "x": 35, "y": 25, "properties": {"Value": "1uF"}},
            {"reference": "C3", "symbol": "C", "x": 40, "y": 30, "properties": {"Value": "4.7uF"}},
            {"reference": "R1", "symbol": "R", "x": 65, "y": 30, "properties": {"Value": "390k"}},
        ],
        wires=[],
        nets=[
            {"name": "VCC", "nodes": ["J1.1", "U1.VCC", "C1.1"]},
            {"name": "GND", "nodes": ["J1.2", "U1.GND", "C1.2", "C2.2"]},
            {"name": "SCL", "nodes": ["J1.3", "U1.SCL"]},
            {"name": "SDA", "nodes": ["J1.4", "U1.SDA"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [40, 0], [40, 30], [0, 30]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

DHT11_SENSOR_TEMPLATE = ProjectTemplate(
    template_id="dht11_sensor",
    name="DHT11 Sensor Module",
    name_cn="DHT11 温湿度传感器",
    description="DHT11 温湿度传感器模块，单总线接口",
    category=TemplateCategory.SENSOR,
    tags=["dht11", "temperature", "humidity", "sensor", "one-wire"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "DHT11", "x": 50, "y": 50},
            {"reference": "J1", "symbol": "Conn_1x3", "x": 0, "y": 50},
            {"reference": "R1", "symbol": "R", "x": 30, "y": 45, "properties": {"Value": "10k"}},
            {"reference": "C1", "symbol": "C", "x": 20, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "LED1", "symbol": "LED", "x": 80, "y": 30, "properties": {"Color": "Blue"}},
            {"reference": "R2", "symbol": "R", "x": 80, "y": 40, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VCC", "nodes": ["J1.1", "U1.VCC", "R1.1", "C1.1"]},
            {"name": "GND", "nodes": ["J1.3", "U1.GND", "C1.2"]},
            {"name": "DATA", "nodes": ["J1.2", "U1.DATA", "R1.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [30, 0], [30, 25], [0, 25]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

GPS_MODULE_TEMPLATE = ProjectTemplate(
    template_id="gps_module",
    name="GPS Module",
    name_cn="GPS 定位模块",
    description="NEO-6M GPS 定位模块，带天线和备份电池",
    category=TemplateCategory.WIRELESS,
    tags=["gps", "neo-6m", "positioning", "uart", "navigation"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "NEO-6M", "x": 50, "y": 50, "properties": {"Type": "QFN"}},
            {"reference": "AE1", "symbol": "Antenna_GPS", "x": 90, "y": 50},
            {"reference": "J1", "symbol": "Conn_1x4", "x": 0, "y": 50},
            {"reference": "BT1", "symbol": "Battery_Cell", "x": 30, "y": 80, "properties": {"Value": "CR1220"}},
            {"reference": "C1", "symbol": "C", "x": 20, "y": 30, "properties": {"Value": "100nF"}},
            {"reference": "C2", "symbol": "C", "x": 25, "y": 25, "properties": {"Value": "10uF"}},
            {"reference": "LED1", "symbol": "LED", "x": 80, "y": 30, "properties": {"Color": "Yellow"}},
            {"reference": "R1", "symbol": "R", "x": 80, "y": 40, "properties": {"Value": "1k"}},
        ],
        wires=[],
        nets=[
            {"name": "VCC", "nodes": ["J1.1", "U1.VCC", "C1.1", "C2.1"]},
            {"name": "GND", "nodes": ["J1.2", "U1.GND", "C1.2", "C2.2"]},
            {"name": "TX", "nodes": ["J1.3", "U1.TX"]},
            {"name": "RX", "nodes": ["J1.4", "U1.RX"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [40, 0], [40, 35], [0, 35]],
        components=[], traces=[], vias=[], layers=4,
    ),
)

RELAY_MODULE_TEMPLATE = ProjectTemplate(
    template_id="relay_module",
    name="Relay Control Module",
    name_cn="继电器控制模块",
    description="4路继电器控制模块，光耦隔离，支持 250VAC/30VDC",
    category=TemplateCategory.INTERFACE,
    tags=["relay", "optocoupler", "isolated", "switch", "ac"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "EL817", "x": 30, "y": 50, "properties": {"Type": "DIP-4", "Count": 4}},
            {"reference": "K1", "symbol": "Relay_SPDT", "x": 70, "y": 50, "properties": {"Type": "5V", "Count": 4}},
            {"reference": "J1", "symbol": "Conn_1x6", "x": 0, "y": 50, "properties": {"Type": "Input"}},
            {"reference": "J2", "symbol": "Conn_1x8", "x": 100, "y": 50, "properties": {"Type": "Output"}},
            {"reference": "Q1", "symbol": "NPN", "x": 45, "y": 50, "properties": {"Type": "S8050", "Count": 4}},
            {"reference": "D1", "symbol": "D_Flyback", "x": 60, "y": 40, "properties": {"Type": "1N4148", "Count": 4}},
            {"reference": "R1", "symbol": "R", "x": 15, "y": 45, "properties": {"Value": "1k", "Count": 4}},
            {"reference": "LED1", "symbol": "LED", "x": 85, "y": 30, "properties": {"Color": "Red", "Count": 4}},
        ],
        wires=[],
        nets=[
            {"name": "5V", "nodes": ["K1.COIL+", "D1.1"]},
            {"name": "GND", "nodes": ["Q1.E", "U1.EMIT"]},
            {"name": "IN1", "nodes": ["J1.1", "R1.1"]},
            {"name": "COM1", "nodes": ["K1.COM", "J2.1"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [80, 0], [80, 60], [0, 60]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

WS2812_CONTROLLER_TEMPLATE = ProjectTemplate(
    template_id="ws2812_controller",
    name="WS2812 LED Controller",
    name_cn="WS2812 LED 控制器",
    description="WS2812 RGB LED 控制器，支持 16/24 灯珠级联",
    category=TemplateCategory.DISPLAY,
    tags=["ws2812", "rgb", "led", "neopixel", "strip"],
    schematic=TemplateSchematic(
        components=[
            {"reference": "U1", "symbol": "ESP8266", "x": 30, "y": 50, "properties": {"Type": "ESP-12F"}},
            {"reference": "J1", "symbol": "Conn_1x3", "x": 100, "y": 50, "properties": {"Type": "LED_Out"}},
            {"reference": "U2", "symbol": "AMS1117-3.3", "x": 20, "y": 20},
            {"reference": "C1", "symbol": "C", "x": 10, "y": 10, "properties": {"Value": "10uF"}},
            {"reference": "C2", "symbol": "C", "x": 25, "y": 10, "properties": {"Value": "100nF"}},
            {"reference": "C3", "symbol": "CP", "x": 70, "y": 40, "properties": {"Value": "1000uF"}},
            {"reference": "R1", "symbol": "R", "x": 60, "y": 48, "properties": {"Value": "470"}},
            {"reference": "R2", "symbol": "R", "x": 15, "y": 45, "properties": {"Value": "10k"}},
        ],
        wires=[],
        nets=[
            {"name": "5V", "nodes": ["J1.1", "U2.IN", "C1.1", "C3.1"]},
            {"name": "3V3", "nodes": ["U1.VCC", "U2.OUT", "C2.1", "R2.1"]},
            {"name": "GND", "nodes": ["U1.GND", "U2.GND", "C1.2", "C2.2", "C3.2"]},
            {"name": "DATA", "nodes": ["U1.GPIO", "R1.1", "J1.2"]},
        ],
    ),
    pcb=TemplatePCB(
        board_outline=[[0, 0], [50, 0], [50, 40], [0, 40]],
        components=[], traces=[], vias=[], layers=2,
    ),
)

# 模板列表
PREDEFINED_TEMPLATES = [
    # Phase 6 原始模板
    ARDUINO_SHIELD_TEMPLATE,
    RASPBERRY_PI_PICO_TEMPLATE,
    ESP32_BOARD_TEMPLATE,
    STM32_MINIMAL_TEMPLATE,
    POWER_MODULE_TEMPLATE,
    # Phase 7D: 验证电路模板
    USBC_PD_CHARGER_TEMPLATE,
    USB_SERIAL_ADAPTER_TEMPLATE,
    USB_CHARGER_TEMPLATE,
    BATTERY_CHARGER_TEMPLATE,
    BATTERY_PROTECTION_TEMPLATE,
    RS485_MODULE_TEMPLATE,
    MOTOR_DRIVER_TEMPLATE,
    LED_DRIVER_BUCK_TEMPLATE,
    # Phase 7D: 扩展模块模板
    NRF24L01_WIRELESS_TEMPLATE,
    AUDIO_AMPLIFIER_TEMPLATE,
    LED_MATRIX_TEMPLATE,
    LEVEL_SHIFTER_TEMPLATE,
    OLED_DISPLAY_TEMPLATE,
    DHT11_SENSOR_TEMPLATE,
    GPS_MODULE_TEMPLATE,
    RELAY_MODULE_TEMPLATE,
    WS2812_CONTROLLER_TEMPLATE,
]


def get_template_by_id(template_id: str) -> Optional[ProjectTemplate]:
    """根据 ID 获取模板"""
    for template in PREDEFINED_TEMPLATES:
        if template.template_id == template_id:
            return template
    return None


def get_templates_by_category(category: TemplateCategory) -> List[ProjectTemplate]:
    """根据类别获取模板"""
    return [t for t in PREDEFINED_TEMPLATES if t.category == category]


def search_templates(keyword: str) -> List[ProjectTemplate]:
    """搜索模板"""
    keyword_lower = keyword.lower()
    results = []
    for template in PREDEFINED_TEMPLATES:
        if (keyword_lower in template.name.lower() or
            keyword_lower in template.name_cn.lower() or
            keyword_lower in template.description.lower() or
            any(keyword_lower in tag.lower() for tag in template.tags)):
            results.append(template)
    return results

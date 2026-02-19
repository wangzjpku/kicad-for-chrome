"""
AI Routes - AI 智能项目创建 API
"""

import logging
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from kicad_ipc_manager import (
    get_footprint_recommendations,
    search_footprint_library,
    get_all_libraries,
    get_default_footprint_for_component,
)

# 导入GLM-4客户端
from glm4_client import get_glm4_client, is_glm4_available

logger = logging.getLogger(__name__)

# ========== 加载本地知识库 ==========
_component_db = None


def get_component_db():
    """获取元件数据库"""
    global _component_db
    if _component_db is None:
        # 修正路径：component_knowledge在agent目录下
        db_path = (
            Path(__file__).parent.parent / "component_knowledge" / "component_db.json"
        )
        if db_path.exists():
            with open(db_path, "r", encoding="utf-8") as f:
                _component_db = json.load(f)
                logger.info(
                    f"已加载元件知识库: {len(_component_db.get('components', {}))} 个元件"
                )
        else:
            logger.warning(f"元件知识库文件不存在: {db_path}")
            _component_db = {"components": {}, "templates": {}}
    return _component_db


def get_component_info(model: str) -> Optional[Dict[str, Any]]:
    """根据型号获取元件信息"""
    db = get_component_db()
    # 精确匹配
    if model in db.get("components", {}):
        return db["components"][model]
    # 模糊匹配
    model_upper = model.upper()
    for comp_key, comp_data in db.get("components", {}).items():
        if model_upper in comp_key.upper() or comp_key.upper() in model_upper:
            return comp_data
    return None


def get_circuit_template(template_name: str) -> Optional[Dict[str, Any]]:
    """获取典型电路模板"""
    db = get_component_db()
    return db.get("templates", {}).get(template_name)


def get_schematic_pins(model: str) -> List[Dict[str, Any]]:
    """获取原理图引脚定义 - 使用知识库"""
    comp_info = get_component_info(model)
    if comp_info and "pins" in comp_info:
        return comp_info["pins"]
    return []


def get_symbol_library(model: str) -> Optional[str]:
    """获取元件符号库名称"""
    comp_info = get_component_info(model)
    if comp_info:
        return comp_info.get("symbol_library")
    return None


def get_typical_circuits(model: str) -> List[str]:
    """获取元件的典型电路"""
    comp_info = get_component_info(model)
    if comp_info:
        return comp_info.get("typical_circuits", [])
    return []


router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


class AnalyzeRequest(BaseModel):
    requirements: str


class ComponentSpec(BaseModel):
    name: str
    model: str
    package: str
    quantity: int = 1
    footprint: Optional[str] = None  # 添加封装字段


class ParameterSpec(BaseModel):
    key: str
    value: str
    unit: Optional[str] = None


class ProjectSpec(BaseModel):
    name: str
    description: str
    components: List[ComponentSpec] = []
    parameters: List[ParameterSpec] = []


class SchematicComponent(BaseModel):
    id: str
    name: str
    model: str
    position: Dict[str, float]
    pins: List[Dict[str, Any]] = []


class SchematicWire(BaseModel):
    id: str
    points: List[Dict[str, float]]
    net: str


class SchematicNet(BaseModel):
    id: str
    name: str


class SchematicData(BaseModel):
    components: List[SchematicComponent] = []
    wires: List[SchematicWire] = []
    nets: List[SchematicNet] = []


class AnalyzeResponse(BaseModel):
    spec: ProjectSpec
    schematic: SchematicData


def _generate_dynamic_project(requirements: str) -> tuple:
    """
    根据用户输入动态生成项目方案

    从需求描述中提取关键信息，生成个性化的项目方案
    """
    import re

    logger.info(f"动态生成项目方案，输入: {requirements}")

    # 提取电压信息
    voltage_match = re.search(r"(\d+)\s*[Vv]", requirements)
    input_voltage = voltage_match.group(1) if voltage_match else "5"

    # 提取电流信息
    current_match = re.search(r"(\d+(?:\.\d+)?)\s*[Aa]", requirements)
    output_current = current_match.group(1) if current_match else "1"

    # 检测功能关键词
    has_motor = any(
        kw in requirements for kw in ["电机", "马达", "motor", "舵机", "servo"]
    )
    has_wifi = any(
        kw in requirements
        for kw in ["wifi", "无线", "物联网", "iot", "智能家居", "smart home"]
    )
    has_bluetooth = any(kw in requirements for kw in ["蓝牙", "bluetooth"])
    has_audio = any(
        kw in requirements for kw in ["音频", "声音", "audio", "音响", "speaker"]
    )
    has_sensor = any(
        kw in requirements for kw in ["传感器", "sensor", "测温", "温湿度"]
    )
    has_display = any(
        kw in requirements for kw in ["显示", "屏幕", "oled", "lcd", "显示屏"]
    )
    has_usb = any(kw in requirements for kw in ["usb", "串口", "uart", "转接"])
    has_battery = any(
        kw in requirements for kw in ["电池", "充电", "battery", "锂电池"]
    )
    has_led = any(kw in requirements for kw in ["led", "灯", "发光", "照明"])
    has_power = any(kw in requirements for kw in ["电源", "稳压", "power", "供电"])

    # 根据输入生成项目名称和描述
    if has_power:
        project_name = f"{input_voltage}V稳压电源"
        description = f"输入220V交流电，输出{input_voltage}V直流电，电流{output_current}A的稳压电源"
        components = [
            ComponentSpec(
                name="变压器",
                model=f"220V->{input_voltage}V 5W",
                package="THT",
                quantity=1,
            ),
            ComponentSpec(name="整流桥", model="MB6S", package="SMD", quantity=1),
            ComponentSpec(
                name="滤波电容", model="1000uF 25V", package="electrolytic", quantity=2
            ),
            ComponentSpec(
                name="稳压芯片", model="LM7805", package="TO-220", quantity=1
            ),
            ComponentSpec(
                name="输出电容", model="10uF 25V", package="0805", quantity=2
            ),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="220", unit="V AC"),
            ParameterSpec(key="输出电压", value=input_voltage, unit="V DC"),
            ParameterSpec(key="输出电流", value=output_current, unit="A"),
        ]
    elif has_wifi:
        project_name = "WiFi智能控制器"
        description = "基于ESP32的WiFi智能控制系统，支持远程控制和监测"
        components = [
            ComponentSpec(
                name="WiFi模块", model="ESP32-WROOM", package="Module", quantity=1
            ),
            ComponentSpec(
                name="继电器", model="5V 10A", package="SRD-05VDC", quantity=4
            ),
            ComponentSpec(
                name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
            ),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=4),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=4),
            ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=4),
            ComponentSpec(name="按键", model="6x6x5", package="THT", quantity=4),
            ComponentSpec(name="USB接口", model="Micro-USB", package="SMD", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value="5", unit="V DC"),
            ParameterSpec(key="通信方式", value="WiFi", unit="2.4GHz"),
            ParameterSpec(key="输出通道", value="4", unit="路"),
            ParameterSpec(key="PCB尺寸", value="50x40", unit="mm"),
        ]
    elif has_motor:
        project_name = "电机驱动控制器"
        description = f"支持多路电机PWM控制的驱动系统，输入{input_voltage}V"
        components = [
            ComponentSpec(
                name="驱动芯片", model="L298N", package="MultiWatt15", quantity=1
            ),
            ComponentSpec(
                name="单片机", model="STM32F103", package="LQFP-48", quantity=1
            ),
            ComponentSpec(
                name="稳压芯片", model="LM7805", package="TO-220", quantity=1
            ),
            ComponentSpec(
                name="电容", model="100uF 25V", package="electrolytic", quantity=2
            ),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=4),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
            ComponentSpec(name="LED", model="5mm", package="THT", quantity=2),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value=input_voltage, unit="V DC"),
            ParameterSpec(key="电机数量", value="2", unit="路"),
            ParameterSpec(key="控制方式", value="PWM", unit=""),
        ]
    elif has_bluetooth:
        project_name = "蓝牙音频模块"
        description = "支持蓝牙接收和音频输出的无线音频系统"
        components = [
            ComponentSpec(
                name="蓝牙模块", model="CSR8645", package="Module", quantity=1
            ),
            ComponentSpec(
                name="功放芯片", model="PAM8403", package="DIP-16", quantity=1
            ),
            ComponentSpec(
                name="音频接口", model="3.5mm Jack", package="THT", quantity=2
            ),
            ComponentSpec(
                name="电容", model="100uF 16V", package="electrolytic", quantity=4
            ),
            ComponentSpec(
                name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
            ),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="5", unit="V DC"),
            ParameterSpec(key="输出功率", value="3", unit="W"),
            ParameterSpec(key="通信", value="Bluetooth", unit="4.0"),
        ]
    elif has_sensor:
        project_name = "传感器数据采集系统"
        description = "基于单片机的多传感器数据采集和显示系统"
        components = [
            ComponentSpec(
                name="单片机", model="STM32F103C8T6", package="LQFP-48", quantity=1
            ),
            ComponentSpec(name="传感器", model="DHT22", package="Module", quantity=1),
            ComponentSpec(
                name="显示模块", model="0.96寸OLED", package="SSD1306", quantity=1
            ),
            ComponentSpec(
                name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
            ),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=4),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
            ComponentSpec(name="LED", model="0603 Green", package="0603", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value="5", unit="V DC"),
            ParameterSpec(key="传感器类型", value="温湿度", unit=""),
            ParameterSpec(key="显示", value="OLED", unit="0.96寸"),
        ]
    elif has_display:
        project_name = "OLED显示控制器"
        description = f"基于单片机控制的{input_voltage}V OLED显示系统"
        components = [
            ComponentSpec(
                name="单片机", model="ATmega328P", package="DIP-28", quantity=1
            ),
            ComponentSpec(
                name="显示模块", model="0.96寸 I2C OLED", package="SSD1306", quantity=1
            ),
            ComponentSpec(
                name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
            ),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=2),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=1),
            ComponentSpec(name="按键", model="6x6x5", package="THT", quantity=3),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value=input_voltage, unit="V DC"),
            ParameterSpec(key="显示", value="0.96寸OLED", unit="I2C"),
            ParameterSpec(key="分辨率", value="128x64", unit="像素"),
        ]
    elif has_usb:
        project_name = "USB转串口模块"
        description = f"USB转TTL串口通信模块，{input_voltage}V供电"
        components = [
            ComponentSpec(
                name="USB转串口芯片", model="CH340G", package="SOP-16", quantity=1
            ),
            ComponentSpec(
                name="USB接口", model="USB-B-Micro", package="SMD", quantity=1
            ),
            ComponentSpec(name="晶振", model="12MHz", package="3225", quantity=1),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=4),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=2),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
            ComponentSpec(name="LED", model="0603 Green", package="0603", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value=input_voltage, unit="V DC"),
            ParameterSpec(key="波特率", value="最高", unit="2Mbps"),
            ParameterSpec(key="接口", value="TTL", unit="3.3V/5V"),
        ]
    elif has_battery:
        project_name = "锂电池充电模块"
        description = "基于TP4056的锂电池充电电路，支持过充过放保护"
        components = [
            ComponentSpec(name="充电芯片", model="TP4056", package="SOP-8", quantity=1),
            ComponentSpec(
                name="保护芯片", model="FS8205", package="TSSOP-8", quantity=1
            ),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=2),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
            ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=1),
            ComponentSpec(name="LED", model="0603 Green", package="0603", quantity=1),
            ComponentSpec(name="USB接口", model="Micro-USB", package="SMD", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="5", unit="V DC"),
            ParameterSpec(key="充电电流", value="1", unit="A"),
            ParameterSpec(key="电池电压", value="3.7", unit="V"),
        ]
    elif has_led:
        project_name = "LED驱动控制系统"
        description = f"基于单片机控制的{input_voltage}V LED驱动系统"
        components = [
            ComponentSpec(
                name="单片机", model="ATtiny85-20PU", package="SOIC-8", quantity=1
            ),
            ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=8),
            ComponentSpec(name="LED", model="0603 Green", package="0603", quantity=8),
            ComponentSpec(name="电阻", model="330Ω 5%", package="0805", quantity=16),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=2),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=1),
            ComponentSpec(name="USB接口", model="Micro-USB", package="SMD", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value=input_voltage, unit="V DC"),
            ParameterSpec(key="LED数量", value="16", unit="颗"),
            ParameterSpec(key="控制方式", value="PWM", unit=""),
        ]
    else:
        # 默认通用项目 - 基于输入内容生成
        project_name = f"自定义电路模块 ({input_voltage}V)"
        description = f"根据您的需求定制的电路模块，输入电压{input_voltage}V，输出电流{output_current}A"
        components = [
            ComponentSpec(
                name="单片机", model="ATmega328P", package="DIP-28", quantity=1
            ),
            ComponentSpec(
                name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
            ),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=4),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
            ComponentSpec(name="LED", model="0603 Green", package="0603", quantity=1),
            ComponentSpec(name="USB接口", model="Micro-USB", package="SMD", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value=input_voltage, unit="V DC"),
            ParameterSpec(key="输出电流", value=output_current, unit="A"),
            ParameterSpec(key="主控", value="ATmega328P", unit=""),
            ParameterSpec(key="PCB尺寸", value="40x30", unit="mm"),
        ]

    logger.info(f"动态生成方案: {project_name}")
    return project_name, description, components, parameters


def _get_footprint_for_component(comp: ComponentSpec) -> str:
    """
    获取元件的封装

    AI 生成时的推荐逻辑：
    1. 如果元件已指定 package，优先使用
    2. 调用封装推荐 API 获取最佳封装
    3. 如果找不到，使用默认封装

    Returns:
        封装名称字符串
    """
    try:
        # 调用封装推荐 API
        result = get_footprint_recommendations(
            component_name=comp.name, component_value=comp.model, package=comp.package
        )

        if result.get("recommendation"):
            logger.info(
                f"元件 '{comp.name}' 推荐封装: {result['recommendation']} "
                f"(来源: {result.get('source', 'unknown')})"
            )
            return result["recommendation"]
    except Exception as e:
        logger.warning(f"获取封装失败 '{comp.name}': {e}")

    # Fallback: 使用默认封装
    return get_default_footprint_for_component(comp.name.lower(), comp.package)


# 模拟 AI 分析结果 - 实际项目中会调用 Claude/OpenAI API
def mock_ai_analyze(requirements: str) -> AnalyzeResponse:
    """模拟 AI 分析 - 实际项目中替换为真实 AI 调用"""
    import logging

    logger = logging.getLogger(__name__)

    # 根据需求关键词生成不同方案
    # 注意：不使用 .lower() 避免中文编码问题
    req = requirements
    logger.info(f"AI分析请求: {req}")

    # 关键词到方案的映射表（按优先级排序）
    # 每个条目: (关键词列表, 项目名, 描述, 元件列表, 参数列表)
    project_templates = [
        # 1. STM32温度控制系统
        (
            ["stm32", "温度控制", "温控", "temperature", "temperature control"],
            "STM32温度控制系统",
            "基于STM32单片机的温度控制系统，支持DS18B20温度传感器、OLED显示屏、继电器控制加热/制冷，蜂鸣器报警",
            [
                ComponentSpec(
                    name="单片机", model="STM32F103C8T6", package="LQFP-48", quantity=1
                ),
                ComponentSpec(
                    name="温度传感器", model="DS18B20", package="TO-92", quantity=2
                ),
                ComponentSpec(
                    name="OLED显示屏", model="0.96寸 I2C", package="SSD1306", quantity=1
                ),
                ComponentSpec(
                    name="继电器", model="5V 10A", package="SRD-05VDC", quantity=2
                ),
                ComponentSpec(
                    name="蜂鸣器", model="5V active", package="12x9.5", quantity=1
                ),
                ComponentSpec(
                    name="USB接口", model="Micro-USB", package="SMD", quantity=1
                ),
                ComponentSpec(
                    name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=4
                ),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=6
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=4),
                ComponentSpec(
                    name="电阻", model="4.7kΩ 5%", package="0805", quantity=2
                ),
                ComponentSpec(name="电阻", model="1kΩ 5%", package="0805", quantity=2),
                ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=2),
                ComponentSpec(
                    name="LED", model="0603 Green", package="0603", quantity=2
                ),
                ComponentSpec(name="按键", model="6x6x5", package="THT", quantity=4),
                ComponentSpec(name="晶振", model="8MHz", package="3225", quantity=1),
                ComponentSpec(name="电池座", model="CR2032", package="SMD", quantity=1),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V USB"),
                ParameterSpec(key="主控芯片", value="STM32F103", unit="C8T6"),
                ParameterSpec(key="温度范围", value="-55~125", unit="℃"),
                ParameterSpec(key="显示", value="0.96寸OLED", unit="I2C"),
                ParameterSpec(key="输出控制", value="2", unit="路继电器"),
                ParameterSpec(key="PCB尺寸", value="60x45", unit="mm"),
            ],
        ),
        # 2. ATtiny85 LED闪烁电路
        (
            ["attiny", "单片机", "mcu", "microcontroller"],
            "ATtiny85 LED闪烁电路",
            "使用ATtiny85单片机控制2个LED闪烁，包含USB供电接口，5V输入",
            [
                ComponentSpec(
                    name="单片机", model="ATtiny85-20PU", package="SOIC-8", quantity=1
                ),
                ComponentSpec(
                    name="USB接口", model="USB-C-SMD", package="USB-C-6P", quantity=1
                ),
                ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=2),
                ComponentSpec(
                    name="LED", model="0603 Green", package="0603", quantity=1
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=1),
                ComponentSpec(name="电阻", model="330Ω 5%", package="0805", quantity=2),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=1
                ),
            ],
            [
                ParameterSpec(key="输入电压", value="5", unit="V USB"),
                ParameterSpec(key="输出", value="2", unit="路LED"),
                ParameterSpec(key="频率", value="可调", unit="Hz"),
                ParameterSpec(key="PCB尺寸", value="30x25", unit="mm"),
            ],
        ),
        # 3. LED闪烁电路
        (
            ["led", "闪烁", "blink", "light", "灯", "发光"],
            "LED闪烁电路",
            "使用单片机或定时器实现的LED闪烁电路",
            [
                ComponentSpec(name="LED", model="5mm Red", package="THT", quantity=2),
                ComponentSpec(
                    name="单片机", model="ATtiny85", package="SOIC-8", quantity=1
                ),
                ComponentSpec(
                    name="电阻", model="330Ω 1/4W", package="0805", quantity=2
                ),
                ComponentSpec(
                    name="电容", model="100uF 16V", package="electrolytic", quantity=1
                ),
                ComponentSpec(
                    name="电阻", model="10kΩ 1/4W", package="0805", quantity=1
                ),
                ComponentSpec(name="USB接口", model="USB-C", package="SMD", quantity=1),
            ],
            [
                ParameterSpec(key="输入电压", value="5", unit="V DC"),
                ParameterSpec(key="LED数量", value="2", unit="个"),
                ParameterSpec(key="频率", value="可调", unit="Hz"),
            ],
        ),
        # 4. LED驱动电路
        (
            ["驱动", "driver", "灯具", "lamp", "照明", "light"],
            "低成本LED驱动电路",
            "基于电容降压的LED驱动电路，适用于各类小型灯具，成本控制在5元内（批量）",
            [
                ComponentSpec(
                    name="降压电容", model="475J 400V", package="CBB22", quantity=1
                ),
                ComponentSpec(
                    name="整流二极管", model="1N4007", package="DO-41", quantity=4
                ),
                ComponentSpec(
                    name="滤波电容",
                    model="10uF 400V",
                    package="electrolytic",
                    quantity=1,
                ),
                ComponentSpec(
                    name="限流电阻", model="100Ω 1W", package="axial", quantity=1
                ),
                ComponentSpec(
                    name="LED", model="2835 White", package="SMD", quantity=10
                ),
                ComponentSpec(name="保险丝", model="0.5A", package="axial", quantity=1),
            ],
            [
                ParameterSpec(key="输入电压", value="220", unit="V AC"),
                ParameterSpec(key="输出电压", value="约30", unit="V"),
                ParameterSpec(key="输出电流", value="60", unit="mA"),
                ParameterSpec(key="成本估算", value="5", unit="元/批量"),
            ],
        ),
        # 5. 5V稳压电源
        (
            ["电源", "稳压", "power supply", "voltage", "5v", "12v", "供电"],
            "5V稳压电源",
            "输入220V交流电，输出5V直流电，电流1A的稳压电源",
            [
                ComponentSpec(
                    name="变压器", model="220V->12V 5W", package="THT", quantity=1
                ),
                ComponentSpec(name="整流桥", model="MB6S", package="SMD", quantity=1),
                ComponentSpec(
                    name="滤波电容",
                    model="1000uF 25V",
                    package="electrolytic",
                    quantity=2,
                ),
                ComponentSpec(
                    name="稳压芯片", model="LM7805", package="TO-220", quantity=1
                ),
                ComponentSpec(
                    name="输出电容", model="10uF 25V", package="0805", quantity=2
                ),
            ],
            [
                ParameterSpec(key="输入电压", value="220", unit="V AC"),
                ParameterSpec(key="输出电压", value="5", unit="V DC"),
                ParameterSpec(key="输出电流", value="1", unit="A"),
            ],
        ),
        # 6. Arduino传感器扩展板
        (
            ["arduino", "传感器", "sensor", "扩展板", "shield"],
            "Arduino传感器扩展板",
            "支持多种传感器接口的Arduino扩展板",
            [
                ComponentSpec(
                    name="排针", model="2.54mm 20P", package="THT", quantity=2
                ),
                ComponentSpec(
                    name="传感器接口", model="3P 2.54mm", package="JST", quantity=6
                ),
                ComponentSpec(
                    name="电源模块", model="AMS1117-5V", package="SOT-223", quantity=1
                ),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V"),
                ParameterSpec(key="传感器接口", value="6", unit="路"),
            ],
        ),
        # 7. 蓝牙音频模块
        (
            ["蓝牙", "audio", "音频", "bluetooth", "音响", "speaker"],
            "蓝牙音频模块",
            "支持蓝牙接收和音频输出的模块",
            [
                ComponentSpec(
                    name="蓝牙模块", model="CSR8645", package="Module", quantity=1
                ),
                ComponentSpec(
                    name="功放芯片", model="PAM8403", package="DIP-16", quantity=1
                ),
                ComponentSpec(
                    name="音频接口", model="3.5mm Jack", package="THT", quantity=2
                ),
                ComponentSpec(
                    name="电容", model="100uF 16V", package="electrolytic", quantity=4
                ),
            ],
            [
                ParameterSpec(key="输入电压", value="5", unit="V DC"),
                ParameterSpec(key="输出功率", value="3", unit="W"),
            ],
        ),
        # 8. 智能家居控制器
        (
            ["智能家居", "smart home", "iot", "物联网", "wifi", "无线控制", "智能控制"],
            "智能家居控制器",
            "基于ESP32的智能家居控制器，支持WiFi远程控制，多路继电器输出",
            [
                ComponentSpec(
                    name="WiFi模块", model="ESP32-WROOM", package="Module", quantity=1
                ),
                ComponentSpec(
                    name="继电器", model="5V 10A", package="SRD-05VDC", quantity=4
                ),
                ComponentSpec(
                    name="稳压芯片", model="AMS1117-3.3", package="SOT-223", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=2
                ),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=4
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=4),
                ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=4),
                ComponentSpec(name="按键", model="6x6x5", package="THT", quantity=4),
                ComponentSpec(
                    name="USB接口", model="Micro-USB", package="SMD", quantity=1
                ),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V DC"),
                ParameterSpec(key="通信方式", value="WiFi", unit="2.4GHz"),
                ParameterSpec(key="输出通道", value="4", unit="路"),
                ParameterSpec(key="PCB尺寸", value="50x40", unit="mm"),
            ],
        ),
        # 9. 电机驱动板
        (
            ["电机", "驱动", "motor", "pwm", "舵机", "servo"],
            "电机驱动板",
            "支持多路电机PWM控制的驱动板",
            [
                ComponentSpec(
                    name="驱动芯片", model="L298N", package="MultiWatt15", quantity=1
                ),
                ComponentSpec(
                    name="单片机", model="STM32F103", package="LQFP-48", quantity=1
                ),
                ComponentSpec(
                    name="稳压芯片", model="LM7805", package="TO-220", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="100uF 25V", package="electrolytic", quantity=2
                ),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=4
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
                ComponentSpec(name="LED", model="5mm", package="THT", quantity=2),
                ComponentSpec(
                    name="接口", model="2.54mm", package="Header", quantity=2
                ),
            ],
            [
                ParameterSpec(key="工作电压", value="12", unit="V DC"),
                ParameterSpec(key="电机数量", value="2", unit="路"),
                ParameterSpec(key="控制方式", value="PWM", unit=""),
            ],
        ),
        # 10. USB转串口模块
        (
            ["usb转串口", "usb uart", "ch340", "cp2102", "ft232", "串口", "uart"],
            "USB转串口模块",
            "USB转TTL串口通信模块",
            [
                ComponentSpec(
                    name="USB转串口芯片", model="CH340G", package="SOP-16", quantity=1
                ),
                ComponentSpec(
                    name="USB接口", model="USB-B-Micro", package="SMD", quantity=1
                ),
                ComponentSpec(name="晶振", model="12MHz", package="3225", quantity=1),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=4
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=2
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
                ComponentSpec(
                    name="LED", model="0603 Green", package="0603", quantity=1
                ),
                ComponentSpec(
                    name="保护二极管", model="ESD", package="SOD-323", quantity=2
                ),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V DC"),
                ParameterSpec(key="波特率", value="最高", unit="2Mbps"),
                ParameterSpec(key="接口", value="TTL", unit="3.3V/5V"),
            ],
        ),
        # 11. 无线充电模块
        (
            ["无线充电", "wireless charge", "qi", "发射", "接收"],
            "无线充电模块",
            "符合Qi标准的无线充电电路",
            [
                ComponentSpec(
                    name="无线充电芯片", model="NR6602", package="QFN-16", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=4
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=2
                ),
                ComponentSpec(name="电感", model="10uH", package="SMD", quantity=2),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
                ComponentSpec(
                    name="LED", model="0603 Green", package="0603", quantity=1
                ),
            ],
            [
                ParameterSpec(key="输入电压", value="5", unit="V DC"),
                ParameterSpec(key="输出功率", value="5", unit="W"),
                ParameterSpec(key="充电标准", value="Qi", unit="1.2"),
            ],
        ),
        # 12. 电子时钟
        (
            ["时钟", "clock", "数码管", "nixie", "显示时间", "time"],
            "电子时钟",
            "基于单片机的数码管电子时钟",
            [
                ComponentSpec(
                    name="单片机", model="ATmega328P", package="DIP-28", quantity=1
                ),
                ComponentSpec(
                    name="数码管", model="4位共阳", package="THT", quantity=1
                ),
                ComponentSpec(
                    name="晶振", model="32.768KHz", package="插件", quantity=1
                ),
                ComponentSpec(
                    name="电阻", model="330Ω 1/4W", package="0805", quantity=8
                ),
                ComponentSpec(name="电容", model="22pF", package="0805", quantity=2),
                ComponentSpec(name="按键", model="6x6x5", package="THT", quantity=4),
                ComponentSpec(
                    name="蜂鸣器", model="5V active", package="12x9.5", quantity=1
                ),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V DC"),
                ParameterSpec(key="显示", value="4位", unit="数码管"),
                ParameterSpec(key="精度", value="±1", unit="秒/天"),
            ],
        ),
        # 13. 电子秤
        (
            ["秤", "称重", "scale", "压力传感器", "weight", "传感器"],
            "电子秤模块",
            "基于HX711的压力传感器称重模块",
            [
                ComponentSpec(
                    name="称重芯片", model="HX711", package="SOP-16", quantity=1
                ),
                ComponentSpec(
                    name="压力传感器", model="50kg", package="SMD", quantity=1
                ),
                ComponentSpec(
                    name="单片机", model="ATmega328P", package="DIP-28", quantity=1
                ),
                ComponentSpec(
                    name="稳压芯片", model="AMS1117-5V", package="SOT-223", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=2
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
                ComponentSpec(name="LED", model="数码管", package="THT", quantity=1),
                ComponentSpec(name="按键", model="6x6x5", package="THT", quantity=3),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V DC"),
                ParameterSpec(key="称重范围", value="0-50", unit="kg"),
                ParameterSpec(key="精度", value="0.01", unit="kg"),
            ],
        ),
        # 14. 超声波测距仪
        (
            ["超声波", "距离", "ultrasonic", "测距", "radar"],
            "超声波测距仪",
            "基于HC-SR04的超声波测距模块",
            [
                ComponentSpec(
                    name="超声波传感器", model="HC-SR04", package="Module", quantity=1
                ),
                ComponentSpec(
                    name="单片机", model="ATmega328P", package="DIP-28", quantity=1
                ),
                ComponentSpec(
                    name="稳压芯片", model="AMS1117-5V", package="SOT-223", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=2
                ),
                ComponentSpec(name="LCD", model="1602", package="I2C", quantity=1),
                ComponentSpec(name="LED", model="5mm", package="THT", quantity=1),
            ],
            [
                ParameterSpec(key="工作电压", value="5", unit="V DC"),
                ParameterSpec(key="测距范围", value="2-400", unit="cm"),
                ParameterSpec(key="精度", value="0.3", unit="cm"),
            ],
        ),
        # 15. 锂电池充电板
        (
            ["锂电池", "充电", "battery", "li-ion", "tp4056", "移动电源"],
            "锂电池充电模块",
            "基于TP4056的锂电池充电电路",
            [
                ComponentSpec(
                    name="充电芯片", model="TP4056", package="SOP-8", quantity=1
                ),
                ComponentSpec(
                    name="保护芯片", model="FS8205", package="TSSOP-8", quantity=1
                ),
                ComponentSpec(
                    name="电容", model="10uF 25V", package="0805", quantity=2
                ),
                ComponentSpec(
                    name="电容", model="100nF 50V", package="0805", quantity=2
                ),
                ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=2),
                ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=1),
                ComponentSpec(
                    name="LED", model="0603 Green", package="0603", quantity=1
                ),
                ComponentSpec(
                    name="USB接口", model="Micro-USB", package="SMD", quantity=1
                ),
            ],
            [
                ParameterSpec(key="输入电压", value="5", unit="V DC"),
                ParameterSpec(key="充电电流", value="1", unit="A"),
                ParameterSpec(key="电池电压", value="3.7", unit="V"),
            ],
        ),
    ]

    # 遍历模板，匹配第一个符合的条件
    # 遍历模板，匹配第一个符合的条件
    project_name = "AI生成项目"
    description = "基于AI分析生成的电路项目"
    components = []
    parameters = []

    # 首先尝试精确匹配（中文关键词直接匹配）
    matched = False
    for keywords, name, desc, comps, params in project_templates:
        for keyword in keywords:
            # 中文关键词直接匹配，英文关键词用小写匹配
            if keyword in req or keyword.lower() in req.lower():
                logger.info(f"匹配模板: {name} (关键词: {keyword})")
                project_name = name
                description = desc
                components = comps.copy()  # 使用 copy 避免修改原模板
                parameters = params.copy()
                matched = True
                break
        if matched:
            break

    # 如果没有匹配到任何模板，尝试根据输入动态生成方案
    if not matched and req.strip():
        logger.info(f"未匹配到预设模板，尝试动态生成方案...")
        project_name, description, components, parameters = _generate_dynamic_project(
            req
        )

    # 生成原理图数据
    # ========== 使用知识库生成真实原理图 ==========
    logger.info("使用知识库生成原理图...")

    # 收集典型电路模板
    all_circuits = []
    for comp in components:
        circuits = get_typical_circuits(comp.model)
        all_circuits.extend(circuits)
    all_circuits = list(set(all_circuits))  # 去重
    logger.info(f"检测到典型电路: {all_circuits}")

    # 生成元件符号和网络
    schematic_components = []
    schematic_wires = []
    schematic_nets = []

    for i, comp in enumerate(components):
        # 尝试从知识库获取真实引脚定义
        real_pins = get_schematic_pins(comp.model)

        if real_pins:
            # 使用知识库中的真实引脚
            pins = real_pins
            logger.info(f"  {comp.model}: 使用知识库引脚 ({len(pins)}个)")
        else:
            # 使用默认引脚
            pins = [{"number": "1", "name": "P1"}, {"number": "2", "name": "P2"}]
            logger.info(f"  {comp.model}: 使用默认引脚")

        schematic_components.append(
            SchematicComponent(
                id=f"comp-{i + 1}",
                name=comp.name,
                model=comp.model,
                position={"x": 100 + (i % 2) * 200, "y": 100 + (i // 2) * 100},
                pins=pins,
            )
        )

    # 生成电源网络
    schematic_nets.append(SchematicNet(id="net-vcc", name="VCC"))
    schematic_nets.append(SchematicNet(id="net-gnd", name="GND"))

    # 为典型电路生成网络连接
    for template_name in all_circuits:
        template = get_circuit_template(template_name)
        if template and "connections" in template:
            for conn in template["connections"]:
                net_name = conn.get("net", "NET")
                if net_name not in [n.name for n in schematic_nets]:
                    schematic_nets.append(
                        SchematicNet(id=f"net-{len(schematic_nets) + 1}", name=net_name)
                    )

    # 生成导线连接 - 基于典型电路
    if all_circuits:
        # 使用典型电路模板连接
        for template_name in all_circuits:
            template = get_circuit_template(template_name)
            if template and "connections" in template:
                for conn in template["connections"]:
                    net_name = conn.get("net", "NET")
                    schematic_wires.append(
                        SchematicWire(
                            id=f"wire-{len(schematic_wires) + 1}",
                            points=[
                                {"x": 150, "y": 150},
                                {"x": 250, "y": 150},
                            ],
                            net=net_name,
                        )
                    )
    else:
        # 默认连接方式
        for i in range(len(components) - 1):
            schematic_wires.append(
                SchematicWire(
                    id=f"wire-{i + 1}",
                    points=[
                        {"x": 100 + (i % 2) * 200 + 30, "y": 100 + (i // 2) * 100},
                        {
                            "x": 100 + ((i + 1) % 2) * 200 - 30,
                            "y": 100 + ((i + 1) // 2) * 100,
                        },
                    ],
                    net="VCC",
                )
            )

    logger.info(
        f"原理图生成完成: {len(schematic_components)}个元件, {len(schematic_wires)}条导线, {len(schematic_nets)}个网络"
    )

    spec = ProjectSpec(
        name=project_name,
        description=description,
        components=components,
        parameters=parameters,
    )

    schematic = SchematicData(
        components=schematic_components, wires=schematic_wires, nets=schematic_nets
    )

    return AnalyzeResponse(spec=spec, schematic=schematic)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_requirements(request: AnalyzeRequest):
    """
    分析用户需求，生成项目方案和原理图

    优先使用 GLM-4 大模型进行智能分析，
    如果没有配置 API Key 或调用失败则回退到模拟实现
    """
    try:
        # 优先使用 GLM-4 大模型
        if is_glm4_available():
            try:
                logger.info(f"使用 GLM-4 分析需求: {request.requirements[:100]}...")
                client = get_glm4_client()
                project_spec = client.generate_project_spec(request.requirements)

                # 转换 GLM-4 返回的格式为 AnalyzeResponse
                components = []
                for comp in project_spec.get("components", []):
                    components.append(
                        ComponentSpec(
                            name=comp.get("name", ""),
                            model=comp.get("model", ""),
                            package=comp.get("package", "0805"),
                            quantity=comp.get("quantity", 1),
                        )
                    )

                parameters = []
                for param in project_spec.get("parameters", []):
                    parameters.append(
                        ParameterSpec(
                            key=param.get("key", ""),
                            value=param.get("value", ""),
                            unit=param.get("unit"),
                        )
                    )

                spec = ProjectSpec(
                    name=project_spec.get("name", "AI生成项目"),
                    description=project_spec.get("description", ""),
                    components=components,
                    parameters=parameters,
                )

                # 处理原理图数据
                schematic_data = project_spec.get("schematic", {})
                schematic_components = []
                for i, comp in enumerate(schematic_data.get("components", [])):
                    schematic_components.append(
                        SchematicComponent(
                            id=comp.get("id", f"comp-{i + 1}"),
                            name=comp.get("name", ""),
                            model=comp.get("model", ""),
                            position=comp.get("position", {"x": 100, "y": 100}),
                            pins=comp.get("pins", []),
                        )
                    )

                schematic_wires = []
                for i, wire in enumerate(schematic_data.get("wires", [])):
                    schematic_wires.append(
                        SchematicWire(
                            id=wire.get("id", f"wire-{i + 1}"),
                            points=wire.get("points", []),
                            net=wire.get("net", ""),
                        )
                    )

                schematic_nets = []
                for i, net in enumerate(schematic_data.get("nets", [])):
                    schematic_nets.append(
                        SchematicNet(
                            id=net.get("id", f"net-{i + 1}"), name=net.get("name", "")
                        )
                    )

                schematic = SchematicData(
                    components=schematic_components,
                    wires=schematic_wires,
                    nets=schematic_nets,
                )

                logger.info(
                    f"GLM-4 生成方案成功: {spec.name}, {len(components)} 个元件"
                )
                return AnalyzeResponse(spec=spec, schematic=schematic)
            except Exception as glm_error:
                # GLM调用失败，记录详细错误信息
                error_msg = str(glm_error)
                print(f"DEBUG: Caught error: {error_msg}")
                logger.warning(f"GLM-4 调用失败: {error_msg}")

                # 检查是否是余额不足错误，回退到模拟实现
                if (
                    "余额" in error_msg
                    or "1113" in error_msg
                    or "rate" in error_msg.lower()
                    or "429" in error_msg
                ):
                    logger.warning("AI服务余额不足或请求频率过高，回退到模拟AI分析...")
                    try:
                        result = mock_ai_analyze(request.requirements)
                        logger.warning("回退到模拟AI分析成功")
                        return result
                    except Exception as mock_err:
                        logger.error(f"回退到模拟AI也失败: {mock_err}")
                        return {
                            "detail": "AI服务暂时不可用：智谱AI API余额不足或请求频率过高，请前往 https://open.bigmodel.cn/ 充值或稍后重试"
                        }
                elif "timeout" in error_msg.lower() or "超时" in error_msg:
                    return {"detail": "AI服务响应超时，请稍后重试"}
                elif (
                    "json" in error_msg.lower()
                    or "解析" in error_msg
                    or "parse" in error_msg.lower()
                ):
                    return {"detail": "AI返回的数据格式错误，请重试"}
                else:
                    # 其他错误，尝试回退到模拟实现
                    logger.warning("准备回退到模拟AI分析...")
                    try:
                        result = mock_ai_analyze(request.requirements)
                        logger.warning("回退到模拟AI分析成功")
                        return result
                    except Exception as mock_err:
                        logger.error(f"回退到模拟AI也失败: {mock_err}")
                        return {"detail": f"AI分析失败: {error_msg}"}
        else:
            # 没有配置 API Key，使用模拟实现
            logger.warning("未配置 ZHIPU_API_KEY，使用模拟AI分析")
            result = mock_ai_analyze(request.requirements)
            return result
    except Exception as e:
        # 发生任何异常
        error_msg = str(e)
        logger.error(f"AI分析发生异常: {error_msg}")
        try:
            logger.warning("发生异常，回退到模拟AI分析")
            result = mock_ai_analyze(request.requirements)
            return result
        except Exception as mock_error:
            logger.error(f"模拟AI分析也失败: {mock_error}")
            return {"detail": f"AI分析失败: {error_msg}"}


@router.get("/health")
async def ai_health():
    """AI 服务健康检查"""
    return {"status": "ok", "service": "ai-analyze"}


# ========== 封装库相关 API ==========


class FootprintSearchRequest(BaseModel):
    component_name: str
    component_value: Optional[str] = None
    package: Optional[str] = None


class FootprintSearchResponse(BaseModel):
    component_name: str
    component_value: Optional[str] = None
    package: Optional[str] = None
    recommendation: str
    source: str  # "library" | "default_mapping" | "fallback"
    alternatives: List[str] = []
    message: str


@router.post("/footprint/recommend", response_model=FootprintSearchResponse)
async def recommend_footprint(request: FootprintSearchRequest):
    """
    获取元件的推荐封装

    AI 在生成电路时应该调用此接口来获取合适的封装。
    如果 KiCad 封装库中没有找到合适的封装，会自动使用默认封装。

    返回的 source 字段说明：
    - "library": 从 KiCad 封装库中找到
    - "default_mapping": 使用内置的符号-封装映射表
    - "fallback": 使用智能推断的默认封装
    """
    try:
        result = get_footprint_recommendations(
            component_name=request.component_name,
            component_value=request.component_value,
            package=request.package,
        )

        return FootprintSearchResponse(
            component_name=request.component_name,
            component_value=request.component_value,
            package=request.package,
            recommendation=result.get(
                "recommendation", "Resistor_SMD:R_0603_1608Metric"
            ),
            source=result.get("source", "fallback"),
            alternatives=result.get("alternatives", []),
            message=result.get("message", ""),
        )
    except Exception as e:
        logger.error(f"封装推荐失败: {e}")
        # 返回 fallback
        return FootprintSearchResponse(
            component_name=request.component_name,
            component_value=request.component_value,
            package=request.package,
            recommendation="Resistor_SMD:R_0603_1608Metric",
            source="fallback",
            alternatives=[],
            message=f"错误: {str(e)}，使用默认封装",
        )


@router.get("/footprint/libraries")
async def get_footprint_libraries():
    """获取所有 KiCad 封装库名称"""
    try:
        libraries = get_all_libraries()
        return {
            "success": True,
            "count": len(libraries),
            "libraries": libraries,
        }
    except Exception as e:
        logger.error(f"获取封装库失败: {e}")
        return {"success": False, "error": str(e)}


@router.get("/footprint/search")
async def search_footprints(keyword: str, limit: int = 20):
    """
    搜索 KiCad 封装库

    Args:
        keyword: 搜索关键词
        limit: 返回结果数量限制
    """
    try:
        results = search_footprint_library(keyword, limit)
        return {
            "success": True,
            "keyword": keyword,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"搜索封装失败: {e}")
        return {"success": False, "error": str(e)}

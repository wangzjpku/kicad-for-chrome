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
# 导入 Kimi 大模型客户端 (优先)
from kimi_client import get_kimi_client, is_kimi_available
# 保留 GLM-4 作为后备
from glm4_client import get_glm4_client, is_glm4_available

# 导入新的原理图生成器
from schematic_generator import generate_standard_schematic, SchematicGenerator

# 导入智能封装查找器
from smart_footprint_finder import find_footprint, get_footprint_finder

# 导入电路增强器
from circuit_enhancer import enhance_with_required_circuits

# 导入质量验证器
from chip_quality_validator import validate_design

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


def _generate_reference(component_name: str, index: int) -> str:
    """
    根据元件名称生成位号（如 U1, R1, C1）

    Args:
        component_name: 元件名称
        index: 元件索引

    Returns:
        位号字符串
    """
    name_lower = component_name.lower()

    # 根据元件类型确定前缀
    if any(kw in name_lower for kw in ["电容", "capacitor", "cap"]):
        prefix = "C"
    elif any(kw in name_lower for kw in ["电阻", "resistor", "res"]):
        prefix = "R"
    elif any(kw in name_lower for kw in ["电感", "inductor"]):
        prefix = "L"
    elif any(kw in name_lower for kw in ["二极管", "diode", "led"]):
        prefix = "D"
    elif any(kw in name_lower for kw in ["三极管", "mos", "transistor"]):
        prefix = "Q"
    elif any(
        kw in name_lower
        for kw in ["单片机", "mcu", "ic", "芯片", "stm32", "atmega", "esp"]
    ):
        prefix = "U"
    elif any(kw in name_lower for kw in ["连接器", "connector", "接口", "usb", "jack"]):
        prefix = "J"
    elif any(kw in name_lower for kw in ["开关", "switch", "按键", "button"]):
        prefix = "SW"
    elif any(kw in name_lower for kw in ["晶振", "crystal", "oscillator"]):
        prefix = "Y"
    elif any(kw in name_lower for kw in ["继电器", "relay"]):
        prefix = "K"
    elif any(kw in name_lower for kw in ["电池", "battery"]):
        prefix = "BT"
    elif any(kw in name_lower for kw in ["保险丝", "fuse"]):
        prefix = "F"
    elif any(kw in name_lower for kw in ["蜂鸣器", "buzzer", "扬声器", "speaker"]):
        prefix = "LS"
    elif any(kw in name_lower for kw in ["显示屏", "display", "oled", "lcd"]):
        prefix = "DS"
    elif any(kw in name_lower for kw in ["传感器", "sensor", "模块", "module"]):
        prefix = "U"
    else:
        prefix = "U"  # 默认使用 U

    return f"{prefix}{index + 1}"


def _get_pin_offset(pin_number: str, total_pins: int) -> Dict[str, float]:
    """
    根据引脚号和总引脚数计算引脚的偏移位置

    偏移量必须与前端 AIProjectDialog.tsx 中的元件渲染匹配：
    - 元件框: width=60, height=40
    - transform: translate(x-30, y-20)
    - 左引脚圆心: cx=0, cy=20 -> 绝对位置 (x-30, y)
    - 右引脚圆心: cx=60, cy=20 -> 绝对位置 (x+30, y)

    所以相对于元件位置 (x, y)：
    - 左侧引脚偏移: (-30, 0)
    - 右侧引脚偏移: (+30, 0)

    Args:
        pin_number: 引脚号
        total_pins: 总引脚数

    Returns:
        包含x和y偏移的字典
    """
    try:
        pin_num = int(pin_number)
    except ValueError:
        pin_num = 1

    # 元件框尺寸：60x40（与前端 AIProjectDialog.tsx 匹配）
    element_width = 60.0
    element_height = 40.0
    half_width = element_width / 2  # 30
    pin_spacing = 25.0  # 引脚垂直间距

    if total_pins <= 2:
        # 两引脚元件（如电阻、电容）- 左右分布
        # 左引脚在 x-30，右引脚在 x+30
        if pin_num == 1:
            return {"x": -half_width, "y": 0.0}
        else:
            return {"x": half_width, "y": 0.0}
    elif total_pins <= 4:
        # 四引脚元件 - 两侧分布，每侧2个引脚
        if pin_num <= 2:
            # 左侧引脚
            y_offset = (pin_num - 1.5) * pin_spacing
            return {"x": -half_width, "y": y_offset}
        else:
            # 右侧引脚
            y_offset = (total_pins - pin_num - 0.5) * pin_spacing
            return {"x": half_width, "y": y_offset}
    else:
        # 多引脚元件 - 根据引脚号计算位置
        half = total_pins // 2
        if pin_num <= half:
            # 左侧引脚
            y_offset = (pin_num - half / 2 - 0.5) * pin_spacing
            return {"x": -half_width, "y": y_offset}
        else:
            # 右侧引脚
            y_offset = (total_pins - pin_num - half / 2 + 0.5) * pin_spacing
            return {"x": half_width, "y": y_offset}


class AnalyzeRequest(BaseModel):
    requirements: Optional[str] = ""
    # 用户对澄清问题的回答
    answers: Optional[Dict[str, str]] = None
    # 是否只需要生成问题（不生成方案）
    questions_only: bool = False
    # 附件（参考资料）
    attachments: Optional[List[Dict[str, str]]] = None
    # 生成模式: 'full'(完整) / 'schematic_only'(仅原理图) / 'pcb_only'(仅PCB)
    mode: Optional[str] = 'full'
    # PCB 参数
    pcb_params: Optional[Dict[str, Any]] = None
    # 原理图数据（用于PCB生成时）
    schematic: Optional[Dict[str, Any]] = None


class AttachmentInfo(BaseModel):
    """附件信息模型"""
    name: str
    path: str
    type: str


class PCBParams(BaseModel):
    """PCB 参数模型"""
    width: float = 100  # mm
    height: float = 80  # mm
    layers: int = 2
    thickness: float = 1.6  # mm
    silkscreen: bool = True
    soldermask: str = 'green'


class ClarificationQuestion(BaseModel):
    """澄清问题模型"""

    id: str
    question: str
    category: str  # "power", "interface", "size", "cost", etc.
    options: Optional[List[str]] = None  # 可选的预设选项
    default: Optional[str] = None  # 默认值
    required: bool = True  # 是否必须回答


class ClarificationResponse(BaseModel):
    """澄清问题响应"""

    questions: List[ClarificationQuestion]
    summary: str  # 需求摘要
    detected_type: str  # 检测到的电路类型


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
    footprint: Optional[str] = None  # 添加封装字段
    symbol_library: Optional[str] = None  # 添加符号库字段
    reference: Optional[str] = None  # 添加位号字段 (如 U1, R1, C1)
    category: Optional[str] = None  # 添加元件类别字段


class SchematicWire(BaseModel):
    id: str
    points: List[Dict[str, float]]
    net: str


class SchematicNet(BaseModel):
    id: str
    name: str


class SchematicNetLabel(BaseModel):
    """网络标签"""
    id: str
    name: str
    position: Dict[str, float]
    direction: Optional[str] = "right"


class PowerSymbol(BaseModel):
    """电源符号"""
    id: str
    netName: str  # 使用 camelCase 与前端保持一致
    position: Dict[str, float]
    type: str  # "vcc" 或 "gnd"


class SchematicData(BaseModel):
    components: List[SchematicComponent] = []
    wires: List[SchematicWire] = []
    nets: List[SchematicNet] = []
    netLabels: List[SchematicNetLabel] = []  # 添加网络标签
    powerSymbols: List[PowerSymbol] = []  # 添加电源符号


class AnalyzeResponse(BaseModel):
    spec: ProjectSpec
    schematic: SchematicData
    pcb: Optional[Dict[str, Any]] = None  # PCB 数据（可选）


def _generate_dynamic_project(
    requirements: str, answers: Optional[Dict[str, str]] = None
) -> tuple:
    """
    根据用户输入动态生成项目方案

    从需求描述中提取关键信息，生成个性化的项目方案
    如果提供了 answers（用户对澄清问题的回答），优先使用 answers 中的值
    """
    import re
    from typing import Dict, Optional

    if answers is None:
        answers = {}

    logger.info(f"动态生成项目方案，输入: {requirements}, 答案: {answers}")

    # ========== 解析输入电压 ==========
    # 检测直流电 (DC)
    dc_match = re.search(
        r"(\d+)\s*V\s*直流|(\d+)\s*V\s*DC|直流\s*(\d+)\s*V|DC\s*(\d+)\s*V",
        requirements,
        re.IGNORECASE,
    )
    # 检测交流电 (AC)
    ac_match = re.search(
        r"(\d+)\s*V\s*交流|(\d+)\s*V\s*AC|交流\s*(\d+)\s*V|AC\s*(\d+)\s*V",
        requirements,
        re.IGNORECASE,
    )

    input_voltage = None
    input_type = "DC"  # 默认直流

    if dc_match:
        # 找到直流输入
        input_voltage = (
            dc_match.group(1)
            or dc_match.group(2)
            or dc_match.group(3)
            or dc_match.group(4)
        )
        input_type = "DC"
    elif ac_match:
        # 找到交流输入
        input_voltage = (
            ac_match.group(1)
            or ac_match.group(2)
            or ac_match.group(3)
            or ac_match.group(4)
        )
        input_type = "AC"

    # 如果没找到明确的输入电压，尝试提取电压数字
    if not input_voltage:
        voltage_match = re.search(r"(\d+)\s*[Vv]", requirements)
        input_voltage = voltage_match.group(1) if voltage_match else "12"
        # 如果用户只说了 "12V"，默认当作直流输入处理

    # ========== 解析输出电压 ==========
    output_voltage = "5"  # 默认5V

    # 先检查是否明确指定了输出电压
    output_match = re.search(
        r"输出\s*(\d+(?:\.\d+)?)\s*V|(\d+(?:\.\d+)?)\s*V\s*输出",
        requirements,
        re.IGNORECASE,
    )
    if output_match:
        output_voltage = output_match.group(1) or output_match.group(2)
    else:
        # 如果没有明确指定输出电压，检查是否是稳压电源场景
        # 用户说 "3.3V稳压电源" 意味着输出3.3V
        has_power_keyword = any(
            kw in requirements for kw in ["稳压", "电源", "power", "voltage"]
        )
        if has_power_keyword:
            # 提取所有电压值，第一个可能是输出电压（如果有输入电压，第二个是输入）
            voltage_values = re.findall(
                r"(\d+(?:\.\d+)?)\s*V", requirements, re.IGNORECASE
            )
            if voltage_values:
                # 如果只有一个电压值，或者第一个值是 3.3/5 等常见输出电压
                first_voltage = voltage_values[0]
                if first_voltage in ["3.3", "5", "12", "9"]:
                    output_voltage = first_voltage
                    # 如果有两个电压值，第一个是输出，第二个是输入
                    if len(voltage_values) > 1 and not input_voltage:
                        input_voltage = voltage_values[1]

    # ========== 解析芯片型号 ==========
    # 优先检测输入中的特定芯片型号
    regulator_chip = None
    mcu_chip = None  # 添加MCU芯片识别

    # 先检测 ESP32
    if "esp32" in requirements.lower():
        mcu_chip = "ESP32-WROOM"
        output_voltage = "3.3"
        # ESP32需要3.3V供电
        regulator_chip = "AMS1117-3.3"

    # 先检测 AMS1117
    if "ams1117" in requirements.lower() or "AMS1117" in requirements:
        if "3.3" in requirements or "3.3v" in requirements.lower():
            regulator_chip = "AMS1117-3.3"
            output_voltage = "3.3"
        elif "5" in requirements or "5v" in requirements.lower():
            regulator_chip = "AMS1117-5V"
            output_voltage = "5"
        else:
            # 没有明确指定电压，根据 output_voltage 判断
            if output_voltage == "3.3":
                regulator_chip = "AMS1117-3.3"
            else:
                regulator_chip = "AMS1117-5V"
    elif "1117" in requirements.lower():
        if output_voltage == "3.3":
            regulator_chip = "AMS1117-3.3"
        else:
            regulator_chip = "AMS1117-5V"
    elif "lm7805" in requirements.lower() or "7805" in requirements:
        regulator_chip = "LM7805"
        output_voltage = "5"

    # 如果没有检测到特定芯片，根据输出电压选择
    if not regulator_chip:
        if output_voltage == "3.3":
            regulator_chip = "AMS1117-3.3"
        elif output_voltage == "5":
            regulator_chip = "AMS1117-5V"
        else:
            regulator_chip = "LM7805"

    # 提取电流信息
    current_match = re.search(r"(\d+(?:\.\d+)?)\s*[Aa]", requirements)
    output_current = current_match.group(1) if current_match else "1"

    # ========== 使用用户答案覆盖参数 ==========
    # 用户答案优先级最高
    if answers:
        # 从用户答案中提取输出电压
        for key in answers:
            val = answers[key]
            if val:
                if "电压" in key or "voltage" in key.lower():
                    # 解析电压值
                    voltage_match = re.search(r"(\d+(?:\.\d+)?)", val)
                    if voltage_match:
                        output_voltage = voltage_match.group(1)
                        # 根据输出电压选择芯片
                        if output_voltage == "3.3":
                            regulator_chip = "AMS1117-3.3"
                        elif output_voltage == "5":
                            regulator_chip = "AMS1117-5V"
                        else:
                            regulator_chip = "LM7805"
                elif "电流" in key or "current" in key.lower():
                    if "500mA" in val:
                        output_current = "0.5"
                    elif "1A" in val:
                        output_current = "1"
                    elif "2A" in val:
                        output_current = "2"
                    elif "5A" in val:
                        output_current = "5"

    logger.info(
        f"最终参数: input_voltage={input_voltage}, input_type={input_type}, output_voltage={output_voltage}, chip={regulator_chip}, current={output_current}A"
    )

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
    # 使用 .lower() 确保大小写不敏感匹配
    req_lower = requirements.lower()
    has_led = any(kw in req_lower for kw in ["led", "灯", "发光", "照明"])
    has_power = any(kw in req_lower for kw in ["电源", "稳压", "power", "供电"])
    has_esp32 = "esp32" in req_lower

    # 根据输入生成项目名称和描述
    # ESP32产品优先级最高
    if has_esp32:
        project_name = "ESP32智能控制器"
        description = "基于ESP32的智能控制器，支持WiFi和蓝牙连接"
        mcu_chip = mcu_chip or "ESP32-WROOM"
        components = [
            ComponentSpec(
                name="WiFi模块", model=mcu_chip, package="Module", quantity=1
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
            ComponentSpec(
                name="电阻", model="10kΩ 5%", package="0805", quantity=2
            ),
            ComponentSpec(
                name="LED", model="0603 Red", package="0603", quantity=1
            ),
            ComponentSpec(
                name="按键", model="6x6x5", package="THT", quantity=1
            ),
            ComponentSpec(
                name="USB接口", model="Micro-USB", package="SMD", quantity=1
            ),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value="3.3", unit="V"),
            ParameterSpec(key="通信方式", value="WiFi/BT", unit="2.4GHz"),
            ParameterSpec(key="PCB尺寸", value="50x30", unit="mm"),
        ]
    elif has_led:
        # LED 电路优先级高于电源电路，因为 "LED电路" 可能包含 "电源" 关键词
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
    elif has_power:
        project_name = f"{output_voltage}V稳压电源"

        # 根据输入类型生成描述
        if input_type == "DC":
            description = f"输入{input_voltage}V直流电，输出{output_voltage}V直流电，电流{output_current}A的稳压电源"
            # 直流输入不需要变压器和整流桥
            components = [
                ComponentSpec(
                    name="稳压芯片", model=regulator_chip, package="SOT-223", quantity=1
                ),
                ComponentSpec(
                    name="输入电容", model="10uF 25V", package="0805", quantity=1
                ),
                ComponentSpec(
                    name="输出电容", model="22uF 10V", package="0805", quantity=2
                ),
                ComponentSpec(
                    name="二极管", model="1N4007", package="DO-41", quantity=1
                )
                if "5" not in input_voltage
                else ComponentSpec(
                    name="TVS二极管", model="SMBJ5.0A", package="SMB", quantity=1
                ),
            ]
        else:
            # 交流输入需要变压器和整流桥
            description = f"输入{input_voltage}V交流电，输出{output_voltage}V直流电，电流{output_current}A的稳压电源"
            components = [
                ComponentSpec(
                    name="变压器",
                    model=f"220V->{output_voltage}V 5W",
                    package="THT",
                    quantity=1,
                ),
                ComponentSpec(name="整流桥", model="MB6S", package="SMD", quantity=1),
                ComponentSpec(
                    name="滤波电容",
                    model="1000uF 25V",
                    package="electrolytic",
                    quantity=2,
                ),
                ComponentSpec(
                    name="稳压芯片", model=regulator_chip, package="SOT-223", quantity=1
                ),
                ComponentSpec(
                    name="输出电容", model="22uF 10V", package="0805", quantity=2
                ),
            ]

        # 根据输出电压选择合适的封装
        if output_voltage == "3.3":
            output_cap_package = "0805"
        else:
            output_cap_package = "0805"

        parameters = [
            ParameterSpec(
                key="输入电压", value=f"{input_voltage}", unit=f"V {input_type}"
            ),
            ParameterSpec(key="输出电压", value=output_voltage, unit="V DC"),
            ParameterSpec(key="输出电流", value=output_current, unit="A"),
            ParameterSpec(key="稳压芯片", value=regulator_chip, unit=""),
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
def mock_ai_analyze(
    requirements: str, answers: Optional[Dict[str, str]] = None
) -> AnalyzeResponse:
    """模拟 AI 分析 - 实际项目中替换为真实 AI 调用"""
    import logging
    from typing import Dict, Optional

    logger = logging.getLogger(__name__)

    # 处理用户答案
    if answers is None:
        answers = {}

    logger.info(f"AI分析请求: {requirements}, 答案: {answers}")

    # 根据需求关键词生成不同方案
    # 注意：不使用 .lower() 避免中文编码问题
    req = requirements

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
        # 8. 智能家居控制器 / ESP32产品
        (
            ["智能家居", "smart home", "iot", "物联网", "wifi", "无线控制", "智能控制", "esp32", "ESP32"],
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

    # 关键修改：如果用户提供了答案（answers），或者输入中包含特定参数，
    # 使用动态生成覆盖模板结果，以根据用户的具体需求定制方案
    # 检测输入中是否包含需要动态处理的特定参数
    has_specific_params = (
        "ams1117" in req.lower()
        or "3.3v" in req.lower()
        or "3.3" in req
        or "直流" in req
        or "dc" in req.lower()
        or "交流" in req
        or "ac" in req.lower()
    )

    if (answers is not None and req.strip()) or has_specific_params:
        logger.info(f"检测到特定参数或用户答案，使用动态生成覆盖模板结果...")
        project_name, description, components, parameters = _generate_dynamic_project(
            req, answers
        )

    # ========== 使用新的标准原理图生成器 ==========
    logger.info("使用标准原理图生成器...")

    # 确定电路类型
    circuit_type = "general"
    req_lower = req.lower()
    if any(kw in req_lower for kw in ["电源", "稳压", "power", "voltage"]):
        circuit_type = "power_supply"
    elif any(kw in req_lower for kw in ["esp32", "stm32", "mcu", "单片机"]):
        circuit_type = "mcu"

    # 准备元件数据
    comp_dicts = []
    for comp in components:
        comp_dicts.append(
            {
                "name": comp.name,
                "model": comp.model,
                "package": comp.package,
                "quantity": comp.quantity,
            }
        )

    # 使用新的原理图生成器
    schematic_data = generate_standard_schematic(comp_dicts, circuit_type)
    logger.info(
        f"原理图生成完成: {len(schematic_data['components'])}个元件, "
        f"{len(schematic_data['wires'])}条导线, "
        f"{len(schematic_data['nets'])}个网络, "
        f"{len(schematic_data.get('powerSymbols', []))}个电源符号, "
        f"{len(schematic_data.get('netLabels', []))}个网络标签"
    )

    # 转换为兼容格式
    schematic_components = [
        SchematicComponent(
            id=c["id"],
            name=c["name"],
            model=c["model"],
            position=c["position"],
            pins=c["pins"],
            footprint=c.get("footprint", ""),
            symbol_library=c.get("symbol_library", ""),
            reference=c.get("reference", "U1"),
            category=c.get("category", ""),  # 添加类别字段
        )
        for c in schematic_data["components"]
    ]

    schematic_wires = [
        SchematicWire(id=w["id"], points=w["points"], net=w["net"])
        for w in schematic_data["wires"]
    ]

    schematic_nets = [
        SchematicNet(id=n["id"], name=n["name"]) for n in schematic_data["nets"]
    ]

    # 转换网络标签
    schematic_net_labels = [
        SchematicNetLabel(
            id=l["id"],
            name=l["name"],
            position=l["position"],
            direction=l.get("direction", "right")
        )
        for l in schematic_data.get("netLabels", [])
    ]

    # 转换电源符号
    schematic_power_symbols = [
        PowerSymbol(
            id=s["id"],
            netName=s["netName"],
            position=s["position"],
            type=s["type"]
        )
        for s in schematic_data.get("powerSymbols", [])
    ]

    # 为 spec.components 添加封装信息
    components_with_footprint = []
    for i, comp in enumerate(components):
        footprint = _get_footprint_for_component(comp)
        components_with_footprint.append(
            ComponentSpec(
                name=comp.name,
                model=comp.model,
                package=comp.package,
                quantity=comp.quantity,
                footprint=footprint,
            )
        )

        # ===== 自动添加必要电路 =====
        # 根据芯片的required_circuits自动添加去耦电容、上拉电阻等必要元件
        try:
            components_dict_list = [
                {"name": c.name, "model": c.model, "footprint": c.footprint}
                for c in components_with_footprint
            ]
            enhanced_components = enhance_with_required_circuits(components_dict_list)

            # 如果添加了新元件,更新列表
            if len(enhanced_components) > len(components_with_footprint):
                logger.info(
                    f"电路增强: 从 {len(components_with_footprint)} 个元件增加到 {len(enhanced_components)} 个"
                )
                # 重新构建ComponentSpec列表
                new_components = []
                for comp in enhanced_components:
                    new_components.append(
                        ComponentSpec(
                            name=comp.get("name", ""),
                            model=comp.get("model", ""),
                            package=comp.get("package", "0805"),
                            quantity=1,
                            footprint=comp.get("footprint", ""),
                        )
                    )
                components_with_footprint = new_components
        except Exception as e:
            logger.warning(f"电路增强失败: {e}")
        # ===== 电路增强结束 =====

    # ===== 质量验证 =====
    try:
        validation_result = validate_design(components_with_footprint)
        if not validation_result.get("overall_pass", True):
            logger.warning(f"质量验证发现问题: {validation_result.get('summary', {})}")
            # 可以选择记录警告或修改components
    except Exception as e:
        logger.warning(f"质量验证失败: {e}")
    # ===== 质量验证结束 =====

    spec = ProjectSpec(
        name=project_name,
        description=description,
        components=components_with_footprint,
        parameters=parameters,
    )

    schematic = SchematicData(
        components=schematic_components,
        wires=schematic_wires,
        nets=schematic_nets,
        netLabels=schematic_net_labels,
        powerSymbols=schematic_power_symbols
    )

    return AnalyzeResponse(spec=spec, schematic=schematic)


# ========== PCB 数据生成函数 ==========
class PCBComponent(BaseModel):
    """PCB 上的元件"""
    id: str
    reference: str
    footprint: str
    position: Dict[str, float]
    rotation: float = 0


class PCBTrace(BaseModel):
    """PCB 走线"""
    net: str
    width: float
    points: List[Dict[str, float]]


class PCBNet(BaseModel):
    """PCB 网络"""
    id: str
    name: str


class PCBData(BaseModel):
    """PCB 数据"""
    width: float
    height: float
    layers: int
    thickness: float
    silkscreen: bool
    soldermask: str
    components: List[PCBComponent]
    nets: List[PCBNet]
    traces: List[PCBTrace]


def generate_pcb_layout(schematic_data: Dict[str, Any], pcb_params: Dict[str, Any]) -> PCBData:
    """
    根据原理图数据和 PCB 参数生成 PCB 布局

    Args:
        schematic_data: 原理图数据
        pcb_params: PCB 参数 (width, height, layers, thickness, silkscreen, soldermask)

    Returns:
        PCBData: PCB 布局数据
    """
    logger.info(f"生成 PCB 布局: {pcb_params}")

    # 提取 PCB 参数
    width = pcb_params.get('width', 100)
    height = pcb_params.get('height', 80)
    layers = pcb_params.get('layers', 2)
    thickness = pcb_params.get('thickness', 1.6)
    silkscreen = pcb_params.get('silkscreen', True)
    soldermask = pcb_params.get('soldermask', 'green')

    # 转换阻焊颜色
    soldermask_colors = {
        'green': '#1a5a1a',
        'red': '#5a1a1a',
        'blue': '#1a1a5a',
        'yellow': '#5a5a1a',
        'white': '#3a3a3a',
        'black': '#0a0a0a'
    }
    soldermask_color = soldermask_colors.get(soldermask, '#1a5a1a')

    # 生成元件位置 - 简单的网格布局算法
    components = []
    schematic_components = schematic_data.get('components', [])

    if not schematic_components:
        # 如果没有原理图数据，创建一些示例元件
        components = [
            PCBComponent(
                id="U1",
                reference="U1",
                footprint="SOIC-8_3.9x4.9mm_P1.27mm",
                position={"x": width / 2, "y": height / 2},
                rotation=0
            ),
            PCBComponent(
                id="C1",
                reference="C1",
                footprint="Capacitor_SMD:C_0603_1608Metric",
                position={"x": width / 2 - 15, "y": height / 2 + 15},
                rotation=0
            ),
            PCBComponent(
                id="C2",
                reference="C2",
                footprint="Capacitor_SMD:C_0603_1608Metric",
                position={"x": width / 2 + 15, "y": height / 2 + 15},
                rotation=0
            ),
            PCBComponent(
                id="R1",
                reference="R1",
                footprint="Resistor_SMD:R_0603_1608Metric",
                position={"x": width / 2 - 20, "y": height / 2 - 15},
                rotation=90
            ),
            PCBComponent(
                id="J1",
                reference="J1",
                footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                position={"x": width - 10, "y": height / 2},
                rotation=0
            ),
        ]
    else:
        # 根据原理图元件生成 PCB 元件
        n = len(schematic_components)
        cols = max(1, int(width / 25))  # 每行最多元件数
        margin_x = 10
        margin_y = 10
        spacing_x = (width - 2 * margin_x) / cols if cols > 0 else 20
        spacing_y = (height - 2 * margin_y) / ((n + cols - 1) // cols) if n > 0 else 20

        for i, comp in enumerate(schematic_components):
            row = i // cols
            col = i % cols

            # 添加一些随机偏移使布局更自然
            import random
            offset_x = random.uniform(-3, 3)
            offset_y = random.uniform(-3, 3)

            x = margin_x + col * spacing_x + spacing_x / 2 + offset_x
            y = margin_y + row * spacing_y + spacing_y / 2 + offset_y

            # 限制在 PCB 范围内
            x = max(5, min(width - 5, x))
            y = max(5, min(height - 5, y))

            # 确定封装
            footprint = comp.get('footprint', '')
            if not footprint:
                # 根据元件名称推断封装
                name_lower = comp.get('name', '').lower()
                if '电容' in name_lower or 'cap' in name_lower:
                    footprint = "Capacitor_SMD:C_0603_1608Metric"
                elif '电阻' in name_lower or 'res' in name_lower:
                    footprint = "Resistor_SMD:R_0603_1608Metric"
                elif 'ic' in name_lower or '芯片' in name_lower or 'u' in comp.get('reference', '').lower():
                    footprint = "SOIC-8_3.9x4.9mm_P1.27mm"
                elif '晶振' in name_lower or 'xtal' in name_lower:
                    footprint = "Crystal:Crystal_SMD_3225"
                elif 'led' in name_lower or '二极管' in name_lower:
                    footprint = "LED_SMD:LED_0603_1608Metric"
                else:
                    footprint = "Resistor_SMD:R_0603_1608Metric"

            components.append(
                PCBComponent(
                    id=comp.get('id', f"comp-{i+1}"),
                    reference=comp.get('reference', comp.get('name', f'U{i+1}')),
                    footprint=footprint,
                    position={"x": x, "y": y},
                    rotation=random.choice([0, 90, 180, 270])
                )
            )

    # 生成网络列表
    nets = []
    schematic_nets = schematic_data.get('nets', [])

    if schematic_nets:
        for i, net in enumerate(schematic_nets[:20]):  # 限制网络数量
            nets.append(
                PCBNet(
                    id=net.get('id', f"net-{i+1}"),
                    name=net.get('name', f"N{i+1}")
                )
            )
    else:
        # 默认网络
        nets = [
            PCBNet(id="net-vcc", name="VCC"),
            PCBNet(id="net-gnd", name="GND"),
            PCBNet(id="net-in", name="INPUT"),
            PCBNet(id="net-out", name="OUTPUT"),
        ]

    # 生成走线 - 基于网格的简单走线
    traces = []
    for net in nets[:10]:  # 限制走线数量
        # 为每个网络生成简单的走线
        net_components = [c for c in components if c.reference.startswith(('U', 'C', 'R'))]

        if len(net_components) >= 2:
            # 选择前两个元件作为走线端点
            start = net_components[0].position
            end = net_components[1].position

            # 生成折线路径
            mid_x = (start["x"] + end["x"]) / 2

            traces.append(
                PCBTrace(
                    net=net.name,
                    width=0.254,  # 0.254mm = 10mil
                    points=[
                        start,
                        {"x": mid_x, "y": start["y"]},
                        {"x": mid_x, "y": end["y"]},
                        end
                    ]
                )
            )

    return PCBData(
        width=width,
        height=height,
        layers=layers,
        thickness=thickness,
        silkscreen=silkscreen,
        soldermask=soldermask_color,
        components=components,
        nets=nets,
        traces=traces
    )


def generate_clarification_questions(requirements: str, attachments: Optional[List[Dict[str, str]]] = None) -> ClarificationResponse:
    """
    根据用户需求生成澄清问题列表

    分析需求描述和提供的参考资料，识别需要澄清的关键参数，
    生成有针对性的问题帮助用户明确需求。

    Args:
        requirements: 用户输入的项目需求描述
        attachments: 可选的附件列表，包含参考资料路径
    """
    import re

    logger.info(f"生成澄清问题: {requirements[:100]}...")

    # 记录附件信息
    if attachments and len(attachments) > 0:
        logger.info(f"用户提供了 {len(attachments)} 个参考资料:")
        for att in attachments:
            logger.info(f"  - {att.get('name', 'unknown')} ({att.get('type', 'unknown')}): {att.get('path', '')}")

    req_lower = requirements.lower()
    questions = []

    # ========== 检测电路类型 ==========
    detected_type = "通用电路模块"

    # 首先检测ESP32/单片机类产品（优先级最高）
    if "esp32" in req_lower or "esp" in req_lower:
        detected_type = "ESP32智能控制器"
    elif "arduino" in req_lower or "avr" in req_lower or "atmega" in req_lower:
        detected_type = "Arduino兼容板"
    elif "stm32" in req_lower:
        detected_type = "STM32开发板"
    elif "raspberry" in req_lower or "rpi" in req_lower:
        detected_type = "树莓派扩展板"
    else:
        # 通用关键词匹配 - 按优先级排序
        # LED相关关键词必须放在电源之前，因为用户可能同时提到LED和电源
        circuit_keywords = [
            # 核心功能关键词（优先级最高）
            (["led", "发光二极管", "发光led", "led灯"], "LED驱动电路"),
            (["电机", "马达", "motor", "舵机", "servo"], "电机控制电路"),
            (["传感器", "sensor", "测温", "温湿度", "光敏", "红外"], "传感器模块"),
            (["蓝牙", "wifi", "无线", "wireless"], "无线通信模块"),
            (["usb", "串口", "uart", "i2c", "spi", "通信"], "通信接口电路"),
            (["音频", "声音", "audio", "扬声器", "麦克风", "功放"], "音频电路"),
            (["充电", "电池", "battery", "锂电池", "tp4056"], "充电电路"),
            (["电源", "稳压", "power", "voltage", "供电", "变压", "ams1117", "7805"], "电源/稳压电路"),
        ]

        for keywords, ctype in circuit_keywords:
            if any(kw in req_lower for kw in keywords):
                detected_type = ctype
                logger.info(f"[电路类型检测] 匹配关键词: {keywords} -> {ctype}")
                break

    # ========== ESP32/单片机特定问题 ==========
    if detected_type in ["ESP32智能控制器", "Arduino兼容板", "STM32开发板"]:
        # ESP32模块选择
        if detected_type == "ESP32智能控制器":
            questions.append(
                ClarificationQuestion(
                    id="esp32_module",
                    question="需要哪种ESP32模块？",
                    category="mcu",
                    options=[
                        "ESP32-WROOM (标准版)",
                        "ESP32-WROVER (带PSRAM)",
                        "ESP32-C3 (RISC-V)",
                        "ESP32-S3 (高性能)",
                    ],
                    default="ESP32-WROOM (标准版)",
                    required=False,
                )
            )

        # 无线通信功能
        questions.append(
            ClarificationQuestion(
                id="wireless_features",
                question="需要哪些无线功能？",
                category="features",
                options=[
                    "WiFi + 蓝牙 (双模)",
                    "仅WiFi",
                    "仅蓝牙",
                    "不需要无线",
                ],
                default="WiFi + 蓝牙 (双模)",
                required=False,
            )
        )

        # 供电方式
        questions.append(
            ClarificationQuestion(
                id="power_source",
                question="供电方式？",
                category="power",
                options=[
                    "USB供电 (5V)",
                    "锂电池供电 (3.7V)",
                    "DC电源插座 (12V)",
                    "太阳能供电",
                ],
                default="USB供电 (5V)",
                required=False,
            )
        )

    # ========== 电源相关问题 ==========
    if any(kw in req_lower for kw in ["电源", "稳压", "power", "供电", "voltage"]):
        # 检查是否已指定输入电压
        input_v_match = re.search(
            r"(\d+(?:\.\d+)?)\s*[Vv].*输入|输入.*(\d+(?:\.\d+)?)\s*[Vv]", requirements
        )
        if not input_v_match:
            questions.append(
                ClarificationQuestion(
                    id="input_voltage",
                    question="输入电压是多少？",
                    category="power",
                    options=[
                        "220V AC (市电)",
                        "12V DC",
                        "5V DC (USB)",
                        "3.7V (锂电池)",
                        "其他",
                    ],
                    required=True,
                )
            )

        # 检查是否已指定输出电压
        output_v_match = re.search(
            r"输出.*(\d+(?:\.\d+)?)\s*[Vv]|(\d+(?:\.\d+)?)\s*[Vv].*输出", requirements
        )
        if not output_v_match:
            questions.append(
                ClarificationQuestion(
                    id="output_voltage",
                    question="需要的输出电压是多少？",
                    category="power",
                    options=["3.3V", "5V", "9V", "12V", "可调"],
                    required=True,
                )
            )

        # 检查输出电流
        current_match = re.search(r"(\d+(?:\.\d+)?)\s*[Aa]", requirements)
        if not current_match:
            questions.append(
                ClarificationQuestion(
                    id="output_current",
                    question="最大输出电流需求是多少？",
                    category="power",
                    options=[
                        "<500mA (小功率)",
                        "500mA-1A",
                        "1A-2A",
                        "2A-5A",
                        ">5A (大功率)",
                    ],
                    required=True,
                )
            )

    # ========== 尺寸和封装相关问题 ==========
    if "尺寸" not in req_lower and "大小" not in req_lower:
        questions.append(
            ClarificationQuestion(
                id="pcb_size",
                question="PCB 尺寸有要求吗？",
                category="size",
                options=["越小越好", "50x50mm", "100x100mm", "无特殊要求"],
                default="无特殊要求",
                required=False,
            )
        )

    # 封装偏好
    questions.append(
        ClarificationQuestion(
            id="package_type",
            question="器件封装偏好？",
            category="package",
            options=["全贴片 (SMD)", "插件 (THT)", "混合使用", "无所谓"],
            default="混合使用",
            required=False,
        )
    )

    # ========== 成本相关问题 ==========
    if "成本" not in req_lower and "价格" not in req_lower and "预算" not in req_lower:
        questions.append(
            ClarificationQuestion(
                id="cost_target",
                question="成本预算范围？",
                category="cost",
                options=[
                    "低成本 (<20元)",
                    "中等 (20-50元)",
                    "高性能 (50-100元)",
                    "不计成本",
                ],
                default="中等 (20-50元)",
                required=False,
            )
        )

    # ========== 接口相关问题 ==========
    if any(kw in req_lower for kw in ["控制", "mcu", "单片机", "智能"]):
        questions.append(
            ClarificationQuestion(
                id="control_interface",
                question="需要什么控制接口？",
                category="interface",
                options=["GPIO (简单控制)", "I2C", "SPI", "UART/串口", "不需要MCU控制"],
                required=False,
            )
        )

    # ========== 特殊功能需求 ==========
    # 是否需要指示灯
    questions.append(
        ClarificationQuestion(
            id="status_led",
            question="需要状态指示灯吗？",
            category="features",
            options=["需要 (电源指示+状态)", "仅电源指示", "不需要"],
            default="需要 (电源指示+状态)",
            required=False,
        )
    )

    # 是否需要保护电路
    if any(kw in req_lower for kw in ["电源", "充电", "电池"]):
        questions.append(
            ClarificationQuestion(
                id="protection",
                question="需要哪些保护功能？",
                category="protection",
                options=["过流保护", "过压保护", "过热保护", "全部需要", "不需要"],
                default="全部需要",
                required=False,
            )
        )

    # ========== 连接器相关问题 ==========
    questions.append(
        ClarificationQuestion(
            id="connector_type",
            question="输入/输出连接器偏好？",
            category="connector",
            options=[
                "接线端子",
                "排针 (2.54mm)",
                "USB 接口",
                "DC 插座",
                "根据需要选择",
            ],
            default="根据需要选择",
            required=False,
        )
    )

    # 生成需求摘要
    summary = f"检测到电路类型: {detected_type}。需要澄清 {len(questions)} 个问题以生成精确的 BOM 和原理图。"

    logger.info(f"生成了 {len(questions)} 个澄清问题")

    return ClarificationResponse(
        questions=questions, summary=summary, detected_type=detected_type
    )


def build_enhanced_requirements(original: str, answers: Dict[str, str]) -> str:
    """
    将原始需求和用户回答合并成增强版需求描述
    """
    enhanced_parts = [f"原始需求: {original}", "\n明确要求:"]

    answer_mapping = {
        "input_voltage": "输入电压",
        "output_voltage": "输出电压",
        "output_current": "输出电流",
        "pcb_size": "PCB尺寸",
        "package_type": "器件封装",
        "cost_target": "成本预算",
        "control_interface": "控制接口",
        "status_led": "状态指示",
        "protection": "保护功能",
        "connector_type": "连接器类型",
    }

    for key, value in answers.items():
        label = answer_mapping.get(key, key)
        enhanced_parts.append(f"- {label}: {value}")

    return "\n".join(enhanced_parts)


@router.post("/clarify", response_model=ClarificationResponse)
async def get_clarification_questions(request: AnalyzeRequest):
    """
    获取澄清问题列表

    用户提交初始需求后，调用此接口获取需要澄清的问题列表。
    前端展示问题，收集用户回答后，再调用 /analyze 接口生成方案。

    如果提供了 attachments（参考资料），会一并发送给 AI 进行分析。
    """
    try:
        if not request.requirements.strip():
            return JSONResponse(status_code=400, content={"detail": "需求描述不能为空"})

        result = generate_clarification_questions(
            request.requirements,
            attachments=request.attachments
        )
        return result

    except Exception as e:
        logger.error(f"生成澄清问题失败: {e}")
        return JSONResponse(
            status_code=500, content={"detail": f"生成问题失败: {str(e)}"}
        )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_requirements(request: AnalyzeRequest):
    """
    分析用户需求，生成项目方案和原理图/PCB

    支持模式:
    - 'full': 完整生成 (原理图 + PCB)
    - 'schematic_only': 仅生成原理图
    - 'pcb_only': 仅生成 PCB (需要先有原理图)

    优先使用 Kimi 大模型进行分析，
    如果没有配置 API Key 或调用失败则回退到模拟实现
    """
    # 调试日志
    logger.info(
        f"DEBUG: analyze_requirements called with requirements='{request.requirements}', "
        f"answers={request.answers}, mode={request.mode}"
    )
    logger.info(f"DEBUG: request.schematic = {request.schematic}")
    logger.info(f"DEBUG: request.pcb_params = {request.pcb_params}")

    # 获取生成模式
    mode = request.mode or 'full'
    logger.info(f"DEBUG: Mode: {mode}, Has schematic: {bool(request.schematic)}")
    logger.info(f"DEBUG: schematic type: {type(request.schematic)}")

    # ========== PCB Only 模式 (不需要 requirements) ==========
    if mode == 'pcb_only' and request.schematic:
        # PCB Only 模式下不需要 requirements
        logger.info("=== PCB Only 模式开始 ===")
        logger.info(f"DEBUG: pcb_params = {request.pcb_params}")
        logger.info(f"DEBUG: schematic keys = {request.schematic.keys() if request.schematic else 'None'}")
        try:
            # 生成 PCB 数据
            pcb_data = generate_pcb_layout(
                request.schematic,
                request.pcb_params or {}
            )
            logger.info(f"PCB 生成成功: {pcb_data.width}x{pcb_data.height}mm, {len(pcb_data.components)} 个元件")

            # 返回兼容格式（包含 spec 和 pcb）
            return AnalyzeResponse(
                spec=ProjectSpec(
                    name="PCB Project",
                    description="Generated from schematic",
                    components=[],
                    parameters=[]
                ),
                schematic=SchematicData(
                    components=[],
                    wires=[],
                    nets=[],
                    netLabels=[],
                    powerSymbols=[]
                ),
                pcb=pcb_data.model_dump()
            )
        except Exception as e:
            logger.error(f"PCB 生成失败: {e}")
            return {"detail": f"PCB 生成失败: {str(e)}"}

    # ========== Schematic Only 或 Full 模式 ==========
    # 验证需求不为空 (仅在非 PCB Only 模式下)
    if mode != 'pcb_only':
        if not request.requirements or not request.requirements.strip():
            raise HTTPException(status_code=400, detail="requirements cannot be empty")

    try:
        # 优先使用 GLM-4 大模型
        # 优先使用 Kimi 大模型
        if is_kimi_available():
            try:
                logger.info(f"使用 Kimi 分析需求: {request.requirements[:100]}...")
                logger.info(f"附件数量: {len(request.attachments) if request.attachments else 0}")
                client = get_kimi_client()
                project_spec = client.generate_project_spec(
                    request.requirements,
                    attachments=request.attachments
                )

                # 转换 Kimi/GLM-4 返回的格式为 AnalyzeResponse
                # Kimi返回: component_list, project_name, technical_parameters, schematic_layout
                # GLM返回: components, name, parameters, schematic
                components = []
                comp_list = project_spec.get("components", []) or project_spec.get("component_list", []) or []
                for comp in comp_list:
                    # 处理 quantity 可能是字符串的情况
                    qty = comp.get("quantity", 1)
                    if isinstance(qty, str):
                        # 尝试解析字符串为整数，如 "As needed" -> 1
                        try:
                            qty = int(qty)
                        except (ValueError, TypeError):
                            qty = 1  # 默认值

                    components.append(
                        ComponentSpec(
                            name=comp.get("name", ""),
                            model=comp.get("model", ""),
                            package=comp.get("package", "0805"),
                            quantity=qty,
                        )
                    )

                parameters = []
                # 处理参数 - 支持多种格式
                raw_params = project_spec.get("parameters") or project_spec.get("technical_parameters") or []
                if isinstance(raw_params, dict):
                    # technical_parameters 是字典格式
                    for key, value in raw_params.items():
                        parameters.append(
                            ParameterSpec(
                                key=key,
                                value=str(value) if value else "",
                                unit=None,
                            )
                        )
                elif isinstance(raw_params, list):
                    # parameters 是列表格式
                    for param in raw_params:
                        if isinstance(param, dict):
                            parameters.append(
                                ParameterSpec(
                                    key=param.get("key", ""),
                                    value=param.get("value", ""),
                                    unit=param.get("unit"),
                                )
                            )

                # 处理 name 字段 (Kimi: project_name)
                project_name = project_spec.get("name") or project_spec.get("project_name", "AI生成项目")
                project_desc = project_spec.get("description") or project_spec.get("project_description", "")

                spec = ProjectSpec(
                    name=project_name,
                    description=project_desc,
                    components=components,
                    parameters=parameters,
                )

                # 处理原理图数据 (Kimi: schematic_layout)
                schematic_data = project_spec.get("schematic", {}) or project_spec.get("schematic_layout", {})
                schematic_components = []
                schematic_nets = []  # 初始化网络列表

                # 如果没有原理图数据，从组件列表生成
                if not schematic_data.get("components") and components:
                    # 从 components 生成原理图元件
                    for i, comp in enumerate(components):
                        footprint = comp.package or "0805"
                        if not footprint:
                            footprint = _get_footprint_for_component(comp)

                        schematic_components.append(
                            SchematicComponent(
                                id=f"comp-{i + 1}",
                                name=comp.name or "",
                                model=comp.model or "",
                                position={"x": 150 + (i % 3) * 200, "y": 150 + (i // 3) * 180},
                                pins=[],
                                footprint=footprint,
                                symbol_library=None,
                                reference=f"{comp.name[0] if comp.name else 'U'}{i + 1}" if comp.name else f"U{i + 1}",
                            )
                        )

                        # 为每个元件创建网络
                        if i == 0:
                            schematic_nets.append(SchematicNet(id="net-vcc", name="VCC"))
                        if i == len(components) - 1:
                            schematic_nets.append(SchematicNet(id="net-gnd", name="GND"))

                # 如果有原理图数据，解析它
                for i, comp in enumerate(schematic_data.get("components", [])):
                    # 获取封装 - 优先使用GLM返回的footprint，否则推断
                    footprint = comp.get("footprint")
                    if not footprint:
                        footprint = _get_footprint_for_component(
                            ComponentSpec(
                                name=comp.get("name", ""),
                                model=comp.get("model", ""),
                                package=comp.get("package", "0805"),
                                quantity=1,
                            )
                        )

                    schematic_components.append(
                        SchematicComponent(
                            id=comp.get("id", f"comp-{i + 1}"),
                            name=comp.get("name", ""),
                            model=comp.get("model", ""),
                            position=comp.get(
                                "position",
                                {"x": 100 + (i % 5) * 200, "y": 100 + (i // 5) * 150},
                            ),
                            pins=comp.get("pins", []),
                            footprint=footprint,
                            symbol_library=comp.get("symbol_library"),
                            reference=comp.get("reference"),
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

                for i, net in enumerate(schematic_data.get("nets", [])):
                    schematic_nets.append(
                        SchematicNet(
                            id=net.get("id", f"net-{i + 1}"), name=net.get("name", "")
                        )
                    )

                # 转换网络标签
                schematic_net_labels = []
                for i, label in enumerate(schematic_data.get("netLabels", [])):
                    schematic_net_labels.append(
                        SchematicNetLabel(
                            id=label.get("id", f"label-{i + 1}"),
                            name=label.get("name", ""),
                            position=label.get("position", {"x": 0, "y": 0}),
                            direction=label.get("direction", "right")
                        )
                    )

                # 转换电源符号
                schematic_power_symbols = []
                for i, symbol in enumerate(schematic_data.get("powerSymbols", [])):
                    schematic_power_symbols.append(
                        PowerSymbol(
                            id=symbol.get("id", f"power-{i + 1}"),
                            netName=symbol.get("netName", symbol.get("net_name", "")),
                            position=symbol.get("position", {"x": 0, "y": 0}),
                            type=symbol.get("type", "vcc")
                        )
                    )

                schematic = SchematicData(
                    components=schematic_components,
                    wires=schematic_wires,
                    nets=schematic_nets,
                    netLabels=schematic_net_labels,
                    powerSymbols=schematic_power_symbols,
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
                        result = mock_ai_analyze(request.requirements, request.answers)
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
                        result = mock_ai_analyze(request.requirements, request.answers)
                        logger.warning("回退到模拟AI分析成功")
                        return result
                    except Exception as mock_err:
                        logger.error(f"回退到模拟AI也失败: {mock_err}")
                        return {"detail": f"AI分析失败: {error_msg}"}
        else:
            # 没有配置 API Key，使用模拟实现
            logger.warning("未配置 ZHIPU_API_KEY，使用模拟AI分析")
            result = mock_ai_analyze(request.requirements, request.answers)
            return result
    except Exception as e:
        # 发生任何异常
        error_msg = str(e)
        logger.error(f"AI分析发生异常: {error_msg}")
        try:
            logger.warning("发生异常，回退到模拟AI分析")
            result = mock_ai_analyze(request.requirements, request.answers)
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


# ========== AI 聊天助手 API ==========


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    actions: Optional[List[Dict[str, str]]] = None
    modifications: Optional[List[Dict[str, Any]]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    AI 聊天助手 - 对话式修改原理图

    用户可以通过对话指出原理图问题，AI 会帮助修改。
    使用与 AI 分析相同的 API Token。

    Args:
        message: 用户消息
        context: 当前原理图上下文
        history: 对话历史
    """
    logger.info(f"AI 聊天请求: {request.message[:50]}...")
    logger.info(f"GLM-4 可用: {is_glm4_available()}")

    try:
        # 优先使用 GLM-4
        # 优先使用 Kimi 大模型
        if is_kimi_available():
            try:
                client = get_kimi_client()

                # 构建系统提示
                system_prompt = """你是一个专业的电路设计助手。用户会告诉你原理图中存在的问题，
你需要理解问题并给出修改建议或直接执行修改。

常见的修改请求包括：
1. 封装问题：如"这个电阻封装不对，应该是0805"
2. 布局问题：如"元件太挤了，调整布局"
3. 连接问题：如"这根线连接错误"
4. 添加元件：如"这里需要加一个去耦电容"
5. 删除元件：如"删除多余的LED"

回复格式：
- 首先确认理解用户的问题
- 然后给出具体的修改建议
- 如果需要修改，说明修改内容"""

                # 构建上下文描述
                context_desc = ""
                if request.context:
                    context_desc = f"\n\n当前原理图信息：\n"
                    context_desc += (
                        f"项目：{request.context.get('projectName', '未知')}\n"
                    )
                    if request.context.get("components"):
                        context_desc += (
                            f"元件数量：{len(request.context['components'])}\n"
                        )
                        for i, comp in enumerate(request.context["components"][:5]):
                            context_desc += f"  - {comp.get('name', '?')} ({comp.get('model', '?')})\n"
                    if request.context.get("nets"):
                        context_desc += (
                            f"网络：{', '.join(request.context['nets'][:10])}\n"
                        )

                # 构建历史对话
                history_text = ""
                if request.history:
                    for msg in request.history[-5:]:  # 只取最近5条
                        role = "用户" if msg.role == "user" else "助手"
                        history_text += f"{role}: {msg.content}\n"

                # 构建完整提示
                full_prompt = ""
                if history_text:
                    full_prompt += f"历史对话:\n{history_text}\n"
                full_prompt += f"用户: {request.message}"

                # 调用 GLM-4
                ai_response = client.chat(
                    prompt=full_prompt,
                    system_prompt=system_prompt + context_desc,
                    temperature=0.7,
                )

                # ai_response 是字符串
                if not ai_response:
                    ai_response = "我理解了您的问题，正在处理..."

                # 解析修改动作
                modifications = None
                actions = []

                # 检查是否包含修改关键词
                if any(
                    kw in request.message
                    for kw in ["修改", "改", "换成", "替换", "删除", "添加", "加"]
                ):
                    actions.append(
                        {
                            "type": "modify",
                            "target": "schematic",
                            "description": "需要修改原理图",
                        }
                    )

                return ChatResponse(
                    response=ai_response,
                    actions=actions if actions else None,
                    modifications=modifications,
                )

            except Exception as glm_error:
                logger.warning(f"GLM-4 聊天失败: {glm_error}")
                # 回退到模拟响应
                return mock_chat_response(request)

        else:
            # 使用模拟响应
            return mock_chat_response(request)

    except Exception as e:
        logger.error(f"AI 聊天失败: {e}")
        return ChatResponse(
            response=f"抱歉，处理您的请求时出错：{str(e)}",
            actions=None,
            modifications=None,
        )


def mock_chat_response(request: ChatRequest) -> ChatResponse:
    """模拟聊天响应 - 当 AI 不可用时使用"""
    logger.info(f"使用 mock_chat_response 处理: {request.message[:50]}")
    import re
    import random

    message = request.message.lower()
    original_message = request.message  # 保存原始消息用于解析中文坐标
    response = ""
    actions = []
    modifications = None

    # 解析位置信息
    def parse_position(text: str) -> dict:
        """尝试从文本中解析位置"""
        # 匹配坐标格式: (100, 200) 或 (100，200) - 更灵活
        coord_match = re.search(r"[(\[]?\s*(\d+)\s*[,，]\s*(\d+)\s*[)\]]?", text)
        if coord_match:
            return {"x": int(coord_match.group(1)), "y": int(coord_match.group(2))}
        # 匹配 x=100 y=200 格式
        x_match = re.search(r"x\s*[=:]\s*(\d+)", text)
        y_match = re.search(r"y\s*[=:]\s*(\d+)", text)
        if x_match and y_match:
            return {"x": int(x_match.group(1)), "y": int(y_match.group(1))}
        # 随机位置作为默认
        return {"x": random.randint(50, 200), "y": random.randint(50, 200)}

    # 解析元件引用（如 R1, C3, U1）
    def parse_reference(text: str) -> Optional[str]:
        """尝试从文本中解析元件引用"""
        ref_match = re.search(r"([RCUQJD])\s*[-_]?\s*(\d+)", text, re.IGNORECASE)
        if ref_match:
            return f"{ref_match.group(1).upper()}{ref_match.group(2)}"
        return None

    # 简单的关键词匹配
    if "封装" in message:
        # 检查是否包含具体的封装值
        package_match = re.search(r"(\d{4})", message)
        if package_match:
            package = package_match.group(1)
            ref = parse_reference(original_message)
            if ref:
                response = f"好的，我已将元件 {ref} 的封装修改为 {package}。"
                modifications = [
                    {
                        "action": "update_property",
                        "id": ref,
                        "property": "footprint",
                        "value": f"R_{package}_Metric",
                    }
                ]
            else:
                response = f"好的，我已将选中的元件封装修改为 {package}。"
                modifications = [
                    {
                        "action": "update_property",
                        "property": "footprint",
                        "value": f"R_{package}_Metric",
                    }
                ]
        else:
            response = "我理解您对封装有疑问。让我检查一下当前元件的封装配置。\n\n"
            response += (
                "建议：检查封装库中是否有更合适的封装，或者根据数据手册选择正确的封装。"
            )
            actions.append(
                {"type": "check", "target": "footprints", "description": "检查元件封装"}
            )

    elif "布局" in message or "排列" in message:
        response = "布局优化建议：\n"
        response += "1. 电源部分放在左上方\n"
        response += "2. 信号流向从左到右\n"
        response += "3. 地线在底部\n"
        response += "4. 避免长距离走线"
        actions.append(
            {"type": "optimize", "target": "layout", "description": "优化布局"}
        )

    elif "电源" in message or "vcc" in message or "gnd" in message:
        response = "电源符号建议：\n"
        response += "• VCC 应该在元件上方，使用向上箭头符号\n"
        response += "• GND 应该在元件下方，使用标准地符号\n"
        response += "需要我帮您添加或调整电源符号吗？"
        actions.append(
            {"type": "modify", "target": "power_symbols", "description": "调整电源符号"}
        )

    elif "电容" in message:
        # 优先处理添加电容的请求
        if "添加" in message or "加一个" in message:
            position = parse_position(original_message)
            response = (
                f"好的，我已在位置 ({position['x']}, {position['y']}) 添加了一个电容。"
            )
            modifications = [
                {
                    "action": "add_component",
                    "type": "capacitor",
                    "value": "100nF",
                    "position": position,
                }
            ]
        # 处理删除电容请求
        elif "删除" in message or "去掉" in message or "移除" in message:
            ref = parse_reference(original_message)
            if ref:
                response = f"好的，我已删除了元件 {ref}。"
                modifications = [
                    {
                        "action": "delete_component",
                        "id": ref,
                    }
                ]
            else:
                response = "好的，我已删除了选中的元件。"
                modifications = [
                    {
                        "action": "delete_component",
                    }
                ]
        else:
            response = "关于电容的建议：\n"
            response += "• 去耦电容应靠近芯片电源引脚\n"
            response += "• 滤波电容应放在整流后\n"
            response += "• 注意电容的耐压值"
            actions.append(
                {
                    "type": "modify",
                    "target": "capacitors",
                    "description": "调整电容位置",
                }
            )

    elif "线" in message or "连接" in message:
        # 尝试解析坐标
        logger.info(f"处理走线请求: {original_message}")
        start_match = re.search(
            r"从\s*[(\[]?\s*(\d+)\s*[,，]\s*(\d+)\s*[)\]]?", original_message
        )
        end_match = re.search(
            r"到\s*[(\[]?\s*(\d+)\s*[,，]\s*(\d+)\s*[)\]]?", original_message
        )

        logger.info(f"Start match: {start_match}, End match: {end_match}")

        if start_match and end_match:
            start = {"x": int(start_match.group(1)), "y": int(start_match.group(2))}
            end = {"x": int(end_match.group(1)), "y": int(end_match.group(2))}
            response = f"好的，我已添加了一条走线从 ({start['x']}, {start['y']}) 到 ({end['x']}, {end['y']})。"
            modifications = [{"action": "add_track", "start": start, "end": end}]
            logger.info(f"返回 modifications: {modifications}")
        else:
            # 尝试解析 "连接 XX 到 YY" 格式（元件名称）
            logger.info(f"尝试解析连接请求，原始消息: {original_message}")
            connect_pattern = r"连接\s*([A-Za-z]+\d*)\s*到\s*([A-Za-z]+\d*)"
            connect_match = re.search(connect_pattern, original_message)
            logger.info(f"连接正则匹配结果: {connect_match}")

            if connect_match:
                from_ref = connect_match.group(1).upper()
                to_ref = connect_match.group(2).upper()
                logger.info(f"解析到连接请求: {from_ref} -> {to_ref}")

                response = f"好的，我已添加了从 {from_ref} 到 {to_ref} 的走线。"
                modifications = [
                    {"action": "connect_components", "from": from_ref, "to": to_ref}
                ]
                logger.info(f"返回 connect_components modifications: {modifications}")
            else:
                response = "好的，我已优化了导线连接。"
                modifications = [{"action": "optimize_wires"}]
                actions.append(
                    {"type": "modify", "target": "wires", "description": "优化导线连接"}
                )

    elif "删除" in message or "去掉" in message:
        ref = parse_reference(original_message)
        if ref:
            response = f"好的，我已删除元件 {ref}。"
            modifications = [{"action": "delete_component", "id": ref}]
        else:
            response = "好的，我已删除选中的元件。"
            modifications = [{"action": "delete_component"}]

    elif "移动" in message or "移到" in message or "移动到" in message:
        ref = parse_reference(original_message)
        position = parse_position(original_message)
        if ref and position:
            response = f"好的，我已将元件 {ref} 移动到位置 ({position['x']}, {position['y']})。"
            modifications = [
                {"action": "move_component", "id": ref, "position": position}
            ]
        else:
            response = "好的，我已移动了元件。"
            modifications = [{"action": "move_component", "position": position}]

    elif "添加" in message or "加一个" in message or "添加一个" in message:
        position = parse_position(original_message)
        if "电容" in message or "cap" in message:
            response = (
                f"好的，我已在位置 ({position['x']}, {position['y']}) 添加了一个电容。"
            )
            modifications = [
                {
                    "action": "add_component",
                    "type": "capacitor",
                    "value": "100nF",
                    "position": position,
                }
            ]
        elif "电阻" in message or "res" in message:
            response = (
                f"好的，我已在位置 ({position['x']}, {position['y']}) 添加了一个电阻。"
            )
            modifications = [
                {
                    "action": "add_component",
                    "type": "resistor",
                    "value": "10k",
                    "position": position,
                }
            ]
        elif "过孔" in message or "via" in message:
            response = (
                f"好的，我已在位置 ({position['x']}, {position['y']}) 添加了一个过孔。"
            )
            modifications = [{"action": "add_via", "position": position}]
        else:
            response = (
                f"好的，我已在位置 ({position['x']}, {position['y']}) 添加了元件。"
            )
            modifications = [{"action": "add_component", "position": position}]

    else:
        response = f'我理解您提到："{request.message}"\n\n'
        response += "请告诉我具体需要修改什么，我会帮您处理。例如：\n"
        response += '• "把电阻R1的封装改成0805"\n'
        response += '• "删除电容C3"\n'
        response += '• "在电源处添加一个100uF电容"'

    return ChatResponse(
        response=response,
        actions=actions if actions else None,
        modifications=modifications,
    )

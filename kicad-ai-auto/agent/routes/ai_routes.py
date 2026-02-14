"""
AI Routes - AI 智能项目创建 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])

class AnalyzeRequest(BaseModel):
    requirements: str

class ComponentSpec(BaseModel):
    name: str
    model: str
    package: str
    quantity: int = 1

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


# 模拟 AI 分析结果 - 实际项目中会调用 Claude/OpenAI API
def mock_ai_analyze(requirements: str) -> AnalyzeResponse:
    """模拟 AI 分析 - 实际项目中替换为真实 AI 调用"""
    import logging
    logger = logging.getLogger(__name__)

    # 根据需求关键词生成不同方案
    # 注意：不使用 .lower() 避免中文编码问题
    req = requirements
    logger.info(f"AI分析请求: {req}")

    # 默认电源模块
    project_name = "AI生成项目"
    description = "基于AI分析生成的电路项目"

    components = []
    parameters = []

    # LED/ATtiny85相关电路优先级最高（更具体的需求）
    if "attiny" in req.lower() or "单片机" in req:
        logger.info("匹配: ATtiny85单片机电路")
        project_name = "ATtiny85 LED闪烁电路"
        description = "使用ATtiny85单片机控制2个LED闪烁，包含USB供电接口，5V输入"
        components = [
            ComponentSpec(name="单片机", model="ATtiny85-20PU", package="SOIC-8", quantity=1),
            ComponentSpec(name="USB接口", model="USB-C-SMD", package="USB-C-6P", quantity=1),
            ComponentSpec(name="LED", model="0603 Red", package="0603", quantity=2),
            ComponentSpec(name="LED", model="0603 Green", package="0603", quantity=1),
            ComponentSpec(name="电阻", model="10kΩ 5%", package="0805", quantity=1),
            ComponentSpec(name="电阻", model="330Ω 5%", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100nF 50V", package="0805", quantity=1),
            ComponentSpec(name="电容", model="10uF 25V", package="0805", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="5", unit="V USB"),
            ParameterSpec(key="输出", value="2", unit="路LED"),
            ParameterSpec(key="频率", value="可调", unit="Hz"),
            ParameterSpec(key="PCB尺寸", value="30x25", unit="mm"),
        ]
    elif "led" in req.lower() or "闪烁" in req or "blink" in req.lower():
        logger.info("匹配: LED闪烁电路")
        project_name = "LED闪烁电路"
        description = "使用单片机或定时器实现的LED闪烁电路"
        components = [
            ComponentSpec(name="LED", model="5mm Red", package="THT", quantity=2),
            ComponentSpec(name="单片机", model="ATtiny85", package="SOIC-8", quantity=1),
            ComponentSpec(name="电阻", model="330Ω 1/4W", package="0805", quantity=2),
            ComponentSpec(name="电容", model="100uF 16V", package="electrolytic", quantity=1),
            ComponentSpec(name="电阻", model="10kΩ 1/4W", package="0805", quantity=1),
            ComponentSpec(name="USB接口", model="USB-C", package="SMD", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="5", unit="V DC"),
            ParameterSpec(key="LED数量", value="2", unit="个"),
            ParameterSpec(key="频率", value="可调", unit="Hz"),
        ]
    elif "驱动" in req:
        logger.info("匹配: LED驱动电路")
        # 低成本LED驱动电路 - 适配小型灯具
        project_name = "低成本LED驱动电路"
        description = "基于电容降压的LED驱动电路，适用于各类小型灯具，成本控制在5元内（批量）"
        components = [
            ComponentSpec(name="降压电容", model="475J 400V", package="CBB22", quantity=1),
            ComponentSpec(name="整流二极管", model="1N4007", package="DO-41", quantity=4),
            ComponentSpec(name="滤波电容", model="10uF 400V", package="electrolytic", quantity=1),
            ComponentSpec(name="限流电阻", model="100Ω 1W", package="axial", quantity=1),
            ComponentSpec(name="LED", model="2835 White", package="SMD", quantity=10),
            ComponentSpec(name="保险丝", model="0.5A", package="axial", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="220", unit="V AC"),
            ParameterSpec(key="输出电压", value="约30", unit="V"),
            ParameterSpec(key="输出电流", value="60", unit="mA"),
            ParameterSpec(key="成本估算", value="5", unit="元/批量"),
        ]
    elif "电源" in req or "稳压" in req or "5v" in req.lower() or "5v" in req:
        logger.info("匹配: 5V稳压电源")
        project_name = "5V稳压电源"
        description = "输入220V交流电，输出5V直流电，电流1A的稳压电源"
        components = [
            ComponentSpec(name="变压器", model="220V->12V 5W", package="THT", quantity=1),
            ComponentSpec(name="整流桥", model="MB6S", package="SMD", quantity=1),
            ComponentSpec(name="滤波电容", model="1000uF 25V", package=" electrolytic", quantity=2),
            ComponentSpec(name="稳压芯片", model="LM7805", package="TO-220", quantity=1),
            ComponentSpec(name="输出电容", model="10uF 25V", package="0805", quantity=2),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="220", unit="V AC"),
            ParameterSpec(key="输出电压", value="5", unit="V DC"),
            ParameterSpec(key="输出电流", value="1", unit="A"),
        ]
    elif "灯具" in req:
        logger.info("匹配: LED灯具")
        # 灯具驱动 - 适配各类小型灯具
        project_name = "低成本LED驱动电路"
        description = "基于电容降压的LED驱动电路，适用于各类小型灯具，成本控制在5元内（批量）"
        components = [
            ComponentSpec(name="降压电容", model="475J 400V", package="CBB22", quantity=1),
            ComponentSpec(name="整流二极管", model="1N4007", package="DO-41", quantity=4),
            ComponentSpec(name="滤波电容", model="10uF 400V", package="electrolytic", quantity=1),
            ComponentSpec(name="限流电阻", model="100Ω 1W", package="axial", quantity=1),
            ComponentSpec(name="LED", model="2835 White", package="SMD", quantity=10),
            ComponentSpec(name="保险丝", model="0.5A", package="axial", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="220", unit="V AC"),
            ParameterSpec(key="输出电压", value="约30", unit="V"),
            ParameterSpec(key="输出电流", value="60", unit="mA"),
            ParameterSpec(key="成本估算", value="5", unit="元/批量"),
        ]
    elif "arduino" in req.lower() or "传感器" in req:
        project_name = "Arduino传感器扩展板"
        description = "支持多种传感器接口的Arduino扩展板"
        components = [
            ComponentSpec(name="排针", model="2.54mm 20P", package="THT", quantity=2),
            ComponentSpec(name="传感器接口", model="3P 2.54mm", package="JST", quantity=6),
            ComponentSpec(name="电源模块", model="AMS1117-5V", package="SOT-223", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value="5", unit="V"),
            ParameterSpec(key="传感器接口", value="6", unit="路"),
        ]
    elif "蓝牙" in req or "音频" in req:
        project_name = "蓝牙音频模块"
        description = "支持蓝牙接收和音频输出的模块"
        components = [
            ComponentSpec(name="蓝牙模块", model="CSR8645", package="Module", quantity=1),
            ComponentSpec(name="功放芯片", model=" PAM8403", package="DIP-16", quantity=1),
            ComponentSpec(name="音频接口", model="3.5mm Jack", package="THT", quantity=2),
            ComponentSpec(name="电容", model="100uF 16V", package="electrolytic", quantity=4),
        ]
        parameters = [
            ParameterSpec(key="输入电压", value="5", unit="V DC"),
            ParameterSpec(key="输出功率", value="3", unit="W"),
        ]
    else:
        # 默认通用电路
        components = [
            ComponentSpec(name="主控芯片", model="ATmega328P", package="DIP-28", quantity=1),
            ComponentSpec(name="晶振", model="16MHz", package="HC-49", quantity=1),
            ComponentSpec(name="电容", model="22pF", package="0805", quantity=2),
            ComponentSpec(name="电阻", model="10kΩ 1/4W", package="0805", quantity=1),
        ]
        parameters = [
            ParameterSpec(key="工作电压", value="5", unit="V DC"),
        ]

    # 生成原理图数据
    schematic_components = []
    schematic_wires = []
    schematic_nets = []

    for i, comp in enumerate(components):
        schematic_components.append(SchematicComponent(
            id=f"comp-{i+1}",
            name=comp.name,
            model=comp.model,
            position={"x": 100 + (i % 2) * 200, "y": 100 + (i // 2) * 100},
            pins=[{"number": "1", "name": "P1"}, {"number": "2", "name": "P2"}]
        ))

    # 生成网络
    schematic_nets.append(SchematicNet(id="net-vcc", name="VCC"))
    schematic_nets.append(SchematicNet(id="net-gnd", name="GND"))

    # 生成一些导线连接
    for i in range(len(components) - 1):
        schematic_wires.append(SchematicWire(
            id=f"wire-{i+1}",
            points=[
                {"x": 100 + (i % 2) * 200 + 30, "y": 100 + (i // 2) * 100},
                {"x": 100 + ((i + 1) % 2) * 200 - 30, "y": 100 + ((i + 1) // 2) * 100}
            ],
            net="VCC"
        ))

    spec = ProjectSpec(
        name=project_name,
        description=description,
        components=components,
        parameters=parameters
    )

    schematic = SchematicData(
        components=schematic_components,
        wires=schematic_wires,
        nets=schematic_nets
    )

    return AnalyzeResponse(spec=spec, schematic=schematic)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_requirements(request: AnalyzeRequest):
    """
    分析用户需求，生成项目方案和原理图
    """
    try:
        # 实际项目中这里会调用 Claude/OpenAI API
        # 这里使用模拟数据演示
        result = mock_ai_analyze(request.requirements)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_health():
    """AI 服务健康检查"""
    return {"status": "ok", "service": "ai-analyze"}

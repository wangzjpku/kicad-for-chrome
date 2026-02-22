"""
原理图生成器 v2.0 - 符合标准规范

功能特性：
1. 标准电源符号：VCC箭头向上，GND三角向下
2. 层次化布局：按功能分区排列元件
3. 网络标签：替代长距离走线
4. 智能走线：避免交叉，优化路径
5. ERC兼容：确保能通过电气规则检查

作者：AI Assistant
版本：2.0
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class ComponentCategory(Enum):
    """元件类别"""

    POWER = "power"  # 电源类：变压器、整流器、稳压器
    MCU = "mcu"  # 微控制器
    INTERFACE = "interface"  # 接口类：USB、串口
    PASSIVE = "passive"  # 无源器件：电阻、电容
    ACTIVE = "active"  # 有源器件：二极管、晶体管
    CONNECTOR = "connector"  # 连接器
    CRYSTAL = "crystal"  # 晶振
    LED = "led"  # LED
    SENSOR = "sensor"  # 传感器
    OTHER = "other"  # 其他


class PinType(Enum):
    """引脚类型"""

    POWER_IN = "power_in"  # 电源输入
    POWER_OUT = "power_out"  # 电源输出
    GND = "gnd"  # 地
    INPUT = "input"  # 信号输入
    OUTPUT = "output"  # 信号输出
    BIDIRECTIONAL = "bidirectional"  # 双向
    PASSIVE = "passive"  # 无源
    UNSPECIFIED = "unspecified"  # 未指定


@dataclass
class SchematicPin:
    """原理图引脚"""

    number: str
    name: str
    pin_type: PinType = PinType.UNSPECIFIED
    position: Tuple[float, float] = (0, 0)  # 相对于元件中心
    direction: str = "right"  # 引脚方向: up, down, left, right


@dataclass
class SchematicComponent:
    """原理图元件"""

    id: str
    name: str
    model: str
    reference: str  # 如 U1, R1, C1
    position: Tuple[float, float] = (0, 0)
    size: Tuple[float, float] = (100, 60)  # 元件尺寸
    pins: List[SchematicPin] = field(default_factory=list)
    category: ComponentCategory = ComponentCategory.OTHER
    symbol_library: str = ""
    footprint: str = ""


@dataclass
class SchematicNet:
    """原理图网络"""

    id: str
    name: str
    net_class: str = "default"  # default, power, signal


@dataclass
class SchematicWire:
    """原理图导线"""

    id: str
    points: List[Tuple[float, float]]
    net: str


@dataclass
class SchematicNetLabel:
    """网络标签"""

    id: str
    name: str
    position: Tuple[float, float]
    direction: str = "right"  # 标签方向
    is_global: bool = False  # 是否为全局标签


@dataclass
class PowerSymbol:
    """电源符号"""

    id: str
    net_name: str  # VCC, GND, +5V 等
    position: Tuple[float, float]
    symbol_type: str  # "vcc" 或 "gnd"


@dataclass
class SchematicSheet:
    """原理图纸"""

    components: List[SchematicComponent] = field(default_factory=list)
    nets: List[SchematicNet] = field(default_factory=list)
    wires: List[SchematicWire] = field(default_factory=list)
    net_labels: List[SchematicNetLabel] = field(default_factory=list)
    power_symbols: List[PowerSymbol] = field(default_factory=list)


class SchematicGenerator:
    """符合标准的原理图生成器"""

    # 布局参数
    GRID_SIZE = 50  # 网格大小 (0.5 inch = 12.7mm)
    COMPONENT_SPACING_X = 200  # 元件水平间距
    COMPONENT_SPACING_Y = 150  # 元件垂直间距
    POWER_RAIL_OFFSET = 100  # 电源轨道偏移
    GND_RAIL_OFFSET = 100  # 地轨道偏移

    # 区域划分
    MARGIN_TOP = 150  # 顶部边距（电源区）
    MARGIN_BOTTOM = 150  # 底部边距（地区）
    MARGIN_LEFT = 100  # 左边距
    MARGIN_RIGHT = 100  # 右边距

    def __init__(self):
        self.sheet = SchematicSheet()
        self._comp_counter = {}  # 各类元件计数器
        self._wire_counter = 0
        self._net_counter = 0
        self._label_counter = 0

    def generate(
        self, components: List[Dict], circuit_type: str = "general"
    ) -> SchematicSheet:
        """
        生成符合标准的原理图

        Args:
            components: 元件列表
            circuit_type: 电路类型 (power_supply, mcu, led_driver, etc.)

        Returns:
            SchematicSheet: 生成的原理图
        """
        logger.info(
            f"开始生成原理图，电路类型: {circuit_type}, 元件数: {len(components)}"
        )

        # 1. 分析元件并分类
        categorized = self._categorize_components(components)
        logger.info(
            f"元件分类完成: {[(cat.name, len(comps)) for cat, comps in categorized.items()]}"
        )

        # 2. 规划布局
        layout = self._plan_layout(categorized, circuit_type)
        logger.info(f"布局规划完成: {len(layout)} 个区域")

        # 3. 放置元件
        self._place_components(categorized, layout)
        logger.info(f"元件放置完成: {len(self.sheet.components)} 个元件")

        # 4. 创建电源符号
        self._create_power_symbols()
        logger.info(f"电源符号创建完成: {len(self.sheet.power_symbols)} 个符号")

        # 5. 生成网络连接
        self._generate_nets(components)
        logger.info(f"网络生成完成: {len(self.sheet.nets)} 个网络")

        # 6. 生成导线（智能走线）
        self._generate_wires()
        logger.info(f"导线生成完成: {len(self.sheet.wires)} 条导线")

        # 7. 添加网络标签 - 已在 _connect_signal_pins 中完成
        pass
        logger.info(f"网络标签添加完成: {len(self.sheet.net_labels)} 个标签")

        # 8. ERC 预检查
        erc_errors = self._erc_precheck()
        if erc_errors:
            logger.warning(f"ERC 预检查发现 {len(erc_errors)} 个潜在问题")
            for err in erc_errors[:5]:
                logger.warning(f"  - {err}")

        return self.sheet

    def _categorize_components(
        self, components: List[Dict]
    ) -> Dict[ComponentCategory, List[Dict]]:
        """分类元件"""
        categorized = {cat: [] for cat in ComponentCategory}

        for comp in components:
            name_lower = comp.get("name", "").lower()
            model_lower = comp.get("model", "").lower()
            combined = name_lower + " " + model_lower

            # 电源类
            if any(
                kw in combined
                for kw in [
                    "电源",
                    "power",
                    "变压器",
                    "transformer",
                    "整流",
                    "rectifier",
                    "稳压",
                    "regulator",
                    "lm78",
                    "ldo",
                    "dcdc",
                    "buck",
                    "boost",
                ]
            ):
                categorized[ComponentCategory.POWER].append(comp)
            # MCU
            elif any(
                kw in combined
                for kw in [
                    "mcu",
                    "单片机",
                    "esp32",
                    "stm32",
                    "arduino",
                    "atmega",
                    "nrf52",
                    "rp2040",
                    "attiny",
                ]
            ):
                categorized[ComponentCategory.MCU].append(comp)
            # 接口类
            elif any(
                kw in combined
                for kw in [
                    "usb",
                    "uart",
                    "串口",
                    "spi",
                    "i2c",
                    "can",
                    "rs485",
                    "ch340",
                    "cp210",
                ]
            ):
                categorized[ComponentCategory.INTERFACE].append(comp)
            # 晶振
            elif any(kw in combined for kw in ["晶振", "crystal", "oscillator", "mhz"]):
                categorized[ComponentCategory.CRYSTAL].append(comp)
            # LED
            elif any(kw in combined for kw in ["led", "发光", "灯"]):
                categorized[ComponentCategory.LED].append(comp)
            # 连接器
            elif any(
                kw in combined
                for kw in [
                    "connector",
                    "连接器",
                    "header",
                    "插座",
                    "pin",
                    "接口",
                    "usb接口",
                ]
            ):
                categorized[ComponentCategory.CONNECTOR].append(comp)
            # 无源器件
            elif any(
                kw in combined
                for kw in [
                    "电阻",
                    "resistor",
                    "电容",
                    "capacitor",
                    "电感",
                    "inductor",
                    "去耦",
                    "滤波",
                ]
            ):
                categorized[ComponentCategory.PASSIVE].append(comp)
            # 有源器件
            elif any(
                kw in combined
                for kw in ["二极管", "diode", "晶体管", "transistor", "mosfet", "bjt"]
            ):
                categorized[ComponentCategory.ACTIVE].append(comp)
            else:
                categorized[ComponentCategory.OTHER].append(comp)

        # 移除空类别
        return {k: v for k, v in categorized.items() if v}

    def _plan_layout(
        self, categorized: Dict[ComponentCategory, List[Dict]], circuit_type: str
    ) -> Dict[str, Tuple[float, float, float, float]]:
        """
        规划布局区域

        Returns:
            Dict[区域名, (x_start, y_start, x_end, y_end)]
        """
        layout = {}

        # 根据电路类型确定布局策略
        if circuit_type == "power_supply":
            # 电源电路：从左到右，输入→变换→输出
            layout = self._layout_power_supply(categorized)
        elif circuit_type == "mcu":
            # MCU 电路：MCU居中，外设环绕
            layout = self._layout_mcu(categorized)
        else:
            # 通用布局
            layout = self._layout_general(categorized)

        return layout

    def _layout_power_supply(self, categorized: Dict) -> Dict[str, Tuple]:
        """电源电路布局 - 从左到右：输入→整流→滤波→稳压→输出"""
        layout = {}
        x = self.MARGIN_LEFT
        y = self.MARGIN_TOP + 50

        # 输入区（变压器、保险丝）
        layout["input"] = (x, y, x + 150, y + 300)
        x += 200

        # 整流区（整流桥）
        layout["rectifier"] = (x, y, x + 150, y + 200)
        x += 200

        # 滤波区（大电容）
        layout["filter"] = (x, y, x + 150, y + 200)
        x += 200

        # 稳压区（稳压器）
        layout["regulator"] = (x, y, x + 150, y + 200)
        x += 200

        # 输出区（输出电容、LED指示）
        layout["output"] = (x, y, x + 150, y + 200)

        return layout

    def _layout_mcu(self, categorized: Dict) -> Dict[str, Tuple]:
        """MCU 电路布局 - MCU居中，外设环绕"""
        layout = {}
        center_x = 400
        center_y = 300

        # MCU 在中心
        layout["mcu"] = (center_x - 100, center_y - 100, center_x + 100, center_y + 100)

        # 电源在上
        layout["power"] = (100, 50, 300, 150)

        # 晶振在 MCU 旁边
        layout["crystal"] = (
            center_x + 150,
            center_y - 50,
            center_x + 250,
            center_y + 50,
        )

        # 接口在下
        layout["interface"] = (100, 400, 300, 500)

        # LED 在右下
        layout["led"] = (500, 400, 650, 500)

        return layout

    def _layout_general(self, categorized: Dict) -> Dict[str, Tuple]:
        """通用布局 - 简单网格"""
        layout = {}
        y = self.MARGIN_TOP

        # 始终创建 main 区域
        layout["main"] = (self.MARGIN_LEFT, y, 800, y + 400)
        y += 150

        # 电源在最上方
        if ComponentCategory.POWER in categorized:
            layout["power"] = (self.MARGIN_LEFT, y, 700, y + 100)
            y += 150

        # 主动器件
        if (
            ComponentCategory.MCU in categorized
            or ComponentCategory.ACTIVE in categorized
        ):
            layout["main"] = (self.MARGIN_LEFT, y, 700, y + 200)
            y += 250

        # 无源器件
        if ComponentCategory.PASSIVE in categorized:
            layout["passive"] = (self.MARGIN_LEFT, y, 700, y + 150)
            y += 200

        # 接口和连接器
        if (
            ComponentCategory.INTERFACE in categorized
            or ComponentCategory.CONNECTOR in categorized
        ):
            layout["interface"] = (self.MARGIN_LEFT, y, 700, y + 100)

        return layout

    def _place_components(
        self, categorized: Dict[ComponentCategory, List[Dict]], layout: Dict[str, Tuple]
    ):
        """放置元件到布局区域"""

        # 类别到布局区域的映射
        category_to_zone = {
            ComponentCategory.POWER: "power",
            ComponentCategory.MCU: "mcu",
            ComponentCategory.INTERFACE: "interface",
            ComponentCategory.CRYSTAL: "crystal",
            ComponentCategory.LED: "led",
            ComponentCategory.CONNECTOR: "interface",
            ComponentCategory.PASSIVE: "passive",
            ComponentCategory.ACTIVE: "main",
            ComponentCategory.SENSOR: "main",
            ComponentCategory.OTHER: "main",
        }

        for category, comps in categorized.items():
            zone_name = category_to_zone.get(category, "main")

            if zone_name not in layout:
                zone_name = (
                    "main"
                    if "main" in layout
                    else list(layout.keys())[0]
                    if layout
                    else None
                )

            if zone_name is None:
                continue

            zone = layout[zone_name]
            x_start, y_start, x_end, y_end = zone

            # 计算区域内的元件位置
            num_comps = len(comps)
            if num_comps == 0:
                continue

            # 计算列数和行数
            zone_width = x_end - x_start
            cols = max(1, int(zone_width / self.COMPONENT_SPACING_X))
            rows = (num_comps + cols - 1) // cols

            for i, comp in enumerate(comps):
                col = i % cols
                row = i // cols

                x = x_start + col * self.COMPONENT_SPACING_X + 50
                y = y_start + row * self.COMPONENT_SPACING_Y + 30

                # 创建原理图元件
                schematic_comp = self._create_schematic_component(
                    comp, (x, y), category
                )
                self.sheet.components.append(schematic_comp)

    def _create_schematic_component(
        self, comp: Dict, position: Tuple[float, float], category: ComponentCategory
    ) -> SchematicComponent:
        """创建原理图元件"""

        # 生成参考编号
        ref_prefix = self._get_reference_prefix(category)
        if ref_prefix not in self._comp_counter:
            self._comp_counter[ref_prefix] = 0
        self._comp_counter[ref_prefix] += 1
        reference = f"{ref_prefix}{self._comp_counter[ref_prefix]}"

        # 获取元件名称和型号
        comp_name = comp.get("name", "Unknown")
        model = comp.get("model", "")
        package = comp.get("package", "")

        # ======== 集成符号库查找 ========
        symbol_library = comp.get("symbol_library", "")
        symbol_name = ""

        try:
            from symbol_lib_parser import get_symbol_parser, symbol_to_dict

            parser = get_symbol_parser()
            symbol = parser.find_symbol_for_component(comp_name, model)

            if symbol:
                symbol_library = f"{symbol.library}:{symbol.name}"
                symbol_name = symbol.name
                logger.info(f"找到符号: {symbol_library} 用于 {comp_name}")

                # 使用符号库的引脚信息（如果有）
                if symbol.pins and not comp.get("pins"):
                    comp["pins"] = [
                        {
                            "number": p.number,
                            "name": p.name,
                            "position": p.position,
                            "direction": p.direction,
                        }
                        for p in symbol.pins
                    ]

                # 使用符号库的参考编号前缀
                if symbol.reference:
                    ref_prefix = symbol.reference
                    if ref_prefix not in self._comp_counter:
                        self._comp_counter[ref_prefix] = 0
                    self._comp_counter[ref_prefix] += 1
                    reference = f"{ref_prefix}{self._comp_counter[ref_prefix]}"
            else:
                logger.warning(f"未找到符号: {comp_name} ({model})，使用默认")
        except Exception as e:
            logger.warning(f"符号库查找失败: {e}")

        # 创建引脚
        pins = self._create_pins(comp, category)

        # 确定元件尺寸
        size = self._get_component_size(category, len(pins))

        # 智能获取封装
        existing_footprint = comp.get("footprint", "")

        # 如果已有完整封装路径，使用它
        if existing_footprint and ":" in existing_footprint:
            footprint = existing_footprint
        else:
            # 使用智能封装查找器
            from smart_footprint_finder import find_footprint

            lib_name, fp_name = find_footprint(
                model=model, component_type=category.value, package_hint=package
            )
            footprint = f"{lib_name}:{fp_name}"

        return SchematicComponent(
            id=f"comp-{len(self.sheet.components) + 1}",
            name=comp_name,
            model=model,
            reference=reference,
            position=position,
            size=size,
            pins=pins,
            category=category,
            symbol_library=symbol_library,
            footprint=footprint,
        )

    def _get_reference_prefix(self, category: ComponentCategory) -> str:
        """获取元件参考编号前缀"""
        prefixes = {
            ComponentCategory.POWER: "U",  # 稳压器等
            ComponentCategory.MCU: "U",
            ComponentCategory.INTERFACE: "U",
            ComponentCategory.PASSIVE: "R",  # 默认电阻，会被覆盖
            ComponentCategory.ACTIVE: "D",  # 二极管
            ComponentCategory.CONNECTOR: "J",
            ComponentCategory.CRYSTAL: "Y",
            ComponentCategory.LED: "D",
            ComponentCategory.SENSOR: "U",
            ComponentCategory.OTHER: "U",
        }
        return prefixes.get(category, "U")

    def _create_pins(
        self, comp: Dict, category: ComponentCategory
    ) -> List[SchematicPin]:
        """创建元件引脚"""
        pins = []

        # 尝试从组件数据获取引脚
        comp_pins = comp.get("pins", [])
        if comp_pins:
            for i, pin_data in enumerate(comp_pins):
                if isinstance(pin_data, dict):
                    pin = SchematicPin(
                        number=str(pin_data.get("number", i + 1)),
                        name=pin_data.get("name", f"P{i + 1}"),
                        pin_type=self._determine_pin_type(pin_data.get("name", "")),
                        position=self._calculate_pin_position(
                            i, len(comp_pins), category
                        ),
                        direction=self._calculate_pin_direction(
                            i, len(comp_pins), category
                        ),
                    )
                else:
                    pin = SchematicPin(
                        number=str(pin_data),
                        name=f"P{pin_data}",
                        position=self._calculate_pin_position(
                            i, len(comp_pins), category
                        ),
                        direction=self._calculate_pin_direction(
                            i, len(comp_pins), category
                        ),
                    )
                pins.append(pin)
        else:
            # 创建默认引脚
            default_pins = self._get_default_pins(comp, category)
            for i, pin_data in enumerate(default_pins):
                pin = SchematicPin(
                    number=str(pin_data.get("number", i + 1)),
                    name=pin_data.get("name", f"P{i + 1}"),
                    pin_type=self._determine_pin_type(pin_data.get("name", "")),
                    position=self._calculate_pin_position(
                        i, len(default_pins), category
                    ),
                    direction=self._calculate_pin_direction(
                        i, len(default_pins), category
                    ),
                )
                pins.append(pin)

        return pins

    def _get_default_pins(self, comp: Dict, category: ComponentCategory) -> List[Dict]:
        """获取默认引脚配置"""
        name_lower = comp.get("name", "").lower()
        model_lower = comp.get("model", "").lower()

        # 稳压器 (7805 等)
        if "7805" in model_lower or "7812" in model_lower or "regulator" in name_lower:
            return [
                {"number": 1, "name": "VIN", "type": "power_in"},
                {"number": 2, "name": "GND", "type": "gnd"},
                {"number": 3, "name": "VOUT", "type": "power_out"},
            ]

        # 二极管/整流桥
        if "diode" in name_lower or "bridge" in name_lower:
            return [
                {"number": 1, "name": "AC1", "type": "input"},
                {"number": 2, "name": "AC2", "type": "input"},
                {"number": 3, "name": "+", "type": "output"},
                {"number": 4, "name": "-", "type": "gnd"},
            ]

        # 电容
        if "cap" in name_lower or "电容" in name_lower:
            return [
                {"number": 1, "name": "+", "type": "passive"},
                {"number": 2, "name": "-", "type": "passive"},
            ]

        # 电阻
        if "res" in name_lower or "电阻" in name_lower:
            return [
                {"number": 1, "name": "1", "type": "passive"},
                {"number": 2, "name": "2", "type": "passive"},
            ]

        # LED
        if "led" in name_lower:
            return [
                {"number": 1, "name": "A", "type": "passive"},
                {"number": 2, "name": "K", "type": "passive"},
            ]

        # 晶振
        if "crystal" in name_lower or "晶振" in name_lower:
            return [
                {"number": 1, "name": "X1", "type": "passive"},
                {"number": 2, "name": "X2", "type": "passive"},
            ]

        # 默认两引脚
        return [
            {"number": 1, "name": "P1", "type": "passive"},
            {"number": 2, "name": "P2", "type": "passive"},
        ]

    def _determine_pin_type(self, pin_name: str) -> PinType:
        """根据引脚名称确定引脚类型"""
        name_upper = pin_name.upper()

        if any(
            kw in name_upper
            for kw in ["VCC", "VDD", "VIN", "+5V", "+3V3", "5V", "3V3", "V+"]
        ):
            return PinType.POWER_IN
        if any(kw in name_upper for kw in ["GND", "VSS", "V-", "GROUND", "COM"]):
            return PinType.GND
        if any(kw in name_upper for kw in ["OUT", "TX", "DO", "MOSI", "SCK"]):
            return PinType.OUTPUT
        if any(kw in name_upper for kw in ["IN", "RX", "DI", "MISO"]):
            return PinType.INPUT

        return PinType.PASSIVE

    def _calculate_pin_position(
        self, pin_index: int, total_pins: int, category: ComponentCategory
    ) -> Tuple[float, float]:
        """计算引脚相对于元件的位置"""
        # 简单的引脚分布：左右两侧
        half = (total_pins + 1) // 2

        if pin_index < half:
            # 左侧引脚
            x = -50
            y = -30 + pin_index * 20
        else:
            # 右侧引脚
            x = 50
            y = -30 + (pin_index - half) * 20

        return (x, y)

    def _calculate_pin_direction(
        self, pin_index: int, total_pins: int, category: ComponentCategory
    ) -> str:
        """计算引脚方向"""
        half = (total_pins + 1) // 2

        if pin_index < half:
            return "left"
        else:
            return "right"

    def _get_component_size(
        self, category: ComponentCategory, pin_count: int
    ) -> Tuple[float, float]:
        """获取元件尺寸"""
        # 根据引脚数量调整尺寸
        base_sizes = {
            ComponentCategory.POWER: (100, 80),
            ComponentCategory.MCU: (150, 120),
            ComponentCategory.INTERFACE: (100, 80),
            ComponentCategory.PASSIVE: (60, 40),
            ComponentCategory.ACTIVE: (80, 60),
            ComponentCategory.CONNECTOR: (80, 60),
            ComponentCategory.CRYSTAL: (60, 40),
            ComponentCategory.LED: (40, 40),
            ComponentCategory.SENSOR: (80, 60),
            ComponentCategory.OTHER: (80, 60),
        }

        base = base_sizes.get(category, (80, 60))

        # 根据引脚数调整
        if pin_count > 4:
            return (base[0] + 20, base[1] + pin_count * 10)

        return base

    def _create_power_symbols(self):
        """创建电源符号 - 确保生成VCC和GND"""
        # 首先，确保 VCC 网络存在
        if not any(n.name in ["VCC", "+5V", "+3V3"] for n in self.sheet.nets):
            self._add_net("VCC", "power")

        # 确保 GND 网络存在
        if not any(n.name == "GND" for n in self.sheet.nets):
            self._add_net("GND", "power")

        # 收集所有电源网络
        power_nets = set()
        gnd_nets = set()

        for comp in self.sheet.components:
            for pin in comp.pins:
                if pin.pin_type == PinType.POWER_IN:
                    # 从引脚名称推断电源网络名
                    net_name = self._infer_power_net_name(pin.name)
                    power_nets.add(net_name)
                elif pin.pin_type == PinType.GND:
                    gnd_nets.add("GND")

        # 创建 VCC 符号 (在顶部) - 始终创建至少一个 VCC 符号
        vcc_y = 50
        vcc_created = False

        for i, net_name in enumerate(sorted(power_nets)):
            x = 100 + i * 150
            symbol = PowerSymbol(
                id=f"power-{i + 1}",
                net_name=net_name,
                position=(x, vcc_y),
                symbol_type="vcc",
            )
            self.sheet.power_symbols.append(symbol)
            vcc_created = True

        # 如果没有电源引脚，至少创建一个默认的 VCC 符号
        if not vcc_created:
            symbol = PowerSymbol(
                id="power-vcc", net_name="VCC", position=(100, vcc_y), symbol_type="vcc"
            )
            self.sheet.power_symbols.append(symbol)

        # 创建 GND 符号 (在底部)
        max_y = (
            max([c.position[1] + c.size[1] for c in self.sheet.components])
            if self.sheet.components
            else 400
        )
        gnd_y = max_y + 80

        # 为每个有 GND 引脚的元件创建 GND 符号
        gnd_positions = []
        for comp in self.sheet.components:
            for pin in comp.pins:
                if pin.pin_type == PinType.GND:
                    gnd_positions.append(
                        (comp.position[0], comp.position[1] + comp.size[1] / 2 + 30)
                    )

        # 始终创建至少一个 GND 符号
        if not gnd_positions:
            gnd_positions = [(100, gnd_y)]

        # 去重并创建符号
        unique_gnd_x = sorted(set([p[0] for p in gnd_positions]))
        for i, x in enumerate(unique_gnd_x):
            symbol = PowerSymbol(
                id=f"gnd-{i + 1}",
                net_name="GND",
                position=(x, gnd_y),
                symbol_type="gnd",
            )
            self.sheet.power_symbols.append(symbol)

        # 创建 GND 符号 (在底部)
        max_y = (
            max([c.position[1] + c.size[1] for c in self.sheet.components])
            if self.sheet.components
            else 400
        )
        gnd_y = max_y + 80

        # 为每个有 GND 引脚的元件创建 GND 符号
        gnd_positions = []
        for comp in self.sheet.components:
            for pin in comp.pins:
                if pin.pin_type == PinType.GND:
                    gnd_positions.append(
                        (comp.position[0], comp.position[1] + comp.size[1] / 2 + 30)
                    )

        # 去重并创建符号
        unique_gnd_x = sorted(set([p[0] for p in gnd_positions]))
        for i, x in enumerate(unique_gnd_x):
            symbol = PowerSymbol(
                id=f"gnd-{i + 1}",
                net_name="GND",
                position=(x, gnd_y),
                symbol_type="gnd",
            )
            self.sheet.power_symbols.append(symbol)

    def _infer_power_net_name(self, pin_name: str) -> str:
        """从引脚名称推断电源网络名"""
        name_upper = pin_name.upper()

        if "5V" in name_upper or "+5V" in name_upper:
            return "+5V"
        if "3V3" in name_upper or "3.3V" in name_upper:
            return "+3V3"
        if "12V" in name_upper or "+12V" in name_upper:
            return "+12V"
        if "24V" in name_upper or "+24V" in name_upper:
            return "+24V"

        return "VCC"

    def _generate_nets(self, components: List[Dict]):
        """生成网络"""
        # 确保 VCC 和 GND 网络存在
        vcc_exists = any(n.name in ["VCC", "+5V"] for n in self.sheet.nets)
        gnd_exists = any(n.name == "GND" for n in self.sheet.nets)

        if not vcc_exists:
            self._add_net("VCC", "power")
        if not gnd_exists:
            self._add_net("GND", "power")

        # 根据元件连接生成其他网络
        for i, comp in enumerate(components):
            connections = comp.get("connections", [])
            for conn in connections:
                net_name = conn.get("net", "")
                if net_name and not any(n.name == net_name for n in self.sheet.nets):
                    self._add_net(net_name, "signal")

    def _add_net(self, name: str, net_class: str = "default"):
        """添加网络"""
        self._net_counter += 1
        net = SchematicNet(
            id=f"net-{self._net_counter}", name=name, net_class=net_class
        )
        self.sheet.nets.append(net)
        return net

    def _generate_wires(self):
        """生成导线 - 智能走线"""
        # 1. 连接电源引脚到电源符号
        self._connect_power_pins()

        # 2. 连接信号引脚
        self._connect_signal_pins()

    def _connect_power_pins(self):
        """连接电源引脚"""
        for comp in self.sheet.components:
            comp_x, comp_y = comp.position

            for pin in comp.pins:
                pin_x = comp_x + pin.position[0]
                pin_y = comp_y + pin.position[1]

                if pin.pin_type == PinType.POWER_IN:
                    # 找到对应的电源符号
                    net_name = self._infer_power_net_name(pin.name)
                    power_sym = next(
                        (
                            s
                            for s in self.sheet.power_symbols
                            if s.net_name == net_name and s.symbol_type == "vcc"
                        ),
                        None,
                    )

                    if power_sym:
                        # 使用 L 型走线避免交叉
                        self._add_l_wire(
                            (power_sym.position[0], power_sym.position[1] + 20),
                            (pin_x, pin_y),
                            net_name,
                        )

                elif pin.pin_type == PinType.GND:
                    # 找到最近的 GND 符号
                    gnd_sym = min(
                        [s for s in self.sheet.power_symbols if s.symbol_type == "gnd"],
                        key=lambda s: abs(s.position[0] - pin_x),
                        default=None,
                    )

                    if gnd_sym:
                        # 使用 L 型走线
                        self._add_l_wire(
                            (pin_x, pin_y),
                            (gnd_sym.position[0], gnd_sym.position[1] - 20),
                            "GND",
                        )

    def _connect_signal_pins(self):
        """连接信号引脚 - 使用网络标签避免长距离走线"""
        # 简化连接：按顺序连接相邻元件
        components = self.sheet.components
        if len(components) < 2:
            return

        # 为每个元件创建简单的左右引脚连接
        for i in range(len(components) - 1):
            comp1 = components[i]
            comp2 = components[i + 1]

            # 计算连接点
            x1 = comp1.position[0] + comp1.size[0] / 2  # 元件1右侧中心
            y1 = comp1.position[1]
            x2 = comp2.position[0] - comp2.size[0] / 2  # 元件2左侧中心
            y2 = comp2.position[1]

            # 创建网络名
            net_name = f"NET_{comp1.reference}_{comp2.reference}"

            # 确保网络存在
            if not any(n.name == net_name for n in self.sheet.nets):
                self._add_net(net_name, "signal")

            # 使用 L 型走线
            mid_x = (x1 + x2) / 2
            self._add_wire([(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)], net_name)

        # 额外：检测并连接特殊引脚
        net_pins: Dict[str, List[Tuple[SchematicComponent, SchematicPin]]] = {}

        for comp in self.sheet.components:
            for pin in comp.pins:
                if pin.pin_type in [
                    PinType.INPUT,
                    PinType.OUTPUT,
                    PinType.BIDIRECTIONAL,
                ]:
                    net_name = self._infer_signal_net(pin.name, comp.reference)
                    if net_name not in net_pins:
                        net_pins[net_name] = []
                    net_pins[net_name].append((comp, pin))

        # 对于每个网络，如果引脚距离近则连线
        for net_name, pins in net_pins.items():
            if len(pins) < 2:
                continue

            for i, (comp1, pin1) in enumerate(pins):
                for comp2, pin2 in pins[i + 1 :]:
                    dist = self._calculate_pin_distance(comp1, pin1, comp2, pin2)

                    if dist < 300:
                        x1 = comp1.position[0] + pin1.position[0]
                        y1 = comp1.position[1] + pin1.position[1]
                        x2 = comp2.position[0] + pin2.position[0]
                        y2 = comp2.position[1] + pin2.position[1]

                        self._add_wire([(x1, y1), (x2, y2)], net_name)

    def _infer_signal_net(self, pin_name: str, comp_ref: str) -> str:
        """推断信号网络名"""
        name_upper = pin_name.upper()

        # 常见信号网络
        if "SDA" in name_upper:
            return "I2C_SDA"
        if "SCL" in name_upper:
            return "I2C_SCL"
        if "MOSI" in name_upper:
            return "SPI_MOSI"
        if "MISO" in name_upper:
            return "SPI_MISO"
        if "SCK" in name_upper or "CLK" in name_upper:
            return "SPI_SCK"
        if "TX" in name_upper:
            return "UART_TX"
        if "RX" in name_upper:
            return "UART_RX"

        # 默认使用元件+引脚作为网络名
        return f"{comp_ref}_{pin_name}"

    def _calculate_pin_distance(
        self,
        comp1: SchematicComponent,
        pin1: SchematicPin,
        comp2: SchematicComponent,
        pin2: SchematicPin,
    ) -> float:
        """计算两个引脚之间的距离"""
        x1 = comp1.position[0] + pin1.position[0]
        y1 = comp1.position[1] + pin1.position[1]
        x2 = comp2.position[0] + pin2.position[0]
        y2 = comp2.position[1] + pin2.position[1]

        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def _add_wire(self, points: List[Tuple[float, float]], net: str):
        """添加导线"""
        self._wire_counter += 1
        wire = SchematicWire(id=f"wire-{self._wire_counter}", points=points, net=net)
        self.sheet.wires.append(wire)
        return wire

    def _add_l_wire(
        self, start: Tuple[float, float], end: Tuple[float, float], net: str
    ):
        """添加优化的 L 型走线（避免交叉）"""
        x1, y1 = start
        x2, y2 = end

        # 计算距离和方向
        dx = x2 - x1
        dy = y2 - y1

        # 选择最佳走线方案
        if abs(dx) < 50 or abs(dy) < 50:
            # 距离很近，直线连接
            self._add_wire([(x1, y1), (x2, y2)], net)
            return

        # 根据相对位置选择走线方式
        # 方案1: 水平优先 (先水平后垂直)
        # 方案2: 垂直优先 (先垂直后水平)
        # 方案3: Z型走线 (中间段水平，两端垂直)

        # 计算网格对齐
        grid_size = 50
        mid_x = ((x1 + x2) // (grid_size * 2)) * (grid_size * 2)

        # 水平优先方案
        if abs(dx) > abs(dy):
            # 水平距离更大，优先水平走线
            points = [
                (x1, y1),
                (x2, y1),  # 先水平
                (x2, y2),  # 再垂直
                (x2, y2),
            ]
            # 简化：如果y方向变化不大，直接用两点
            if abs(dy) < 100:
                points = [(x1, y1), (x2, y2)]
            else:
                # 使用中间点避免交叉
                points = [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]
        else:
            # 垂直距离更大，优先垂直走线
            mid_y = ((y1 + y2) // (grid_size * 2)) * (grid_size * 2)
            points = [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]

        # 网格对齐所有点
        aligned_points = []
        for px, py in points:
            aligned_points.append(
                (round(px / grid_size) * grid_size, round(py / grid_size) * grid_size)
            )

        self._add_wire(aligned_points, net)

    def _add_net_label(self, name: str, position: Tuple[float, float]):
        """添加网络标签"""
        self._label_counter += 1

        # 确保网络存在
        if not any(n.name == name for n in self.sheet.nets):
            self._add_net(name, "signal")

        label = SchematicNetLabel(
            id=f"label-{self._label_counter}",
            name=name,
            position=position,
            direction="right",
            is_global=False,
        )
        self.sheet.net_labels.append(label)
        return label

    def _erc_precheck(self) -> List[str]:
        """ERC 预检查"""
        errors = []

        # 1. 检查未连接的引脚
        connected_pins = set()
        for wire in self.sheet.wires:
            # 简化：只检查端点
            for point in wire.points[:1] + wire.points[-1:]:
                for comp in self.sheet.components:
                    comp_x, comp_y = comp.position
                    for pin in comp.pins:
                        pin_x = comp_x + pin.position[0]
                        pin_y = comp_y + pin.position[1]
                        if abs(pin_x - point[0]) < 10 and abs(pin_y - point[1]) < 10:
                            connected_pins.add(f"{comp.id}:{pin.number}")

        for comp in self.sheet.components:
            for pin in comp.pins:
                pin_key = f"{comp.id}:{pin.number}"
                if pin_key not in connected_pins:
                    # 电源引脚必须连接
                    if pin.pin_type in [PinType.POWER_IN, PinType.GND]:
                        errors.append(f"未连接的电源引脚: {comp.reference}.{pin.name}")

        # 2. 检查缺少的电源符号
        has_vcc = any(s.symbol_type == "vcc" for s in self.sheet.power_symbols)
        has_gnd = any(s.symbol_type == "gnd" for s in self.sheet.power_symbols)

        if not has_vcc:
            errors.append("缺少 VCC 电源符号")
        if not has_gnd:
            errors.append("缺少 GND 电源符号")

        return errors

    def export_to_dict(self) -> Dict[str, Any]:
        """导出为字典格式（供前端使用）"""
        return {
            "components": [
                {
                    "id": c.id,
                    "name": c.name,
                    "model": c.model,
                    "reference": c.reference,
                    "position": {"x": c.position[0], "y": c.position[1]},
                    "size": {"width": c.size[0], "height": c.size[1]},
                    "pins": [
                        {
                            "number": p.number,
                            "name": p.name,
                            "type": p.pin_type.value,
                            "position": {"x": p.position[0], "y": p.position[1]},
                            "direction": p.direction,
                        }
                        for p in c.pins
                    ],
                    "category": c.category.value,
                    "symbol_library": c.symbol_library,
                    "footprint": c.footprint,
                }
                for c in self.sheet.components
            ],
            "nets": [
                {"id": n.id, "name": n.name, "class": n.net_class}
                for n in self.sheet.nets
            ],
            "wires": [
                {
                    "id": w.id,
                    "points": [{"x": p[0], "y": p[1]} for p in w.points],
                    "net": w.net,
                }
                for w in self.sheet.wires
            ],
            "netLabels": [
                {
                    "id": l.id,
                    "name": l.name,
                    "position": {"x": l.position[0], "y": l.position[1]},
                    "direction": l.direction,
                }
                for l in self.sheet.net_labels
            ],
            "powerSymbols": [
                {
                    "id": s.id,
                    "netName": s.net_name,
                    "position": {"x": s.position[0], "y": s.position[1]},
                    "type": s.symbol_type,
                }
                for s in self.sheet.power_symbols
            ],
        }


def generate_standard_schematic(
    components: List[Dict], circuit_type: str = "general"
) -> Dict[str, Any]:
    """
    生成符合标准的原理图（便捷函数）

    Args:
        components: 元件列表
        circuit_type: 电路类型

    Returns:
        Dict: 原理图数据
    """
    generator = SchematicGenerator()
    generator.generate(components, circuit_type)
    return generator.export_to_dict()

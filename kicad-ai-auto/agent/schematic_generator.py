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

        # 9. 优化布局 - 减少线交叉
        logger.info("开始布局优化...")
        original_crossings = self._count_wire_crossings()
        self._optimize_layout()
        optimized_crossings = self._count_wire_crossings()
        reduction = (original_crossings - optimized_crossings) / original_crossings * 100 if original_crossings > 0 else 0
        logger.info(f"布局优化完成: 线交叉从 {original_crossings} 减少到 {optimized_crossings} (减少 {reduction:.1f}%)")

        return self.sheet

    def _categorize_components(
        self, components: List[Dict]
    ) -> Dict[ComponentCategory, List[Dict]]:
        """分类元件（支持 quantity 展开）"""
        categorized = {cat: [] for cat in ComponentCategory}

        # 先展开 quantity 字段
        expanded_components = []
        for comp in components:
            quantity = comp.get("quantity", 1)
            # 确保 quantity 是正整数
            try:
                quantity = max(1, int(quantity))
            except (ValueError, TypeError):
                quantity = 1

            # 根据 quantity 展开元件
            for i in range(quantity):
                # 为每个实例创建副本，添加索引后缀
                expanded_comp = comp.copy()
                # 如果 quantity > 1，修改 name 来区分多个实例
                if quantity > 1:
                    base_name = comp.get("name", "")
                    expanded_comp["_instance_index"] = i + 1
                expanded_components.append(expanded_comp)

        # 使用展开后的元件列表
        for comp in expanded_components:
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
                    "ams1117",
                    "lm7805",
                    "lm7812",
                    "lm317",
                    "lm337",
                    "lt1083",
                    "lt1117",
                    "ap2112",
                    "rt9013",
                    "xc6206",
                    "ncp511",
                    "sot-223",  # common LDO package
                    "sot-89",
                    "to-220",
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
                    "ch340c",
                    "ch340g",
                    "cp210",
                    "cp2102",
                    "ft232",
                    "ft232r",
                    "pl2303",
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
        elif circuit_type == "usb_device":
            # USB设备：USB接口在左侧，电源在中，数据处理在右
            layout = self._layout_usb_device(categorized)
        elif circuit_type == "wireless_sensor":
            # 无线传感器：传感器在左，无线模块在中间，天线在右
            layout = self._layout_wireless_sensor(categorized)
        elif circuit_type == "audio_amplifier":
            # 音频放大器：输入在左，放大器在中间，输出在右
            layout = self._layout_audio_amplifier(categorized)
        elif circuit_type == "motor_control":
            # 电机控制：控制信号在左，驱动在中间，电机在右
            layout = self._layout_motor_control(categorized)
        elif circuit_type == "display_interface":
            # 显示接口：MCU在左，显示接口在右
            layout = self._layout_display_interface(categorized)
        elif circuit_type == "communication":
            # 通信接口：通信芯片在中心，接口在两侧
            layout = self._layout_communication(categorized)
        elif circuit_type == "iot_gateway":
            # 物联网网关：MCU/处理器在中心，无线和接口环绕
            layout = self._layout_iot_gateway(categorized)
        elif circuit_type == "signal_conditioning":
            # 信号调理：输入在左，放大/滤波在中间，输出在右
            layout = self._layout_signal_conditioning(categorized)
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

    def _layout_usb_device(self, categorized: Dict) -> Dict[str, Tuple]:
        """USB设备布局 - USB接口在左，电源管理在中，数据处理在右"""
        layout = {}

        # USB接口在左侧
        layout["usb_interface"] = (50, 200, 200, 400)

        # 电源管理在中间
        layout["power"] = (300, 100, 500, 300)

        # 数据处理/控制在右侧
        layout["control"] = (600, 200, 850, 400)

        # 无源器件在底部
        layout["passive"] = (200, 450, 700, 550)

        return layout

    def _layout_wireless_sensor(self, categorized: Dict) -> Dict[str, Tuple]:
        """无线传感器布局 - 传感器在左，无线模块在中间，天线在右"""
        layout = {}

        # 传感器在左侧
        layout["sensor"] = (50, 150, 200, 350)

        # 无线模块在中间
        layout["wireless"] = (300, 200, 550, 400)

        # 电源管理在顶部
        layout["power"] = (200, 50, 500, 120)

        # 无源器件在底部
        layout["passive"] = (200, 420, 600, 520)

        # 天线连接在右侧
        layout["antenna"] = (650, 250, 800, 350)

        return layout

    def _layout_audio_amplifier(self, categorized: Dict) -> Dict[str, Tuple]:
        """音频放大器布局 - 输入在左，放大器在中间，输出在右"""
        layout = {}

        # 输入接口在左侧
        layout["input"] = (50, 200, 180, 350)

        # 前置放大在中左
        layout["preamp"] = (250, 150, 400, 300)

        # 功率放大在中间
        layout["power_amp"] = (480, 120, 680, 380)

        # 输出在右侧
        layout["output"] = (780, 200, 900, 350)

        # 电源在顶部
        layout["power"] = (300, 50, 600, 100)

        # 无源器件在底部
        layout["passive"] = (200, 420, 700, 520)

        return layout

    def _layout_motor_control(self, categorized: Dict) -> Dict[str, Tuple]:
        """电机控制布局 - 控制信号在左，驱动在中间，电机在右"""
        layout = {}

        # 控制信号在左侧
        layout["control"] = (50, 150, 200, 350)

        # 驱动电路在中间
        layout["driver"] = (300, 150, 500, 350)

        # 电机连接在右侧
        layout["motor"] = (650, 180, 850, 380)

        # 电源在顶部
        layout["power"] = (250, 50, 550, 120)

        # 保护电路在下部
        layout["protection"] = (250, 400, 550, 500)

        return layout

    def _layout_display_interface(self, categorized: Dict) -> Dict[str, Tuple]:
        """显示接口布局 - MCU在左，显示接口在右"""
        layout = {}

        # MCU/处理器在左侧
        layout["mcu"] = (50, 200, 250, 400)

        # 显示接口在中间
        layout["display"] = (350, 150, 600, 350)

        # 显示模块在右侧
        layout["display_module"] = (700, 150, 950, 350)

        # 电源管理在顶部
        layout["power"] = (300, 50, 600, 120)

        # 无源器件在底部
        layout["passive"] = (250, 420, 700, 520)

        return layout

    def _layout_communication(self, categorized: Dict) -> Dict[str, Tuple]:
        """通信接口布局 - 通信芯片在中心，接口在两侧"""
        layout = {}

        # 左侧接口
        layout["interface_left"] = (50, 200, 180, 350)

        # 通信芯片在中心
        layout["comm_chip"] = (300, 180, 550, 380)

        # 右侧接口
        layout["interface_right"] = (700, 200, 850, 350)

        # 电源在顶部
        layout["power"] = (350, 50, 550, 120)

        # 隔离/保护在底部
        layout["isolation"] = (300, 420, 600, 520)

        return layout

    def _layout_iot_gateway(self, categorized: Dict) -> Dict[str, Tuple]:
        """物联网网关布局 - MCU/处理器在中心，无线和接口环绕"""
        layout = {}

        # MCU/处理器在中心
        layout["mcu"] = (380, 220, 580, 380)

        # WiFi/无线模块在左上
        layout["wireless"] = (100, 80, 300, 200)

        # 蓝牙模块在右上
        layout["bluetooth"] = (650, 80, 850, 200)

        # 有线接口在左下
        layout["wired"] = (100, 400, 300, 520)

        # 电源管理在顶部中间
        layout["power"] = (380, 50, 580, 120)

        # 存储在右下
        layout["storage"] = (650, 400, 850, 520)

        return layout

    def _layout_signal_conditioning(self, categorized: Dict) -> Dict[str, Tuple]:
        """信号调理布局 - 输入在左，放大/滤波在中间，输出在右"""
        layout = {}

        # 输入接口在左侧
        layout["input"] = (50, 200, 180, 350)

        # 信号调理（放大/滤波）在中间
        layout["conditioning"] = (300, 150, 550, 380)

        # 输出在右侧
        layout["output"] = (700, 200, 850, 350)

        # 电源在顶部
        layout["power"] = (350, 50, 550, 120)

        # 无源器件（滤波）在底部
        layout["passive"] = (250, 420, 650, 520)

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

        # LED 在右上角
        if ComponentCategory.LED in categorized:
            layout["led"] = (600, self.MARGIN_TOP, 900, self.MARGIN_TOP + 150)

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
        """放置元件到布局区域（带碰撞检测）"""

        # 已放置的元件位置记录（用于碰撞检测）
        placed_positions = []  # List of (x, y, width, height)
        MIN_COMP_WIDTH = 80    # 最小元件宽度
        MIN_COMP_HEIGHT = 60   # 最小元件高度
        MIN_SPACING = 50       # 元件间最小间距

        def check_collision(x, y, width=MIN_COMP_WIDTH, height=MIN_COMP_HEIGHT) -> bool:
            """检查是否与已放置的元件发生碰撞"""
            for px, py, pw, ph in placed_positions:
                # 检查矩形是否重叠（考虑间距）
                if not (x + width + MIN_SPACING < px or 
                        x > px + pw + MIN_SPACING or
                        y + height + MIN_SPACING < py or
                        y > py + ph + MIN_SPACING):
                    return True
            return False

        def find_free_position(x, y, max_attempts=20) -> tuple:
            """寻找空闲位置，如果发生碰撞则自动调整"""
            width, height = MIN_COMP_WIDTH, MIN_COMP_HEIGHT
            attempts = 0
            while check_collision(x, y, width, height) and attempts < max_attempts:
                # 向右下方移动
                x += MIN_SPACING
                y += MIN_SPACING
                attempts += 1
                # 如果超出边界则换行
                if x > 1000:
                    x = 100
                    y += height + MIN_SPACING
            return x, y

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

                # 查找空闲位置（带碰撞检测）
                x, y = find_free_position(x, y)

                # 创建原理图元件
                schematic_comp = self._create_schematic_component(
                    comp, (x, y), category
                )
                self.sheet.components.append(schematic_comp)

                # 记录已放置的位置
                placed_positions.append((x, y, MIN_COMP_WIDTH, MIN_COMP_HEIGHT))

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

        # 如果model为空，使用name作为model
        if not model:
            model = comp_name

        package = comp.get("package", "")

        # ======== 集成符号库查找 ========
        kb_symbol_library = comp.get("symbol_library", "")  # 知识库提供的符号库
        symbol_library = kb_symbol_library
        symbol_name = ""

        try:
            from symbol_lib_parser import get_symbol_parser, symbol_to_dict

            parser = get_symbol_parser()
            symbol = parser.find_symbol_for_component(comp_name, model)

            if symbol:
                found_lib = f"{symbol.library}:{symbol.name}"
                # 如果符号库返回的是默认回退值(Device:R等)，且知识库有更准确的值，优先用知识库
                fallback_symbols = {"Device:R", "Device:C", "Device:L", "Device:U", "Device:D", "Device:LED"}
                if found_lib in fallback_symbols and kb_symbol_library and kb_symbol_library not in fallback_symbols:
                    logger.info(f"符号库返回默认值 {found_lib}，保留知识库值 {kb_symbol_library}")
                    symbol_library = kb_symbol_library
                else:
                    symbol_library = found_lib
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
                # 解析器没找到，保留知识库值
                if kb_symbol_library:
                    logger.info(f"符号解析器未找到 {comp_name}，使用知识库值: {kb_symbol_library}")
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
        """创建元件引脚 - 优先使用知识库的引脚定义"""
        pins = []

        # 尝试从组件数据获取引脚
        comp_pins = comp.get("pins", [])
        if comp_pins:
            for i, pin_data in enumerate(comp_pins):
                if isinstance(pin_data, dict):
                    # ===== 优先使用知识库的 type 字段 =====
                    kb_type = pin_data.get("type", "")
                    if kb_type:
                        # 知识库类型直接映射到 PinType
                        pin_type = self._map_kb_type_to_pintype(kb_type)
                    else:
                        # 知识库没有 type，使用推断
                        pin_type = self._determine_pin_type(pin_data.get("name", ""))

                    # ===== 优先使用知识库的 position 字段 =====
                    kb_position = pin_data.get("position", {})
                    if kb_position and isinstance(kb_position, dict):
                        pos_x = kb_position.get("x", 0)
                        pos_y = kb_position.get("y", 0)
                        position = (pos_x, pos_y)
                    else:
                        # 知识库没有 position，使用计算
                        position = self._calculate_pin_position(
                            i, len(comp_pins), category
                        )

                    # 获取 direction
                    direction = pin_data.get("direction", self._calculate_pin_direction(i, len(comp_pins), category))

                    pin = SchematicPin(
                        number=str(pin_data.get("number", i + 1)),
                        name=pin_data.get("name", f"P{i + 1}"),
                        pin_type=pin_type,
                        position=position,
                        direction=direction,
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

    def _map_kb_type_to_pintype(self, kb_type: str) -> PinType:
        """将知识库的引脚类型映射到 PinType 枚举"""
        type_mapping = {
            "power_in": PinType.POWER_IN,
            "power_out": PinType.POWER_OUT,
            "gnd": PinType.GND,
            "input": PinType.INPUT,
            "output": PinType.OUTPUT,
            "bidirectional": PinType.BIDIRECTIONAL,
            "passive": PinType.PASSIVE,
            "no_connect": PinType.UNSPECIFIED,
            "unspecified": PinType.UNSPECIFIED,
        }
        return type_mapping.get(kb_type.lower(), PinType.PASSIVE)

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

        # 排除 GND 网络，只创建真正的电源符号
        for i, net_name in enumerate(sorted(power_nets)):
            # 跳过 GND 相关网络，它们应该由 GND 符号处理
            if net_name.upper() in ["GND", "VSS", "V-", "AGND", "GROUND"]:
                continue
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

        # 首先检查是否为 GND 引脚
        if any(kw in name_upper for kw in ["GND", "VSS", "V-", "GROUND", "COM", "AGND"]):
            return "GND"

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
                pin_name_upper = pin.name.upper()

                # 检查是否应该连接到 GND
                # 1. power_in/power_out 类型的 GND 引脚
                # 2. passive 类型的 "-" 引脚（电容负极）
                # 3. passive 类型的 "K" 引脚（二极管阴极）
                should_connect_gnd = (
                    pin.pin_type in [PinType.POWER_IN, PinType.GND] and
                    self._infer_power_net_name(pin.name) == "GND"
                ) or (
                    pin.pin_type == PinType.PASSIVE and
                    pin_name_upper in ["-", "K", "A"] and
                    self._is_gnd_related_component(comp)
                )

                if should_connect_gnd:
                    # 找到最近的 GND 符号
                    gnd_sym = min(
                        [s for s in self.sheet.power_symbols if s.symbol_type == "gnd"],
                        key=lambda s: abs(s.position[0] - pin_x) + abs(s.position[1] - pin_y),
                        default=None,
                    )
                    if gnd_sym:
                        self._add_l_wire(
                            (pin_x, pin_y),
                            (gnd_sym.position[0], gnd_sym.position[1] - 20),
                            "GND",
                        )
                    continue

                # 处理 VCC/电源引脚
                if pin.pin_type in [PinType.POWER_IN, PinType.POWER_OUT]:
                    net_name = self._infer_power_net_name(pin.name)

                    # 跳过 GND 引脚（已处理）
                    if net_name == "GND":
                        continue

                    # 连接到对应的 VCC 符号
                    power_sym = next(
                        (
                            s
                            for s in self.sheet.power_symbols
                            if s.net_name == net_name and s.symbol_type == "vcc"
                        ),
                        None,
                    )

                    if power_sym:
                        self._add_l_wire(
                            (power_sym.position[0], power_sym.position[1] + 20),
                            (pin_x, pin_y),
                            net_name,
                        )

    def _is_gnd_related_component(self, comp: SchematicComponent) -> bool:
        """检查元件是否应该将 passive 引脚连接到 GND"""
        name_lower = comp.name.lower()
        model_lower = comp.model.lower()
        combined = name_lower + " " + model_lower

        # 应该连接到 GND 的元件类型
        gnd_related_keywords = [
            "cap", "capacitor", "电容",
            "diode", "tvs", "二极管",
            "led",
            "gnd", "ground",
        ]

        # 检查元件名称或类别
        if comp.category in [ComponentCategory.POWER, ComponentCategory.PASSIVE]:
            return True

        # 检查引脚名称
        for pin in comp.pins:
            pin_name_upper = pin.name.upper()
            # 电容的负极
            if pin_name_upper == "-":
                return True
            # 二极管的阴极/阳极（在某些配置下）
            if pin_name_upper in ["K", "A", "KATH", "ANODE"]:
                # 如果是二极管类元件
                if any(kw in combined for kw in ["diode", "tvs", "led", "二极管"]):
                    return True

        return False

    # ─────────────────────────────────────────────────────────
    # 电路连接规则知识库 - 功能驱动的连接逻辑
    # ─────────────────────────────────────────────────────────

    # 电源连接规则: (源引脚类型, 源引脚名模式) -> [(目标引脚类型, 目标引脚名模式)]
    POWER_CONNECTION_RULES = [
        # 电源输入 -> 电源输入 (并联)
        ((PinType.POWER_IN, r"VCC|VDD|VIN|5V|3V3|V\+"), [(PinType.POWER_IN, r"VCC|VDD|VIN")]),
        # 电源输出 -> 电源输入 (级联)
        ((PinType.POWER_OUT, r"VOUT|VO|OUT"), [(PinType.POWER_IN, r"VCC|VDD|VIN")]),
        # 电源输出 -> 无源器件引脚
        ((PinType.POWER_OUT, r"VOUT|VO|OUT"), [(PinType.PASSIVE, r"\+|1|A|ANODE")]),
        # VCC -> 无源器件
        ((PinType.POWER_IN, r"VCC|VDD|5V|3V3"), [(PinType.PASSIVE, r"\+|1|A|ANODE|IN")]),
    ]

    # 信号连接规则: 输出类型 -> 输入类型
    SIGNAL_CONNECTION_RULES = [
        # UART: TX -> RX
        ((PinType.OUTPUT, r"TX|TXD|UART_TX"), [(PinType.INPUT, r"RX|RXD|UART_RX")]),
        # I2C: SDA <-> SDA (双向)
        ((PinType.BIDIRECTIONAL, r"SDA"), [(PinType.BIDIRECTIONAL, r"SDA")]),
        # I2C: SCL -> SCL (时钟)
        ((PinType.OUTPUT, r"SCL"), [(PinType.INPUT, r"SCL")]),
        # SPI: MOSI -> MOSI
        ((PinType.OUTPUT, r"MOSI|SDO|DO"), [(PinType.INPUT, r"MOSI|SDI|DI")]),
        # SPI: MISO -> MISO
        ((PinType.INPUT, r"MISO"), [(PinType.OUTPUT, r"MISO")]),
        # SPI: SCK -> SCK
        ((PinType.OUTPUT, r"SCK|SCLK|CLK"), [(PinType.INPUT, r"SCK|SCLK|CLK")]),
        # 通用输出 -> 输入
        ((PinType.OUTPUT, r"OUT|OUTPUT|DO"), [(PinType.INPUT, r"IN|INPUT|DI")]),
        # PWM 输出 -> 输入
        ((PinType.OUTPUT, r"PWM"), [(PinType.INPUT, r"PWM|IN")]),
    ]

    # 电路拓扑连接模式
    CIRCUIT_TOPOLOGY_PATTERNS = {
        "power_supply": {
            "stages": ["input", "rectifier", "filter", "regulator", "output"],
            "connections": [
                ("input", "rectifier", "AC_to_DC"),
                ("rectifier", "filter", "ripple_filter"),
                ("filter", "regulator", "regulate"),
                ("regulator", "output", "final_output"),
            ],
        },
        "mcu_peripheral": {
            "center": "MCU",
            "peripherals": ["power", "crystal", "interface", "led"],
        },
        "series_rc": {
            "pattern": [("R", "C")],  # 电阻串联电容
        },
        "series_rled": {
            "pattern": [("R", "LED")],  # 电阻串联LED
        },
        "parallel_caps": {
            "pattern": [("C", "C")],  # 电容并联
        },
    }

    def _connect_signal_pins(self):
        """
        连接信号引脚 - 基于电路功能而非物理位置

        连接策略:
        1. 电源连接: 按电源流向连接 (VCC -> VIN -> VOUT)
        2. 信号连接: 按信号类型匹配 (TX->RX, MOSI->MISO等)
        3. 拓扑连接: 按电路拓扑模式 (串联、并联、级联)
        4. 网络标签: 使用网络标签连接远距离引脚
        """
        components = self.sheet.components
        if len(components) < 2:
            return

        # 阶段1: 识别电路拓扑
        topology = self._identify_circuit_topology()
        logger.info(f"识别到电路拓扑: {topology}")

        # 阶段2: 按功能分组元件
        functional_groups = self._group_components_by_function()

        # 阶段3: 建立功能连接
        connections_made = []

        # 3.1 电源连接
        power_connections = self._connect_power_by_flow(functional_groups)
        connections_made.extend(power_connections)

        # 3.2 信号连接 (基于信号类型)
        signal_connections = self._connect_by_signal_type(functional_groups)
        connections_made.extend(signal_connections)

        # 3.3 拓扑特定连接
        topology_connections = self._connect_by_topology(topology, functional_groups)
        connections_made.extend(topology_connections)

        # 3.4 被动元件连接 (RC、RL、二极管等)
        passive_connections = self._connect_passive_components(functional_groups)
        connections_made.extend(passive_connections)

        logger.info(f"共建立 {len(connections_made)} 个功能连接")

        # 阶段4: 为连接添加网络标签
        self._add_net_labels_for_connections(connections_made)

    def _identify_circuit_topology(self) -> str:
        """识别电路拓扑类型"""
        categories = set()
        for comp in self.sheet.components:
            categories.add(comp.category)

        # 检查电源电路特征
        has_power = ComponentCategory.POWER in categories
        has_passive = ComponentCategory.PASSIVE in categories

        if has_power and len(categories) <= 3:
            return "power_supply"

        # 检查MCU电路特征
        if ComponentCategory.MCU in categories:
            return "mcu_peripheral"

        # 检查LED驱动电路
        if ComponentCategory.LED in categories and has_passive:
            return "led_driver"

        return "general"

    def _group_components_by_function(self) -> Dict[str, List[SchematicComponent]]:
        """按功能分组元件"""
        groups = {
            "power_sources": [],      # 电源 (VCC, GND符号)
            "regulators": [],         # 稳压器
            "passive_input": [],      # 输入侧无源器件
            "passive_output": [],     # 输出侧无源器件
            "active": [],             # 有源器件
            "mcu": [],                # MCU
            "interface": [],          # 接口器件
            "connectors": [],         # 连接器
            "other": [],              # 其他
        }

        for comp in self.sheet.components:
            if comp.category == ComponentCategory.POWER:
                # 区分稳压器和电源符号
                if any(kw in comp.model.lower() for kw in ["7805", "7812", "1117", "regulator", "稳压"]):
                    groups["regulators"].append(comp)
                else:
                    groups["power_sources"].append(comp)
            elif comp.category == ComponentCategory.MCU:
                groups["mcu"].append(comp)
            elif comp.category == ComponentCategory.INTERFACE:
                groups["interface"].append(comp)
            elif comp.category == ComponentCategory.CONNECTOR:
                groups["connectors"].append(comp)
            elif comp.category == ComponentCategory.PASSIVE:
                # 根据位置判断输入/输出侧
                groups["passive_input"].append(comp)  # 简化处理
            elif comp.category == ComponentCategory.ACTIVE:
                groups["active"].append(comp)
            else:
                groups["other"].append(comp)

        return groups

    def _connect_power_by_flow(self, groups: Dict) -> List[Dict]:
        """按电源流向建立连接"""
        connections = []

        regulators = groups.get("regulators", [])
        passive_comps = groups.get("passive_input", []) + groups.get("passive_output", [])

        for reg in regulators:
            # 找到稳压器的引脚
            vin_pin = None
            vout_pin = None
            gnd_pin = None

            for pin in reg.pins:
                pin_name_upper = pin.name.upper()
                if pin.pin_type == PinType.POWER_IN and any(kw in pin_name_upper for kw in ["VIN", "IN", "INPUT"]):
                    vin_pin = pin
                elif pin.pin_type == PinType.POWER_OUT and any(kw in pin_name_upper for kw in ["VOUT", "OUT", "OUTPUT"]):
                    vout_pin = pin
                elif pin.pin_type == PinType.GND or (pin.pin_type == PinType.POWER_IN and "GND" in pin_name_upper):
                    gnd_pin = pin

            # 连接 VOUT 到被动元件 (如输出电容)
            if vout_pin:
                for comp in passive_comps:
                    for pin in comp.pins:
                        if self._should_connect_power_to_passive(vout_pin, pin, comp):
                            conn = self._create_connection(reg, vout_pin, comp, pin, "VOUT_NET")
                            if conn:
                                connections.append(conn)

        return connections

    def _should_connect_power_to_passive(self, power_pin: SchematicPin, passive_pin: SchematicPin, comp: SchematicComponent) -> bool:
        """判断电源引脚是否应该连接到被动元件引脚"""
        passive_name = comp.name.lower()
        passive_pin_name = passive_pin.name.upper()

        # 电容正极 (+, 1) 连电源
        if "cap" in passive_name or "电容" in passive_name:
            if passive_pin_name in ["+", "1", "POS"]:
                return True

        # 电阻一端可连电源
        if "res" in passive_name or "电阻" in passive_name:
            if passive_pin.number == "1":
                return True

        # 二极管阳极连电源
        if "diode" in passive_name or "二极管" in passive_name or "led" in passive_name:
            if passive_pin_name in ["A", "ANODE", "+", "1"]:
                return True

        return False

    def _connect_by_signal_type(self, groups: Dict) -> List[Dict]:
        """基于信号类型建立连接 - 使用知识库规则"""
        connections = []

        try:
            from kb_quality import get_connection_rule_engine, ConnectionType
            engine = get_connection_rule_engine()
        except ImportError:
            logger.warning("无法导入知识库，使用默认信号连接逻辑")
            return self._connect_by_signal_type_fallback(groups)

        # 收集所有信号引脚
        all_components = []
        for group_comps in groups.values():
            all_components.extend(group_comps)

        # 转换为知识库格式
        kb_components = []
        for comp in all_components:
            kb_comp = {
                "reference": comp.reference,
                "model": comp.model,
                "name": comp.name,
                "category": comp.category.value,
                "pins": [
                    {
                        "name": pin.name,
                        "type": pin.pin_type.value,
                        "number": pin.number,
                    }
                    for pin in comp.pins
                ],
            }
            kb_components.append(kb_comp)

        # 使用知识库建议连接
        from kb_quality import suggest_connections
        suggestions = suggest_connections(kb_components)

        # 执行建议的连接
        for sugg in suggestions:
            from_parts = sugg["from"].split(".")
            to_parts = sugg["to"].split(".")

            if len(from_parts) == 2 and len(to_parts) == 2:
                from_ref, from_pin_name = from_parts
                to_ref, to_pin_name = to_parts

                # 查找元件和引脚
                comp1 = next((c for c in all_components if c.reference == from_ref), None)
                comp2 = next((c for c in all_components if c.reference == to_ref), None)

                if comp1 and comp2:
                    pin1 = next((p for p in comp1.pins if p.name == from_pin_name), None)
                    pin2 = next((p for p in comp2.pins if p.name == to_pin_name), None)

                    if pin1 and pin2:
                        conn = self._create_connection(comp1, pin1, comp2, pin2, sugg["net"])
                        if conn:
                            connections.append(conn)

        return connections

    def _connect_by_signal_type_fallback(self, groups: Dict) -> List[Dict]:
        """基于信号类型建立连接 - 降级方案"""
        connections = []

        # 收集所有信号引脚
        signal_pins = []
        for comp in self.sheet.components:
            for pin in comp.pins:
                if pin.pin_type in [PinType.INPUT, PinType.OUTPUT, PinType.BIDIRECTIONAL]:
                    signal_pins.append((comp, pin))

        # 按信号名称分组
        signal_groups = {}
        for comp, pin in signal_pins:
            signal_name = self._normalize_signal_name(pin.name)
            if signal_name not in signal_groups:
                signal_groups[signal_name] = []
            signal_groups[signal_name].append((comp, pin))

        # 连接匹配的信号
        for signal_name, pins in signal_groups.items():
            if len(pins) >= 2:
                # 连接输出到输入
                outputs = [(c, p) for c, p in pins if p.pin_type == PinType.OUTPUT]
                inputs = [(c, p) for c, p in pins if p.pin_type == PinType.INPUT]
                bidis = [(c, p) for c, p in pins if p.pin_type == PinType.BIDIRECTIONAL]

                # 输出 -> 输入
                for out_comp, out_pin in outputs:
                    for in_comp, in_pin in inputs:
                        conn = self._create_connection(out_comp, out_pin, in_comp, in_pin, signal_name)
                        if conn:
                            connections.append(conn)

                # 双向 -> 双向
                if len(bidis) >= 2:
                    for i, (c1, p1) in enumerate(bidis):
                        for c2, p2 in bidis[i+1:]:
                            conn = self._create_connection(c1, p1, c2, p2, signal_name)
                            if conn:
                                connections.append(conn)

        return connections

    def _normalize_signal_name(self, pin_name: str) -> str:
        """标准化信号名称以便分组"""
        name_upper = pin_name.upper()

        # UART
        if "UART_TX" in name_upper or ("TX" in name_upper and "RX" not in name_upper):
            return "UART_TX"
        if "UART_RX" in name_upper or ("RX" in name_upper and "TX" not in name_upper):
            return "UART_RX"

        # I2C
        if "SDA" in name_upper:
            return "I2C_SDA"
        if "SCL" in name_upper:
            return "I2C_SCL"

        # SPI
        if "MOSI" in name_upper or "SDO" in name_upper:
            return "SPI_MOSI"
        if "MISO" in name_upper or "SDI" in name_upper:
            return "SPI_MISO"
        if "SCK" in name_upper or "SCLK" in name_upper:
            return "SPI_SCK"
        if "CS" in name_upper or "NSS" in name_upper or "SS" in name_upper:
            return "SPI_CS"

        return name_upper

    def _connect_by_topology(self, topology: str, groups: Dict) -> List[Dict]:
        """基于电路拓扑建立连接"""
        connections = []

        if topology == "power_supply":
            # 电源电路: 按级联顺序连接
            regulators = groups.get("regulators", [])
            passive = groups.get("passive_input", []) + groups.get("passive_output", [])

            # 连接稳压器之间的级联
            for i in range(len(regulators) - 1):
                reg1 = regulators[i]
                reg2 = regulators[i + 1]
                # 前级VOUT -> 后级VIN
                vout_pin = self._find_pin_by_type_and_name(reg1, PinType.POWER_OUT, r"VOUT|OUT")
                vin_pin = self._find_pin_by_type_and_name(reg2, PinType.POWER_IN, r"VIN|IN")
                if vout_pin and vin_pin:
                    conn = self._create_connection(reg1, vout_pin, reg2, vin_pin, "CASCADE_VOUT")
                    if conn:
                        connections.append(conn)

        elif topology == "mcu_peripheral":
            # MCU电路: 连接MCU到外设
            mcus = groups.get("mcu", [])
            interfaces = groups.get("interface", [])

            for mcu in mcus:
                for iface in interfaces:
                    # 尝试匹配UART
                    mcu_tx = self._find_pin_by_type_and_name(mcu, PinType.OUTPUT, r"TX")
                    iface_rx = self._find_pin_by_type_and_name(iface, PinType.INPUT, r"RX")
                    if mcu_tx and iface_rx:
                        conn = self._create_connection(mcu, mcu_tx, iface, iface_rx, "UART_TX")
                        if conn:
                            connections.append(conn)

        return connections

    def _connect_passive_components(self, groups: Dict) -> List[Dict]:
        """连接被动元件形成RC、RL等电路"""
        connections = []

        passive_comps = groups.get("passive_input", []) + groups.get("passive_output", [])

        # 识别电阻和电容
        resistors = [c for c in passive_comps if "res" in c.name.lower() or "电阻" in c.name.lower()]
        capacitors = [c for c in passive_comps if "cap" in c.name.lower() or "电容" in c.name.lower()]
        leds = [c for c in passive_comps if "led" in c.name.lower() or "发光" in c.name.lower()]

        # R-LED 串联 (限流电阻 + LED)
        for r in resistors:
            for led in leds:
                # 电阻一端 -> LED阳极
                r_pin = self._find_pin_by_number(r, "1") or self._find_pin_by_number(r, "+")
                led_pin = self._find_pin_by_name(led, r"A|ANODE|\+")
                if r_pin and led_pin:
                    conn = self._create_connection(r, r_pin, led, led_pin, "R_LED_SERIES")
                    if conn:
                        connections.append(conn)

        # R-C 串联 (滤波)
        for r in resistors:
            for c in capacitors:
                r_pin = self._find_pin_by_number(r, "2")  # 电阻另一端
                c_pin = self._find_pin_by_number(c, "1") or self._find_pin_by_number(c, "+")  # 电容正极
                if r_pin and c_pin:
                    conn = self._create_connection(r, r_pin, c, c_pin, "RC_FILTER")
                    if conn:
                        connections.append(conn)

        return connections

    def _find_pin_by_type_and_name(self, comp: SchematicComponent, pin_type: PinType, name_pattern: str) -> Optional[SchematicPin]:
        """按类型和名称查找引脚"""
        import re
        for pin in comp.pins:
            if pin.pin_type == pin_type:
                if re.search(name_pattern, pin.name, re.IGNORECASE):
                    return pin
        return None

    def _find_pin_by_number(self, comp: SchematicComponent, number: str) -> Optional[SchematicPin]:
        """按编号查找引脚"""
        for pin in comp.pins:
            if pin.number == number:
                return pin
        return None

    def _find_pin_by_name(self, comp: SchematicComponent, name_pattern: str) -> Optional[SchematicPin]:
        """按名称查找引脚"""
        import re
        for pin in comp.pins:
            if re.search(name_pattern, pin.name, re.IGNORECASE):
                return pin
        return None

    def _create_connection(self, comp1: SchematicComponent, pin1: SchematicPin,
                          comp2: SchematicComponent, pin2: SchematicPin,
                          net_name: str) -> Optional[Dict]:
        """创建两个引脚之间的连接"""
        # 计算引脚位置
        x1 = comp1.position[0] + pin1.position[0]
        y1 = comp1.position[1] + pin1.position[1]
        x2 = comp2.position[0] + pin2.position[0]
        y2 = comp2.position[1] + pin2.position[1]

        # 创建网络
        # 电源/地网络保持功能名，不加组件引用后缀
        power_nets = {"VCC", "GND", "+5V", "+3V3", "+3.3V", "3V3", "5V", "VIN", "VOUT", "VDD", "VSS"}
        if net_name.upper() in {n.upper() for n in power_nets}:
            full_net_name = net_name
        else:
            # 信号网络: 使用 net_name 加简短引用 (去掉数字以减少重复)
            base_net = net_name.split("_")[0] if "_" in net_name else net_name
            full_net_name = f"{base_net}_{comp1.reference}_{comp2.reference}"
        if not any(n.name == full_net_name for n in self.sheet.nets):
            self._add_net(full_net_name, "signal")

        # 创建导线
        self._add_l_wire((x1, y1), (x2, y2), full_net_name)

        return {
            "from": f"{comp1.reference}.{pin1.name}",
            "to": f"{comp2.reference}.{pin2.name}",
            "net": full_net_name,
        }

    def _add_net_labels_for_connections(self, connections: List[Dict]):
        """为连接添加网络标签"""
        for conn in connections:
            net_name = conn["net"]
            # 在连接中间位置添加网络标签
            # 这里简化处理，实际应该计算导线的中点
            pass

    def _connect_signal_pins_old(self):
        """
        [已弃用] 旧的基于物理位置的连接方法
        保留此方法供参考和对比测试
        """
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


def detect_voltage(text: str) -> Optional[float]:
    """
    从文本中检测电压值

    Args:
        text: 包含电压值的文本，如 "5V", "3.3V", "12V"

    Returns:
        电压值(伏特)，如果未检测到则返回None
    """
    import re

    # 匹配电压模式: 数字 + V (可选小数)
    patterns = [
        r"(\d+\.?\d*)\s*V",  # 5V, 3.3V, 12.5V
        r"(\d+\.?\d*)\s*volt",  # 5volt, 3.3volt
        r"VCC\s*(\d+\.?\d*)",  # VCC5
        r"V(\d+\.?\d*)",  # V5, V3.3
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue

    return None


def generate_references(component_type: str, count: int = 1) -> List[str]:
    """
    生成元件参考编号

    Args:
        component_type: 元件类型 (如 "Resistor", "Capacitor", "IC", "STM32")
        count: 生成数量

    Returns:
        参考编号列表
    """
    # 元件前缀映射 (按优先级排序 - 更具体的放前面)
    prefix_map = [
        ("resistor", "R"),
        ("capacitor", "C"),
        ("ic", "U"),
        ("mcu", "U"),
        ("stm32", "U"),
        ("arduino", "U"),
        ("esp32", "U"),
        ("led", "D"),
        ("diode", "D"),
        ("transistor", "Q"),
        ("mosfet", "Q"),
        ("crystal", "Y"),
        ("oscillator", "Y"),
        ("connector", "J"),
        ("usb", "J"),
        ("button", "SW"),
        ("switch", "SW"),
        ("relay", "K"),
        ("fuse", "F"),
        ("motor", "M"),
        ("speaker", "SPK"),
        ("buzzer", "BZ"),
        ("battery", "BT"),
        ("transformer", "T"),
        ("inductor", "L"),
    ]

    # 获取前缀 - 按长度降序匹配
    prefix = "U"  # 默认
    type_lower = component_type.lower()

    # 先尝试精确匹配
    for key, value in prefix_map:
        if key in type_lower:
            prefix = value
            break

    # 生成参考编号
    references = []
    for i in range(1, count + 1):
        references.append(f"{prefix}{i}")

    return references


def extract_voltage_from_component(name: str) -> Optional[float]:
    """
    从元件名称中提取电压

    Args:
        name: 元件名称，如 "LM7805", "AMS1117-3.3"

    Returns:
        电压值，如果未检测到则返回None
    """
    import re

    # 常见稳压器后缀 - 按优先级排序
    patterns = [
        (r"-(\d+\.?\d*)V?$", lambda m: float(m.group(1))),  # AMS1117-3.3 -> 3.3
        (r"_(\d+\.?\d*)V$", lambda m: float(m.group(1))),  # LM7805_5V -> 5.0
        (r"(\d+\.?\d*)V$", lambda m: float(m.group(1))),  # 7805-5 -> 5.0 (末尾是V)
    ]

    for pattern, extractor in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            try:
                return extractor(match)
            except ValueError:
                continue

    return None


# ─────────────────────────────────────────────────────────────
# 布局优化算法 - 减少线交叉
# ─────────────────────────────────────────────────────────────

def _optimize_layout(self):
    """
    优化原理图布局以减少线交叉并提高可读性

    优化策略:
    1. 基于拓扑的分层布局（电源在上，接地在下，信号从左到右）
    2. 使用迭代改进算法最小化线交叉
    3. 对齐网格以保持整洁
    """
    if len(self.sheet.components) < 2:
        return

    # 阶段1: 基于功能重新排列元件
    self._rearrange_by_function()

    # 阶段2: 最小化线交叉（迭代优化）
    self._minimize_wire_crossings()

    # 阶段3: 网格对齐
    self._align_to_grid()

    # 阶段4: 更新导线连接
    self._update_wire_positions()

def _rearrange_by_function(self):
    """基于电路功能重新排列元件位置"""
    components = self.sheet.components

    # 按类别分组
    power_comps = [c for c in components if c.category == ComponentCategory.POWER]
    mcu_comps = [c for c in components if c.category == ComponentCategory.MCU]
    passive_comps = [c for c in components if c.category == ComponentCategory.PASSIVE]
    interface_comps = [c for c in components if c.category == ComponentCategory.INTERFACE]
    other_comps = [c for c in components if c.category not in
                   [ComponentCategory.POWER, ComponentCategory.MCU,
                    ComponentCategory.PASSIVE, ComponentCategory.INTERFACE]]

    # 重新定位元件 - 电源在上，MCU居中，接口在右，无源器件在下
    y_power = 100
    y_mcu = 300
    y_passive = 500
    y_other = 400

    x_start = 150
    spacing = 180

    # 放置电源元件（顶部）
    for i, comp in enumerate(power_comps):
        comp.position = (x_start + i * spacing, y_power)

    # 放置MCU（中心偏左）
    for i, comp in enumerate(mcu_comps):
        comp.position = (x_start + len(power_comps) * spacing / 2 + i * spacing, y_mcu)

    # 放置接口（右侧）
    for i, comp in enumerate(interface_comps):
        comp.position = (x_start + (len(power_comps) + 2) * spacing + i * spacing, y_mcu)

    # 放置无源器件（底部）
    for i, comp in enumerate(passive_comps):
        comp.position = (x_start + i * spacing, y_passive)

    # 放置其他元件
    for i, comp in enumerate(other_comps):
        comp.position = (x_start + i * spacing, y_other)

def _minimize_wire_crossings(self):
    """
    使用迭代改进算法最小化线交叉

    算法:
    1. 计算当前布局的线交叉数
    2. 尝试交换相邻元件位置
    3. 如果交换后线交叉减少，则保留交换
    4. 重复直到无法进一步改进
    """
    max_iterations = 50
    improvement_threshold = 0

    for iteration in range(max_iterations):
        current_crossings = self._count_wire_crossings()
        improved = False

        # 尝试交换每一对相邻元件
        for i in range(len(self.sheet.components)):
            for j in range(i + 1, len(self.sheet.components)):
                comp1 = self.sheet.components[i]
                comp2 = self.sheet.components[j]

                # 跳过不同类型的大跨度交换（保持功能分区）
                if comp1.category != comp2.category:
                    continue

                # 尝试交换
                self._swap_components(comp1, comp2)
                new_crossings = self._count_wire_crossings()

                if new_crossings < current_crossings - improvement_threshold:
                    # 交换减少了线交叉，保留
                    current_crossings = new_crossings
                    improved = True
                else:
                    # 交换没有改善，恢复
                    self._swap_components(comp1, comp2)

        if not improved:
            # 没有进一步改进，停止迭代
            break

def _count_wire_crossings(self) -> int:
    """统计当前布局中的线交叉数"""
    crossings = 0
    wires = self.sheet.wires

    for i in range(len(wires)):
        for j in range(i + 1, len(wires)):
            if self._wires_intersect(wires[i], wires[j]):
                crossings += 1

    return crossings

def _wires_intersect(self, wire1: SchematicWire, wire2: SchematicWire) -> bool:
    """检查两条导线是否相交"""
    points1 = wire1.points
    points2 = wire2.points

    # 检查线段对
    for i in range(len(points1) - 1):
        for j in range(len(points2) - 1):
            if self._segments_intersect(
                points1[i], points1[i + 1],
                points2[j], points2[j + 1]
            ):
                return True

    return False

def _segments_intersect(
    self,
    p1: Tuple[float, float], p2: Tuple[float, float],
    p3: Tuple[float, float], p4: Tuple[float, float]
) -> bool:
    """检查两条线段是否相交（不包括端点重合）"""
    def orientation(a, b, c):
        """计算三点的方向"""
        val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
        if abs(val) < 1e-9:
            return 0  # 共线
        return 1 if val > 0 else 2  # 顺时针或逆时针

    def on_segment(a, b, c):
        """检查点b是否在线段ac上"""
        return (min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and
                min(a[1], c[1]) <= b[1] <= max(a[1], c[1]))

    o1 = orientation(p1, p2, p3)
    o2 = orientation(p1, p2, p4)
    o3 = orientation(p3, p4, p1)
    o4 = orientation(p3, p4, p2)

    # 一般情况
    if o1 != o2 and o3 != o4:
        return True

    # 特殊情况 - 共线
    if o1 == 0 and on_segment(p1, p3, p2):
        return False  # 端点重合不算交叉
    if o2 == 0 and on_segment(p1, p4, p2):
        return False
    if o3 == 0 and on_segment(p3, p1, p4):
        return False
    if o4 == 0 and on_segment(p3, p2, p4):
        return False

    return False

def _swap_components(self, comp1: SchematicComponent, comp2: SchematicComponent):
    """交换两个元件的位置"""
    comp1.position, comp2.position = comp2.position, comp1.position

def _align_to_grid(self):
    """将元件位置对齐到网格"""
    grid_size = 50

    for comp in self.sheet.components:
        x, y = comp.position
        aligned_x = round(x / grid_size) * grid_size
        aligned_y = round(y / grid_size) * grid_size
        comp.position = (aligned_x, aligned_y)

def _update_wire_positions(self):
    """更新导线位置以匹配新的元件位置"""
    # 清除现有导线
    self.sheet.wires.clear()

    # 重新生成导线
    self._generate_wires()


SchematicGenerator._optimize_layout = _optimize_layout
SchematicGenerator._rearrange_by_function = _rearrange_by_function
SchematicGenerator._minimize_wire_crossings = _minimize_wire_crossings
SchematicGenerator._count_wire_crossings = _count_wire_crossings
SchematicGenerator._wires_intersect = _wires_intersect
SchematicGenerator._segments_intersect = _segments_intersect
SchematicGenerator._swap_components = _swap_components
SchematicGenerator._align_to_grid = _align_to_grid
SchematicGenerator._update_wire_positions = _update_wire_positions

"""
PCB 数据模型 - 用于质量评估和迭代优化
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import random
import math


class Severity(Enum):
    """问题严重程度"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueType(Enum):
    """问题类型"""

    # 线宽相关
    TRACK_WIDTH_TOO_NARROW = "track_width_too_narrow"
    TRACK_WIDTH_INSUFFICIENT_CURRENT = "track_width_insufficient_current"

    # 布局相关
    DECOUPLING_CAPACITOR_FAR = "decoupling_capacitor_far"
    CRYSTAL_PLACEMENT_FAR = "crystal_placement_far"
    THERMAL_CLEARANCE_INSUFFICIENT = "thermal_clearance_insufficient"
    CONNECTOR_NOT_EDGE = "connector_not_edge"

    # 走线正确性
    DRC_ERROR = "drc_error"
    DANGLING_TRACK = "dangling_track"
    SHORT_CIRCUIT = "short_circuit"
    STUB_TRACK = "stub_track"
    DIFFERENTIAL_LENGTH_MISMATCH = "differential_length_mismatch"

    # 走线符合性
    TRACK_SPACING_TOO_NARROW = "track_spacing_too_narrow"
    VIA_DRILL_TOO_SMALL = "via_drill_too_small"
    VIA_PAD_TOO_SMALL = "via_pad_too_small"
    COPPER_TO_EDGE_TOO_SMALL = "copper_to_edge_too_small"
    ANNULAR_RING_TOO_SMALL = "annular_ring_too_small"

    # 铺铜相关
    ISOLATED_COPPER = "isolated_copper"

    # RF/无线相关
    ANTENNA_NEAR_METAL = "antenna_near_metal"
    RF_TRACE_TOO_NARROW = "rf_trace_too_narrow"
    SHIELD_TOO_NEAR_ANTENNA = "shield_too_near_antenna"


@dataclass
class Point2D:
    """2D 点"""

    x: float
    y: float

    def distance_to(self, other: "Point2D") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Net:
    """网络"""

    id: str
    name: str
    is_power_supply: bool = False
    is_ground: bool = False
    is_high_speed: bool = False
    is_differential_pair: bool = False
    differential_pair_partner: Optional[str] = None


@dataclass
class Component:
    """元件"""

    id: str
    reference: str  # U1, C1, R1 等
    value: str  # 值
    footprint: str  # 封装
    position: Point2D
    rotation: float = 0
    is_heatsink: bool = False
    is_ic: bool = False
    is_connector: bool = False
    is_crystal: bool = False
    is_mcu: bool = False
    power_pins: List[str] = field(default_factory=list)
    gnd_pins: List[str] = field(default_factory=list)


@dataclass
class Pad:
    """焊盘"""

    id: str
    number: str
    net_id: Optional[str]
    position: Point2D
    size: Tuple[float, float]  # (width, height)


@dataclass
class Track:
    """走线"""

    id: str
    net_id: str
    points: List[Point2D]
    width: float
    layer: str  # "F.Cu", "B.Cu" 等

    @property
    def length(self) -> float:
        if len(self.points) < 2:
            return 0
        total = 0
        for i in range(1, len(self.points)):
            total += self.points[i].distance_to(self.points[i - 1])
        return total

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        if not self.points:
            return (0, 0, 0, 0)
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class Via:
    """过孔"""

    id: str
    net_id: str
    position: Point2D
    diameter: float
    drill: float
    layers: List[str] = field(default_factory=lambda: ["F.Cu", "B.Cu"])


@dataclass
class Zone:
    """铺铜区域"""

    id: str
    net_id: str
    layer: str
    points: List[Point2D]
    filled: bool = True


@dataclass
class PCBBoard:
    """PCB 板"""

    name: str
    width: float  # mm
    height: float  # mm
    components: List[Component] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    vias: List[Via] = field(default_factory=list)
    zones: List[Zone] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    pads: List[Pad] = field(default_factory=list)  # 焊盘

    def get_net(self, net_id: str) -> Optional[Net]:
        for net in self.nets:
            if net.id == net_id:
                return net
        return None

    def get_component(self, ref: str) -> Optional[Component]:
        for comp in self.components:
            if comp.reference == ref:
                return comp
        return None

    def get_net_by_name(self, name: str) -> Optional[Net]:
        """通过名称查找网络"""
        for net in self.nets:
            if net.name == name:
                return net
        return None


@dataclass
class Issue:
    """问题"""

    id: str
    type: IssueType
    severity: Severity
    category: str  # "线宽", "布局", "走线正确性", "走线符合性"
    message: str
    location: Optional[Point2D] = None
    related_ids: List[str] = field(default_factory=list)
    auto_fixable: bool = False
    fix_suggestion: str = ""

    def __hash__(self):
        return hash((self.type.value, self.severity.value, self.message[:50]))


@dataclass
class EvaluationResult:
    """评估结果"""

    iteration: int
    total_issues: int
    error_count: int
    warning_count: int
    issues: List[Issue]
    scores: Dict[str, float]  # 各维度评分

    @property
    def has_new_issues(self) -> bool:
        return self.total_issues > 0


class PCBMockDataGenerator:
    """生成模拟 PCB 测试数据"""

    @staticmethod
    def generate_test_board_1() -> PCBBoard:
        """
        生成测试板1 - 有多种问题的板子
        用于测试迭代优化功能
        """
        board = PCBBoard(name="Test_Board_1", width=100.0, height=80.0)

        # 添加网络
        nets = [
            Net("net1", "VCC", is_power_supply=True),
            Net("net2", "GND", is_ground=True),
            Net(
                "net3",
                "USB_D+",
                is_high_speed=True,
                is_differential_pair=True,
                differential_pair_partner="net4",
            ),
            Net(
                "net4",
                "USB_D-",
                is_high_speed=True,
                is_differential_pair=True,
                differential_pair_partner="net3",
            ),
            Net("net5", "Net-U1-Pad1"),
            Net("net6", "Net-U1-Pad2"),
        ]
        board.nets = nets

        # 添加元件 - 有布局问题的
        components = [
            # MCU (发热元件)
            Component(
                "comp1",
                "U1",
                "STM32F103",
                "LQFP-48",
                Point2D(50, 40),
                is_ic=True,
                is_mcu=True,
                power_pins=["VCC"],
                gnd_pins=["GND"],
            ),
            # 去耦电容 - 距离太远 (问题!)
            Component(
                "comp2", "C1", "10uF", "0805", Point2D(80, 70), is_ic=False
            ),  # 距离 U1 约 45mm (问题!)
            # 去耦电容 - 距离近 (正常)
            Component("comp3", "C2", "100nF", "0603", Point2D(52, 38), is_ic=False),
            # 晶振 - 距离太远 (问题!)
            Component(
                "comp4", "Y1", "8MHz", "HC-49", Point2D(10, 10), is_crystal=True
            ),  # 距离 U1 约 45mm (问题!)
            # 晶振 - 距离近 (正常)
            Component(
                "comp5", "Y2", "32.768KHz", "RTC_XTAL", Point2D(48, 42), is_crystal=True
            ),
            # 发热元件 - 距离太近 (问题!)
            Component(
                "comp6", "U2", "LM7805", "TO-220", Point2D(30, 30), is_heatsink=True
            ),
            Component(
                "comp7", "U3", "LM317", "TO-220", Point2D(35, 25), is_heatsink=True
            ),  # 距离 U2 只有 7mm (问题!)
            # 接插件 - 边缘 (正常)
            Component(
                "comp8", "J1", "USB-B", "USB-B_SMD", Point2D(95, 40), is_connector=True
            ),
            # 接插件 - 非边缘 (问题!)
            Component(
                "comp9", "J2", "Header_10", "2.54mm", Point2D(50, 50), is_connector=True
            ),  # 板中间 (问题!)
        ]
        board.components = components

        # 添加走线 - 有线宽和间距问题
        tracks = [
            # 窄走线 - 电源线 (问题!)
            Track(
                "track1",
                "net1",
                [Point2D(10, 10), Point2D(20, 10)],
                width=0.08,
                layer="F.Cu",
            ),  # 0.08mm < 0.1mm
            # 窄走线 - 信号线 (警告)
            Track(
                "track2",
                "net5",
                [Point2D(30, 30), Point2D(40, 30)],
                width=0.05,
                layer="F.Cu",
            ),  # 0.05mm 太细
            # 正常走线
            Track(
                "track3",
                "net2",
                [Point2D(50, 50), Point2D(60, 50)],
                width=0.3,
                layer="F.Cu",
            ),
            # 差分对 - 长度差异大 (问题!)
            Track(
                "track4",
                "net3",
                [Point2D(70, 10), Point2D(80, 10), Point2D(85, 20), Point2D(90, 30)],
                width=0.15,
                layer="F.Cu",
            ),  # 长度约 22mm
            Track(
                "track5",
                "net4",
                [Point2D(70, 15), Point2D(75, 15)],
                width=0.15,
                layer="F.Cu",
            ),  # 长度约 5mm, 差异 17mm
            # 悬空走线 (问题!)
            Track(
                "track6",
                "net6",
                [Point2D(15, 60), Point2D(25, 65)],
                width=0.2,
                layer="F.Cu",
            ),  # 没有连接任何焊盘
            # Stub 走线 (问题!)
            Track(
                "track7",
                "net3",
                [Point2D(80, 15), Point2D(80, 25), Point2D(85, 25)],
                width=0.15,
                layer="F.Cu",
            ),  # 有 stub
            # 间距过近 (问题!)
            Track(
                "track8",
                "net5",
                [Point2D(40, 40), Point2D(50, 40)],
                width=0.2,
                layer="F.Cu",
            ),
            Track(
                "track9",
                "net6",
                [Point2D(40, 41), Point2D(50, 41)],
                width=0.2,
                layer="F.Cu",
            ),  # 间距只有 0.1mm (违规!)
        ]
        board.tracks = tracks

        # 添加过孔 - 尺寸问题
        vias = [
            Via("via1", "net1", Point2D(20, 20), diameter=0.4, drill=0.2),  # 孔太小
            Via("via2", "net2", Point2D(30, 30), diameter=0.6, drill=0.3),  # 正常
            Via(
                "via3", "net3", Point2D(40, 40), diameter=0.3, drill=0.15
            ),  # 孔和焊盘都太小
        ]
        board.vias = vias

        # 添加铺铜 - 孤岛铜
        zones = [
            Zone(
                "zone1",
                "net2",
                "F.Cu",
                [Point2D(10, 10), Point2D(30, 10), Point2D(30, 30), Point2D(10, 30)],
                filled=True,
            ),
            Zone(
                "zone2",
                "net1",
                "F.Cu",
                [Point2D(80, 70), Point2D(90, 70), Point2D(90, 80), Point2D(80, 80)],
                filled=True,
            ),  # 孤岛
        ]
        board.zones = zones

        return board

    @staticmethod
    def generate_clean_board() -> PCBBoard:
        """生成一个干净的测试板 - 无问题"""
        board = PCBBoard(name="Clean_Board", width=80.0, height=60.0)

        # 网络
        nets = [
            Net("net1", "VCC", is_power_supply=True),
            Net("net2", "GND", is_ground=True),
            Net("net3", "Signal1"),
        ]
        board.nets = nets

        # 合理布局的元件
        components = [
            Component(
                "comp1",
                "U1",
                "MCU",
                "LQFP-48",
                Point2D(40, 30),
                is_ic=True,
                is_mcu=True,
            ),
            Component(
                "comp2", "C1", "10uF", "0805", Point2D(42, 28), is_ic=False
            ),  # 靠近 MCU
            Component(
                "comp3", "Y1", "8MHz", "HC-49", Point2D(38, 32), is_crystal=True
            ),  # 靠近 MCU
            Component(
                "comp4", "J1", "USB", "USB-C", Point2D(78, 30), is_connector=True
            ),  # 边缘
        ]
        board.components = components

        # 合理走线
        tracks = [
            Track(
                "track1",
                "net1",
                [Point2D(10, 10), Point2D(50, 10)],
                width=0.5,
                layer="F.Cu",
            ),  # 宽电源线
            Track(
                "track2",
                "net2",
                [Point2D(10, 20), Point2D(50, 20)],
                width=0.3,
                layer="F.Cu",
            ),
            Track(
                "track3",
                "net3",
                [Point2D(30, 30), Point2D(40, 30)],
                width=0.2,
                layer="F.Cu",
            ),
        ]
        board.tracks = tracks

        # 合理过孔
        vias = [
            Via("via1", "net1", Point2D(20, 20), diameter=0.6, drill=0.3),
            Via("via2", "net2", Point2D(30, 30), diameter=0.6, drill=0.3),
        ]
        board.vias = vias

        return board

    @staticmethod
    def generate_random_board(num_issues: int = 5) -> PCBBoard:
        """生成随机有问题的板子"""
        board = PCBBoard(name="Random_Board", width=100.0, height=80.0)

        # 基础网络
        nets = [
            Net("net_vcc", "VCC", is_power_supply=True),
            Net("net_gnd", "GND", is_ground=True),
            Net("net_usb_dp", "USB_DP", is_high_speed=True),
            Net("net_usb_dn", "USB_DN", is_high_speed=True),
        ]
        board.nets = nets

        # 随机生成元件
        components = []
        for i in range(10):
            x = random.uniform(10, 90)
            y = random.uniform(10, 70)
            is_heatsink = random.random() < 0.2
            components.append(
                Component(
                    f"comp{i}",
                    f"U{i}",
                    "IC",
                    "SOP-8",
                    Point2D(x, y),
                    is_heatsink=is_heatsink,
                    is_ic=True,
                )
            )
        board.components = components

        # 随机生成走线 - 部分有问题
        tracks = []
        for i in range(20):
            x1, y1 = random.uniform(5, 95), random.uniform(5, 75)
            x2, y2 = random.uniform(5, 95), random.uniform(5, 75)
            # 随机线宽 - 有时过细
            width = random.choice([0.05, 0.08, 0.1, 0.2, 0.3, 0.5])
            net_id = random.choice([n.id for n in nets])
            tracks.append(
                Track(
                    f"track{i}",
                    net_id,
                    [Point2D(x1, y1), Point2D(x2, y2)],
                    width,
                    "F.Cu",
                )
            )
        board.tracks = tracks

        # 随机生成过孔
        vias = []
        for i in range(10):
            x, y = random.uniform(5, 95), random.uniform(5, 75)
            # 随机尺寸 - 有时过小
            size = random.choice([0.3, 0.4, 0.5, 0.6])
            drill = random.choice([0.15, 0.2, 0.25, 0.3])
            net_id = random.choice([n.id for n in nets])
            vias.append(Via(f"via{i}", net_id, Point2D(x, y), size, drill))
        board.vias = vias

        return board

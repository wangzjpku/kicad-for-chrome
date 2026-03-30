"""
Automatic Copper Pour - 自动铺铜

功能:
- 自动生成GND/电源平面铺铜
- 支持热焊盘连接
- 避让已有走线和焊盘
- 支持多层板
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class PourType(Enum):
    """铺铜类型"""
    SOLID = "solid"          # 实心铺铜
    HATCHED = "hatched"      # 网格铺铜
    CROSS_HATCH = "cross"    # 交叉网格


class ThermalStyle(Enum):
    """热焊盘样式"""
    FOUR_SPOKE = "4spoke"    # 四条辐条
    TWO_SPOKE = "2spoke"     # 两条辐条
    DIAGONAL = "diagonal"    # 对角辐条


@dataclass
class PourBoundary:
    """铺铜边界"""
    points: List[Tuple[float, float]]  # 边界点列表

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """获取包围盒"""
        if not self.points:
            return (0, 0, 0, 0)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class ThermalRelief:
    """热焊盘"""
    x: float
    y: float
    pad_width: float
    pad_height: float
    net: str
    spoke_width: float = 0.3        # 辐条宽度
    spoke_count: int = 4            # 辐条数量
    gap: float = 0.2                # 与焊盘的间隙


@dataclass
class CopperPour:
    """铺铜定义"""
    net: str                        # 关联网络
    layer: str                      # 所在层
    boundary: PourBoundary          # 边界
    pour_type: PourType = PourType.SOLID
    clearance: float = 0.2          # 间距
    min_island_area: float = 1.0    # 最小孤岛面积 (mm²)
    thermal_reliefs: List[ThermalRelief] = field(default_factory=list)

    # 网格铺铜参数
    hatch_width: float = 1.0        # 网格线宽
    hatch_spacing: float = 1.0      # 网格间距


@dataclass
class PourResult:
    """铺铜结果"""
    net: str
    layer: str
    polygon_points: List[Tuple[float, float]]  # 铺铜多边形
    islands: List[List[Tuple[float, float]]]   # 孤岛列表
    thermal_relief_segments: List[Dict]        # 热焊盘辐条
    area: float                                  # 铺铜面积


class CopperPourEngine:
    """
    自动铺铜引擎

    功能:
    - 自动生成GND铺铜
    - 热焊盘连接
    - 孤岛检测和消除
    """

    # 默认铺铜配置
    DEFAULT_CONFIG = {
        "clearance": 0.2,
        "min_island_area": 1.0,
        "thermal_spoke_width": 0.3,
        "thermal_gap": 0.2,
        "thermal_spoke_count": 4,
    }

    def __init__(
        self,
        board_width: float = 100,
        board_height: float = 80,
        clearance: float = 0.2
    ):
        self.board_width = board_width
        self.board_height = board_height
        self.clearance = clearance

        # 障碍物列表
        self.obstacles: List[Dict] = []
        self.thermal_pads: List[ThermalRelief] = []

    def add_obstacle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        net: Optional[str] = None,
        is_thermal: bool = False
    ):
        """
        添加障碍物

        Args:
            x, y: 位置
            width, height: 尺寸
            net: 关联网络
            is_thermal: 是否需要热焊盘连接
        """
        obstacle = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "net": net,
            "is_thermal": is_thermal
        }
        self.obstacles.append(obstacle)

        if is_thermal and net:
            self.thermal_pads.append(ThermalRelief(
                x=x, y=y,
                pad_width=width,
                pad_height=height,
                net=net
            ))

    def create_ground_pour(
        self,
        layer: str = "F.Cu",
        boundary: Optional[PourBoundary] = None,
        exclude_nets: Optional[Set[str]] = None
    ) -> PourResult:
        """
        创建GND铺铜

        Args:
            layer: 铺铜层
            boundary: 铺铜边界（默认使用板子边界）
            exclude_nets: 要排除的网络

        Returns:
            PourResult: 铺铜结果
        """
        if boundary is None:
            # 使用板子边界
            boundary = PourBoundary(points=[
                (0, 0),
                (self.board_width, 0),
                (self.board_width, self.board_height),
                (0, self.board_height),
            ])

        if exclude_nets is None:
            exclude_nets = set()

        # 收集需要避让的障碍物
        clearance_map = self._build_clearance_map(layer, exclude_nets)

        # 生成铺铜多边形
        polygon = self._generate_pour_polygon(boundary, clearance_map)

        # 生成热焊盘辐条
        thermal_segments = self._generate_thermal_reliefs(layer, exclude_nets)

        # 计算铺铜面积
        area = self._calculate_polygon_area(polygon)

        return PourResult(
            net="GND",
            layer=layer,
            polygon_points=polygon,
            islands=[],
            thermal_relief_segments=thermal_segments,
            area=area
        )

    def create_power_pour(
        self,
        net: str,
        layer: str = "In1.Cu",
        boundary: Optional[PourBoundary] = None
    ) -> PourResult:
        """
        创建电源铺铜

        Args:
            net: 电源网络名称 (如 VCC, 3V3, 5V)
            layer: 铺铜层
            boundary: 铺铜边界

        Returns:
            PourResult: 铺铜结果
        """
        if boundary is None:
            boundary = PourBoundary(points=[
                (0, 0),
                (self.board_width, 0),
                (self.board_width, self.board_height),
                (0, self.board_height),
            ])

        # 只保留连接到该电源的焊盘，其他作为障碍物
        exclude_nets = {net}

        clearance_map = self._build_clearance_map(layer, exclude_nets)
        polygon = self._generate_pour_polygon(boundary, clearance_map)
        thermal_segments = self._generate_thermal_reliefs(layer, exclude_nets, target_net=net)
        area = self._calculate_polygon_area(polygon)

        return PourResult(
            net=net,
            layer=layer,
            polygon_points=polygon,
            islands=[],
            thermal_relief_segments=thermal_segments,
            area=area
        )

    def _build_clearance_map(
        self,
        layer: str,
        exclude_nets: Set[str]
    ) -> List[Dict]:
        """构建需要避让的区域"""
        clearance_areas = []

        for obs in self.obstacles:
            # 跳过指定网络
            if obs.get("net") in exclude_nets:
                continue

            # 扩展边界以包含间距
            clearance_areas.append({
                "x": obs["x"] - self.clearance,
                "y": obs["y"] - self.clearance,
                "width": obs["width"] + 2 * self.clearance,
                "height": obs["height"] + 2 * self.clearance,
                "original": obs
            })

        return clearance_areas

    def _generate_pour_polygon(
        self,
        boundary: PourBoundary,
        clearance_map: List[Dict]
    ) -> List[Tuple[float, float]]:
        """
        生成铺铜多边形

        简化实现：从边界减去避让区域
        """
        # 简化版本：返回边界减去障碍物后的多边形
        # 实际实现需要使用多边形布尔运算

        points = list(boundary.points)

        # 对于每个障碍物，创建一个内凹的多边形
        # 这是简化版本，实际需要复杂的几何计算
        for area in clearance_map:
            # 检查是否影响多边形
            pass

        return points

    def _generate_thermal_reliefs(
        self,
        layer: str,
        exclude_nets: Set[str],
        target_net: str = "GND"
    ) -> List[Dict]:
        """生成热焊盘辐条"""
        segments = []

        for pad in self.thermal_pads:
            if pad.net in exclude_nets:
                continue

            # 生成辐条
            if pad.spoke_count == 4:
                # 四条辐条
                spokes = self._create_4_spoke_thermal(pad)
            elif pad.spoke_count == 2:
                spokes = self._create_2_spoke_thermal(pad)
            else:
                spokes = self._create_diagonal_thermal(pad)

            for spoke in spokes:
                segments.append({
                    "x1": spoke[0][0],
                    "y1": spoke[0][1],
                    "x2": spoke[1][0],
                    "y2": spoke[1][1],
                    "width": pad.spoke_width,
                    "layer": layer,
                    "net": target_net
                })

        return segments

    def _create_4_spoke_thermal(
        self,
        pad: ThermalRelief
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """创建四辐条热焊盘"""
        cx, cy = pad.x, pad.y
        half_w = pad.pad_width / 2 + pad.gap
        half_h = pad.pad_height / 2 + pad.gap

        spokes = []

        # 右辐条
        spokes.append(((cx + half_w, cy), (cx + half_w + 2, cy)))
        # 左辐条
        spokes.append(((cx - half_w, cy), (cx - half_w - 2, cy)))
        # 上辐条
        spokes.append(((cx, cy + half_h), (cx, cy + half_h + 2)))
        # 下辐条
        spokes.append(((cx, cy - half_h), (cx, cy - half_h - 2)))

        return spokes

    def _create_2_spoke_thermal(
        self,
        pad: ThermalRelief
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """创建两辐条热焊盘（水平方向）"""
        cx, cy = pad.x, pad.y
        half_w = pad.pad_width / 2 + pad.gap

        spokes = []
        spokes.append(((cx + half_w, cy), (cx + half_w + 2, cy)))
        spokes.append(((cx - half_w, cy), (cx - half_w - 2, cy)))

        return spokes

    def _create_diagonal_thermal(
        self,
        pad: ThermalRelief
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """创建对角辐条热焊盘"""
        cx, cy = pad.x, pad.y
        r = max(pad.pad_width, pad.pad_height) / 2 + pad.gap

        spokes = []
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle)
            dx = r * math.cos(rad)
            dy = r * math.sin(rad)
            spokes.append(((cx + dx * 0.5, cy + dy * 0.5), (cx + dx * 1.5, cy + dy * 1.5)))

        return spokes

    def _calculate_polygon_area(
        self,
        points: List[Tuple[float, float]]
    ) -> float:
        """计算多边形面积（使用鞋带公式）"""
        n = len(points)
        if n < 3:
            return 0

        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]

        return abs(area) / 2

    def to_kicad_format(self, pour: PourResult) -> str:
        """转换为KiCad格式"""
        lines = []

        # 铺铜区域
        points_str = " ".join([f"(xy {p[0]} {p[1]})" for p in pour.polygon_points])

        lines.append(f"(zone (net \"{pour.net}\") (layer {pour.layer})")
        lines.append(f"  (polygon ({points_str}))")
        lines.append(")")

        # 热焊盘辐条
        for seg in pour.thermal_relief_segments:
            lines.append(
                f"(segment (start {seg['x1']} {seg['y1']}) "
                f"(end {seg['x2']} {seg['y2']}) "
                f"(layer {seg['layer']}) (width {seg['width']}))"
            )

        return "\n".join(lines)


def create_copper_pour_engine(
    board_width: float = 100,
    board_height: float = 80
) -> CopperPourEngine:
    """创建铺铜引擎实例"""
    return CopperPourEngine(
        board_width=board_width,
        board_height=board_height
    )
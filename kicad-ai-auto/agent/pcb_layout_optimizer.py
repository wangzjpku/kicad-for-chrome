"""
PCB 自动布局优化器 v1.0

功能特性：
1. 分离电源/模拟/数字区域
2. 相关元件靠近放置
3. 最小化连线长度
4. 遵守 DFM 规则

作者：AI Assistant
版本：1.0
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class ComponentCategory(Enum):
    """元件类别"""
    POWER = "power"  # 电源类
    ANALOG = "analog"  # 模拟信号
    DIGITAL = "digital"  # 数字信号
    CONNECTOR = "connector"  # 连接器
    IC = "ic"  # 集成电路
    PASSIVE = "passive"  # 无源器件
    OTHER = "other"  # 其他


@dataclass
class LayoutConstraints:
    """布局约束"""
    board_width: float = 100.0  # 板宽 (mm)
    board_height: float = 80.0  # 板高 (mm)
    layer_count: int = 2  # 层数
    keepout_areas: List[Tuple[float, float, float, float]] = None  # 禁布区 [(x1,y1,x2,y2),...]
    fixed_components: List[str] = None  # 固定位置的元件
    nets_to_route_first: List[str] = None  # 优先布线的网络

    def __post_init__(self):
        if self.keepout_areas is None:
            self.keepout_areas = []
        if self.fixed_components is None:
            self.fixed_components = []
        if self.nets_to_route_first is None:
            self.nets_to_route_first = []


@dataclass
class Component:
    """PCB 元件"""
    id: str
    name: str
    width: float  # 宽度 mm
    height: float  # 高度 mm
    category: ComponentCategory = ComponentCategory.OTHER
    fixed_position: Optional[Tuple[float, float]] = None  # 固定位置 (x, y)
    rotation: float = 0.0  # 旋转角度
    nets: List[str] = None  # 连接的 nets

    def __post_init__(self):
        if self.nets is None:
            self.nets = []


@dataclass
class Placement:
    """元件放置"""
    component_id: str
    x: float
    y: float
    rotation: float = 0.0


class PCBLayoutOptimizer:
    """
    PCB 自动布局优化器

    策略:
    1. 分离电源/模拟/数字区域
    2. 相关元件靠近放置
    3. 最小化连线长度
    4. 遵守 DFM 规则
    """

    # 区域边距
    MARGIN = 5.0  # mm
    COMPONENT_SPACING = 2.0  # mm
    REGION_SPACING = 10.0  # mm

    def __init__(self):
        self.components: List[Component] = []
        self.constraints = LayoutConstraints()
        self.placements: Dict[str, Placement] = {}

    def optimize(
        self,
        components: List[Dict],
        constraints: Optional[LayoutConstraints] = None
    ) -> Dict[str, Placement]:
        """
        布局优化

        Args:
            components: 元件列表
            constraints: 布局约束

        Returns:
            Dict[元件ID, Placement] - 元件放置结果
        """
        if constraints:
            self.constraints = constraints

        # 转换元件数据
        self.components = self._parse_components(components)

        # 分类元件
        categorized = self._categorize_components(self.components)

        # 区域划分
        regions = self._partition_regions(categorized)

        # 初始放置
        placements = self._initial_placement(categorized, regions)

        # 迭代优化
        for iteration in range(100):
            cost = self._calculate_cost(placements)
            if cost < 0.01:
                break
            placements = self._optimize_step(placements, cost)

        self.placements = placements
        return placements

    def _parse_components(self, components: List[Dict]) -> List[Component]:
        """解析元件数据"""
        result = []
        for comp_data in components:
            comp = Component(
                id=comp_data.get("id", comp_data.get("reference", "")),
                name=comp_data.get("name", ""),
                width=comp_data.get("width", 10.0),
                height=comp_data.get("height", 10.0),
                category=ComponentCategory.OTHER,
                nets=comp_data.get("nets", [])
            )
            result.append(comp)
        return result

    def _categorize_components(
        self, components: List[Component]
    ) -> Dict[ComponentCategory, List[Component]]:
        """根据名称和 nets 分类元件"""
        categorized = {cat: [] for cat in ComponentCategory}

        for comp in components:
            # 检查是否是电源相关
            if any(net.lower() in ["vcc", "vdda", "vdd", "3v3", "5v"]
                   for net in comp.nets):
                categorized[ComponentCategory.POWER].append(comp)
            # 检查是否是模拟相关
            elif any(net.lower() in ["ain", "aout", "adc", "dac"]
                     for net in comp.nets):
                categorized[ComponentCategory.ANALOG].append(comp)
            # 检查是否是数字相关
            elif any(net.lower() in ["din", "dout", "gpio", "spi", "i2c"]
                     for net in comp.nets):
                categorized[ComponentCategory.DIGITAL].append(comp)
            else:
                # 根据名称分类
                name_lower = comp.name.lower()
                if "ic" in name_lower or "chip" in name_lower:
                    categorized[ComponentCategory.IC].append(comp)
                elif "connector" in name_lower or "usb" in name_lower:
                    categorized[ComponentCategory.CONNECTOR].append(comp)
                elif "resistor" in name_lower or "capacitor" in name_lower:
                    categorized[ComponentCategory.PASSIVE].append(comp)
                else:
                    categorized[ComponentCategory.OTHER].append(comp)

        return categorized

    def _partition_regions(
        self, categorized: Dict[ComponentCategory, List[Component]]
    ) -> Dict[str, Tuple[float, float, float, float]]:
        """
        划分区域

        Returns:
            Dict[区域名, (x1, y1, x2, y2)]
        """
        regions = {}
        board_width = self.constraints.board_width
        board_height = self.constraints.board_height

        # 计算各区域面积需求
        total_area = board_width * board_height
        margin = self.MARGIN

        # 电源区域 - 左上
        regions["power"] = (margin, margin, board_width * 0.3, board_height * 0.4)

        # 模拟区域 - 右上
        regions["analog"] = (board_width * 0.35, margin, board_width * 0.65, board_height * 0.4)

        # 数字区域 - 中下
        regions["digital"] = (margin, board_height * 0.45, board_width * 0.65, board_height * 0.9)

        # 连接器区域 - 右下
        regions["connector"] = (board_width * 0.7, board_height * 0.45, board_width - margin, board_height - margin)

        return regions

    def _initial_placement(
        self,
        categorized: Dict[ComponentCategory, List[Component]],
        regions: Dict[str, Tuple[float, float, float, float]]
    ) -> Dict[str, Placement]:
        """初始放置"""
        placements = {}

        # 映射类别到区域
        category_to_region = {
            ComponentCategory.POWER: "power",
            ComponentCategory.ANALOG: "analog",
            ComponentCategory.DIGITAL: "digital",
            ComponentCategory.CONNECTOR: "connector",
            ComponentCategory.IC: "digital",
            ComponentCategory.PASSIVE: "digital",
            ComponentCategory.OTHER: "digital",
        }

        for category, components in categorized.items():
            region_name = category_to_region.get(category, "digital")
            if region_name not in regions:
                continue

            x1, y1, x2, y2 = regions[region_name]
            region_width = x2 - x1
            region_height = y2 - y1

            # 计算该区域的元件数量和布局
            n = len(components)
            if n == 0:
                continue

            # 简单网格布局
            cols = math.ceil(math.sqrt(n * region_width / region_height))
            rows = math.ceil(n / cols)

            cell_width = (region_width - 2 * self.MARGIN) / cols
            cell_height = (region_height - 2 * self.MARGIN) / rows

            for i, comp in enumerate(components):
                if comp.id in self.constraints.fixed_components and comp.fixed_position:
                    # 使用固定位置
                    placements[comp.id] = Placement(
                        component_id=comp.id,
                        x=comp.fixed_position[0],
                        y=comp.fixed_position[1],
                        rotation=comp.rotation
                    )
                else:
                    # 计算位置
                    col = i % cols
                    row = i // cols

                    x = x1 + self.MARGIN + col * cell_width + cell_width / 2 - comp.width / 2
                    y = y1 + self.MARGIN + row * cell_height + cell_height / 2 - comp.height / 2

                    placements[comp.id] = Placement(
                        component_id=comp.id,
                        x=max(x, self.MARGIN),
                        y=max(y, self.MARGIN),
                        rotation=comp.rotation
                    )

        return placements

    def _calculate_cost(self, placements: Dict[str, Placement]) -> float:
        """计算布局成本"""
        cost = 0.0

        # 计算连线长度成本
        for comp in self.components:
            if comp.id not in placements:
                continue

            pos = placements[comp.id]
            for net in comp.nets:
                # 找到连接同一 net 的其他元件
                for other in self.components:
                    if other.id == comp.id or other.id not in placements:
                        continue
                    if net in other.nets:
                        other_pos = placements[other.id]
                        dist = math.sqrt((pos.x - other_pos.x) ** 2 + (pos.y - other_pos.y) ** 2)
                        cost += dist

        # 计算重叠惩罚
        for id1, pos1 in placements.items():
            for id2, pos2 in placements.items():
                if id1 >= id2:
                    continue

                comp1 = next((c for c in self.components if c.id == id1), None)
                comp2 = next((c for c in self.components if c.id == id2), None)

                if not comp1 or not comp2:
                    continue

                # 检查重叠
                overlap_x = abs(pos1.x - pos2.x) < (comp1.width + comp2.width) / 2
                overlap_y = abs(pos1.y - pos2.y) < (comp1.height + comp2.height) / 2

                if overlap_x and overlap_y:
                    cost += 1000.0  # 重叠惩罚

        return cost

    def _optimize_step(
        self, placements: Dict[str, Placement], current_cost: float
    ) -> Dict[str, Placement]:
        """单步优化 - 简单的贪心移动"""
        improved = placements.copy()

        for comp_id, placement in placements.items():
            comp = next((c for c in self.components if c.id == comp_id), None)
            if not comp:
                continue

            # 尝试向四个方向移动
            best_pos = placement
            best_cost = current_cost
            step = 5.0  # mm

            for dx, dy in [(0, -step), (0, step), (-step, 0), (step, 0)]:
                new_placement = Placement(
                    component_id=comp_id,
                    x=placement.x + dx,
                    y=placement.y + dy,
                    rotation=placement.rotation
                )

                # 临时更新
                test_placements = improved.copy()
                test_placements[comp_id] = new_placement

                # 检查是否在边界内
                if (new_placement.x < self.MARGIN or
                    new_placement.y < self.MARGIN or
                    new_placement.x > self.constraints.board_width - comp.width or
                    new_placement.y > self.constraints.board_height - comp.height):
                    continue

                # 计算新成本
                new_cost = self._calculate_cost(test_placements)

                if new_cost < best_cost:
                    best_cost = new_cost
                    best_pos = new_placement

            improved[comp_id] = best_pos

        return improved

    def get_result(self) -> List[Dict[str, Any]]:
        """获取结果"""
        return [
            {
                "id": p.component_id,
                "x": p.x,
                "y": p.y,
                "rotation": p.rotation
            }
            for p in self.placements.values()
        ]


# 全局实例
_layout_optimizer: Optional[PCBLayoutOptimizer] = None


def get_layout_optimizer() -> PCBLayoutOptimizer:
    """获取布局优化器单例"""
    global _layout_optimizer
    if _layout_optimizer is None:
        _layout_optimizer = PCBLayoutOptimizer()
    return _layout_optimizer


def auto_layout_components(
    components: List[Dict],
    constraints: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    自动布局元件

    Args:
        components: 元件列表
        constraints: 布局约束

    Returns:
        元件放置结果
    """
    optimizer = get_layout_optimizer()

    # 转换约束
    layout_constraints = None
    if constraints:
        layout_constraints = LayoutConstraints(
            board_width=constraints.get("board_width", 100.0),
            board_height=constraints.get("board_height", 80.0),
            layer_count=constraints.get("layer_count", 2),
            fixed_components=constraints.get("fixed_components", []),
            nets_to_route_first=constraints.get("nets_to_route_first", [])
        )

    optimizer.optimize(components, layout_constraints)
    return optimizer.get_result()

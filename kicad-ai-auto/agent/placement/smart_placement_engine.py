"""
智能PCB布局引擎

基于 kicad-auto-designer 算法移植
实现约束驱动布局、货架装箱、力导向松弛、边缘放置等功能

Author: Claude Code
Date: 2026-03-29
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class ComponentCategory(Enum):
    """组件类别枚举"""
    POWER = "Power"
    MCU = "MCU"
    WIRELESS = "Wireless"
    MOTOR = "Motor"
    INTERFACE = "Interface"
    ANTENNA = "Antenna"
    PASSIVE = "Passive"
    CRYSTAL = "Crystal"
    SENSOR = "Sensor"
    OTHER = "Other"


@dataclass
class Component:
    """PCB组件数据结构"""
    reference: str
    footprint: str
    value: str = ""
    width: float = 5.0
    height: float = 5.0
    category: ComponentCategory = ComponentCategory.OTHER
    position: Optional[Dict[str, float]] = None
    nets: List[str] = field(default_factory=list)
    pins: List[Dict] = field(default_factory=list)
    is_connector: bool = False
    is_power_component: bool = False

    def get_area(self) -> float:
        return self.width * self.height


@dataclass
class PlacementConstraint:
    """布局约束"""
    constraint_type: str
    component_refs: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlacementResult:
    """布局结果"""
    positions: Dict[str, Dict[str, float]]
    score: float = 0.0
    violations: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


class SmartPlacementEngine:
    """
    智能PCB布局引擎

    核心算法:
    1. 组件分类 (Component Categorization)
    2. 货架装箱 (Shelf Packing - NFDH)
    3. 力导向松弛 (Force-Directed Relaxation)
    4. 边缘放置 (Edge Placement)
    """

    CATEGORY_PRIORITY = {
        ComponentCategory.POWER: 1,
        ComponentCategory.MCU: 2,
        ComponentCategory.WIRELESS: 3,
        ComponentCategory.MOTOR: 4,
        ComponentCategory.CRYSTAL: 5,
        ComponentCategory.SENSOR: 6,
        ComponentCategory.INTERFACE: 7,
        ComponentCategory.ANTENNA: 8,
        ComponentCategory.PASSIVE: 9,
        ComponentCategory.OTHER: 99,
    }

    EDGE_RULES = {
        "USB": {"edge": "bottom", "orientation": 0, "priority": 1},
        "UART": {"edge": "right", "orientation": 90, "priority": 2},
        "JTAG": {"edge": "right", "orientation": 90, "priority": 3},
        "POWER": {"edge": "bottom", "orientation": 0, "priority": 1},
        "ANTENNA": {"edge": "bottom-left", "orientation": 0, "priority": 0},
    }

    CONNECTOR_KEYWORDS = ["USB", "UART", "JTAG", "DEBUG", "POWER", "GPIO", "ANT"]
    POWER_KEYWORDS = ["LDO", "DCDC", "PMIC", "MP1584", "AMS1117", "TPS", "LM", "7805"]

    def __init__(self, board_width=100.0, board_height=80.0, margin=4.0, spacing=2.0):
        self.board_width = board_width
        self.board_height = board_height
        self.margin = margin
        self.spacing = spacing
        self.max_iterations = 80
        self.relax_iterations = 20
        self.min_spacing_relax = 0.5
        logger.info(f"SmartPlacementEngine: {board_width}x{board_height}mm")

    def place(self, components, constraints=None):
        """执行智能布局"""
        logger.info(f"Placing {len(components)} components")

        self._categorize_components(components)
        self._identify_special_components(components)
        edge_comps, inner_comps = self._separate_edge_components(components)

        inner_pos = self._shelf_packing(inner_comps)
        edge_pos = self._place_edge_components(edge_comps)

        all_pos = {**inner_pos, **edge_pos}
        all_pos = self._force_directed_relaxation(all_pos, components)
        all_pos = self._compact_layout(all_pos, components)

        score, violations, stats = self._evaluate_layout(all_pos, components)

        return PlacementResult(positions=all_pos, score=score, violations=violations, statistics=stats)

    def _categorize_components(self, components):
        for c in components:
            c.category = self._detect_category(c)

    def _detect_category(self, comp):
        ref = comp.reference.upper()
        fp = comp.footprint.lower() if comp.footprint else ""

        if any(kw in ref for kw in self.CONNECTOR_KEYWORDS):
            if "ANT" in ref:
                return ComponentCategory.ANTENNA
            return ComponentCategory.INTERFACE
        if ref.startswith("U") and any(kw in fp for kw in ["qfn", "qfp", "bga"]):
            return ComponentCategory.MCU
        if ref.startswith(("R", "C", "L", "D")):
            return ComponentCategory.PASSIVE
        return ComponentCategory.OTHER

    def _identify_special_components(self, components):
        for c in components:
            c.is_connector = any(kw in c.reference.upper() for kw in self.CONNECTOR_KEYWORDS)

    def _separate_edge_components(self, components):
        edge, inner = [], []
        for c in components:
            if c.is_connector or c.category == ComponentCategory.ANTENNA:
                edge.append(c)
            else:
                inner.append(c)
        return edge, inner

    def _shelf_packing(self, components):
        """货架装箱算法 (Next-Fit Decreasing Height)"""
        if not components:
            return {}

        # 排序：优先级 → 面积（大到小）→ 引用编号（确保稳定排序）
        sorted_comps = sorted(
            components,
            key=lambda c: (
                self.CATEGORY_PRIORITY.get(c.category, 99),
                -c.width * c.height,
                c.reference  # 确保相同尺寸组件有不同的排序
            )
        )
        positions = {}

        x, y, row_h = self.margin, self.margin, 0
        target_w = min(
            self.board_width - 2 * self.margin,
            math.sqrt(sum(c.width * c.height for c in sorted_comps) * 1.5)
        )
        target_w = max(target_w, self.margin + 10)  # 确保最小宽度

        for c in sorted_comps:
            # 检查是否需要换行
            if x + c.width > target_w:
                x = self.margin
                y += row_h + self.spacing
                row_h = 0

            # 检查是否超出边界，如果超出则扩展目标宽度
            if y + c.height > self.board_height - self.margin:
                # 扩展目标宽度，重新开始
                target_w = self.board_width - 2 * self.margin
                x = self.margin
                y = self.margin
                row_h = 0

            positions[c.reference] = {
                "x": x + c.width / 2,
                "y": y + c.height / 2,
                "rotation": 0
            }
            x += c.width + self.spacing
            row_h = max(row_h, c.height)

        return positions

    def _place_edge_components(self, components):
        """边缘组件放置"""
        positions = {}
        bottom_x = self.margin
        right_y = self.margin

        # 按优先级排序
        def get_priority(c):
            ref = c.reference.upper()
            for kw, rule in self.EDGE_RULES.items():
                if kw in ref:
                    return rule.get("priority", 99)
            return 99

        sorted_comps = sorted(components, key=get_priority)

        for c in sorted_comps:
            ref_upper = c.reference.upper()
            rule = {"edge": "right", "orientation": 90}

            for kw, r in self.EDGE_RULES.items():
                if kw in ref_upper:
                    rule = r
                    break

            if rule["edge"] == "bottom":
                positions[c.reference] = {
                    "x": bottom_x + c.width / 2,
                    "y": self.board_height - self.margin - c.height / 2,
                    "rotation": 0
                }
                bottom_x += c.width + self.spacing
            else:
                positions[c.reference] = {
                    "x": self.board_width - self.margin - c.width / 2,
                    "y": right_y + c.height / 2,
                    "rotation": 90
                }
                right_y += c.height + self.spacing

        return positions

    def _force_directed_relaxation(self, positions, components, iterations=None):
        """力导向松弛算法 - 消除重叠"""
        import random
        random.seed(42)  # 确保可重复性

        iterations = iterations or self.relax_iterations
        comp_dict = {c.reference: c for c in components}
        positions = {k: v.copy() for k, v in positions.items()}

        for iteration in range(iterations):
            forces = {r: [0.0, 0.0] for r in positions}
            refs = list(positions.keys())

            # 计算两两之间的斥力
            for i, r1 in enumerate(refs):
                for r2 in refs[i + 1:]:
                    if r1 not in comp_dict or r2 not in comp_dict:
                        continue
                    c1, c2 = comp_dict[r1], comp_dict[r2]
                    p1, p2 = positions[r1], positions[r2]

                    dx = p2["x"] - p1["x"]
                    dy = p2["y"] - p1["y"]
                    dist = math.sqrt(dx * dx + dy * dy)

                    # 处理完全重叠或非常接近的情况
                    if dist < 0.1:
                        # 给一个确定性的推开方向（基于引用名）
                        # 确保方向不是零向量
                        angle = (hash(r1) + iteration * 0.5) % 6.28  # 使用 hash 和迭代次数
                        dx = math.cos(angle)
                        dy = math.sin(angle)
                        dist = 0.1

                    # 计算最小允许距离
                    min_d = (
                        max(c1.width, c1.height) / 2 +
                        max(c2.width, c2.height) / 2 +
                        self.min_spacing_relax
                    )

                    # 如果距离小于最小距离，施加斥力
                    if dist < min_d:
                        # 力的大小与重叠程度成正比
                        overlap = min_d - dist
                        f = overlap * 2.0  # 增强力的大小

                        forces[r1][0] -= f * dx / dist
                        forces[r1][1] -= f * dy / dist
                        forces[r2][0] += f * dx / dist
                        forces[r2][1] += f * dy / dist

            # 应用力，限制在板子范围内
            for r in positions:
                if r not in comp_dict:
                    continue
                c = comp_dict[r]
                positions[r]["x"] = max(
                    self.margin + c.width / 2,
                    min(self.board_width - self.margin - c.width / 2, positions[r]["x"] + forces[r][0])
                )
                positions[r]["y"] = max(
                    self.margin + c.height / 2,
                    min(self.board_height - self.margin - c.height / 2, positions[r]["y"] + forces[r][1])
                )

        return positions

    def _compact_layout(self, positions, components):
        """2D压缩优化"""
        comp_dict = {c.reference: c for c in components}

        for _ in range(self.max_iterations):
            improved = False
            for r in sorted(positions.keys(), key=lambda x: positions[x]["x"]):
                if r not in comp_dict:
                    continue
                c = comp_dict[r]
                new_x = positions[r]["x"] - 0.5
                if new_x >= self.margin + c.width / 2:
                    positions[r]["x"] = new_x
                    improved = True

            if not improved:
                break

        return positions

    def _evaluate_layout(self, positions, components):
        """评估布局质量"""
        violations = []
        comp_dict = {c.reference: c for c in components}
        overlaps = 0

        refs = list(positions.keys())
        for i, r1 in enumerate(refs):
            for r2 in refs[i + 1:]:
                if r1 not in comp_dict or r2 not in comp_dict:
                    continue
                c1, c2 = comp_dict[r1], comp_dict[r2]
                p1, p2 = positions[r1], positions[r2]

                if (abs(p1["x"] - p2["x"]) < (c1.width + c2.width) / 2 and
                    abs(p1["y"] - p2["y"]) < (c1.height + c2.height) / 2):
                    overlaps += 1
                    violations.append(f"Overlap: {r1} and {r2}")

        score = max(0, 100 - overlaps * 20)
        stats = {
            "total_components": len(components),
            "overlaps": overlaps,
            "board_utilization": sum(c.width * c.height for c in components) / (self.board_width * self.board_height)
        }

        return score, violations, stats


def create_components_from_schematic(schematic_data):
    """从原理图数据创建组件列表"""
    components = []
    for cd in schematic_data.get("components", []):
        components.append(Component(
            reference=cd.get("reference", ""),
            footprint=cd.get("footprint", ""),
            value=cd.get("value", ""),
            width=cd.get("width", 5.0),
            height=cd.get("height", 5.0),
            nets=cd.get("nets", []),
        ))
    return components
"""
Bulk Placement Engine - 批量放置引擎

Phase 6: 提供从 BOM 批量添加元件到原理图的功能

功能:
- 从 BOM 批量添加元件
- 自动排布元件位置
- 批量属性编辑

Author: Claude Code
Date: 2026-03-30
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PlacementStrategy(Enum):
    """放置策略"""
    GRID = "grid"           # 网格排列
    HORIZONTAL = "horizontal"  # 水平排列
    VERTICAL = "vertical"    # 垂直排列
    AUTO = "auto"           # 自动选择


@dataclass
class BOMItem:
    """BOM 元件"""
    reference: str           # 参考标识 (R1, C1, U1)
    value: str               # 值 (10k, 100nF, STM32F103)
    footprint: str = ""      # 封装 (0805, QFN-48)
    symbol: str = ""         # 符号库名称
    quantity: int = 1        # 数量


@dataclass
class PlacedComponent:
    """已放置元件"""
    reference: str
    symbol_name: str
    library: str
    x: float
    y: float
    rotation: float = 0.0
    properties: Dict[str, str] = field(default_factory=dict)


@dataclass
class PlacementResult:
    """放置结果"""
    components: List[PlacedComponent]
    total: int
    strategy: PlacementStrategy
    grid_cols: int = 0
    grid_rows: int = 0


class BulkPlacementEngine:
    """
    批量放置引擎

    支持:
    - 从 BOM 批量放置元件
    - 多种排列策略
    - 自动坐标分配
    """

    def __init__(
        self,
        start_x: float = 100.0,
        start_y: float = 100.0,
        spacing_x: float = 50.0,
        spacing_y: float = 30.0,
    ):
        """
        Args:
            start_x: 起始 X 坐标
            start_y: 起始 Y 坐标
            spacing_x: 元件间距 X
            spacing_y: 元件间距 Y
        """
        self.start_x = start_x
        self.start_y = start_y
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y

    def place_from_bom(
        self,
        bom_items: List[BOMItem],
        strategy: PlacementStrategy = PlacementStrategy.AUTO,
        max_cols: int = 10,
    ) -> PlacementResult:
        """
        从 BOM 批量放置元件

        Args:
            bom_items: BOM 元件列表
            max_cols: 最大列数（网格策略）

        Returns:
            PlacementResult: 放置结果
        """
        if not bom_items:
            return PlacementResult(
                components=[],
                total=0,
                strategy=strategy,
            )

        # 根据元件数量自动选择策略
        if strategy == PlacementStrategy.AUTO:
            total = sum(item.quantity for item in bom_items)
            if total <= 5:
                strategy = PlacementStrategy.HORIZONTAL
            elif total <= 20:
                strategy = PlacementStrategy.GRID
            else:
                strategy = PlacementStrategy.VERTICAL

        if strategy == PlacementStrategy.GRID:
            return self._place_grid(bom_items, max_cols)
        elif strategy == PlacementStrategy.HORIZONTAL:
            return self._place_horizontal(bom_items)
        else:
            return self._place_vertical(bom_items)

    def _place_grid(
        self,
        bom_items: List[BOMItem],
        max_cols: int,
    ) -> PlacementResult:
        """网格排列"""
        components: List[PlacedComponent] = []
        row, col = 0, 0

        for item in bom_items:
            for q in range(item.quantity):
                x = self.start_x + col * self.spacing_x
                y = self.start_y + row * self.spacing_y

                ref = f"{item.reference}" if q == 0 else f"{item.reference[:-1]}{q + 1}"

                component = PlacedComponent(
                    reference=ref,
                    symbol_name=item.symbol,
                    library=item.footprint,
                    x=x,
                    y=y,
                    properties={
                        "Value": item.value,
                        "Footprint": item.footprint,
                    },
                )
                components.append(component)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        return PlacementResult(
            components=components,
            total=len(components),
            strategy=PlacementStrategy.GRID,
            grid_cols=min(max_cols, len(components)),
            grid_rows=row + 1,
        )

    def _place_horizontal(
        self,
        bom_items: List[BOMItem],
    ) -> PlacementResult:
        """水平排列"""
        components: List[PlacedComponent] = []
        x = self.start_x

        for item in bom_items:
            for q in range(item.quantity):
                y = self.start_y

                ref = f"{item.reference}" if q == 0 else f"{item.reference[:-1]}{q + 1}"

                component = PlacedComponent(
                    reference=ref,
                    symbol_name=item.symbol,
                    library=item.footprint,
                    x=x,
                    y=y,
                    properties={
                        "Value": item.value,
                        "Footprint": item.footprint,
                    },
                )
                components.append(component)
                x += self.spacing_x

        return PlacementResult(
            components=components,
            total=len(components),
            strategy=PlacementStrategy.HORIZONTAL,
        )

    def _place_vertical(
        self,
        bom_items: List[BOMItem],
    ) -> PlacementResult:
        """垂直排列"""
        components: List[PlacedComponent] = []
        y = self.start_y

        for item in bom_items:
            for q in range(item.quantity):
                x = self.start_x

                ref = f"{item.reference}" if q == 0 else f"{item.reference[:-1]}{q + 1}"

                component = PlacedComponent(
                    reference=ref,
                    symbol_name=item.symbol,
                    library=item.footprint,
                    x=x,
                    y=y,
                    properties={
                        "Value": item.value,
                        "Footprint": item.footprint,
                    },
                )
                components.append(component)
                y += self.spacing_y

        return PlacementResult(
            components=components,
            total=len(components),
            strategy=PlacementStrategy.VERTICAL,
        )

    def update_positions(
        self,
        components: List[PlacedComponent],
        start_x: Optional[float] = None,
        start_y: Optional[float] = None,
        spacing_x: Optional[float] = None,
        spacing_y: Optional[float] = None,
        strategy: PlacementStrategy = PlacementStrategy.GRID,
        max_cols: int = 10,
    ) -> PlacementResult:
        """更新元件位置"""
        if start_x is not None:
            self.start_x = start_x
        if start_y is not None:
            self.start_y = start_y
        if spacing_x is not None:
            self.spacing_x = spacing_x
        if spacing_y is not None:
            self.spacing_y = spacing_y

        # 重新计算位置
        result = self.place_from_bom(
            [
                BOMItem(
                    reference=c.reference,
                    value=c.properties.get("Value", ""),
                    footprint=c.library,
                    symbol=c.symbol_name,
                )
                for c in components
            ],
            strategy=strategy,
            max_cols=max_cols,
        )

        # 保留原始属性
        for i, comp in enumerate(result.components):
            if i < len(components):
                result.components[i].properties = components[i].properties
                result.components[i].rotation = components[i].rotation

        return result


def parse_bom_text(bom_text: str) -> List[BOMItem]:
    """
    解析 BOM 文本 (CSV 格式)

    支持格式:
    Reference,Value,Footprint,Symbol
    R1,10k,0805,R
    C1,100nF,0805,C
    """
    items: List[BOMItem] = []
    lines = bom_text.strip().split("\n")

    if not lines:
        return items

    # 跳过表头
    start_idx = 0
    header = lines[0].lower()
    if "reference" in header or "value" in header:
        start_idx = 1

    for line in lines[start_idx:]:
        if not line.strip():
            continue

        # 支持逗号、制表符和空格分隔
        if "," in line:
            parts = [p.strip() for p in line.split(",")]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        else:
            # 空格分隔，但保留值中可能的空格
            parts = line.strip().split(None, 3)  # 最多分4段: ref value footprint symbol

        if len(parts) < 2:
            continue

        reference = parts[0]
        value = parts[1]
        footprint = parts[2] if len(parts) > 2 else ""
        symbol = parts[3] if len(parts) > 3 else ""

        # 处理数量前缀 (e.g., "R1-R5" -> R1, R2, R3, R4, R5)
        refs = _expand_reference_range(reference)

        for i, ref in enumerate(refs):
            item = BOMItem(
                reference=ref,
                value=value,
                footprint=footprint,
                symbol=symbol,
            )
            items.append(item)

    return items


def _expand_reference_range(reference: str) -> List[str]:
    """展开参考标识范围 (e.g., R1-R5 -> [R1, R2, R3, R4, R5])"""
    if "-" not in reference:
        return [reference]

    # 例如 R1-R5 或 C10-C15
    prefix = ""
    parts = reference.split("-")

    if len(parts) != 2:
        return [reference]

    # 提取前缀和数字
    start_str = parts[0]
    end_str = parts[1]

    # 找出前缀 (非数字部分)
    for i, c in enumerate(start_str):
        if c.isdigit():
            prefix = start_str[:i]
            break
    else:
        prefix = ""

    if not prefix:
        return [reference]

    try:
        start_num = int(start_str[len(prefix):])
        end_num = int(end_str[len(prefix):])
    except ValueError:
        return [reference]

    refs = []
    for i in range(start_num, end_num + 1):
        refs.append(f"{prefix}{i}")

    return refs

"""
Hierarchical Schematic Engine - 层次化原理图引擎

Phase 6: 提供层次化原理图支持

功能:
- 支持子原理图（层次化）
- Sheet 符号与子原理图关联
- 层次间连线

Author: Claude Code
Date: 2026-03-30
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SheetType(Enum):
    """Sheet 类型"""
    ROOT = "root"       # 根 sheet
    CHILD = "child"     # 子 sheet


@dataclass
class SheetPin:
    """Sheet 引脚"""
    name: str           # 引脚名称
    number: str          # 引脚编号
    side: str = "left"  # 位置: left, right, top, bottom
    type: str = "input" # 类型: input, output, bidirectional, power


@dataclass
class SchematicSheet:
    """原理图 Sheet"""
    sheet_id: str        # 唯一标识
    name: str           # Sheet 名称
    file_path: str      # 文件路径
    sheet_type: SheetType = SheetType.CHILD
    parent_id: Optional[str] = None  # 父 Sheet ID
    pins: List[SheetPin] = field(default_factory=list)
    graphics: List[Dict[str, Any]] = field(default_factory=list)
    components: List[str] = field(default_factory=list)  # 子元件 ID 列表


@dataclass
class SheetSymbol:
    """Sheet 符号 (在父 sheet 中代表子 sheet)"""
    symbol_id: str
    sheet_id: str        # 关联的子 sheet ID
    reference: str       # 参考标识 (如 "A1")
    x: float
    y: float
    rotation: float = 0.0
    label: str = ""     # 显示标签


@dataclass
class HierarchicalConnection:
    """层次连接"""
    connection_id: str
    from_sheet_id: str   # 源 sheet ID
    from_pin: str       # 源引脚
    to_sheet_id: str    # 目标 sheet ID
    to_pin: str         # 目标引脚
    net_name: str = ""  # 网络名称


@dataclass
class HierarchicalSchematic:
    """层次化原理图"""
    root_sheet: SchematicSheet
    sheets: Dict[str, SchematicSheet] = field(default_factory=dict)  # sheet_id -> sheet
    sheet_symbols: Dict[str, SheetSymbol] = field(default_factory=dict)  # symbol_id -> symbol
    connections: List[HierarchicalConnection] = field(default_factory=list)


class HierarchicalSchematicEngine:
    """
    层次化原理图引擎

    支持:
    - 创建子 sheet
    - Sheet 符号放置
    - 层次间连线
    """

    def __init__(self):
        self.schematics: Dict[str, HierarchicalSchematic] = {}

    def create_project(
        self,
        project_id: str,
        root_name: str = "main",
    ) -> HierarchicalSchematic:
        """
        创建层次化原理图项目

        Args:
            project_id: 项目 ID
            root_name: 根 sheet 名称

        Returns:
            HierarchicalSchematic: 层次化原理图
        """
        root_id = str(uuid.uuid4())

        root_sheet = SchematicSheet(
            sheet_id=root_id,
            name=root_name,
            file_path=f"{root_name}.kicad_sch",
            sheet_type=SheetType.ROOT,
        )

        schematic = HierarchicalSchematic(
            root_sheet=root_sheet,
            sheets={root_id: root_sheet},
        )

        self.schematics[project_id] = schematic
        return schematic

    def add_child_sheet(
        self,
        project_id: str,
        name: str,
        parent_id: Optional[str] = None,
    ) -> SchematicSheet:
        """
        添加子 sheet

        Args:
            project_id: 项目 ID
            name: Sheet 名称
            parent_id: 父 Sheet ID (None 表示根 sheet)

        Returns:
            SchematicSheet: 创建的子 sheet
        """
        if project_id not in self.schematics:
            self.create_project(project_id, name)

        schematic = self.schematics[project_id]

        # 如果没有指定父，使用根 sheet
        if parent_id is None:
            parent_id = schematic.root_sheet.sheet_id

        sheet_id = str(uuid.uuid4())

        child_sheet = SchematicSheet(
            sheet_id=sheet_id,
            name=name,
            file_path=f"{name}.kicad_sch",
            sheet_type=SheetType.CHILD,
            parent_id=parent_id,
        )

        schematic.sheets[sheet_id] = child_sheet

        # 在父 sheet 中创建 sheet 符号
        self._create_sheet_symbol(project_id, parent_id, sheet_id, name)

        return child_sheet

    def _create_sheet_symbol(
        self,
        project_id: str,
        parent_sheet_id: str,
        child_sheet_id: str,
        label: str,
    ) -> SheetSymbol:
        """在父 sheet 中创建代表子 sheet 的符号"""
        schematic = self.schematics[project_id]

        symbol_id = str(uuid.uuid4())

        # 自动计算位置 (放在父 sheet 右侧)
        existing_symbols = list(schematic.sheet_symbols.values())
        offset_x = 300
        offset_y = 100 + len([s for s in existing_symbols if s.symbol_id.startswith(symbol_id[:8])]) * 50

        sheet_symbol = SheetSymbol(
            symbol_id=symbol_id,
            sheet_id=child_sheet_id,
            reference=f"A{len(existing_symbols) + 1}",
            x=offset_x,
            y=offset_y,
            label=label,
        )

        schematic.sheet_symbols[symbol_id] = sheet_symbol
        return sheet_symbol

    def add_sheet_pin(
        self,
        project_id: str,
        sheet_id: str,
        name: str,
        number: str,
        side: str = "left",
        pin_type: str = "input",
    ) -> SheetPin:
        """
        添加 Sheet 引脚

        Args:
            project_id: 项目 ID
            sheet_id: Sheet ID
            name: 引脚名称
            number: 引脚编号
            side: 位置
            pin_type: 类型

        Returns:
            SheetPin: 创建的引脚
        """
        if project_id not in self.schematics:
            raise ValueError(f"项目不存在: {project_id}")

        schematic = self.schematics[project_id]

        if sheet_id not in schematic.sheets:
            raise ValueError(f"Sheet 不存在: {sheet_id}")

        sheet = schematic.sheets[sheet_id]

        pin = SheetPin(
            name=name,
            number=number,
            side=side,
            type=pin_type,
        )

        sheet.pins.append(pin)
        return pin

    def connect_hierarchical(
        self,
        project_id: str,
        from_sheet_id: str,
        from_pin: str,
        to_sheet_id: str,
        to_pin: str,
        net_name: str = "",
    ) -> HierarchicalConnection:
        """
        创建层次连接

        Args:
            project_id: 项目 ID
            from_sheet_id: 源 sheet ID
            from_pin: 源引脚
            to_sheet_id: 目标 sheet ID
            to_pin: 目标引脚
            net_name: 网络名称

        Returns:
            HierarchicalConnection: 创建的连接
        """
        if project_id not in self.schematics:
            raise ValueError(f"项目不存在: {project_id}")

        schematic = self.schematics[project_id]

        connection = HierarchicalConnection(
            connection_id=str(uuid.uuid4()),
            from_sheet_id=from_sheet_id,
            from_pin=from_pin,
            to_sheet_id=to_sheet_id,
            to_pin=to_pin,
            net_name=net_name or f"net_{len(schematic.connections) + 1}",
        )

        schematic.connections.append(connection)
        return connection

    def get_sheet_hierarchy(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        获取 Sheet 层级结构

        Returns:
            层级结构数据
        """
        if project_id not in self.schematics:
            raise ValueError(f"项目不存在: {project_id}")

        schematic = self.schematics[project_id]

        def build_tree(sheet_id: str) -> Dict[str, Any]:
            sheet = schematic.sheets[sheet_id]
            children = [
                sid for sid, s in schematic.sheets.items()
                if s.parent_id == sheet_id
            ]

            return {
                "sheet_id": sheet.sheet_id,
                "name": sheet.name,
                "file_path": sheet.file_path,
                "type": sheet.sheet_type.value,
                "pins": [
                    {
                        "name": p.name,
                        "number": p.number,
                        "side": p.side,
                        "type": p.type,
                    }
                    for p in sheet.pins
                ],
                "children": [build_tree(cid) for cid in children],
            }

        return build_tree(schematic.root_sheet.sheet_id)

    def export_to_kicad_format(
        self,
        project_id: str,
    ) -> Dict[str, str]:
        """
        导出为 KiCad 格式

        Returns:
            {sheet_id: kicad_s_expression}
        """
        if project_id not in self.schematics:
            raise ValueError(f"项目不存在: {project_id}")

        schematic = self.schematics[project_id]
        result = {}

        for sheet_id, sheet in schematic.sheets.items():
            if sheet.sheet_type == SheetType.ROOT:
                # 根 sheet 需要包含 sheet 符号
                s_expr = self._generate_root_sheet_expr(schematic, sheet)
            else:
                # 子 sheet 保持原有格式
                s_expr = self._generate_child_sheet_expr(sheet)

            result[sheet_id] = s_expr

        return result

    def _generate_root_sheet_expr(
        self,
        schematic: HierarchicalSchematic,
        root: SchematicSheet,
    ) -> str:
        """生成根 sheet 的 S-Expression"""
        lines = ["(kicad_sch (version 20230108)"]

        # 添加 sheet 符号
        for symbol_id, symbol in schematic.sheet_symbols.items():
            sheet = schematic.sheets[symbol.sheet_id]
            lines.append(f"  (sheet (at {symbol.x} {symbol.y}) (rotation {symbol.rotation})")
            lines.append(f"    (sheet_name \"{sheet.name}\")")
            lines.append(f"    (sheet_file \"{sheet.file_path}\")")
            lines.append(f"    (pin (uuid {symbol_id})")
            lines.append(f"      (pin_name \"{symbol.label}\")")
            lines.append("    )")
            lines.append("  )")

        # 添加层次连接
        for conn in schematic.connections:
            lines.append(f"  (connection (from {conn.from_sheet_id}/{conn.from_pin}) (to {conn.to_sheet_id}/{conn.to_pin}) (net \"{conn.net_name}\"))")

        lines.append(")")
        return "\n".join(lines)

    def _generate_child_sheet_expr(
        self,
        sheet: SchematicSheet,
    ) -> str:
        """生成子 sheet 的 S-Expression"""
        lines = ["(kicad_sch (version 20230108)"]

        # 添加 sheet 引脚定义
        for pin in sheet.pins:
            lines.append(f"  (pin (name \"{pin.name}\") (number \"{pin.number}\") (type {pin.type}))")

        lines.append(")")
        return "\n".join(lines)

    def get_schematic(self, project_id: str) -> Optional[HierarchicalSchematic]:
        """获取原理图"""
        return self.schematics.get(project_id)


# 全局引擎实例
_hierarchical_engine: Optional[HierarchicalSchematicEngine] = None


def get_hierarchical_engine() -> HierarchicalSchematicEngine:
    """获取层次化原理图引擎单例"""
    global _hierarchical_engine
    if _hierarchical_engine is None:
        _hierarchical_engine = HierarchicalSchematicEngine()
    return _hierarchical_engine

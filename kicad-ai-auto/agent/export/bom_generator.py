"""
BOM Generator - 物料清单生成器

Phase 5: 支持 LCSC 料号查询的增强 BOM 生成

Author: Claude Code
Date: 2026-03-30
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import csv
import logging

logger = logging.getLogger(__name__)


@dataclass
class BOMItem:
    """BOM 元器件条目"""
    reference: str           # 参考编号 (如 R1, C1, U1)
    value: str              # 值 (如 10k, 100nF)
    footprint: str           # 封装 (如 0805, SOT-23)
    symbol: str = ""         # 符号库
    datasheet: str = ""      # 数据手册 URL
    lcsc_part: str = ""      # LCSC 料号
    mfg_part: str = ""       # 厂商料号
    manufacturer: str = ""   # 厂商
    description: str = ""    # 描述
    quantity: int = 1        # 数量


@dataclass
class BOMOutput:
    """BOM 导出结果"""
    success: bool
    items: List[BOMItem]
    output_path: str
    grouped_items: List[Dict[str, Any]] = field(default_factory=list)  # 按值分组的 BOM
    errors: List[str] = field(default_factory=list)


class BOMGenerator:
    """
    BOM 生成器

    支持:
    - 基本 BOM 导出 (CSV/JSON/XML)
    - LCSC 料号查询 (可选)
    - 按值分组统计
    """

    # 常见元件值到 LCSC 料号的映射 (示例)
    COMMON_PARTS_LCSC = {
        "100nF": "C2335",  # 100nF 0603 C0G
        "10nF": "C14635",
        "1uF": "C14634",
        "10uF": "C9172",
        "100uF": "C28343",
        "10k": "R_10K",   # 10k 0805 1%
        "4.7k": "R_4_7K",
        "1k": "R_1K",
        "0R": "R_0R",     # 0欧姆电阻
        "AMS1117-3.3": "C20564",  # AMS1117-3.3 LDO
        "CH340C": "C85287",  # CH340C USB转串口芯片
    }

    def __init__(self, schematic_data: Dict[str, Any]):
        """
        Args:
            schematic_data: 原理图数据
        """
        self.schematic_data = schematic_data
        self.components = schematic_data.get("components", [])

    def parse_components(self) -> List[BOMItem]:
        """
        从原理图数据解析元器件

        Returns:
            List[BOMItem]: BOM 条目列表
        """
        items = []

        for comp in self.components:
            ref = comp.get("reference", "")
            value = comp.get("value", "")
            footprint = comp.get("footprint", "")
            symbol = comp.get("symbol", "")
            datasheet = comp.get("datasheet", "")

            # 自动推断 LCSC 料号
            lcsc_part = self._lookup_lcsc_part(value, footprint)

            item = BOMItem(
                reference=ref,
                value=value,
                footprint=footprint,
                symbol=symbol,
                datasheet=datasheet,
                lcsc_part=lcsc_part,
            )
            items.append(item)

        return items

    def _lookup_lcsc_part(self, value: str, footprint: str) -> str:
        """
        根据值和封装查找 LCSC 料号

        Args:
            value: 元件值
            footprint: 封装

        Returns:
            str: LCSC 料号 (如果找到)
        """
        # 先精确匹配
        if value in self.COMMON_PARTS_LCSC:
            return self.COMMON_PARTS_LCSC[value]

        # 尝试模糊匹配
        value_upper = value.upper()
        for key, lcsc in self.COMMON_PARTS_LCSC.items():
            if key.upper() in value_upper:
                return lcsc

        return ""

    def group_by_value(self, items: List[BOMItem]) -> List[Dict[str, Any]]:
        """
        按值分组 BOM 条目

        Args:
            items: BOM 条目列表

        Returns:
            List[Dict]: 分组后的 BOM [{value, footprint, references: [], quantity}, ...]
        """
        groups: Dict[str, Dict[str, Any]] = {}

        for item in items:
            # 创建分组键 (值 + 封装)
            key = f"{item.value}|{item.footprint}"

            if key not in groups:
                groups[key] = {
                    "value": item.value,
                    "footprint": item.footprint,
                    "references": [],
                    "quantity": 0,
                    "lcsc_part": item.lcsc_part,
                    "mfg_part": item.mfg_part,
                    "manufacturer": item.manufacturer,
                    "description": item.description,
                }

            groups[key]["references"].append(item.reference)
            groups[key]["quantity"] += item.quantity

        return list(groups.values())

    def export_csv(
        self,
        output_path: str,
        grouped: bool = True,
        include_lcsc: bool = True,
    ) -> BOMOutput:
        """
        导出 BOM 为 CSV 格式

        Args:
            output_path: 输出文件路径
            grouped: 是否按值分组
            include_lcsc: 是否包含 LCSC 料号

        Returns:
            BOMOutput: 导出结果
        """
        items = self.parse_components()
        errors = []

        try:
            if grouped:
                grouped_items = self.group_by_value(items)
                self._write_grouped_csv(output_path, grouped_items, include_lcsc)
            else:
                grouped_items = []
                self._write_flat_csv(output_path, items, include_lcsc)

            return BOMOutput(
                success=True,
                items=items,
                output_path=output_path,
                grouped_items=grouped_items,
                errors=errors,
            )
        except Exception as e:
            logger.error(f"Failed to export BOM CSV: {e}")
            errors.append(str(e))
            return BOMOutput(
                success=False,
                items=items,
                output_path=output_path,
                errors=errors,
            )

    def _write_flat_csv(
        self,
        output_path: str,
        items: List[BOMItem],
        include_lcsc: bool,
    ):
        """写 BOM CSV (扁平格式)"""
        fieldnames = ["Reference", "Value", "Footprint", "Symbol", "Datasheet"]
        if include_lcsc:
            fieldnames.extend(["LCSC Part", "Manufacturer Part", "Manufacturer"])

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in items:
                row = {
                    "Reference": item.reference,
                    "Value": item.value,
                    "Footprint": item.footprint,
                    "Symbol": item.symbol,
                    "Datasheet": item.datasheet,
                }
                if include_lcsc:
                    row.update({
                        "LCSC Part": item.lcsc_part,
                        "Manufacturer Part": item.mfg_part,
                        "Manufacturer": item.manufacturer,
                    })
                writer.writerow(row)

    def _write_grouped_csv(
        self,
        output_path: str,
        grouped_items: List[Dict[str, Any]],
        include_lcsc: bool,
    ):
        """写 BOM CSV (分组格式)"""
        fieldnames = ["References", "Value", "Footprint", "Quantity"]
        if include_lcsc:
            fieldnames.extend(["LCSC Part", "Manufacturer Part", "Manufacturer"])

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for group in grouped_items:
                row = {
                    "References": ",".join(group["references"]),
                    "Value": group["value"],
                    "Footprint": group["footprint"],
                    "Quantity": group["quantity"],
                }
                if include_lcsc:
                    row.update({
                        "LCSC Part": group.get("lcsc_part", ""),
                        "Manufacturer Part": group.get("mfg_part", ""),
                        "Manufacturer": group.get("manufacturer", ""),
                    })
                writer.writerow(row)

    def export_json(self, output_path: str) -> BOMOutput:
        """
        导出 BOM 为 JSON 格式

        Args:
            output_path: 输出文件路径

        Returns:
            BOMOutput: 导出结果
        """
        import json

        items = self.parse_components()
        grouped_items = self.group_by_value(items)
        errors = []

        try:
            data = {
                "components": [item.__dict__ for item in items],
                "grouped": grouped_items,
                "summary": {
                    "total_components": len(items),
                    "unique_parts": len(grouped_items),
                }
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return BOMOutput(
                success=True,
                items=items,
                output_path=output_path,
                grouped_items=grouped_items,
                errors=errors,
            )
        except Exception as e:
            logger.error(f"Failed to export BOM JSON: {e}")
            errors.append(str(e))
            return BOMOutput(
                success=False,
                items=items,
                output_path=output_path,
                errors=errors,
            )

    def export_xml(self, output_path: str) -> BOMOutput:
        """
        导出 BOM 为 KiCad XML 格式

        Args:
            output_path: 输出文件路径

        Returns:
            BOMOutput: 导出结果
        """
        import xml.etree.ElementTree as ET

        items = self.parse_components()
        grouped_items = self.group_by_value(items)
        errors = []

        try:
            root = ET.Element("export")
            components_elem = ET.SubElement(root, "components")

            for item in items:
                comp_elem = ET.SubElement(components_elem, "comp")
                comp_elem.set("ref", item.reference)
                ET.SubElement(comp_elem, "value").text = item.value
                ET.SubElement(comp_elem, "footprint").text = item.footprint
                ET.SubElement(comp_elem, "fields")

            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)

            return BOMOutput(
                success=True,
                items=items,
                output_path=output_path,
                grouped_items=grouped_items,
                errors=errors,
            )
        except Exception as e:
            logger.error(f"Failed to export BOM XML: {e}")
            errors.append(str(e))
            return BOMOutput(
                success=False,
                items=items,
                output_path=output_path,
                errors=errors,
            )

    def generate_pick_place(
        self,
        output_path: str,
        pcb_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成贴片机坐标文件 (Pick & Place)

        Args:
            output_path: 输出文件路径
            pcb_data: PCB 数据 (可选，用于获取位置)

        Returns:
            Dict: 结果
        """
        items = self.parse_components()
        pcb_components = (pcb_data or {}).get("components", [])

        # 建立位置映射
        pos_map = {
            c.get("reference", ""): c.get("position", {})
            for c in pcb_components
        }

        fieldnames = ["Reference", "Val", "Package", "PosX", "PosY", "Rotation", "Side"]

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in items:
                pos = pos_map.get(item.reference, {})
                row = {
                    "Reference": item.reference,
                    "Val": item.value,
                    "Package": item.footprint,
                    "PosX": f"{pos.get('x', 0):.4f}",
                    "PosY": f"{pos.get('y', 0):.4f}",
                    "Rotation": str(item.__dict__.get("rotation", 0)),
                    "Side": "Top" if not item.__dict__.get("bottom", False) else "Bottom",
                }
                writer.writerow(row)

        return {"success": True, "output_path": output_path, "count": len(items)}

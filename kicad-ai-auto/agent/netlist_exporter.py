#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KiCad 网表导出器 v1.0

功能：
1. 将原理图数据导出为KiCad标准XML网表格式
2. 支持导出PCB网络信息
3. 生成BOM物料清单

作者：AI Assistant
"""

import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class NetlistComponent:
    """网表元件"""
    reference: str
    value: str = ""
    footprint: str = ""
    lib_id: str = ""
    datasheet: str = ""
    fields: Dict[str, str] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = {}


@dataclass
class NetlistNet:
    """网表网络"""
    name: str
    code: int
    nodes: List[Dict[str, str]] = None  # [{node: ref, pin: pin}]

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []


class NetlistExporter:
    """KiCad 网表导出器"""

    def __init__(self):
        self.components: List[NetlistComponent] = []
        self.nets: List[NetlistNet] = []
        self.design = {}
        self.settings = {}

    def add_component(self, component: NetlistComponent):
        """添加元件"""
        self.components.append(component)

    def add_net(self, net: NetlistNet):
        """添加网络"""
        self.nets.append(net)

    def set_design_info(self, title: str = "", date: str = "", revision: str = "",
                        company: str = "", comment1: str = "", comment2: str = "",
                        comment3: str = "", comment4: str = ""):
        """设置设计信息"""
        self.design = {
            "title": title,
            "date": date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "revision": revision,
            "company": company,
            "comment1": comment1,
            "comment2": comment2,
            "comment3": comment3,
            "comment4": comment4
        }

    def export_xml(self, output) -> str:
        """
        导出为KiCad XML网表格式

        Args:
            output: 输出文件路径 或 StringIO对象

        Returns:
            str: 生成的XML内容
        """
        import io

        # 判断是文件路径还是StringIO
        write_to_file = True
        if isinstance(output, io.StringIO):
            write_to_file = False
        # 创建根元素
        export = ET.Element("export", version="1.1")

        # 设计信息
        design = ET.SubElement(export, "design")
        date = ET.SubElement(design, "date")
        date.text = self.design.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        tool = ET.SubElement(design, "tool")
        tool.text = "kicad-ai-auto"

        for key in ["title", "comment1", "comment2", "comment3", "comment4"]:
            if self.design.get(key):
                elem = ET.SubElement(design, key)
                elem.text = self.design[key]

        # 元件库
        libs = ET.SubElement(components := ET.SubElement(export, "components"), "libsource", dict(
            library="kicad-ai-auto",
            part="Device"
        ))
        power = ET.SubElement(components, "sheet", dict(sheetName="", sheetNumber=""))

        # 添加元件
        for comp in self.components:
            comp_elem = ET.SubElement(components, "comp", dict(ref=comp.reference))

            # 属性
            for prop_name, prop_value in [
                ("value", comp.value),
                ("footprint", comp.footprint),
                ("datasheet", comp.datasheet),
                ("lib_id", comp.lib_id)
            ]:
                if prop_value:
                    ET.SubElement(comp_elem, "property", dict(name=prop_name, value=prop_value))

            # 额外字段
            for field_name, field_value in comp.fields.items():
                ET.SubElement(comp_elem, "field", dict(name=field_name)).text = field_value

        # 网络
        ET.SubElement(nets := ET.SubElement(export, "nets"), "net", dict(code="0", name=""))

        for net in self.nets:
            net_elem = ET.SubElement(nets, "net", dict(code=str(net.code), name=net.name))

            for node in net.nodes:
                ET.SubElement(net_elem, "node", dict(
                    ref=node.get("ref", ""),
                    pin=node.get("pin", ""),
                    gate=node.get("gate", ""),
                    pinfunction=node.get("pinfunction", "")
                ))

        # 生成XML字符串
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += ET.tostring(export, encoding="unicode")

        # 格式化XML
        xml_str = self._format_xml(xml_str)

        # 保存
        if write_to_file:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            logger.info(f"网表已导出: {output}")
        else:
            output.write(xml_str)

        return xml_str

    def _format_xml(self, xml_str: str) -> str:
        """格式化XML"""
        import xml.dom.minidom
        dom = xml.dom.minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")

    def export_csv(self, output) -> str:
        """
        导出为CSV BOM格式

        Args:
            output: 输出文件路径 或 StringIO对象

        Returns:
            str: 生成的CSV内容
        """
        import io
        write_to_file = True
        if isinstance(output, io.StringIO):
            write_to_file = False

        lines = ["Reference,Value,Footprint,Symbol,Datasheet"]

        for comp in self.components:
            line = f'"{comp.reference}","{comp.value}","{comp.footprint}","{comp.lib_id}","{comp.datasheet}"'
            lines.append(line)

        csv_content = "\n".join(lines)

        if write_to_file:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            logger.info(f"BOM已导出: {output}")
        else:
            output.write(csv_content)

        return csv_content

    def export_json(self, output) -> str:
        """
        导出为JSON格式

        Args:
            output: 输出文件路径 或 StringIO对象

        Returns:
            str: 生成的JSON内容
        """
        import io
        import json

        write_to_file = True
        if isinstance(output, io.StringIO):
            write_to_file = False

        data = {
            "design": self.design,
            "components": [
                {
                    "reference": c.reference,
                    "value": c.value,
                    "footprint": c.footprint,
                    "lib_id": c.lib_id,
                    "datasheet": c.datasheet,
                    "fields": c.fields
                } for c in self.components
            ],
            "nets": [
                {
                    "name": n.name,
                    "code": n.code,
                    "nodes": n.nodes
                } for n in self.nets
            ]
        }

        json_content = json.dumps(data, indent=2, ensure_ascii=False)

        if write_to_file:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(json_content)
            logger.info(f"JSON网表已导出: {output}")
        else:
            output.write(json_content)

        return json_content


# 便捷函数
def create_netlist_from_schematic(schematic_data: Dict[str, Any], output_path: str = None,
                                   design_info: Dict[str, str] = None,
                                   return_content: bool = True) -> str:
    """
    从原理图数据创建网表

    Args:
        schematic_data: 原理图数据字典
        output_path: 输出文件路径 (如果return_content=True则可选)
        design_info: 设计信息
        return_content: 是否返回内容而不是写入文件

    Returns:
        str: 生成的XML内容
    """
    exporter = NetlistExporter()

    # 设置设计信息
    if design_info:
        exporter.set_design_info(**design_info)
    else:
        exporter.set_design_info(
            title=schematic_data.get("name", "Untitled"),
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    # 添加元件
    for comp_data in schematic_data.get("components", []):
        comp = NetlistComponent(
            reference=comp_data.get("reference", ""),
            value=comp_data.get("value", ""),
            footprint=comp_data.get("footprint", ""),
            lib_id=comp_data.get("symbol_library", ""),
            datasheet=comp_data.get("datasheet", "")
        )
        exporter.add_component(comp)

    # 添加网络
    net_code = 1
    for net_data in schematic_data.get("nets", []):
        net = NetlistNet(
            name=net_data.get("name", ""),
            code=net_code,
            nodes=net_data.get("connections", [])
        )
        exporter.add_net(net)
        net_code += 1

    # 确定导出格式
    fmt = "xml"
    if output_path:
        if output_path.endswith(".csv"):
            fmt = "csv"
        elif output_path.endswith(".json"):
            fmt = "json"

    # 如果只需要返回内容,不写入文件
    if return_content and not output_path:
        import io
        output = io.StringIO()
        if fmt == "xml":
            return exporter.export_xml(output)
        elif fmt == "csv":
            return exporter.export_csv(output)
        elif fmt == "json":
            return exporter.export_json(output)
        else:
            return exporter.export_xml(output)

    # 否则写入文件
    if output_path:
        if fmt == "xml":
            return exporter.export_xml(output_path)
        elif fmt == "csv":
            return exporter.export_csv(output_path)
        elif fmt == "json":
            return exporter.export_json(output_path)
        else:
            return exporter.export_xml(output_path + ".xml")

    return ""


# 测试代码
if __name__ == "__main__":
    # 创建测试数据
    test_schematic = {
        "name": "test_pcb",
        "components": [
            {"reference": "U1", "value": "STM32F103C8T6", "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
             "symbol_library": "MCU_ST_STM32", "datasheet": "https://www.st.com/stm32f103"},
            {"reference": "R1", "value": "10K", "footprint": "Resistor_SMD:R_0603_1608Metric",
             "symbol_library": "Device", "datasheet": ""},
            {"reference": "C1", "value": "10uF", "footprint": "Capacitor_SMD:C_0603_1608Metric",
             "symbol_library": "Device", "datasheet": ""},
        ],
        "nets": [
            {"name": "VCC", "connections": [{"ref": "U1", "pin": "VDD"}, {"ref": "R1", "pin": "1"}]},
            {"name": "GND", "connections": [{"ref": "U1", "pin": "VSS"}, {"ref": "C1", "pin": "2"}]},
            {"name": "NET1", "connections": [{"ref": "R1", "pin": "2"}, {"ref": "C1", "pin": "1"}]},
        ]
    }

    design_info = {
        "title": "Test PCB Project",
        "revision": "v1.0",
        "company": "AI Design",
        "comment1": "Created by kicad-ai-auto"
    }

    # 导出XML
    print("导出XML网表...")
    create_netlist_from_schematic(test_schematic, "test_output.xml", design_info)
    print("已生成: test_output.xml")

    # 导出CSV (BOM)
    print("\n导出CSV BOM...")
    create_netlist_from_schematic(test_schematic, "test_bom.csv", design_info)
    print("已生成: test_bom.csv")

    # 导出JSON
    print("\n导出JSON网表...")
    create_netlist_from_schematic(test_schematic, "test_netlist.json", design_info)
    print("已生成: test_netlist.json")

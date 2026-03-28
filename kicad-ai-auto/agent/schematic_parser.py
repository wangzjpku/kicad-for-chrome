#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KiCad 原理图网表解析器 v1.0

功能：
1. 解析 .kicad_sch 文件
2. 提取元件信息（编号、值、封装、符号库）
3. 提取网络连接（网络名称、连接的引脚）
4. 提取导线信息

作者：AI Assistant
"""

import re
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SchematicComponent:
    """原理图元件"""
    reference: str      # 参考编号 (如 R1, U1)
    value: str          # 值 (如 10K, STM32F103C8T6)
    footprint: str = "" # 封装
    symbol_library: str = ""  # 符号库
    symbol_name: str = ""  # 符号名称
    uuid: str = ""  # 元件UUID
    x: float = 0
    y: float = 0
    datasheet: str = ""


@dataclass
class SchematicNet:
    """原理图网络"""
    name: str  # 网络名称
    connections: List[Dict[str, str]] = field(default_factory=list)  # [{reference, pin}]


@dataclass
class SchematicWire:
    """原理图导线"""
    points: List[Dict[str, float]] = field(default_factory=list)  # [{x, y}]


@dataclass
class Schematic:
    """原理图完整数据"""
    version: str = ""
    generator: str = ""
    uuid: str = ""
    paper: str = "A4"
    components: List[SchematicComponent] = field(default_factory=list)
    nets: List[SchematicNet] = field(default_factory=list)
    wires: List[SchematicWire] = field(default_factory=list)


class SchematicParser:
    """KiCad 原理图解析器"""

    def __init__(self):
        self.schematic = Schematic()

    def parse_file(self, file_path: str) -> Schematic:
        """
        解析原理图文件

        Args:
            file_path: .kicad_sch 文件路径

        Returns:
            Schematic: 原理图数据对象
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        self.schematic = Schematic()

        # 提取文件头信息
        self._parse_header(content)

        # 提取元件
        self._parse_components(content)

        # 提取导线
        self._parse_wires(content)

        # 网络 - KiCad原理图不直接存储网络定义,从导线推断或使用网表导出
        # 这里尝试解析legacy格式,如果没有则提示用户使用网表导出
        self._parse_nets(content)

        logger.info(f"解析完成: {len(self.schematic.components)} 个元件, {len(self.schematic.nets)} 个网络, {len(self.schematic.wires)} 根导线")
        return self.schematic

    def _parse_header(self, content: str):
        """解析文件头"""
        # 版本
        match = re.search(r'kicad_sch\s+\(version\s+(\d+)\)', content)
        if match:
            self.schematic.version = match.group(1)

        # 生成器
        match = re.search(r'generator\s+"([^"]+)"', content)
        if match:
            self.schematic.generator = match.group(1)

        # UUID
        match = re.search(r'\(uuid\s+([^\)]+)\)', content)
        if match:
            self.schematic.uuid = match.group(1).strip()

        # 纸张大小
        match = re.search(r'\(paper\s+"([^"]+)"', content)
        if match:
            self.schematic.paper = match.group(1)

    def _parse_components(self, content: str):
        """解析元件"""
        # 匹配所有symbol实例（带lib_id的）
        # 格式: (symbol (lib_id "Device:R") (at 100.00 50.00 0) ...
        symbol_pattern = r'\(symbol\s+\(lib_id\s+"([^"]+)"\)\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)'

        for match in re.finditer(symbol_pattern, content):
            lib_id = match.group(1)
            x = float(match.group(2))
            y = float(match.group(3))

            # 在这个位置后查找该元件的属性块
            start_pos = match.end()
            search_area = content[start_pos:start_pos + 2000]

            # 解析属性
            ref = ""
            value = ""
            footprint = ""
            datasheet = ""
            uuid = ""

            # 查找Reference
            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', search_area)
            if ref_match:
                ref = ref_match.group(1)

            # 查找Value
            value_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', search_area)
            if value_match:
                value = value_match.group(1)

            # 查找Footprint
            fp_match = re.search(r'\(property\s+"Footprint"\s+"([^"]+)"', search_area)
            if fp_match:
                footprint = fp_match.group(1)

            # 查找Datasheet
            ds_match = re.search(r'\(property\s+"Datasheet"\s+"([^"]+)"', search_area)
            if ds_match:
                datasheet = ds_match.group(1)

            # 查找UUID
            uuid_match = re.search(r'\(uuid\s+([^\)]+)\)', search_area)
            if uuid_match:
                uuid = uuid_match.group(1)

            # 解析符号库和符号名
            if ":" in lib_id:
                library, name = lib_id.split(":", 1)
            else:
                library = ""
                name = lib_id

            # 只添加有参考编号的元件（排除电源符号如#FLG01）
            if ref and not ref.startswith("#"):
                comp = SchematicComponent(
                    reference=ref,
                    value=value,
                    footprint=footprint,
                    symbol_library=library,
                    symbol_name=name,
                    uuid=uuid,
                    x=x,
                    y=y,
                    datasheet=datasheet
                )
                self.schematic.components.append(comp)

    def _parse_wires(self, content: str):
        """解析导线

        格式: (wire (pts (xy x1 y1) (xy x2 y2)) ...)
        """
        wire_pattern = r'\(wire\s+\(pts\s+\(xy\s+([-\d.]+)\s+([-\d.]+)\)\s+\(xy\s+([-\d.]+)\s+([-\d.]+)\)'

        for match in re.finditer(wire_pattern, content):
            wire = SchematicWire(points=[
                {"x": float(match.group(1)), "y": float(match.group(2))},
                {"x": float(match.group(3)), "y": float(match.group(4))}
            ])
            self.schematic.wires.append(wire)

    def _parse_nets(self, content: str):
        """解析网络

        注意: KiCad原理图文件不直接存储网络定义,网络是从导线连接推断出来的。
        这里尝试从schematic文件中提取legacy格式的网络定义(旧版本KiCad),
        如果没有找到则返回空列表,用户应使用KiCad的网表导出功能获取网络信息。
        """
        # 尝试查找legacy格式的网络定义
        net_pattern = r'\(net\s+"([^"]+)"\s+\(code\s+(\d+)\)\s*(\([\s\S]*?)\)\)'

        for match in re.finditer(net_pattern, content):
            net_name = match.group(1)
            connections = []

            # 提取所有引脚连接
            pin_pattern = r'\(pin\s+"([^"]+)"\s+"([^"]+)"\)'
            for pin_match in re.finditer(pin_pattern, match.group(3)):
                connections.append({
                    "reference": pin_match.group(1),
                    "pin": pin_match.group(2)
                })

            net = SchematicNet(name=net_name, connections=connections)
            self.schematic.nets.append(net)

    def get_netlist_dict(self) -> Dict[str, Any]:
        """
        获取网表字典格式

        Returns:
            Dict: 包含components和nets的字典
        """
        components = []
        for comp in self.schematic.components:
            components.append({
                "reference": comp.reference,
                "value": comp.value,
                "footprint": comp.footprint,
                "symbol_library": comp.symbol_library,
                "symbol_name": comp.symbol_name,
                "datasheet": comp.datasheet
            })

        nets = []
        for net in self.schematic.nets:
            nets.append({
                "name": net.name,
                "connections": net.connections
            })

        return {
            "version": self.schematic.version,
            "generator": self.schematic.generator,
            "uuid": self.schematic.uuid,
            "components": components,
            "nets": nets,
            "wire_count": len(self.schematic.wires)
        }


def parse_schematic(file_path: str) -> Dict[str, Any]:
    """
    解析原理图文件的便捷函数

    Args:
        file_path: .kicad_sch 文件路径

    Returns:
        Dict: 网表数据
    """
    parser = SchematicParser()
    schematic = parser.parse_file(file_path)
    return parser.get_netlist_dict()


# 测试代码
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"解析文件: {file_path}")
        result = parse_schematic(file_path)
        print(f"\n=== 解析结果 ===")
        print(f"版本: {result['version']}")
        print(f"生成器: {result['generator']}")
        print(f"UUID: {result['uuid']}")
        print(f"\n元件数量: {len(result['components'])}")
        print(f"网络数量: {len(result['nets'])}")
        print(f"导线数量: {result['wire_count']}")

        if result['components']:
            print("\n=== 前5个元件 ===")
            for comp in result['components'][:5]:
                print(f"  {comp['reference']}: {comp['value']} ({comp['symbol_library']}:{comp['symbol_name']})")

        if result['nets']:
            print("\n=== 前5个网络 ===")
            for net in result['nets'][:5]:
                print(f"  {net['name']}: {len(net['connections'])} 个连接")
    else:
        print("用法: python schematic_parser.py <schematic_file.kicad_sch>")

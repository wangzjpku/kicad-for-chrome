"""
KiCad 文件解析器
解析 .kicad_pcb 和 .sch 文件，转换为 PCB 数据模型
"""

import json
import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from .pcb_models import (
    PCBBoard,
    Component,
    Track,
    Via,
    Zone,
    Net,
    Point2D,
    Pad,
)


class KiCadPCBParser:
    """KiCad PCB 文件解析器 (.kicad_pcb)"""

    def __init__(self):
        self.board: Optional[PCBBoard] = None
        self.footprint_library: Dict[str, Any] = {}

    def parse_file(self, filepath: str) -> PCBBoard:
        """解析 .kicad_pcb 文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse_content(content)

    def parse_content(self, content: str) -> PCBBoard:
        """解析 PCB 内容"""
        # KiCad 8 使用 S-Expression 格式
        # 这里我们简化处理，使用正则表达式提取关键信息

        board = PCBBoard(name="KiCad Board", width=100.0, height=100.0)

        # 解析板边界
        board_outline = self._parse_board_outline(content)
        if board_outline:
            board.width = board_outline.get("width", 100.0)
            board.height = board_outline.get("height", 100.0)

        # 解析网络
        board.nets = self._parse_nets(content)

        # 解析元件 (包括焊盘)
        board.components, board.pads = self._parse_footprints_with_pads(content)

        # 解析走线
        board.tracks = self._parse_tracks(content)

        # 解析过孔
        board.vias = self._parse_vias(content)

        # 解析铺铜区域
        board.zones = self._parse_zones(content)

        self.board = board
        return board

    def _parse_board_outline(self, content: str) -> Dict[str, float]:
        """解析板边界 - 从 Edge.Cuts 层提取"""
        # 查找 Edge.Cuts 层的线条
        # 格式: (gr_line (start x y) (end x y) ... (layer "Edge.Cuts"))
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        # 简单方法：搜索所有坐标
        all_coords = re.findall(
            r"\(gr_line\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)",
            content,
        )

        for match in all_coords:
            x1, y1 = float(match[0]), float(match[1])
            x2, y2 = float(match[2]), float(match[3])
            min_x = min(min_x, x1, x2)
            max_x = max(max_x, x1, x2)
            min_y = min(min_y, y1, y2)
            max_y = max(max_y, y1, y2)

        if min_x != float("inf"):
            width = max_x - min_x
            height = max_y - min_y
            return {"width": width, "height": height}

        return {"width": 100.0, "height": 100.0}

    def _parse_nets(self, content: str) -> List[Net]:
        """解析网络"""
        nets = []

        # 查找 (net ...) 节点
        net_pattern = r'\(net\s+\d+\s+"([^"]+)"\)'
        for match in re.finditer(net_pattern, content):
            name = match.group(1)

            # 判断网络类型
            is_power = name.upper() in ["VCC", "VDD", "VCC3V3", "VCC5V", "VIN", "VOUT"]
            is_ground = name.upper() in ["GND", "VSS", "AGND", "DGND"]
            is_high_speed = any(
                x in name.upper() for x in ["USB", "HDMI", "DP", "DDR", "MIPI"]
            )
            is_diff_pair = "+" in name or "-" in name or "_P" in name or "_N" in name

            net = Net(
                id=f"net_{name}",
                name=name,
                is_power_supply=is_power,
                is_ground=is_ground,
                is_high_speed=is_high_speed,
                is_differential_pair=is_diff_pair,
            )
            nets.append(net)

        # 添加默认网络
        if not nets:
            nets = [
                Net("net_VCC", "VCC", is_power_supply=True),
                Net("net_GND", "GND", is_ground=True),
            ]

        return nets

    def _parse_footprints(self, content: str) -> List[Component]:
        """解析元件封装 - KiCad 9.0 格式"""
        components = []

        # KiCad 9.0 格式:
        # (footprint "library:name" (at x y) ... (property "Reference" "U1" ...) (property "Value" "STM32" ...))

        # 查找所有 footprint 块的起始位置
        # 匹配格式: (footprint "library:name" ...)
        footprint_pattern = r'\(footprint\s+"([^"]+)"'

        for i, fp_match in enumerate(re.finditer(footprint_pattern, content)):
            fp_start = fp_match.start()
            footprint_name = fp_match.group(1)

            # 找到这个 footprint 块的结束位置 (配对的右括号)
            # 简化处理：从下一个 footprint 开始，或者文件结束
            next_fp = re.search(r'\(footprint\s+"', content[fp_start + 10 :])
            if next_fp:
                fp_end = fp_start + 10 + next_fp.start()
            else:
                fp_end = len(content)

            fp_content = content[fp_start:fp_end]

            # 提取位置 (at x y)
            at_match = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\s*\)", fp_content)
            x = float(at_match.group(1)) if at_match else 0
            y = float(at_match.group(2)) if at_match else 0

            # 提取 Reference (元件编号)
            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', fp_content)
            reference = ref_match.group(1) if ref_match else f"U{i}"

            # 提取 Value (元件值)
            value_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', fp_content)
            value = (
                value_match.group(1) if value_match else footprint_name.split(":")[-1]
            )

            # 判断元件类型
            ref_upper = reference.upper()
            is_ic = "U" in ref_upper or "IC" in ref_upper
            is_mcu = any(
                x in ref_upper for x in ["MCU", "STM", "ESP", "ATMEGA", "PIC", "CPU"]
            )
            is_crystal = "Y" in ref_upper or "XTAL" in ref_upper
            is_connector = any(
                x in ref_upper for x in ["J", "JP", "CON", "USB", "HEADER", "P"]
            )
            is_heatsink = (
                "HS" in ref_upper or "HEATSINK" in ref_upper or "FET" in ref_upper
            )

            comp = Component(
                id=f"comp_{i}",
                reference=reference,
                value=value,
                footprint=footprint_name,
                position=Point2D(x, y),
                is_ic=is_ic,
                is_mcu=is_mcu,
                is_crystal=is_crystal,
                is_connector=is_connector,
                is_heatsink=is_heatsink,
            )
            components.append(comp)

        return components

    def _parse_footprints_with_pads(self, content: str):
        """解析元件封装及焊盘 - 返回 (components, pads)"""
        components = []
        pads = []

        # 查找所有 footprint 块的起始位置
        footprint_pattern = r'\(footprint\s+"([^"]+)"'

        for i, fp_match in enumerate(re.finditer(footprint_pattern, content)):
            fp_start = fp_match.start()
            footprint_name = fp_match.group(1)

            # 找到这个 footprint 块的结束位置
            next_fp = re.search(r'\(footprint\s+"', content[fp_start + 10 :])
            if next_fp:
                fp_end = fp_start + 10 + next_fp.start()
            else:
                fp_end = len(content)

            fp_content = content[fp_start:fp_end]

            # 提取位置 (at x y)
            at_match = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\s*\)", fp_content)
            fp_x = float(at_match.group(1)) if at_match else 0
            fp_y = float(at_match.group(2)) if at_match else 0

            # 提取 Reference (元件编号)
            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', fp_content)
            reference = ref_match.group(1) if ref_match else f"U{i}"

            # 提取 Value (元件值)
            value_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', fp_content)
            value = (
                value_match.group(1) if value_match else footprint_name.split(":")[-1]
            )

            # 解析焊盘 - 格式: (pad "1" thru_hole rect (at 0 0) ... (net 9 "VCC"))
            # 先找到每个pad块的结束位置
            pad_start_indices = [
                m.start() for m in re.finditer(r'\(pad\s+"', fp_content)
            ]

            for pad_idx, pad_start in enumerate(pad_start_indices):
                # 确定pad块结束位置
                if pad_idx + 1 < len(pad_start_indices):
                    pad_end = pad_start_indices[pad_idx + 1]
                else:
                    pad_end = len(fp_content)

                pad_block = fp_content[pad_start:pad_end]

                # 提取焊盘名称
                pad_name_match = re.search(r'\(pad\s+"([^"]+)"', pad_block)
                if not pad_name_match:
                    continue
                pad_name = pad_name_match.group(1)

                # 提取焊盘位置
                at_match = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\)", pad_block)
                if not at_match:
                    continue
                pad_local_x = float(at_match.group(1))
                pad_local_y = float(at_match.group(2))
                pad_x = fp_x + pad_local_x
                pad_y = fp_y + pad_local_y

                # 提取焊盘尺寸
                size_match = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)\)", pad_block)
                if size_match:
                    pad_width = float(size_match.group(1))
                    pad_height = float(size_match.group(2))
                else:
                    pad_width = pad_height = 0.6

                # 提取网络 - 格式: (net 9 "VCC")
                net_match = re.search(r'\(net\s+(\d+)\s+"([^"]+)"\)', pad_block)
                if net_match:
                    net_id = f"net_{net_match.group(1)}"
                    net_name = net_match.group(2)
                else:
                    net_id = "net_0"
                    net_name = ""

                pad = Pad(
                    id=f"pad_{len(pads)}",
                    number=pad_name,
                    net_id=net_id,
                    position=Point2D(pad_x, pad_y),
                    size=(pad_width, pad_height),
                )
                pads.append(pad)

            # 判断元件类型
            ref_upper = reference.upper()
            is_ic = "U" in ref_upper or "IC" in ref_upper
            is_mcu = any(
                x in ref_upper for x in ["MCU", "STM", "ESP", "ATMEGA", "PIC", "CPU"]
            )
            is_crystal = "Y" in ref_upper or "XTAL" in ref_upper
            is_connector = any(
                x in ref_upper for x in ["J", "JP", "CON", "USB", "HEADER", "P"]
            )
            is_heatsink = (
                "HS" in ref_upper or "HEATSINK" in ref_upper or "FET" in ref_upper
            )

            comp = Component(
                id=f"comp_{i}",
                reference=reference,
                value=value,
                footprint=footprint_name,
                position=Point2D(fp_x, fp_y),
                is_ic=is_ic,
                is_mcu=is_mcu,
                is_crystal=is_crystal,
                is_connector=is_connector,
                is_heatsink=is_heatsink,
            )
            components.append(comp)

        return components, pads

    def _parse_tracks(self, content: str) -> List[Track]:
        """解析走线"""
        tracks = []

        # 查找 (segment ...) 节点
        # 格式: (segment (start x y) (end x y) (width w) (layer "Cu") (net n))
        segment_pattern = r'\(segment\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+\(width\s+([-\d.]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+\d+\)'

        for i, match in enumerate(re.finditer(segment_pattern, content)):
            x1 = float(match.group(1))
            y1 = float(match.group(2))
            x2 = float(match.group(3))
            y2 = float(match.group(4))
            width = float(match.group(5))
            layer = match.group(6)

            # 确定网络ID
            net_match = re.search(r"\(net\s+(\d+)\)", match.group(0))
            net_id = f"net_{net_match.group(1)}" if net_match else "net_1"

            track = Track(
                id=f"track_{i}",
                net_id=net_id,
                points=[Point2D(x1, y1), Point2D(x2, y2)],
                width=width,
                layer=layer,
            )
            tracks.append(track)

        # 查找 (arc ...) 节点 (圆弧走线)
        arc_pattern = r'\(arc\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+\(width\s+([-\d.]+)\)\s+\(layer\s+"([^"]+)"\)'

        for i, match in enumerate(re.finditer(arc_pattern, content)):
            x1 = float(match.group(1))
            y1 = float(match.group(2))
            x2 = float(match.group(3))
            y2 = float(match.group(4))
            width = float(match.group(5))
            layer = match.group(6)

            net_match = re.search(r"\(net\s+(\d+)\)", match.group(0))
            net_id = f"net_{net_match.group(1)}" if net_match else "net_1"

            track = Track(
                id=f"arc_{i}",
                net_id=net_id,
                points=[Point2D(x1, y1), Point2D(x2, y2)],
                width=width,
                layer=layer,
            )
            tracks.append(track)

        return tracks

    def _parse_vias(self, content: str) -> List[Via]:
        """解析过孔"""
        vias = []

        # 查找 (via ...) 节点
        # 格式: (via (at x y) (size d) (drill d) (layers "F.Cu" "B.Cu") (net n))
        via_pattern = r"\(via\s+\(at\s+([-\d.]+)\s+([-\d.]+)\)\s+\(size\s+([-\d.]+)\)\s+\(drill\s+([-\d.]+)\)"

        for i, match in enumerate(re.finditer(via_pattern, content)):
            x = float(match.group(1))
            y = float(match.group(2))
            size = float(match.group(3))
            drill = float(match.group(4))

            # 确定网络
            net_match = re.search(r"\(net\s+(\d+)\)", match.group(0))
            net_id = f"net_{net_match.group(1)}" if net_match else "net_1"

            via = Via(
                id=f"via_{i}",
                net_id=net_id,
                position=Point2D(x, y),
                diameter=size,
                drill=drill,
            )
            vias.append(via)

        return vias

    def _parse_zones(self, content: str) -> List[Zone]:
        """解析铺铜区域"""
        zones = []

        # 查找 (zone ...) 节点
        zone_pattern = r'\(zone\s+\(\s*net\s+(\d+)\s*\)\s*\(\s*layer\s+"([^"]+)"\s*\)'

        for i, match in enumerate(re.finditer(zone_pattern, content)):
            net_num = match.group(1)
            layer = match.group(2)

            zone = Zone(
                id=f"zone_{i}",
                net_id=f"net_{net_num}",
                layer=layer,
                points=[],
                filled=True,
            )
            zones.append(zone)

        return zones


class KiCadSchematicParser:
    """KiCad 原理图解析器 (.sch)"""

    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """解析 .sch 文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse_content(content)

    def parse_content(self, content: str) -> Dict[str, Any]:
        """解析原理图内容"""
        result = {
            "components": [],
            "nets": [],
            "buses": [],
        }

        # 解析元件 (U, R, C, etc.)
        comp_pattern = r'\$Comp\s*\nL\s+(\S+)\s+(\S+)\s*\nU\s+\d+\s+\d+\s+F\s+"([^"]+)"\s*\n\d+\s+\d+\s+([-\d.]+)\s+([-\d.]+)\s+'
        for match in re.finditer(comp_pattern, content):
            library = match.group(1)
            reference = match.group(2)
            value = match.group(3)
            x = float(match.group(4))
            y = float(match.group(5))

            result["components"].append(
                {
                    "library": library,
                    "reference": reference,
                    "value": value,
                    "position": (x, y),
                }
            )

        # 解析网络连接
        net_pattern = r'\(wire\s+\(bus\s+\(entry\s+\([^)]+\)\s+\([^)]+\)\s*\)\s*\([^)]+\)\s*\)\s*\(net\s+"([^"]+)"\s+(\S+)\)'
        for match in re.finditer(net_pattern, content):
            net_name = match.group(1)
            net_code = match.group(2)
            result["nets"].append(
                {
                    "name": net_name,
                    "code": net_code,
                }
            )

        return result


def load_kicad_project(project_path: str) -> PCBBoard:
    """
    加载 KiCad 项目
    自动查找 .kicad_pcb 文件并解析
    """
    project_dir = Path(project_path)

    # 查找 .kicad_pcb 文件
    pcb_files = list(project_dir.glob("*.kicad_pcb"))

    if not pcb_files:
        # 尝试 KiCad 7/8 格式
        pcb_files = list(project_dir.glob("*.kicad_pcb"))

    if pcb_files:
        parser = KiCadPCBParser()
        return parser.parse_file(str(pcb_files[0]))

    raise FileNotFoundError(f"No .kicad_pcb file found in {project_path}")


# 测试
if __name__ == "__main__":
    # 简单测试
    print("KiCad Parser 测试")
    print("=" * 50)
    print("支持解析 .kicad_pcb 文件格式")
    print("可提取: 元件、走线、过孔、铺铜、网络")
    print("=" * 50)

"""
Enhanced Gerber Generator - 增强的 Gerber 文件生成器

Phase 5: 支持多层板层叠感知的 Gerber 生成

Author: Claude Code
Date: 2026-03-30
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GerberLayerType(Enum):
    """Gerber 层类型"""
    COPPER = "copper"           # 铜皮层
    MASK = "mask"               # 阻焊层
    SILK = "silk"               # 丝印层
    PASTE = "paste"             # 锡膏层
    EDGE = "edge"               # 板框层
    DRILL = "drill"             # 钻孔层
    SCORE = "score"             # V-CUT 分割线


# KiCad 层名到 Gerber 文件后缀的映射
LAYER_SUFFIX_MAP = {
    # 铜层
    "F.Cu": "F_Cu",
    "B.Cu": "B_Cu",
    "In1.Cu": "In1_Cu",
    "In2.Cu": "In2_Cu",
    "In3.Cu": "In3_Cu",
    "In4.Cu": "In4_Cu",
    # 阻焊层
    "F.Mask": "F_Mask",
    "B.Mask": "B_Mask",
    # 丝印层
    "F.SilkS": "F_SilkS",
    "B.SilkS": "B_SilkS",
    # 锡膏层
    "F.Paste": "F_Paste",
    "B.Paste": "B_Paste",
    # 板框
    "Edge.Cuts": "Edge_Cuts",
    #  Margin
    "Margin": "Margin",
    # 孔限
    "Drill": "Drill",
    "DrillPTH": "Drill_PTH",
    "DrillNPTH": "Drill_NPTH",
}


@dataclass
class GerberLayer:
    """Gerber 层定义"""
    name: str                    # KiCad 层名 (如 F.Cu)
    file_suffix: str            # Gerber 文件后缀 (如 F_Cu)
    layer_type: GerberLayerType # 层类型
    content: str = ""           # Gerber 内容


@dataclass
class GerberOutput:
    """Gerber 导出结果"""
    success: bool
    layers: List[GerberLayer]
    output_dir: str
    files: Dict[str, str]  # file_suffix -> filepath
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class EnhancedGerberGenerator:
    """
    增强的 Gerber 生成器

    支持多层板层叠感知的 Gerber 层生成

    使用方法:
        generator = EnhancedGerberGenerator(pcb_data, stackup)
        result = generator.generate()
    """

    def __init__(
        self,
        pcb_data: Dict[str, Any],
        layer_stackup: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            pcb_data: PCB 数据 (PCBData 格式)
            layer_stackup: 层叠配置 (可选)
        """
        self.pcb_data = pcb_data
        self.stackup = layer_stackup or {}
        self.layers_count = pcb_data.get("layers", 2)

    def get_required_layers(self) -> List[str]:
        """
        根据板子层数获取需要的 KiCad 层列表

        Returns:
            List[str]: KiCad 层名列表
        """
        layers = []

        # 铜层
        layers.append("F.Cu")
        if self.layers_count >= 4:
            layers.extend(["In1.Cu", "In2.Cu"])
        if self.layers_count >= 6:
            layers.extend(["In3.Cu", "In4.Cu"])
        layers.append("B.Cu")

        # 阻焊层 (每个铜层对应一个)
        layers.append("F.Mask")
        if self.layers_count >= 4:
            layers.append("In1.Mask")
            layers.append("In2.Mask")
        layers.append("B.Mask")

        # 丝印层
        layers.append("F.SilkS")
        layers.append("B.SilkS")

        # 锡膏层 (顶层和底层)
        layers.append("F.Paste")
        layers.append("B.Paste")

        # 板框
        layers.append("Edge.Cuts")

        return layers

    def generate_copper_layer(self, layer_name: str) -> str:
        """
        生成铜层的 Gerber 内容

        Args:
            layer_name: 层名 (如 F.Cu)

        Returns:
            str: Gerber 格式内容
        """
        lines = []
        lines.append("%FSLAX36Y36*%")  # Format specification
        lines.append('%MOIN*%')  # Modal: Inches units')
        lines.append(f'%ADD${layer_name.replace('.', '_')},C*%')  # Aperture macro

        # 获取该层的走线
        tracks = [
            t for t in self.pcb_data.get("tracks", [])
            if t.get("layer") == layer_name
        ]

        for track in tracks:
            width = track.get("width", 0.2)
            points = track.get("points", [])

            if len(points) < 2:
                continue

            # 解析坐标
            x1, y1 = points[0].get("x", 0), points[0].get("y", 0)
            x2, y2 = points[1].get("x", 0), points[1].get("y", 0)

            # Gerber 使用 3:6 格式 (6位小数，3位整数)
            x1_gerber = f"{x1*1e6:.0f}"
            y1_gerber = f"{y1*1e6:.0f}"
            x2_gerber = f"{x2*1e6:.0f}"
            y2_gerber = f"{y2*1e6:.0f}"

            lines.append(f'%ADD10C,{width*1e6:.1f}*%')  # Draw circle aperture
            lines.append(f'X{x1_gerber}Y{y1_gerber}D02*')  # Move to start
            lines.append(f'X{x2_gerber}Y{y2_gerber}D01*')  # Draw to end

        # 添加过孔
        vias = self.pcb_data.get("vias", [])
        for via in vias:
            if via.get("layer") == layer_name or layer_name in ["F.Cu", "B.Cu"]:
                x = via.get("x", 0) * 1e6
                y = via.get("y", 0) * 1e6
                outer = via.get("outer_diameter", 0.8) * 1e6
                drill = via.get("drill_diameter", 0.4) * 1e6
                lines.append(f'%ADD11C,{outer:.1f}*%')
                lines.append(f'X{x:.0f}Y{y:.0f}D03*')  # Flash via
                lines.append(f'%ADD12C,{drill:.1f}*%')
                lines.append(f'X{x:.0f}Y{y:.0f}D03*')  # Drill

        return '\n'.join(lines)

    def generate_mask_layer(self, layer_name: str) -> str:
        """
        生成阻焊层的 Gerber 内容

        阻焊层通常是铜层的反选 (SMD 焊盘区域)

        Args:
            layer_name: 层名 (如 F.Mask)

        Returns:
            str: Gerber 格式内容
        """
        lines = []
        lines.append('%FSLAX36Y36*%')
        lines.append('%MOIN*%')

        # 获取对应的铜层
        copper_layer = layer_name.replace(".Mask", ".Cu")

        # 获取该层的元件封装焊盘
        components = self.pcb_data.get("components", [])
        for comp in components:
            footprint = comp.get("footprint", "")
            pos = comp.get("position", {})
            x = pos.get("x", 0) * 1e6
            y = pos.get("y", 0) * 1e6

            # 简化：假设每个元件有一个方形焊盘
            # 实际应该从封装定义中读取
            pad_size = 1.0 * 1e6  # 1mm default
            lines.append(f'%ADD13R,{pad_size:.1f}X{pad_size:.1f}*%')
            lines.append(f'X{x:.0f}Y{y:.0f}D03*')

        return '\n'.join(lines)

    def generate_silk_layer(self, layer_name: str) -> str:
        """
        生成丝印层的 Gerber 内容

        Args:
            layer_name: 层名 (如 F.SilkS)

        Returns:
            str: Gerber 格式内容
        """
        lines = []
        lines.append('%FSLAX36Y36*%')
        lines.append('%MOIN*%')

        # 丝印线宽
        silk_width = 0.15 * 1e6  # 0.15mm
        lines.append(f'%ADD14C,{silk_width:.1f}*%')

        # 获取元件丝印
        components = self.pcb_data.get("components", [])
        for comp in components:
            ref = comp.get("reference", "")
            pos = comp.get("position", {})
            x = pos.get("x", 0) * 1e6
            y = pos.get("y", 0) * 1e6

            # 绘制元件参考编号文本 (简化)
            lines.append(f'G04 SMD Ref: {ref}*')
            lines.append(f'X{x:.0f}Y{y:.0f}D02*')

        return '\n'.join(lines)

    def generate_edge_layer(self) -> str:
        """
        生成板框层 (Edge.Cuts) 的 Gerber 内容

        Returns:
            str: Gerber 格式内容
        """
        lines = []
        lines.append('%FSLAX36Y36*%')
        lines.append('%MOIN*%')

        width = self.pcb_data.get("width", 100)
        height = self.pcb_data.get("height", 80)

        # 转换为 1/1000000 单位
        w = width * 1e6
        h = height * 1e6

        # 绘制矩形板框
        lines.append('%ADD15C,0.1*%')  # 0.1mm 宽的线
        lines.append('X0Y0D02*')  # 移动到原点
        lines.append(f'X{w:.0f}Y0D01*')  # 右
        lines.append(f'X{w:.0f}Y{h:.0f}D01*')  # 上
        lines.append(f'X0Y{h:.0f}D01*')  # 左
        lines.append('X0Y0D01*')  # 回到原点

        return '\n'.join(lines)

    def generate(
        self,
        output_dir: str,
        include_layers: Optional[List[str]] = None,
    ) -> GerberOutput:
        """
        生成所有 Gerber 文件

        Args:
            output_dir: 输出目录
            include_layers: 要生成的层列表 (None = 所有需要的层)

        Returns:
            GerberOutput: 导出结果
        """
        import os

        layers = include_layers or self.get_required_layers()
        gerber_layers = []
        files = {}
        errors = []

        for layer_name in layers:
            try:
                file_suffix = LAYER_SUFFIX_MAP.get(layer_name, layer_name.replace(".", "_"))

                if layer_name == "Edge.Cuts":
                    content = self.generate_edge_layer()
                elif ".Cu" in layer_name:
                    content = self.generate_copper_layer(layer_name)
                elif ".Mask" in layer_name:
                    content = self.generate_mask_layer(layer_name)
                elif ".SilkS" in layer_name:
                    content = self.generate_silk_layer(layer_name)
                elif ".Paste" in layer_name:
                    content = ""  # Paste layer not needed for most exports
                else:
                    content = ""
                    errors.append(f"Unknown layer type: {layer_name}")
                    continue

                # 确定层类型
                if "Cu" in layer_name:
                    layer_type = GerberLayerType.COPPER
                elif "Mask" in layer_name:
                    layer_type = GerberLayerType.MASK
                elif "SilkS" in layer_name:
                    layer_type = GerberLayerType.SILK
                elif "Paste" in layer_name:
                    layer_type = GerberLayerType.PASTE
                elif "Edge" in layer_name:
                    layer_type = GerberLayerType.EDGE
                else:
                    layer_type = GerberLayerType.COPPER

                gerber_layer = GerberLayer(
                    name=layer_name,
                    file_suffix=file_suffix,
                    layer_type=layer_type,
                    content=content,
                )
                gerber_layers.append(gerber_layer)

                # 写入文件
                filepath = os.path.join(output_dir, f"{file_suffix}.gbr")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                files[file_suffix] = filepath

            except Exception as e:
                logger.error(f"Failed to generate layer {layer_name}: {e}")
                errors.append(f"Layer {layer_name}: {str(e)}")

        return GerberOutput(
            success=len(errors) == 0,
            layers=gerber_layers,
            output_dir=output_dir,
            files=files,
            errors=errors,
        )

    def get_layer_file_map(self) -> Dict[str, str]:
        """
        获取 KiCad 层名到 Gerber 文件后缀的映射

        Returns:
            Dict[str, str]: KiCad 层名 -> Gerber 后缀
        """
        return LAYER_SUFFIX_MAP.copy()

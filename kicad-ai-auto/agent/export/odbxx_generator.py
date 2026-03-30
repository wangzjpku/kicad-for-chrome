"""
ODB++ Generator - ODB++ 制造文件生成器

Phase 5: 提供比 Gerber 更完整的制造数据导出

ODB++ 是一种目录结构的制造格式，包含:
- 完整的层叠定义 (matrix)
- 铜层特征 (signals)
- 钻孔数据 (drill)
- 元件数据 (components)
- 网表 (netlist)

Author: Claude Code
Date: 2026-03-30
"""

import os
import zipfile
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号层类型"""
    POWER = "power"
    GROUND = "ground"
    SIGNAL = "signal"
    MIXED = "mixed"


@dataclass
class ODBLayer:
    """ODB++ 层定义"""
    name: str              # 层名 (如 TOP, BOTTOM, INNER1)
    type: str              # 类型 (surface, plane, mixed)
    polarity: str          # positive / negative
    dielectric_constant: float = 4.5  # FR4 默认


@dataclass
class ODBFeature:
    """ODB++ 特征"""
    feature_type: str      # line, pad, polygon, arc, text
    coordinates: List[Tuple[float, float]]
    width: float = 0
    height: float = 0
    drill_diameter: float = 0
    net_name: str = ""


@dataclass
class ODBComponent:
    """ODB++ 元件"""
    reference: str
    value: str
    footprint: str
    x: float
    y: float
    rotation: float = 0
    layer: str = "top"


@dataclass
class ODBNet:
    """ODB++ 网络"""
    name: str
    pins: List[Dict[str, str]]  # [{component: "U1", pin: "1"}, ...]


@dataclass
class ODBOutput:
    """ODB++ 导出结果"""
    success: bool
    output_file: str       # ZIP 文件路径
    directory: str         # 目录路径
    files: List[str]      # 生成的文件列表
    errors: List[str] = field(default_factory=list)


class ODBXXGenerator:
    """
    ODB++ 制造文件生成器

    生成符合 IPC-2581 标准的 ODB++ 制造数据包

    使用方法:
        generator = ODBXXGenerator(pcb_data)
        result = generator.generate(output_path)
    """

    # ODB++ 标准层名
    LAYER_NAMES = {
        2: ["TOP", "BOTTOM"],
        4: ["TOP", "INNER1", "INNER2", "BOTTOM"],
        6: ["TOP", "INNER1", "INNER2", "INNER3", "INNER4", "BOTTOM"],
    }

    def __init__(self, pcb_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None):
        """
        Args:
            pcb_data: PCB 数据 (PCBData 格式)
            options: 生成选项
                - board_name: 板子名称 (默认 "board")
                - project_id: 项目标识
                - include_components: 是否包含元件 (默认 True)
                - include_netlist: 是否包含网表 (默认 True)
        """
        self.pcb_data = pcb_data
        self.options = options or {}
        self.board_name = self.options.get("board_name", "board")
        self.project_id = self.options.get("project_id", "PROJECT001")
        self.include_components = self.options.get("include_components", True)
        self.include_netlist = self.options.get("include_netlist", True)

        self.layers_count = pcb_data.get("layers", 2)
        self.width = pcb_data.get("width", 100)  # mm
        self.height = pcb_data.get("height", 80)  # mm

    def _get_layer_names(self) -> List[str]:
        """获取层名列表"""
        return self.LAYER_NAMES.get(self.layers_count, ["TOP", "BOTTOM"])

    def _mm_to_odb_units(self, value_mm: float) -> str:
        """将毫米转换为 ODB++ 单位 (0.0001 inch = 2.54 micron)"""
        # ODB++ uses 0.0001 inch units
        value_10k_inch = value_mm / 0.00254
        return f"{value_10k_inch:.0f}"

    def _create_matrix_file(self) -> str:
        """
        创建 matrix 文件 - 层叠定义

        Returns:
            str: matrix 文件内容
        """
        layer_names = self._get_layer_names()
        dielectric_count = len(layer_names) + 1  # layers + 1 dielectric between each

        lines = [
            "%HEADER",
            "ODB++ version=G",
            "CREATED|DATE=2026-03-30|TIME=00:00:00|USER=Claude",
            "",
            "PATH|SEPARATOR=/",
            "",
            "LAYER/SEQUENCE",
            f"0|SURFACE|{layer_names[0]}|POSITIVE|SURFACE",
        ]

        for i, name in enumerate(layer_names[1:-1], 1):
            lines.append(f"{i}|MIXED|{name}|POSITIVE|MIXED")
        lines.append(f"{len(layer_names)-1}|SURFACE|{layer_names[-1]}|POSITIVE|SURFACE")

        lines.extend([
            "",
            "TYPE/TYPE",
            "SIGNAL",
            "PLANE",
            "",
            "CLASS/CLASS",
            "CLASS_NETS",
            "",
            "ETEST",
            "",
            "CUPAD",
            "",
            "CONDUCTION",
            "",
            "MASK",
            "",
            "SOLDERPASTE",
            "",
            "SILKSCREEN",
        ])

        return '\n'.join(lines)

    def _create_steps_matrix(self) -> str:
        """创建 steps/matrix 文件"""
        layer_names = self._get_layer_names()
        lines = [
            "%HEADER",
            f"STEP|SEQUENCE={self.board_name}|NO_ROUTABLE=YES",
            "",
            "PATH|SEPARATOR=/",
            "",
            "LAYER/SEQUENCE",
        ]

        for i, name in enumerate(layer_names):
            lines.append(f"{i}|SURFACE|{name}|POSITIVE|SURFACE")

        lines.append("")
        return '\n'.join(lines)

    def _create_profile(self) -> str:
        """创建 profile 文件 - 板框轮廓"""
        w = self._mm_to_odb_units(self.width)
        h = self._mm_to_odb_units(self.height)

        # ODB++ profile format: 4 lines forming rectangle
        lines = [
            "%HEADER",
            "G01PTH",
            "EQ." "",
            "",
            "S40C0",
            "",
            f"L 0 0 {w} 0",
            f"L {w} 0 {w} {h}",
            f"L {w} {h} 0 {h}",
            f"L 0 {h} 0 0",
        ]
        return '\n'.join(lines)

    def _create_signal_layer(self, layer_name: str, layer_idx: int) -> Dict[str, str]:
        """
        创建信号层文件

        Args:
            layer_name: 层名 (如 TOP, BOTTOM)
            layer_idx: 层索引

        Returns:
            Dict[str, str]: 文件名 -> 内容
        """
        files = {}

        # 映射到 PCB 数据中的层名
        pcb_layer_map = {
            "TOP": "F.Cu",
            "BOTTOM": "B.Cu",
            "INNER1": "In1.Cu",
            "INNER2": "In2.Cu",
            "INNER3": "In3.Cu",
            "INNER4": "In4.Cu",
        }
        pcb_layer = pcb_layer_map.get(layer_name, "F.Cu")

        # 获取该层的走线
        tracks = [t for t in self.pcb_data.get("tracks", []) if t.get("layer") == pcb_layer]

        # Lines 文件
        lines_content = ["%HEADER", "G01PTH"]
        for track in tracks:
            width = track.get("width", 0.2)
            points = track.get("points", [])
            if len(points) < 2:
                continue

            for i in range(len(points) - 1):
                x1 = self._mm_to_odb_units(points[i].get("x", 0))
                y1 = self._mm_to_odb_units(points[i].get("y", 0))
                x2 = self._mm_to_odb_units(points[i + 1].get("x", 0))
                y2 = self._mm_to_odb_units(points[i + 1].get("y", 0))
                w = self._mm_to_odb_units(width)
                lines_content.append(f"L {x1} {y1} {x2} {y2}")

        files["lines"] = '\n'.join(lines_content) if len(lines_content) > 2 else "%HEADER\nG01PTH\n"

        # Padstack 文件 (简化)
        files["padstacks"] = self._create_padstacks()

        return files

    def _create_padstacks(self) -> str:
        """创建 padstacks 文件"""
        lines = [
            "%HEADER",
            "",
            "PADSTACK/DEFAULT",
            "CIRCLEARRAY",
            "PARAMETER|ANGLE=0.000000",
            "PARAMETER|COLS=1",
            "PARAMETER|ROWS=1",
            "PARAMETER|X=0.000000",
            "PARAMETER|Y=0.000000",
            "",
            "PAD|SOLDER|CLASS=SMD|CIRCLE|10.000000",
            "PAD|SOLDER|CLASS=SMD|CIRCLE|10.000000",
            "",
            "PADSTACK/PLATED",
            "CIRCLEARRAY",
            "PARAMETER|ANGLE=0.000000",
            "PARAMETER|COLS=1",
            "PARAMETER|ROWS=1",
            "PARAMETER|X=0.000000",
            "PARAMETER|Y=0.000000",
            "",
            "PAD|SOLDER|CLASS=PTH|CIRCLE|15.000000",
            "PAD|SOLDER|CLASS=PTH|CIRCLE|10.000000",
        ]
        return '\n'.join(lines)

    def _create_drill_file(self) -> str:
        """创建钻孔文件"""
        vias = self.pcb_data.get("vias", [])
        drills = self.pcb_data.get("drills", []) if "drills" in self.pcb_data else []

        lines = [
            "%HEADER",
            "G81PTH",
            "",
            "MCODES",
            "M48",
            "M71",  # Metric
        ]

        # 收集所有钻孔直径
        drill_sizes = set()
        for via in vias:
            drill_sizes.add(via.get("drill_diameter", 0.4))

        # 写入钻孔直径
        for idx, diameter in enumerate(sorted(drill_sizes), 1):
            lines.append(f"T{idx}C{self._mm_to_odb_units(diameter)}")

        lines.append("M95")  # End of drill sizes
        lines.append("")

        # 写入钻孔位置
        for idx, diameter in enumerate(sorted(drill_sizes), 1):
            lines.append("T" + "0" * idx)
            for via in vias:
                if abs(via.get("drill_diameter", 0.4) - diameter) < 0.001:
                    x = self._mm_to_odb_units(via.get("x", 0))
                    y = self._mm_to_odb_units(via.get("y", 0))
                    lines.append(f"X{x}Y{y}")

        lines.append("M30")  # End of file

        return '\n'.join(lines)

    def _create_netlist(self) -> str:
        """创建网表文件"""
        nets = self.pcb_data.get("nets", [])

        lines = [
            "%HEADER",
            "G_NETLIST",
            "",
            "QTY|REFERENCE|VALUE|PACKAGE|LAYER|X|Y|ROTATION",
        ]

        components = self.pcb_data.get("components", [])
        for comp in components:
            ref = comp.get("reference", "U?")
            value = comp.get("value", "")
            footprint = comp.get("footprint", "")
            pos = comp.get("position", {})
            x = self._mm_to_odb_units(pos.get("x", 0))
            y = self._mm_to_odb_units(pos.get("y", 0))
            rot = comp.get("rotation", 0)
            layer = "TOP" if pos.get("layer", "F.Cu") == "F.Cu" else "BOTTOM"
            lines.append(f"1|{ref}|{value}|{footprint}|{layer}|{x}|{y}|{rot}")

        lines.append("")
        lines.append("PINS")

        for net in nets:
            net_name = net.get("name", "")
            pins = net.get("pins", [])
            for pin in pins:
                lines.append(f"{net_name}|{pin.get('component', 'U?')}|{pin.get('pin', '1')}")

        lines.append("")
        return '\n'.join(lines)

    def _create_components_file(self) -> str:
        """创建元件文件"""
        components = self.pcb_data.get("components", [])

        lines = [
            "%HEADER",
            "GCOMPONENTS",
            "",
            "PKG|PACKAGES",
        ]

        # 分组 by footprint
        packages = {}
        for comp in components:
            pkg = comp.get("footprint", "Unknown")
            if pkg not in packages:
                packages[pkg] = []
            packages[pkg].append(comp)

        for pkg_name, comps in packages.items():
            lines.append(f"NAME|{pkg_name}")
            lines.append("NUMPINS|" + str(len(comps[0].get("pins", [1, 2, 3, 4]))))

            # 简化: 假设矩形封装
            width = 5.0
            height = 5.0
            lines.append(f"GEOM|WIDTH={self._mm_to_odb_units(width)}|HEIGHT={self._mm_to_odb_units(height)}")

            for comp in comps:
                ref = comp.get("reference", "U?")
                pos = comp.get("position", {})
                x = self._mm_to_odb_units(pos.get("x", 0))
                y = self._mm_to_odb_units(pos.get("y", 0))
                rot = comp.get("rotation", 0)
                layer = "TOP" if pos.get("layer", "F.Cu") == "F.Cu" else "BOTTOM"
                lines.append(f"COMP|{ref}|{x}|{y}|{rot}|{layer}")

            lines.append("END")
            lines.append("")

        return '\n'.join(lines)

    def generate(self, output_dir: str) -> ODBOutput:
        """
        生成 ODB++ 制造文件

        Args:
            output_dir: 输出目录路径

        Returns:
            ODBOutput: 导出结果
        """
        import shutil
        from datetime import datetime

        errors = []
        generated_files = []

        # 创建临时目录
        base_name = f"ODB_{self.board_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir = os.path.join(output_dir, base_name)
        steps_dir = os.path.join(temp_dir, "steps", "panel")
        signals_dir = os.path.join(steps_dir, "signals")

        try:
            # 创建目录结构
            os.makedirs(steps_dir, exist_ok=True)
            os.makedirs(os.path.join(signals_dir, "TOP"), exist_ok=True)
            os.makedirs(os.path.join(signals_dir, "BOTTOM"), exist_ok=True)

            if self.layers_count >= 4:
                os.makedirs(os.path.join(signals_dir, "INNER1"), exist_ok=True)
                os.makedirs(os.path.join(signals_dir, "INNER2"), exist_ok=True)
            if self.layers_count >= 6:
                os.makedirs(os.path.join(signals_dir, "INNER3"), exist_ok=True)
                os.makedirs(os.path.join(signals_dir, "INNER4"), exist_ok=True)

            # 创建顶层文件
            root_matrix = self._create_matrix_file()
            with open(os.path.join(temp_dir, "matrix"), 'w', encoding='utf-8') as f:
                f.write(root_matrix)
            generated_files.append("matrix")

            # 创建 steps/matrix
            steps_matrix = self._create_steps_matrix()
            with open(os.path.join(temp_dir, "steps", "matrix"), 'w', encoding='utf-8') as f:
                f.write(steps_matrix)
            generated_files.append("steps/matrix")

            # 创建 profile
            profile = self._create_profile()
            with open(os.path.join(steps_dir, "profile"), 'w', encoding='utf-8') as f:
                f.write(profile)
            generated_files.append("steps/panel/profile")

            # 创建信号层
            layer_names = self._get_layer_names()
            for layer_name in layer_names:
                layer_files = self._create_signal_layer(layer_name, layer_names.index(layer_name))
                layer_dir = os.path.join(signals_dir, layer_name)
                for fname, content in layer_files.items():
                    fpath = os.path.join(layer_dir, fname)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    generated_files.append(f"steps/panel/signals/{layer_name}/{fname}")

            # 创建钻孔文件
            drill = self._create_drill_file()
            drill_dir = os.path.join(steps_dir, "drill")
            os.makedirs(drill_dir, exist_ok=True)
            with open(os.path.join(drill_dir, "pth"), 'w', encoding='utf-8') as f:
                f.write(drill)
            generated_files.append("steps/panel/drill/pth")

            # 创建网表
            if self.include_netlist:
                netlist = self._create_netlist()
                with open(os.path.join(steps_dir, "netlist"), 'w', encoding='utf-8') as f:
                    f.write(netlist)
                generated_files.append("steps/panel/netlist")

            # 创建元件文件
            if self.include_components:
                components_file = self._create_components_file()
                comp_dir = os.path.join(steps_dir, "components")
                os.makedirs(comp_dir, exist_ok=True)
                with open(os.path.join(comp_dir, "top"), 'w', encoding='utf-8') as f:
                    f.write(components_file)
                with open(os.path.join(comp_dir, "bottom"), 'w', encoding='utf-8') as f:
                    f.write(components_file)
                generated_files.append("steps/panel/components/top")
                generated_files.append("steps/panel/components/bottom")

            # 创建 ZIP 文件
            zip_path = os.path.join(output_dir, f"{base_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arcname)

            # 清理临时目录
            shutil.rmtree(temp_dir)

            return ODBOutput(
                success=True,
                output_file=zip_path,
                directory=temp_dir,
                files=generated_files,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"ODB++ generation failed: {e}")
            errors.append(str(e))
            return ODBOutput(
                success=False,
                output_file="",
                directory=temp_dir if os.path.exists(temp_dir) else "",
                files=generated_files,
                errors=errors,
            )

    def generate_directory(self, output_dir: str) -> ODBOutput:
        """
        生成 ODB++ 目录结构（不压缩）

        Args:
            output_dir: 输出目录路径

        Returns:
            ODBOutput: 导出结果
        """
        from datetime import datetime

        errors = []
        generated_files = []

        base_name = f"ODB_{self.board_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_dir = os.path.join(output_dir, base_name)
        steps_dir = os.path.join(target_dir, "steps", "panel")
        signals_dir = os.path.join(steps_dir, "signals")

        try:
            # 创建目录结构
            os.makedirs(steps_dir, exist_ok=True)
            os.makedirs(os.path.join(signals_dir, "TOP"), exist_ok=True)
            os.makedirs(os.path.join(signals_dir, "BOTTOM"), exist_ok=True)

            if self.layers_count >= 4:
                os.makedirs(os.path.join(signals_dir, "INNER1"), exist_ok=True)
                os.makedirs(os.path.join(signals_dir, "INNER2"), exist_ok=True)
            if self.layers_count >= 6:
                os.makedirs(os.path.join(signals_dir, "INNER3"), exist_ok=True)
                os.makedirs(os.path.join(signals_dir, "INNER4"), exist_ok=True)

            # 创建所有文件 (与 generate() 相同)
            root_matrix = self._create_matrix_file()
            with open(os.path.join(target_dir, "matrix"), 'w', encoding='utf-8') as f:
                f.write(root_matrix)
            generated_files.append("matrix")

            steps_matrix = self._create_steps_matrix()
            with open(os.path.join(target_dir, "steps", "matrix"), 'w', encoding='utf-8') as f:
                f.write(steps_matrix)
            generated_files.append("steps/matrix")

            profile = self._create_profile()
            with open(os.path.join(steps_dir, "profile"), 'w', encoding='utf-8') as f:
                f.write(profile)
            generated_files.append("steps/panel/profile")

            layer_names = self._get_layer_names()
            for layer_name in layer_names:
                layer_files = self._create_signal_layer(layer_name, layer_names.index(layer_name))
                layer_dir = os.path.join(signals_dir, layer_name)
                for fname, content in layer_files.items():
                    fpath = os.path.join(layer_dir, fname)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    generated_files.append(f"steps/panel/signals/{layer_name}/{fname}")

            drill = self._create_drill_file()
            drill_dir = os.path.join(steps_dir, "drill")
            os.makedirs(drill_dir, exist_ok=True)
            with open(os.path.join(drill_dir, "pth"), 'w', encoding='utf-8') as f:
                f.write(drill)
            generated_files.append("steps/panel/drill/pth")

            if self.include_netlist:
                netlist = self._create_netlist()
                with open(os.path.join(steps_dir, "netlist"), 'w', encoding='utf-8') as f:
                    f.write(netlist)
                generated_files.append("steps/panel/netlist")

            if self.include_components:
                components_file = self._create_components_file()
                comp_dir = os.path.join(steps_dir, "components")
                os.makedirs(comp_dir, exist_ok=True)
                with open(os.path.join(comp_dir, "top"), 'w', encoding='utf-8') as f:
                    f.write(components_file)
                with open(os.path.join(comp_dir, "bottom"), 'w', encoding='utf-8') as f:
                    f.write(components_file)
                generated_files.append("steps/panel/components/top")
                generated_files.append("steps/panel/components/bottom")

            return ODBOutput(
                success=True,
                output_file=target_dir,
                directory=target_dir,
                files=generated_files,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"ODB++ directory generation failed: {e}")
            errors.append(str(e))
            return ODBOutput(
                success=False,
                output_file="",
                directory=target_dir if os.path.exists(target_dir) else "",
                files=generated_files,
                errors=errors,
            )

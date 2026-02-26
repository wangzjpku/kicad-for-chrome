"""
KiCad Exporter - 使用正确的 S-Expression 格式
基于 KiCad 官方文件格式规范
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any

# 安全配置：允许的输出目录
ALLOWED_OUTPUT_BASE = Path(os.getenv("OUTPUT_DIR", "output")).resolve()


def _validate_output_path(output_path: str) -> Path:
    """
    验证输出路径安全性

    Args:
        output_path: 用户提供的输出路径

    Returns:
        验证后的安全路径

    Raises:
        ValueError: 如果路径不安全
    """
    path = Path(output_path).resolve()

    # 检查路径遍历
    if ".." in str(path):
        raise ValueError("Path traversal not allowed in output path")

    # 确保路径在允许的基础目录内
    try:
        path.relative_to(ALLOWED_OUTPUT_BASE)
    except ValueError:
        # 也允许在当前工作目录的 output 子目录
        cwd_output = Path.cwd() / "output"
        try:
            path.relative_to(cwd_output.resolve())
        except ValueError:
            raise ValueError(
                f"Output path must be within {ALLOWED_OUTPUT_BASE}"
            )

    return path


def escape_kicad_string(s):
    """转义 KiCad 字符串中的特殊字符"""
    return s.replace("\\", "\\\\").replace('"', "\\~")


def json_to_kicad_schematic(schematic_data: Dict[str, Any], output_path: str):
    """生成正确的 KiCad 原理图文件"""

    components = schematic_data.get("components", [])

    lines = []
    lines.append('(kicad_sch (version 20230115) (generator "kicad-ai-auto")')
    lines.append("  (version 20230115)")
    lines.append("")
    lines.append("  (setup")
    lines.append('    (stackup "default")')
    lines.append("  )")
    lines.append("")

    # 空的符号库定义 - 使用 KiCad 内置符号
    lines.append("  (lib_symbols")
    lines.append("  )")
    lines.append("")

    # 直接创建符号实例 - 简化格式
    # 原理图位置单位是 mils (1/1000 inch)

    for i, comp in enumerate(components):
        ref = comp.get("reference", f"U{i}")
        name = comp.get("name", "Unknown")
        pos = comp.get("position", {"x": 0, "y": 0})
        x = int(pos.get("x", 0) * 10)  # 转换单位
        y = int(pos.get("y", 0) * 10)
        footprint = comp.get("footprint", "")

        # 生成符号实例 - 使用简化格式
        lines.append(f'  (symbol (lib_id "{name}") (at {x} {y} 0)')
        lines.append("    (unit 1)")
        lines.append("    (in_bom yes)")
        lines.append("    (on_board yes)")
        lines.append(f'    (property "Reference" "{ref}" (id 0) (at {x} {y - 100} 0)')
        lines.append("      (effects (font (size 1.27 1.27)) (justify left))")
        lines.append("    )")
        lines.append(f'    (property "Value" "{name}" (id 1) (at {x} {y - 200} 0)')
        lines.append("      (effects (font (size 1.27 1.27)) (justify left))")
        lines.append("    )")

        # 添加引脚
        pins = comp.get("pins", [])
        for j, pin in enumerate(pins):
            pin_num = pin.get("number", str(j + 1))
            pin_name = pin.get("name", f"P{pin_num}")
            pin_type = pin.get("type", "passive")

            # 引脚位置偏移
            if j % 2 == 0:
                pin_x = x - 100
                pin_ang = 0  # 左边
            else:
                pin_x = x + 100
                pin_ang = 180  # 右边

            lines.append(
                f'    (pin "{pin_type}" {pin_ang} "{pin_name}" (at {pin_x} {y} {pin_ang})'
            )
            lines.append(f'      (length 100) (name "{pin_name}") (number "{pin_num}")')
            lines.append("      (types (passive))")
            lines.append("    )")

        lines.append("  )")
        lines.append("")

    # 添加电源符号
    lines.append('  (symbol "GND" (power) (in_bom yes) (on_board yes)')
    lines.append('    (property "Reference" "#PWR" (id 0) (at 0 0 0)')
    lines.append("      (effects (font (size 1.27 1.27)))")
    lines.append("    )")
    lines.append('    (property "Value" "GND" (id 1) (at 0 0 0)')
    lines.append("      (effects (font (size 1.27 1.27)))")
    lines.append("    )")
    lines.append('    (pin "1" input (at 0 0 270)')
    lines.append('      (length 0) (name "1") (number "1")')
    lines.append("      (types (power_in))")
    lines.append("    )")
    lines.append("  )")
    lines.append("")

    lines.append('  (symbol "VCC" (power) (in_bom yes) (on_board yes)')
    lines.append('    (property "Reference" "#PWR" (id 0) (at 0 0 0)')
    lines.append("      (effects (font (size 1.27 1.27)))")
    lines.append("    )")
    lines.append('    (property "Value" "VCC" (id 1) (at 0 0 0)')
    lines.append("      (effects (font (size 1.27 1.27)))")
    lines.append("    )")
    lines.append('    (pin "1" input (at 0 0 270)')
    lines.append('      (length 0) (name "1") (number "1")')
    lines.append("      (types (power_in))")
    lines.append("    )")
    lines.append("  )")
    lines.append(")")

    # 验证输出路径安全性
    safe_path = _validate_output_path(output_path)

    # 确保输出目录存在
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(safe_path)


def json_to_kicad_pcb(pcb_data: Dict[str, Any], output_path: str):
    """生成正确的 KiCad PCB 文件"""

    components = pcb_data.get("components", [])
    width = pcb_data.get("width", 100)
    height = pcb_data.get("height", 100)

    lines = []
    lines.append('(kicad_pcb (version 20230115) (generator "kicad-ai-auto")')
    lines.append('  (generator "kicad-ai-auto")')
    lines.append("  (generator_version 8)")
    lines.append("")
    lines.append("  (general")
    lines.append("    (thickness 1.6)")
    lines.append("    (drawings 0)")
    lines.append("    (tracks 0)")
    lines.append("    (modules 0)")
    lines.append("    (nets 1)")
    lines.append("  )")
    lines.append("")
    lines.append('  (paper "A4")')
    lines.append("")
    lines.append("  (layers")
    lines.append('    (0 "F.Cu" "Top Copper" signal)')
    lines.append('    (31 "B.Cu" "Bottom Copper" signal)')
    lines.append('    (32 "B.Paste" "Bottom Paste" user)')
    lines.append('    (33 "F.Paste" "Top Paste" user)')
    lines.append('    (34 "F.SilkS" "Top Silkscreen" user)')
    lines.append('    (35 "B.SilkS" "Bottom Silkscreen" user)')
    lines.append('    (36 "F.Mask" "Top Mask" user)')
    lines.append('    (37 "B.Mask" "Bottom Mask" user)')
    lines.append('    (40 "Edge.Cuts" "Edges" user)')
    lines.append("  )")
    lines.append("")
    lines.append("  (setup")
    lines.append("    (pad_to_mask_clearance 0)")
    lines.append("    (solder_mask_min_width 0.25)")
    lines.append("    (pcbplotparams")
    lines.append("      (layerselection 0x00010f_80000001)")
    lines.append("    )")
    lines.append("  )")
    lines.append("")
    lines.append('  (net_class Default "This is the default net class."')
    lines.append("    (clearance 0.2)")
    lines.append("    (trace_width 0.25)")
    lines.append("    (via_dia 0.6)")
    lines.append("    (via_drill 0.4)")
    lines.append("    (uvia_dia 0.3)")
    lines.append("    (uvia_drill 0.1)")
    lines.append("  )")
    lines.append("")

    # PCB 边框 - 100x100mm
    lines.append(
        '  (gr_line (start 0 0) (end 0 100000) (layer "Edge.Cuts") (width 0.1))'
    )
    lines.append(
        '  (gr_line (start 0 100000) (end 100000 100000) (layer "Edge.Cuts") (width 0.1))'
    )
    lines.append(
        '  (gr_line (start 100000 100000) (end 100000 0) (layer "Edge.Cuts") (width 0.1))'
    )
    lines.append(
        '  (gr_line (start 100000 0) (end 0 0) (layer "Edge.Cuts") (width 0.1))'
    )
    lines.append("")

    # 放置封装
    for i, comp in enumerate(components):
        ref = comp.get("reference", f"U{i}")
        value = comp.get("value", "")
        footprint = comp.get("footprint", "")
        pos = comp.get("position", {"x": 0, "y": 0})

        # 转换为 mm (坐标单位是 0.1mil)
        x_mm = pos.get("x", 0) * 0.00254
        y_mm = pos.get("y", 0) * 0.00254

        if footprint:
            lines.append(f'  (footprint "{footprint}"')
            lines.append('    (layer "F.Cu")')
            lines.append(f"    (at {x_mm:.4f} {y_mm:.4f})")

            # 检查封装类型
            is_tht = "DIP" in footprint or "_TH" in footprint or "THT" in footprint
            attr = "through_hole" if is_tht else "smd"
            lines.append(f"    (attr {attr})")

            lines.append(f'    (fp_text reference "{ref}"')
            lines.append("      (at 0 0)")
            lines.append('      (layer "F.SilkS")')
            lines.append("      (effects (font (size 1 1))))")
            lines.append("    )")

            lines.append(f'    (fp_text value "{value}"')
            lines.append("      (at 0 1.5)")
            lines.append('      (layer "F.Fab")')
            lines.append("      (effects (font (size 1 1))))")
            lines.append("    )")
            lines.append("  )")
            lines.append("")

    lines.append(")")

    # 验证输出路径安全性
    safe_path = _validate_output_path(output_path)

    # 确保输出目录存在
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(safe_path)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(__file__))

    schematic_json = "output/ne555_schematic.json"
    pcb_json = "output/ne555_pcb.json"
    output_dir = "output/kicad_files"

    os.makedirs(output_dir, exist_ok=True)

    with open(schematic_json, "r", encoding="utf-8") as f:
        schematic_data = json.load(f)

    with open(pcb_json, "r", encoding="utf-8") as f:
        pcb_data = json.load(f)

    sch_path = os.path.join(output_dir, "ne555_blink.sch")
    json_to_kicad_schematic(schematic_data, sch_path)
    print(f"[OK] Schematic: {sch_path}")

    pcb_path = os.path.join(output_dir, "ne555_blink.kicad_pcb")
    json_to_kicad_pcb(pcb_data, pcb_path)
    print(f"[OK] PCB: {pcb_path}")

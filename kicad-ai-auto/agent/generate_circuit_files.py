#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电路到 KiCad 文件生成器
工作流：电路JSON → HTML可视化 → KiCad原理图/PCB
"""

import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import json
import uuid
from pathlib import Path

# ============== 配置 ==============
# 使用PCB JSON因为它有完整的pins数据
INPUT_JSON = "output/ne555_pcb.json"
OUTPUT_DIR = Path("output/kicad_files")
HTML_OUTPUT = "output/circuit_viewer.html"

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


def generate_html_viewer(data: dict, output_path: str):
    """生成 HTML 可视化"""

    nets = {}
    for comp in data.get("components", []):
        for pin in comp.get("pins", []):
            net_name = pin.get("net", "")
            if net_name:
                if net_name not in nets:
                    nets[net_name] = []
                nets[net_name].append(
                    {
                        "ref": comp.get("reference", ""),
                        "value": comp.get("value", ""),
                        "pin": pin.get("number", ""),
                        "x": comp.get("position", {}).get("x", 0),
                        "y": comp.get("position", {}).get("y", 0),
                    }
                )

    comp_styles = {
        "LED": {"color": "#e74c3c", "width": 30, "height": 18},
    }
    for v in ["10K", "1K", "100", "220", "470"]:
        comp_styles[v] = {"color": "#3498db", "width": 28, "height": 14}
    for v in ["10uF", "100nF", "1uF", "NE555"]:
        comp_styles[v] = {
            "color": "#9b59b6" if v == "NE555" else "#f39c12",
            "width": 50 if v == "NE555" else 28,
            "height": 35 if v == "NE555" else 14,
        }

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>电路可视化</title>
    <style>
        body { background:#1a1a2e;color:#fff;font-family:Arial;padding:20px;margin:0; }
        h1 { color:#00d4ff;text-align:center; }
        .container { display:flex;gap:20px;max-width:1400px;margin:0 auto; }
        .pcb-view { flex:1;background:#0d1b2a;padding:20px;border-radius:12px;min-height:500px;position:relative; }
        .net-panel { width:320px;background:#0d1b2a;padding:20px;border-radius:12px;max-height:550px;overflow-y:auto; }
        .stats { display:flex;gap:15px;margin-bottom:15px; }
        .stat-box { background:#1b2838;padding:12px 20px;border-radius:8px;text-align:center;flex:1; }
        .stat-num { font-size:22px;font-weight:bold;color:#00d4ff; }
        .stat-label { font-size:11px;color:#8899aa; }
        
        .net-item { background:#1b2838;margin-bottom:6px;border-radius:6px;overflow:hidden; }
        .net-header { padding:8px 12px;font-weight:bold; }
        .net-power { background:linear-gradient(90deg,#ff6b6b,#ee5a5a); }
        .net-signal { background:linear-gradient(90deg,#4ecdc4,#44a08d); }
        .net-pins { padding:6px 10px;background:#0d1b2a;font-size:11px; }
        
        .comp { position:absolute;border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:10px;}
        .comp-pin { position:absolute;width:8px;height:8px;border-radius:50%; }
        
        .legend { position:absolute;bottom:10px;left:15px;font-size:11px;display:flex;gap:12px; }
        .legend-item { display:flex;align-items:center;gap:4px; }
        .legend-box { width:12px;height:12px;border-radius:2px; }
    </style>
</head>
<body>
    <h1>🔌 电路网络可视化</h1>
    <div class="container">
        <div class="pcb-view">
""")

    # 添加组件
    for comp in data.get("components", []):
        ref = comp.get("reference", "")
        # JSON中使用name字段，而不是value字段！
        value = comp.get("value", comp.get("name", ""))
        x = comp.get("position", {}).get("x", 0)
        y = comp.get("position", {}).get("y", 0)

        # PCB坐标使用0.254转换(2000->508mm)，HTML使用0.1缩放以便显示
        px = x * 0.1 + 50
        py = y * 0.1 + 50

        style = comp_styles.get(value, {"color": "#888", "width": 28, "height": 14})

        html_parts.append(
            f'            <div class="comp" style="left:{px}px;top:{py}px;width:{style["width"]}px;height:{style["height"]}px;background:{style["color"]};">'
        )
        html_parts.append(f"                {ref}")

        pins = comp.get("pins", [])
        left_pins = pins[: len(pins) // 2]
        right_pins = pins[len(pins) // 2 :]

        for i, pin in enumerate(left_pins):
            net = pin.get("net", "")
            color = "#ff6b6b" if net in ["VCC", "GND"] else "#4ecdc4"
            html_parts.append(
                f'                <div class="comp-pin" style="left:-10px;top:{i * 12 + 5}px;background:{color};"></div>'
            )

        for i, pin in enumerate(right_pins):
            net = pin.get("net", "")
            color = "#ff6b6b" if net in ["VCC", "GND"] else "#4ecdc4"
            html_parts.append(
                f'                <div class="comp-pin" style="right:-10px;top:{i * 12 + 5}px;background:{color};"></div>'
            )

        html_parts.append("            </div>")

    # 添加图例
    html_parts.append("""            <div class="legend">
                <div class="legend-item"><div class="legend-box" style="background:#9b59b6"></div>IC</div>
                <div class="legend-item"><div class="legend-box" style="background:#e74c3c"></div>LED</div>
                <div class="legend-item"><div class="legend-box" style="background:#3498db"></div>电阻</div>
                <div class="legend-item"><div class="legend-box" style="background:#f39c12"></div>电容</div>
                <div class="legend-item"><div class="legend-box" style="background:#ff6b6b"></div>电源</div>
                <div class="legend-item"><div class="legend-box" style="background:#4ecdc4"></div>信号</div>
            </div>
        </div>
        
        <div class="net-panel">
            <div class="stats">
                <div class="stat-box"><div class="stat-num">""")
    html_parts.append(str(len(nets)))
    html_parts.append("""</div><div class="stat-label">网络</div></div>
                <div class="stat-box"><div class="stat-num">""")
    html_parts.append(str(len(data.get("components", []))))
    html_parts.append("""</div><div class="stat-label">器件</div></div>
            </div>
            <h3 style="color:#00d4ff;margin-bottom:10px;">📡 网络列表</h3>
""")

    # 添加网络列表
    for net_name, connections in nets.items():
        net_class = "power" if net_name in ["VCC", "GND"] else "signal"
        html_parts.append(f'            <div class="net-item">')
        html_parts.append(
            f'                <div class="net-header net-{net_class}">{net_name} <span style="float:right;font-size:11px;">{len(connections)}脚</span></div>'
        )
        html_parts.append('                <div class="net-pins">')
        for conn in connections:
            html_parts.append(
                f"                    <div>{conn['ref']} ({conn['value']}) Pin{conn['pin']}</div>"
            )
        html_parts.append("                </div>")
        html_parts.append("            </div>")

    html_parts.append("""        </div>
    </div>
</body>
</html>""")

    # 验证输出路径安全性
    safe_path = _validate_output_path(output_path)

    # 确保输出目录存在
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"✅ HTML 可视化已生成: {safe_path}")
    return True


def generate_uuid():
    return str(uuid.uuid4())


def create_footprint(lines, comp, x, y):
    footprint = comp.get("footprint", "Resistor_SMD:R_0603")
    reference = comp.get("reference", "R")
    value = comp.get("value", comp.get("name", "R"))

    if ":" in footprint:
        fp_lib, fp_name = footprint.split(":", 1)
    else:
        fp_lib = "Resistor_SMD"
        fp_name = footprint

    lines.append(f'\t(footprint "{footprint}"')
    lines.append('\t\t(layer "F.Cu")')
    lines.append(f'\t\t(uuid "{generate_uuid()}")')
    lines.append(f"\t\t(at {x:.2f} {y:.2f})")
    lines.append(f'\t\t(descr "{value}")')

    lines.append(f'\t\t(property "Reference" "{reference}"')
    lines.append("\t\t\t(at 0 0 0)")
    lines.append('\t\t\t(layer "F.SilkS")')
    lines.append(f'\t\t\t(uuid "{generate_uuid()}")')
    lines.append("\t\t\t(effects")
    lines.append("\t\t\t\t(font")
    lines.append("\t\t\t\t\t(size 1 1)")
    lines.append("\t\t\t\t\t(thickness 0.15)")
    lines.append("\t\t\t\t)")
    lines.append("\t\t\t)")
    lines.append("\t\t)")

    lines.append(f'\t\t(property "Value" "{value}"')
    lines.append("\t\t\t(at 0 0 0)")
    lines.append('\t\t\t(layer "F.Fab")')
    lines.append(f'\t\t\t(uuid "{generate_uuid()}")')
    lines.append("\t\t\t(effects")
    lines.append("\t\t\t\t(font")
    lines.append("\t\t\t\t\t(size 1 1)")
    lines.append("\t\t\t\t\t(thickness 0.15)")
    lines.append("\t\t\t\t)")
    lines.append("\t\t\t)")
    lines.append("\t\t)")

    if "DIP" in fp_name and "8" in fp_name:
        # KiCad DIP-8 物理引脚布局（从上方看）
        # Pin1在左下角，Pin8在右下角
        #    1  8
        #    2  7
        #    3  6
        #    4  5
        pad_positions = [
            (x - 3.81, y - 3.81, 1),  # Pin1: 左下角
            (x - 3.81, y - 1.27, 2),  # Pin2
            (x - 3.81, y + 1.27, 3),  # Pin3
            (x - 3.81, y + 3.81, 4),  # Pin4: 左上角
            (x + 3.81, y + 3.81, 5),  # Pin5: 右上角
            (x + 3.81, y + 1.27, 6),  # Pin6
            (x + 3.81, y - 1.27, 7),  # Pin7
            (x + 3.81, y - 3.81, 8),  # Pin8: 右下角
        ]
        for px, py, num in pad_positions:
            lines.append(
                f"\t\t(pad {num} thru_hole circle (at {px:.2f} {py:.2f}) (size 0.6 0.6) (drill 0.4) (layers *.Cu F.Mask F.SilkS))"
            )
    elif "LED" in fp_name:
        lines.append(
            "\t\t(pad 1 smd rect (at -0.7 0) (size 0.6 0.6) (layers F.Cu F.Paste F.Mask))"
        )
        lines.append(
            "\t\t(pad 2 smd rect (at 0.7 0) (size 0.6 0.6) (layers F.Cu F.Paste F.Mask))"
        )
    else:
        lines.append(
            "\t\t(pad 1 smd rect (at -0.8 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask))"
        )
        lines.append(
            "\t\t(pad 2 smd rect (at 0.8 0) (size 0.9 0.8) (layers F.Cu F.Paste F.Mask))"
        )

    lines.append("\t)")


def generate_pcb(data: dict, output_path: str) -> bool:
    lines = []

    lines.append("(kicad_pcb")
    lines.append("\t(version 20241229)")
    lines.append('\t(generator "pcbnew")')
    lines.append('\t(generator_version "9.0")')
    lines.append("")
    lines.append("\t(general")
    lines.append("\t\t(thickness 1.6)")
    lines.append("\t\t(legacy_teardrops no)")
    lines.append("\t)")
    lines.append("")
    lines.append('\t(paper "A4")')
    lines.append("")

    lines.append("\t(layers")
    lines.append('\t\t(0 "F.Cu" signal "top_layer")')
    lines.append('\t\t(2 "B.Cu" signal "bottom_layer")')
    lines.append('\t\t(31 "F.CrtYd" user "F.Courtyard")')
    lines.append('\t\t(35 "F.Fab" user)')
    lines.append('\t\t(5 "F.SilkS" user)')
    lines.append('\t\t(1 "F.Mask" user)')
    lines.append('\t\t(13 "F.Paste" user)')
    lines.append('\t\t(25 "Edge.Cuts" user)')
    lines.append("\t)")
    lines.append("")

    lines.append("\t(setup")
    lines.append("\t\t(pad_to_mask_clearance 0)")
    lines.append("\t\t(aux_axis_origin 0 0)")
    lines.append("\t)")
    lines.append("")

    lines.append('\t(net 0 "")')
    nets = data.get("nets", [])
    for i, net in enumerate(nets, 1):
        lines.append(f'\t(net {i} "{net.get("name", "")}")')
    lines.append("")

    components = data.get("components", [])

    for comp in components:
        pos = comp.get("position", {})
        # 使用更小的缩放因子，让PCB布局更紧凑
        # 原始坐标2000 -> 50mm (缩放0.025)
        x = pos.get("x", 0) * 0.025
        y = pos.get("y", 0) * 0.025
        create_footprint(lines, comp, x, y)
        lines.append("")

    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for comp in components:
        pos = comp.get("position", {})
        x = pos.get("x", 0) * 0.025
        y = pos.get("y", 0) * 0.025
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)

    margin = 10
    min_x = min_x - margin if min_x != float("inf") else 0
    max_x = max_x + margin if max_x != float("-inf") else 100
    min_y = min_y - margin if min_y != float("inf") else 0
    max_y = max_y + margin if max_y != float("-inf") else 80

    lines.append(
        f"\t(gr_line (start {min_x:.1f} {min_y:.1f}) (end {max_x:.1f} {min_y:.1f}) (layer Edge.Cuts) (width 0.1))"
    )
    lines.append(
        f"\t(gr_line (start {max_x:.1f} {min_y:.1f}) (end {max_x:.1f} {max_y:.1f}) (layer Edge.Cuts) (width 0.1))"
    )
    lines.append(
        f"\t(gr_line (start {max_x:.1f} {max_y:.1f}) (end {min_x:.1f} {max_y:.1f}) (layer Edge.Cuts) (width 0.1))"
    )
    lines.append(
        f"\t(gr_line (start {min_x:.1f} {max_y:.1f}) (end {min_x:.1f} {min_y:.1f}) (layer Edge.Cuts) (width 0.1))"
    )
    lines.append("")

    net_map = {net.get("name", ""): i + 1 for i, net in enumerate(nets)}
    net_pads = {net.get("name", ""): [] for net in nets}

    for comp in components:
        ref = comp.get("reference", "")
        pos = comp.get("position", {})
        x = pos.get("x", 0) * 0.025
        y = pos.get("y", 0) * 0.025
        footprint = comp.get("footprint", "")
        pins = comp.get("pins", [])

        if "DIP" in footprint and "8" in footprint:
            # KiCad DIP-8 物理引脚布局（从上方看）
            # 左边引脚（1-4，从下到上）| 右边引脚（5-8，从上到下）
            # Pin1在左下角，Pin8在右下角
            #    1  8
            #    2  7
            #    3  6
            #    4  5
            pad_positions = [
                (x - 3.81, y - 3.81, 1),  # Pin1: 左下角 (GND)
                (x - 3.81, y - 1.27, 2),  # Pin2: 左边偏下
                (x - 3.81, y + 1.27, 3),  # Pin3: 左边偏上
                (x - 3.81, y + 3.81, 4),  # Pin4: 左上角
                (x + 3.81, y + 3.81, 5),  # Pin5: 右上角  <-- 修正！
                (x + 3.81, y + 1.27, 6),  # Pin6: 右边偏上
                (x + 3.81, y - 1.27, 7),  # Pin7: 右边偏下
                (x + 3.81, y - 3.81, 8),  # Pin8: 右下角  <-- 修正！
            ]
            for pad in pad_positions:
                pad_num = pad[2]
                for pin in pins:
                    if str(pin.get("number", "")) == str(pad_num):
                        net_name = pin.get("net", "")
                        if net_name and net_name in net_pads:
                            net_pads[net_name].append((ref, pad_num, pad[0], pad[1]))
                        break
        else:
            pad_positions = [(x - 0.8, y, 1), (x + 0.8, y, 2)]
            for i, pin in enumerate(pins):
                if i < len(pad_positions):
                    net_name = pin.get("net", "")
                    if net_name and net_name in net_pads:
                        p = pad_positions[i]
                        net_pads[net_name].append(
                            (ref, pin.get("number", ""), p[0], p[1])
                        )

    for net_name, pads in net_pads.items():
        if net_name not in net_map or len(pads) < 2:
            continue
        net_num = net_map[net_name]

        for i in range(len(pads) - 1):
            p1, p2 = pads[i], pads[i + 1]
            lines.append(
                f"\t(segment (start {p1[2]:.2f} {p1[3]:.2f}) (end {p2[2]:.2f} {p2[3]:.2f}) (width 0.25) (layer F.Cu) (net {net_num}))"
            )

    lines.append("")

    lines.append('\t(net_class "Default" "This is the default net class"')
    lines.append("\t\t(clearance 0.254)")
    lines.append("\t\t(trace_width 0.254)")
    lines.append('\t\t(add_net "")')
    for net in nets:
        lines.append(f'\t\t(add_net "{net.get("name", "")}")')
    lines.append("\t)")
    lines.append(")")

    # 验证输出路径安全性
    safe_path = _validate_output_path(output_path)

    # 确保输出目录存在
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    print(f"✅ PCB 文件已生成: {safe_path}")
    return True


def main():
    print("=" * 50)
    print("电路 → HTML 可视化 + KiCad 文件")
    print("=" * 50)

    json_path = Path(INPUT_JSON)
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n📊 电路数据:")
    print(f"   - 器件: {len(data.get('components', []))} 个")
    print(f"   - 网络: {len(data.get('nets', []))} 个")

    print(f"\n🔄 步骤1: 生成 HTML 可视化...")
    generate_html_viewer(data, HTML_OUTPUT)

    print(f"\n🔄 步骤2: 生成 KiCad PCB...")
    pcb_path = OUTPUT_DIR / "circuit.kicad_pcb"
    generate_pcb(data, str(pcb_path))

    print("\n" + "=" * 50)
    print("✅ 完成! 生成的文件:")
    print(f"   📄 HTML: {HTML_OUTPUT}")
    print(f"   🟢 PCB:  {pcb_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()

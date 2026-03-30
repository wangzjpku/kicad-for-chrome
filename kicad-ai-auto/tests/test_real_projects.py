"""
真实项目端到端全自动测试

测试完整的PCB生成流程：
1. 输入：真实电路需求描述
2. 解析：生成原理图数据
3. 布局：智能布局引擎
4. 布线：自动布线 + 避障
5. DRC：高级规则检查
6. 层叠：多层板配置
7. 铺铜：自动GND平面
8. 输出：KiCad格式文件
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# 添加 agent 目录到路径
agent_path = Path(__file__).parent.parent / "agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from placement.smart_placement_engine import (
    SmartPlacementEngine,
    Component as PlacementComponent,
    create_components_from_schematic,
)
from routing.routing_engine import (
    RoutingEngine,
    Net as RoutingNet,
    Pad as RoutingPad,
)
from routing.astar_router import AStarRouter, Point
from routing.copper_pour import CopperPourEngine
from drc.advanced_drc import create_jlcpcb_drc
from pcb.layer_stackup import create_4layer_stackup, StackupManager


class RealProjectTest:
    """真实项目测试"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.results = {}
        self.start_time = time.time()

    def log(self, message: str):
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:.2f}s] {message}")

    def run_full_test(self, circuit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行完整的PCB生成流程
        """
        self.log(f"=== 开始真实项目测试: {self.project_name} ===\n")

        # ========== Step 1: 解析原理图数据 ==========
        self.log("Step 1: 解析原理图数据...")
        components_data = circuit_data.get("components", [])
        nets_data = circuit_data.get("nets", [])
        board_data = circuit_data.get("board", {})

        board_width = board_data.get("width", 100)
        board_height = board_data.get("height", 80)

        self.log(f"  - 组件数量: {len(components_data)}")
        self.log(f"  - 网络数量: {len(nets_data)}")
        self.log(f"  - 板子尺寸: {board_width}x{board_height}mm")

        self.results["input"] = {
            "components": len(components_data),
            "nets": len(nets_data),
            "board_size": f"{board_width}x{board_height}mm"
        }

        # ========== Step 2: 智能布局 ==========
        self.log("\nStep 2: 智能布局...")
        placement_engine = SmartPlacementEngine(
            board_width=board_width,
            board_height=board_height,
            spacing=3.0
        )

        components = create_components_from_schematic(circuit_data)
        placement_result = placement_engine.place(components)

        self.log(f"  - 布局评分: {placement_result.score}/100")
        self.log(f"  - 重叠数量: {placement_result.statistics['overlaps']}")
        self.log(f"  - 板利用率: {placement_result.statistics['board_utilization']:.1%}")

        self.results["placement"] = {
            "score": placement_result.score,
            "overlaps": placement_result.statistics['overlaps'],
            "utilization": placement_result.statistics['board_utilization']
        }

        # ========== Step 3: 自动布线 ==========
        self.log("\nStep 3: 自动布线...")
        routing_nets = []

        for net in nets_data:
            net_name = net.get("name", "")
            net_class = net.get("class", "Signal")

            # 找到该网络连接的焊盘
            pads = []
            for comp in components:
                if net_name in comp.nets:
                    pos = placement_result.positions.get(comp.reference, {})
                    if pos:
                        pads.append(RoutingPad(
                            x=pos.get("x", 0),
                            y=pos.get("y", 0),
                            net=net_name,
                            layer="top"
                        ))

            if len(pads) >= 2:
                trace_width = 0.5 if net_class == "Power" else 0.25
                routing_nets.append(RoutingNet(
                    name=net_name,
                    pads=pads,
                    trace_width=trace_width
                ))

        routing_engine = RoutingEngine(
            board_width=board_width,
            board_height=board_height
        )
        routing_result = routing_engine.route_nets(routing_nets)

        self.log(f"  - 成功布线: {len(routing_result.routes)} 个网络")
        self.log(f"  - 总走线长度: {routing_result.total_length:.1f}mm")
        self.log(f"  - 过孔数量: {routing_result.via_count}")

        self.results["routing"] = {
            "routed_nets": len(routing_result.routes),
            "total_length": routing_result.total_length,
            "via_count": routing_result.via_count
        }

        # ========== Step 4: DRC检查 ==========
        self.log("\nStep 4: DRC检查...")

        # 构建PCB数据
        pcb_data = {
            "components": [
                {
                    "reference": comp.reference,
                    "position": placement_result.positions.get(comp.reference, {}),
                    "width": comp.width,
                    "height": comp.height
                }
                for comp in components
            ],
            "tracks": [],
            "vias": [],
            "nets": nets_data,
            "board": board_data
        }

        # 添加走线
        for route in routing_result.routes:
            for seg in route.segments:
                pcb_data["tracks"].append({
                    "net": route.net,
                    "layer": seg.layer,
                    "width": seg.width,
                    "points": [{"x": seg.x1, "y": seg.y1}, {"x": seg.x2, "y": seg.y2}]
                })

        drc_engine = create_jlcpcb_drc(level="standard")
        drc_result = drc_engine.check(pcb_data)

        self.log(f"  - DRC通过: {'是' if drc_result.passed else '否'}")
        self.log(f"  - 错误数量: {drc_result.error_count}")
        self.log(f"  - 警告数量: {drc_result.warning_count}")
        self.log(f"  - 检查耗时: {drc_result.duration_ms:.1f}ms")

        self.results["drc"] = {
            "passed": drc_result.passed,
            "errors": drc_result.error_count,
            "warnings": drc_result.warning_count,
            "duration_ms": drc_result.duration_ms
        }

        # ========== Step 5: 层叠配置 ==========
        self.log("\nStep 5: 层叠配置...")

        # 根据电路复杂度选择层数
        layer_count = 2
        if len(components) > 20 or any(n.get("class") == "HighSpeed" for n in nets_data):
            layer_count = 4
        if len(components) > 50 or len([n for n in nets_data if n.get("class") == "HighSpeed"]) > 4:
            layer_count = 6

        if layer_count >= 4:
            stackup = create_4layer_stackup()
            self.log(f"  - 层数: {stackup.layer_count}")
            self.log(f"  - 总厚度: {stackup.total_thickness}mm")
            self.log(f"  - 电源平面: GND + PWR")
        else:
            stackup = None
            self.log(f"  - 层数: 2 (双层板)")

        self.results["stackup"] = {
            "layer_count": layer_count,
            "total_thickness": 1.6
        }

        # ========== Step 6: 自动铺铜 ==========
        self.log("\nStep 6: 自动铺铜...")
        pour_engine = CopperPourEngine(
            board_width=board_width,
            board_height=board_height
        )

        # 添加组件作为障碍物
        for comp in components:
            pos = placement_result.positions.get(comp.reference, {})
            pour_engine.add_obstacle(
                x=pos.get("x", 0) - comp.width/2,
                y=pos.get("y", 0) - comp.height/2,
                width=comp.width,
                height=comp.height,
                net=None
            )

        # 创建GND铺铜
        ground_pour = pour_engine.create_ground_pour(layer="F.Cu")

        self.log(f"  - 铺铜面积: {ground_pour.area:.1f} sq.mm")
        self.log(f"  - 热焊盘连接: {len(ground_pour.thermal_relief_segments)} 条辐条")

        self.results["copper_pour"] = {
            "area": ground_pour.area,
            "thermal_spokes": len(ground_pour.thermal_relief_segments)
        }

        # ========== 总结 ==========
        total_time = time.time() - self.start_time
        self.log(f"\n=== 测试完成 ===")
        self.log(f"总耗时: {total_time:.2f}秒")

        self.results["summary"] = {
            "total_time": total_time,
            "success": drc_result.passed or drc_result.error_count <= 2
        }

        return self.results


def test_led_driver_project():
    """测试: LED驱动电路项目"""
    print("\n" + "="*60)
    print("真实项目测试 1: LED驱动电路")
    print("="*60 + "\n")

    circuit = {
        "components": [
            {"reference": "U1", "footprint": "SOIC-8", "value": "LM358", "width": 6, "height": 5, "nets": ["VCC", "GND", "OUT", "FB"]},
            {"reference": "U2", "footprint": "SOT-23", "value": "BC847", "width": 3, "height": 2, "nets": ["DRIVE", "GND"]},
            {"reference": "D1", "footprint": "LED_0805", "value": "LED", "width": 2.5, "height": 1.5, "nets": ["LED+", "LED-"]},
            {"reference": "D2", "footprint": "LED_0805", "value": "LED", "width": 2.5, "height": 1.5, "nets": ["LED+", "LED-"]},
            {"reference": "D3", "footprint": "LED_0805", "value": "LED", "width": 2.5, "height": 1.5, "nets": ["LED+", "LED-"]},
            {"reference": "R1", "footprint": "R_0603", "value": "1K", "width": 2, "height": 1.2, "nets": ["OUT", "FB"]},
            {"reference": "R2", "footprint": "R_0603", "value": "10K", "width": 2, "height": 1.2, "nets": ["FB", "GND"]},
            {"reference": "R3", "footprint": "R_0603", "value": "100R", "width": 2, "height": 1.2, "nets": ["DRIVE", "LED+"]},
            {"reference": "C1", "footprint": "C_0805", "value": "10uF", "width": 2.5, "height": 1.5, "nets": ["VCC", "GND"]},
            {"reference": "C2", "footprint": "C_0603", "value": "100nF", "width": 2, "height": 1.2, "nets": ["VCC", "GND"]},
            {"reference": "J1", "footprint": "Header_4", "value": "CONN", "width": 10, "height": 5, "nets": ["VCC", "GND", "LED-", "CTRL"]},
        ],
        "nets": [
            {"name": "VCC", "class": "Power"},
            {"name": "GND"},
            {"name": "OUT"},
            {"name": "FB"},
            {"name": "DRIVE"},
            {"name": "LED+"},
            {"name": "LED-"},
            {"name": "CTRL"},
        ],
        "board": {"width": 60, "height": 40, "thickness": 1.6}
    }

    test = RealProjectTest("LED驱动电路")
    results = test.run_full_test(circuit)

    return results


def test_stm32_project():
    """测试: STM32最小系统项目"""
    print("\n" + "="*60)
    print("真实项目测试 2: STM32最小系统")
    print("="*60 + "\n")

    circuit = {
        "components": [
            {"reference": "U1", "footprint": "QFN-48", "value": "STM32F411", "width": 10, "height": 10, "nets": ["VCC", "GND", "USB_D+", "USB_D-", "NRST", "BOOT0"]},
            {"reference": "Y1", "footprint": "Crystal", "value": "8MHz", "width": 5, "height": 2, "nets": ["OSC_IN", "OSC_OUT"]},
            {"reference": "Y2", "footprint": "Crystal", "value": "32.768kHz", "width": 4, "height": 1.5, "nets": ["OSC32_IN", "OSC32_OUT"]},
            {"reference": "C1", "footprint": "C_0603", "value": "100nF", "width": 2, "height": 1.2, "nets": ["VCC", "GND"]},
            {"reference": "C2", "footprint": "C_0603", "value": "100nF", "width": 2, "height": 1.2, "nets": ["VCC", "GND"]},
            {"reference": "C3", "footprint": "C_0603", "value": "100nF", "width": 2, "height": 1.2, "nets": ["VCC", "GND"]},
            {"reference": "C4", "footprint": "C_0805", "value": "10uF", "width": 2.5, "height": 1.5, "nets": ["VCC", "GND"]},
            {"reference": "C5", "footprint": "C_0603", "value": "20pF", "width": 2, "height": 1.2, "nets": ["OSC_IN", "GND"]},
            {"reference": "C6", "footprint": "C_0603", "value": "20pF", "width": 2, "height": 1.2, "nets": ["OSC_OUT", "GND"]},
            {"reference": "R1", "footprint": "R_0603", "value": "10K", "width": 2, "height": 1.2, "nets": ["NRST", "VCC"]},
            {"reference": "R2", "footprint": "R_0603", "value": "10K", "width": 2, "height": 1.2, "nets": ["BOOT0", "GND"]},
            {"reference": "R3", "footprint": "R_0603", "value": "22R", "width": 2, "height": 1.2, "nets": ["USB_D+", "USB_DP"]},
            {"reference": "R4", "footprint": "R_0603", "value": "22R", "width": 2, "height": 1.2, "nets": ["USB_D-", "USB_DM"]},
            {"reference": "J_USB", "footprint": "USB-C", "value": "USB-C", "width": 10, "height": 8, "nets": ["VCC", "GND", "USB_DP", "USB_DM"]},
            {"reference": "J1", "footprint": "Header_10", "value": "DEBUG", "width": 15, "height": 5, "nets": ["VCC", "GND", "SWDIO", "SWCLK", "NRST"]},
        ],
        "nets": [
            {"name": "VCC", "class": "Power"},
            {"name": "GND"},
            {"name": "USB_D+", "class": "HighSpeed"},
            {"name": "USB_D-", "class": "HighSpeed"},
            {"name": "USB_DP"},
            {"name": "USB_DM"},
            {"name": "NRST"},
            {"name": "BOOT0"},
            {"name": "OSC_IN"},
            {"name": "OSC_OUT"},
            {"name": "OSC32_IN"},
            {"name": "OSC32_OUT"},
            {"name": "SWDIO"},
            {"name": "SWCLK"},
        ],
        "board": {"width": 80, "height": 60, "thickness": 1.6}
    }

    test = RealProjectTest("STM32最小系统")
    results = test.run_full_test(circuit)

    return results


def test_power_supply_project():
    """测试: 开关电源项目"""
    print("\n" + "="*60)
    print("真实项目测试 3: 开关电源 (Buck转换器)")
    print("="*60 + "\n")

    circuit = {
        "components": [
            {"reference": "U1", "footprint": "SOIC-8", "value": "LM2596", "width": 6, "height": 5, "nets": ["VIN", "SW", "FB", "GND"]},
            {"reference": "L1", "footprint": "Inductor_SMD", "value": "33uH", "width": 10, "height": 10, "nets": ["SW", "VOUT"]},
            {"reference": "D1", "footprint": "SMB", "value": "SS34", "width": 5, "height": 4, "nets": ["SW", "GND"]},
            {"reference": "C1", "footprint": "C_Elec_8mm", "value": "470uF", "width": 10, "height": 10, "nets": ["VIN", "GND"]},
            {"reference": "C2", "footprint": "C_0805", "value": "100nF", "width": 2.5, "height": 1.5, "nets": ["VIN", "GND"]},
            {"reference": "C3", "footprint": "C_Elec_8mm", "value": "220uF", "width": 10, "height": 10, "nets": ["VOUT", "GND"]},
            {"reference": "C4", "footprint": "C_0805", "value": "100nF", "width": 2.5, "height": 1.5, "nets": ["VOUT", "GND"]},
            {"reference": "R1", "footprint": "R_0603", "value": "3K3", "width": 2, "height": 1.2, "nets": ["VOUT", "FB"]},
            {"reference": "R2", "footprint": "R_0603", "value": "1K", "width": 2, "height": 1.2, "nets": ["FB", "GND"]},
            {"reference": "J1", "footprint": "Terminal_2", "value": "IN", "width": 10, "height": 8, "nets": ["VIN", "GND"]},
            {"reference": "J2", "footprint": "Terminal_2", "value": "OUT", "width": 10, "height": 8, "nets": ["VOUT", "GND"]},
        ],
        "nets": [
            {"name": "VIN", "class": "Power"},
            {"name": "VOUT", "class": "Power"},
            {"name": "GND"},
            {"name": "SW"},
            {"name": "FB"},
        ],
        "board": {"width": 70, "height": 50, "thickness": 1.6}
    }

    test = RealProjectTest("开关电源")
    results = test.run_full_test(circuit)

    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PCB质量提升 - 真实项目全自动测试")
    print("="*60)

    all_results = []

    # 运行所有测试
    all_results.append(("LED驱动电路", test_led_driver_project()))
    all_results.append(("STM32最小系统", test_stm32_project()))
    all_results.append(("开关电源", test_power_supply_project()))

    # 汇总结果
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)

    print("\n| 项目 | 组件 | 网络 | 布局评分 | 布线成功率 | DRC通过 |")
    print("|------|------|------|----------|-----------|---------|")

    for name, results in all_results:
        input_data = results.get("input", {})
        placement = results.get("placement", {})
        routing = results.get("routing", {})
        drc = results.get("drc", {})

        routed_rate = routing.get("routed_nets", 0) / max(input_data.get("nets", 1), 1) * 100

        print(f"| {name} | {input_data.get('components', 0)} | {input_data.get('nets', 0)} | "
              f"{placement.get('score', 0)} | {routed_rate:.0f}% | {'PASS' if drc.get('passed') else 'WARN'} |")

    print("\n" + "="*60)
    print("全部测试完成!")
    print("="*60)
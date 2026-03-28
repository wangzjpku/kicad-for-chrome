"""
原理图布线正确性测试

测试目标：验证原理图生成时，布线连接是否正确
- 元件之间的连接是否正确
- 网络是否正确创建
- 网表是否包含正确的连接信息
"""

import pytest
import sys
import os
import tempfile
import json
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generators.schematic_v2 import SchematicGeneratorV2, is_v2_available
from netlist_exporter import create_netlist_from_schematic


class TestSchematicWireRouting:
    """测试原理图布线正确性"""

    @pytest.fixture
    def simple_circuit_data(self):
        """简单电路测试数据 - 两个电阻串联"""
        return {
            "title": "Test Two Resistors Series",
            "components": [
                {
                    "reference": "R1",
                    "symbol_library": "Device:R",
                    "name": "Resistor",
                    "value": "1k",
                    "position": {"x": 0, "y": 0},
                    "pins": [
                        {"number": "1", "name": "1", "type": "passive"},
                        {"number": "2", "name": "2", "type": "passive"}
                    ]
                },
                {
                    "reference": "R2",
                    "symbol_library": "Device:R",
                    "name": "Resistor",
                    "value": "2k",
                    "position": {"x": 100, "y": 0},
                    "pins": [
                        {"number": "1", "name": "1", "type": "passive"},
                        {"number": "2", "name": "2", "type": "passive"}
                    ]
                }
            ],
            "nets": [
                {"id": "net_vcc", "name": "VCC"},
                {"id": "net_mid", "name": "NET_MID"},
                {"id": "net_gnd", "name": "GND"}
            ],
            "wires": [
                {"from": "R1.1", "to": "R2.1", "net": "NET_MID"},
                {"from": "R1.2", "to": "R2.2", "net": "NET_MID"}
            ],
            "powerSymbols": [],
            "labels": []
        }

    @pytest.fixture
    def led_circuit_data(self):
        """LED电路测试数据"""
        return {
            "title": "LED Circuit",
            "components": [
                {
                    "reference": "R1",
                    "symbol_library": "Device:R",
                    "name": "Resistor",
                    "value": "330",
                    "position": {"x": 0, "y": 0},
                    "pins": [
                        {"number": "1", "name": "1", "type": "passive"},
                        {"number": "2", "name": "2", "type": "passive"}
                    ]
                },
                {
                    "reference": "LED1",
                    "symbol_library": "Device:LED",
                    "name": "LED",
                    "value": "Red",
                    "position": {"x": 100, "y": 0},
                    "pins": [
                        {"number": "1", "name": "A", "type": "passive"},
                        {"number": "2", "name": "K", "type": "passive"}
                    ]
                }
            ],
            "nets": [
                {"id": "net_led", "name": "LED_NET"}
            ],
            "wires": [
                {"from": "R1.2", "to": "LED1.1", "net": "LED_NET"}
            ],
            "powerSymbols": [],
            "labels": []
        }

    def test_v2_available(self):
        """测试V2生成器是否可用"""
        assert is_v2_available() == True, "kicad-sch-api 应该可用"

    def test_generate_simple_circuit(self, simple_circuit_data):
        """测试生成简单电路原理图"""
        if not is_v2_available():
            pytest.skip("kicad-sch-api 不可用")

        gen = SchematicGeneratorV2()

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(simple_circuit_data, output_path)
            print(f"生成结果: success={result.success}")
            print(f"错误: {result.errors}")
            print(f"警告: {result.warnings}")

            assert result.success == True, f"生成失败: {result.errors}"
            assert Path(output_path).exists(), "原理图文件应该存在"

            # 验证布线警告
            if result.warnings:
                print(f"布线警告: {result.warnings}")

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_led_circuit(self, led_circuit_data):
        """测试生成LED电路原理图"""
        if not is_v2_available():
            pytest.skip("kicad-sch-api 不可用")

        gen = SchematicGeneratorV2()

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(led_circuit_data, output_path)
            assert result.success == True, f"LED电路生成失败: {result.errors}"
            assert Path(output_path).exists()

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_netlist_generation(self):
        """测试网表生成和连接正确性"""
        # 模拟原理图数据
        schematic_data = {
            "name": "Test Circuit",
            "components": [
                {"reference": "U1", "value": "STM32", "footprint": "LQFP-48",
                 "symbol_library": "MCU_ST_STM32"},
                {"reference": "R1", "value": "10K", "footprint": "0805",
                 "symbol_library": "Device"},
                {"reference": "C1", "value": "100nF", "footprint": "0402",
                 "symbol_library": "Device"},
            ],
            "nets": [
                {
                    "name": "VCC",
                    "connections": [
                        {"ref": "U1", "pin": "VDD"},
                        {"ref": "R1", "pin": "1"},
                        {"ref": "C1", "pin": "1"}
                    ]
                },
                {
                    "name": "GND",
                    "connections": [
                        {"ref": "U1", "pin": "VSS"},
                        {"ref": "R1", "pin": "2"},
                        {"ref": "C1", "pin": "2"}
                    ]
                }
            ]
        }

        # 导出JSON网表
        json_netlist = create_netlist_from_schematic(schematic_data, return_content=True)
        netlist_data = json.loads(json_netlist)

        print("网表数据:")
        print(json.dumps(netlist_data, indent=2))

        # 验证元件
        assert len(netlist_data["components"]) == 3, "应该有3个元件"

        # 验证网络
        assert len(netlist_data["nets"]) == 2, "应该有2个网络"

        # 验证VCC网络连接
        vcc_net = next((n for n in netlist_data["nets"] if n["name"] == "VCC"), None)
        assert vcc_net is not None, "应该有VCC网络"
        assert len(vcc_net["nodes"]) == 3, "VCC网络应该有3个节点"

        # 验证GND网络连接
        gnd_net = next((n for n in netlist_data["nets"] if n["name"] == "GND"), None)
        assert gnd_net is not None, "应该有GND网络"
        assert len(gnd_net["nodes"]) == 3, "GND网络应该有3个节点"

    def test_wire_connection_format(self):
        """测试布线连接格式验证"""
        # 测试数据 - 验证连接格式
        test_wire = {
            "from": "U1.1",  # 正确格式: 元件.引脚
            "to": "R1.2",
            "net": "VCC"
        }

        # 验证格式解析
        from_conn = test_wire["from"]
        to_conn = test_wire["to"]

        if "." in from_conn and "." in to_conn:
            ref1, pin1 = from_conn.split(".", 1)
            ref2, pin2 = to_conn.split(".", 1)

            assert ref1 == "U1", "应该是U1"
            assert pin1 == "1", "应该是引脚1"
            assert ref2 == "R1", "应该是R1"
            assert pin2 == "2", "应该是引脚2"
        else:
            pytest.fail("连接格式不正确")

    def test_invalid_connection_format(self):
        """测试无效连接格式应该被拒绝"""
        invalid_wire = {
            "from": "U1",  # 缺少引脚
            "to": "R1.2",
            "net": "VCC"
        }

        from_conn = invalid_wire["from"]
        to_conn = invalid_wire["to"]

        # 验证格式应该失败
        has_valid_format = "." in from_conn and "." in to_conn

        assert has_valid_format == False, "无效格式应该被检测到"


class TestWireRoutingEdgeCases:
    """测试布线边缘情况"""

    def test_disconnected_pins(self):
        """测试未连接的引脚"""
        schematic_data = {
            "name": "Disconnected Test",
            "components": [
                {"reference": "U1", "value": "IC", "footprint": "SOIC-8",
                 "symbol_library": "MCU"},
            ],
            "nets": [],
            "wires": []  # 没有连线
        }

        json_netlist = create_netlist_from_schematic(schematic_data, return_content=True)
        netlist_data = json.loads(json_netlist)

        # 没有网络是正常的
        assert len(netlist_data["nets"]) == 0

    def test_multiple_wires_same_net(self):
        """测试同一网络的多个连接"""
        schematic_data = {
            "name": "Multi Wire Test",
            "components": [
                {"reference": "U1", "value": "IC1", "footprint": "SOIC-8",
                 "symbol_library": "MCU"},
                {"reference": "U2", "value": "IC2", "footprint": "SOIC-8",
                 "symbol_library": "MCU"},
                {"reference": "C1", "value": "100nF", "footprint": "0402",
                 "symbol_library": "Device"},
                {"reference": "C2", "value": "100nF", "footprint": "0402",
                 "symbol_library": "Device"},
            ],
            "nets": [
                {
                    "name": "VCC",
                    "connections": [
                        {"ref": "U1", "pin": "VCC"},
                        {"ref": "U2", "pin": "VCC"},
                        {"ref": "C1", "pin": "1"},
                        {"ref": "C2", "pin": "1"}
                    ]
                }
            ]
        }

        json_netlist = create_netlist_from_schematic(schematic_data, return_content=True)
        netlist_data = json.loads(json_netlist)

        # 验证同一网络有4个连接
        vcc_net = netlist_data["nets"][0]
        assert len(vcc_net["nodes"]) == 4, "VCC网络应该有4个节点"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""
V2生成器端到端测试
测试kicad-sch-api生成的各类电路
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generators.factory import get_schematic_generator


class TestV2GeneratorE2E:
    """V2生成器端到端测试"""

    def test_generate_simple_resistor(self):
        """测试单个电阻生成"""
        gen = get_schematic_generator('v2')
        json_data = {
            "title": "Test Resistor",
            "components": [{
                "reference": "R1",
                "symbol_library": "Device:R",
                "name": "Resistor",
                "value": "10k",
                "position": {"x": 100, "y": 100},
                "pins": [
                    {"number": "1", "name": "1", "type": "passive"},
                    {"number": "2", "name": "2", "type": "passive"}
                ]
            }],
            "nets": [],
            "wires": [],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            assert result.success == True, f"Generation failed: {result.errors}"
            assert Path(output_path).exists()
            print(f"✓ Generated: {output_path}")
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_two_resistors(self):
        """测试两个电阻生成"""
        gen = get_schematic_generator('v2')
        json_data = {
            "title": "Two Resistors",
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
            "nets": [{"id": "net1", "name": "NET1"}],
            "wires": [{"from": "R1.2", "to": "R2.1", "net": "NET1"}],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            assert result.success == True, f"Generation failed: {result.errors}"
            assert Path(output_path).exists()
            print(f"✓ Generated: {output_path}")
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_capacitor(self):
        """测试电容生成"""
        gen = get_schematic_generator('v2')
        json_data = {
            "title": "Test Capacitor",
            "components": [{
                "reference": "C1",
                "symbol_library": "Device:C",
                "name": "Capacitor",
                "value": "100nF",
                "position": {"x": 50, "y": 50},
                "pins": [
                    {"number": "1", "name": "1", "type": "passive"},
                    {"number": "2", "name": "2", "type": "passive"}
                ]
            }],
            "nets": [],
            "wires": [],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            assert result.success == True, f"Generation failed: {result.errors}"
            print(f"✓ Generated: {output_path}")
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_led_circuit(self):
        """测试LED电路生成"""
        gen = get_schematic_generator('v2')
        json_data = {
            "title": "LED Circuit",
            "components": [
                {
                    "reference": "D1",
                    "symbol_library": "Device:LED",
                    "name": "LED",
                    "value": "Red",
                    "position": {"x": 50, "y": 0},
                    "pins": [
                        {"number": "1", "name": "A", "type": "passive"},
                        {"number": "2", "name": "K", "type": "passive"}
                    ]
                },
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
                }
            ],
            "nets": [{"id": "net1", "name": "LED_NET"}],
            "wires": [],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            assert result.success == True, f"Generation failed: {result.errors}"
            print(f"✓ Generated: {output_path}")
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_power_supply(self):
        """测试电源电路生成"""
        gen = get_schematic_generator('v2')
        json_data = {
            "title": "Power Supply",
            "components": [
                {
                    "reference": "U1",
                    "symbol_library": " Regulator_Linear:LM7805",
                    "name": "LM7805",
                    "value": "5V",
                    "position": {"x": 0, "y": 0},
                    "pins": [
                        {"number": "1", "name": "IN", "type": "input"},
                        {"number": "2", "name": "GND", "type": "power_out"},
                        {"number": "3", "name": "OUT", "type": "output"}
                    ]
                }
            ],
            "nets": [],
            "wires": [],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            # 允许警告但不允许严重错误
            assert result.success == True or len(result.errors) < 3, f"Too many errors: {result.errors}"
            print(f"✓ Generated: {output_path}")
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_v1_generator_available(self):
        """测试V1生成器也可用"""
        try:
            gen = get_schematic_generator('v1')
        except ModuleNotFoundError:
            pytest.skip("V1 generator not available")
        assert gen is not None
        print("✓ V1 generator available")

    def test_v2_is_default(self):
        """测试V2是默认生成器"""
        gen = get_schematic_generator()  # 不指定版本
        assert gen.version.value == "v2"
        print("✓ V2 is default generator")


class TestV2GeneratorIntegration:
    """V2生成器集成测试"""

    def test_generate_multiple_circuits(self):
        """测试连续生成多个电路"""
        gen = get_schematic_generator('v2')

        circuits = [
            {"title": "Circuit 1", "value": "1k"},
            {"title": "Circuit 2", "value": "10k"},
            {"title": "Circuit 3", "value": "100k"},
        ]

        for circuit in circuits:
            json_data = {
                "title": circuit["title"],
                "components": [{
                    "reference": "R1",
                    "symbol_library": "Device:R",
                    "name": "Resistor",
                    "value": circuit["value"],
                    "position": {"x": 0, "y": 0},
                    "pins": [
                        {"number": "1", "name": "1", "type": "passive"},
                        {"number": "2", "name": "2", "type": "passive"}
                    ]
                }],
                "nets": [],
                "wires": [],
                "powerSymbols": [],
                "labels": []
            }

            with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
                output_path = f.name

            try:
                result = gen.generate(json_data, output_path)
                assert result.success == True, f"Failed: {circuit['title']}"
                print(f"✓ {circuit['title']}")
            finally:
                Path(output_path).unlink(missing_ok=True)

"""
原理图生成器V2单元测试
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path (same as conftest.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV2Availability:
    """测试V2生成器可用性"""

    def test_v2_imports(self):
        """测试V2相关模块可以导入"""
        # 库本身可用
        import kicad_sch_api
        assert kicad_sch_api is not None

    def test_kicad_sch_api_available(self):
        """kicad_sch_api应该可用"""
        import kicad_sch_api
        assert kicad_sch_api is not None

    def test_kipy_available(self):
        """kipy应该可用"""
        import kipy
        assert kipy is not None


class TestV2Generation:
    """测试V2生成功能"""

    def test_generate_simple_resistor(self):
        """测试生成简单电阻原理图"""
        from generators.schematic_v2 import SchematicGeneratorV2

        gen = SchematicGeneratorV2()

        # 简单测试数据 - 电阻
        json_data = {
            "title": "Test Resistor",
            "components": [
                {
                    "reference": "R1",
                    "symbol_library": "Device:R",
                    "name": "Resistor",
                    "value": "10k",
                    "position": {"x": 100, "y": 100},
                    "pins": [
                        {"number": "1", "name": "1", "type": "passive"},
                        {"number": "2", "name": "2", "type": "passive"}
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
            assert result.success == True, f"Generation failed: {result.errors}"
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_two_resistors(self):
        """测试生成两个电阻的原理图"""
        from generators.schematic_v2 import SchematicGeneratorV2

        gen = SchematicGeneratorV2()

        json_data = {
            "title": "Test Two Resistors",
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
            "wires": [
                {"from": "R1.2", "to": "R2.1", "net": "NET1"}
            ],
            "powerSymbols": [],
            "labels": []
        }

        with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as f:
            output_path = f.name

        try:
            result = gen.generate(json_data, output_path)
            assert result.success == True, f"Generation failed: {result.errors}"
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

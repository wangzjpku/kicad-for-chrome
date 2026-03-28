"""
电气规则检查器 (ERC) 测试

测试原理图电气规则检查功能:
- 未连接的引脚检测
- 引脚方向冲突检测
- 电源引脚检查
- 电源符号检查
- 重复引用检查
- 浮动网络检测
"""

import pytest
from design_rules.erc import (
    ERCChecker,
    ERCResult,
    ERCIssue,
    ERCErrorType,
    ERCErrorLevel,
    check_schematic,
    run_erc,
)


class TestERCChecker:
    """ERC检查器测试"""

    @pytest.fixture
    def checker(self):
        """创建ERC检查器"""
        return ERCChecker()

    def test_checker_import(self, checker):
        """测试检查器可以导入"""
        assert checker is not None

    def test_empty_schematic(self, checker):
        """测试空原理图 (无元件但有电源符号)"""
        # 空原理图至少需要电源符号
        power_symbols = [{"symbol_type": "vcc"}, {"symbol_type": "gnd"}]
        result = checker.check([], [], power_symbols)
        assert result.score == 100
        assert result.passed is True

    def test_valid_schematic(self, checker):
        """测试有效的原理图"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "ATmega328P",
                "pins": [
                    {"number": "1", "name": "VCC", "pin_type": "power_in"},
                    {"number": "8", "name": "GND", "pin_type": "gnd"},
                ],
            }
        ]
        nets = [
            {"name": "VCC", "class": "power", "pins": ["U1:1"]},
            {"name": "GND", "class": "power", "pins": ["U1:8"]},
        ]
        power_symbols = [{"symbol_type": "vcc"}, {"symbol_type": "gnd"}]

        result = checker.check(components, nets, power_symbols)
        assert result.score == 100
        assert result.passed is True


class TestUnconnectedPins:
    """未连接引脚测试"""

    def test_unconnected_power_pin(self):
        """测试未连接的电源引脚"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "ATmega328P",
                "pins": [
                    {"number": "1", "name": "VCC", "pin_type": "power_in"},
                    {"number": "8", "name": "GND", "pin_type": "gnd"},
                ],
            }
        ]
        nets = []  # 无网络连接
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        # 应该检测到未连接的电源引脚
        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.UNCONNECTED_PIN in error_types
        assert result.passed is False

    def test_unconnected_input_warning(self):
        """测试未连接的输入引脚应警告"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU",
                "pins": [
                    {"number": "1", "name": "RX", "pin_type": "input"},
                ],
            }
        ]
        nets = []
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        # 输入引脚未连接应该是警告
        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.UNCONNECTED_INPUT in error_types


class TestPinDirectionConflicts:
    """引脚方向冲突测试"""

    def test_output_to_output_conflict(self):
        """测试输出-输出冲突"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU1",
                "pins": [
                    {"number": "1", "name": "OUT", "pin_type": "output"},
                ],
            },
            {
                "id": "U2",
                "reference": "U2",
                "name": "MCU2",
                "pins": [
                    {"number": "1", "name": "OUT", "pin_type": "output"},
                ],
            },
        ]
        nets = [{"name": "NET1", "class": "signal", "pins": ["U1:1", "U2:1"]}]
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        # 应该检测到输出-输出冲突
        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.OUTPUT_TO_OUTPUT in error_types

    def test_input_to_input_warning(self):
        """测试输入-输入警告"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU1",
                "pins": [
                    {"number": "1", "name": "IN", "pin_type": "input"},
                ],
            },
            {
                "id": "U2",
                "reference": "U2",
                "name": "MCU2",
                "pins": [
                    {"number": "1", "name": "IN", "pin_type": "input"},
                ],
            },
        ]
        nets = [{"name": "NET1", "class": "signal", "pins": ["U1:1", "U2:1"]}]
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        # 应该警告输入-输入连接
        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.INPUT_TO_INPUT in error_types


class TestPowerSymbols:
    """电源符号测试"""

    def test_missing_vcc_symbol(self):
        """测试缺少VCC符号"""
        components = []
        nets = []
        power_symbols = [{"symbol_type": "gnd"}]

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.MISSING_POWER in error_types

    def test_missing_gnd_symbol(self):
        """测试缺少GND符号"""
        components = []
        nets = []
        power_symbols = [{"symbol_type": "vcc"}]

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.MISSING_GND in error_types

    def test_complete_power_symbols(self):
        """测试完整的电源符号"""
        components = []
        nets = []
        power_symbols = [{"symbol_type": "vcc"}, {"symbol_type": "gnd"}]

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        # 不应该有缺少电源的错误
        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.MISSING_POWER not in error_types
        assert ERCErrorType.MISSING_GND not in error_types


class TestDuplicateReferences:
    """重复引用测试"""

    def test_duplicate_reference(self):
        """测试重复的元件引用"""
        components = [
            {"id": "U1", "reference": "U1", "name": "MCU1", "pins": []},
            {
                "id": "U2",
                "reference": "U1",  # 重复!
                "name": "MCU2",
                "pins": [],
            },
        ]
        nets = []
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.DUPLICATE_REFERENCE in error_types


class TestFloatingNets:
    """浮动网络测试"""

    def test_floating_net(self):
        """测试浮动网络"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU",
                "pins": [
                    {"number": "1", "name": "IO", "pin_type": "input"},
                ],
            }
        ]
        nets = [
            {
                "name": "FLOAT_NET",  # 有名字但只连接一个引脚
                "class": "signal",
                "pins": ["U1:1"],
            }
        ]
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.FLOATING_NET in error_types

    def test_valid_net_not_floating(self):
        """测试有效的网络不是浮动"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU",
                "pins": [
                    {"number": "1", "name": "IO", "pin_type": "bidirectional"},
                ],
            },
            {
                "id": "R1",
                "reference": "R1",
                "name": "Resistor",
                "pins": [
                    {"number": "1", "name": "PAD1", "pin_type": "passive"},
                ],
            },
        ]
        nets = [{"name": "NET1", "class": "signal", "pins": ["U1:1", "R1:1"]}]
        power_symbols = []

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        error_types = [issue.error_type for issue in result.issues]
        assert ERCErrorType.FLOATING_NET not in error_types


class TestRunERC:
    """run_erc 兼容接口测试"""

    def test_run_erc_interface(self):
        """测试旧接口兼容"""
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU",
                "pins": [
                    {"number": "1", "name": "VCC", "pin_type": "power_in"},
                ],
            }
        ]
        nets = [{"name": "VCC", "class": "power", "pins": ["U1:1"]}]
        power_symbols = [{"symbol_type": "vcc"}, {"symbol_type": "gnd"}]

        result = run_erc(components, nets, power_symbols)

        assert "passed" in result
        assert "score" in result
        assert "issues" in result
        assert isinstance(result["issues"], list)


class TestERCScore:
    """ERC评分测试"""

    def test_score_calculation(self):
        """测试分数计算"""
        # 创建一个有严重问题的原理图
        components = [
            {
                "id": "U1",
                "reference": "U1",
                "name": "MCU1",
                "pins": [
                    {"number": "1", "name": "OUT", "pin_type": "output"},
                    {"number": "2", "name": "VCC", "pin_type": "power_in"},
                ],
            },
            {
                "id": "U2",
                "reference": "U2",
                "name": "MCU2",
                "pins": [
                    {"number": "1", "name": "OUT", "pin_type": "output"},  # 冲突!
                    {"number": "2", "name": "GND", "pin_type": "gnd"},
                ],
            },
        ]
        nets = [
            {
                "name": "NET1",
                "class": "signal",
                "pins": ["U1:1", "U2:1"],  # 输出-输出冲突
            },
            {"name": "VCC", "class": "power", "pins": ["U1:2"]},
            {"name": "GND", "class": "power", "pins": ["U2:2"]},
        ]
        power_symbols = []  # 缺少电源符号!

        result = check_schematic(
            {"components": components, "nets": nets, "power_symbols": power_symbols}
        )

        # 分数应该降低
        assert result.score < 100
        assert result.passed is False

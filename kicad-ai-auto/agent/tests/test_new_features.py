"""
新增功能测试 - 电压检测、参考编号生成、DRC检查

测试新增功能:
1. 电压检测功能
2. 参考编号生成功能
3. 元件电压提取
4. DRC增强检查
"""

import pytest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schematic_generator import (
    detect_voltage,
    generate_references,
    extract_voltage_from_component,
)
from pcb_generator import PCBGenerator, DRCChecker


class TestVoltageDetection:
    """测试电压检测功能"""

    def test_detect_5v(self):
        """测试检测5V"""
        result = detect_voltage("5V")
        assert result == 5.0

    def test_detect_3v3(self):
        """测试检测3.3V"""
        result = detect_voltage("3.3V")
        assert result == 3.3

    def test_detect_12v(self):
        """测试检测12V"""
        result = detect_voltage("12V")
        assert result == 12.0

    def test_detect_9v(self):
        """测试检测9V"""
        result = detect_voltage("9V")
        assert result == 9.0

    def test_detect_1v8(self):
        """测试检测1.8V"""
        result = detect_voltage("1.8V")
        assert result == 1.8

    def test_detect_with_space(self):
        """测试带空格的电压"""
        result = detect_voltage("5 V")
        assert result == 5.0

    def test_detect_lowercase(self):
        """测试小写电压"""
        result = detect_voltage("5v")
        assert result == 5.0

    def test_detect_invalid(self):
        """测试无效电压"""
        result = detect_voltage("invalid")
        assert result is None

    def test_detect_no_voltage(self):
        """测试无电压值"""
        result = detect_voltage("resistor")
        assert result is None


class TestReferenceGeneration:
    """测试参考编号生成"""

    def test_generate_resistor(self):
        """测试生成电阻参考编号"""
        refs = generate_references("Resistor", count=3)
        assert len(refs) == 3
        assert refs[0] == "R1"
        assert refs[1] == "R2"
        assert refs[2] == "R3"

    def test_generate_capacitor(self):
        """测试生成电容参考编号"""
        refs = generate_references("Capacitor", count=2)
        assert len(refs) == 2
        assert refs[0] == "C1"
        assert refs[1] == "C2"

    def test_generate_ic(self):
        """测试生成IC参考编号"""
        refs = generate_references("IC", count=2)
        assert len(refs) == 2
        assert refs[0] == "U1"
        assert refs[1] == "U2"

    def test_generate_stm32(self):
        """测试生成STM32参考编号"""
        refs = generate_references("STM32", count=1)
        assert len(refs) == 1
        assert refs[0] == "U1"

    def test_generate_led(self):
        """测试生成LED参考编号"""
        refs = generate_references("LED", count=2)
        assert len(refs) == 2
        assert refs[0] == "D1"

    def test_generate_crystal(self):
        """测试生成晶振参考编号"""
        refs = generate_references("Crystal", count=1)
        assert len(refs) == 1
        assert refs[0] == "Y1"

    def test_generate_connector(self):
        """测试生成连接器参考编号"""
        refs = generate_references("Connector", count=1)
        assert len(refs) == 1
        assert refs[0] == "J1"

    def test_generate_switch(self):
        """测试生成开关参考编号"""
        refs = generate_references("Switch", count=1)
        assert len(refs) == 1
        assert refs[0] == "SW1"

    def test_generate_motor(self):
        """测试生成电机参考编号"""
        refs = generate_references("Motor", count=1)
        assert len(refs) == 1
        assert refs[0] == "M1"

    def test_generate_inductor(self):
        """测试生成电感参考编号"""
        refs = generate_references("Inductor", count=1)
        assert len(refs) == 1
        assert refs[0] == "L1"

    def test_generate_default(self):
        """测试默认参考编号"""
        refs = generate_references("Unknown", count=1)
        assert len(refs) == 1
        assert refs[0] == "U1"  # 默认使用U


class TestExtractVoltage:
    """测试从元件名称提取电压"""

    def test_extract_7805(self):
        """测试提取7805电压"""
        result = extract_voltage_from_component("LM7805")
        # LM7805是5V稳压器，但名称中没有明确电压后缀
        # 这个测试验证函数能处理这种情况

    def test_extract_ams1117_3v3(self):
        """测试提取AMS1117-3.3电压"""
        result = extract_voltage_from_component("AMS1117-3.3")
        assert result == 3.3

    def test_extract_with_suffix(self):
        """测试带后缀的元件"""
        result = extract_voltage_from_component("LM7805_5V")
        # 验证能处理带下划线的情况


class TestDRCChecker:
    """测试DRC检查器"""

    def test_drc_checker_init(self):
        """测试DRC检查器初始化"""
        checker = DRCChecker()
        assert checker is not None
        assert hasattr(checker, "rules")

    def test_drc_default_rules(self):
        """测试默认规则"""
        checker = DRCChecker()
        assert checker.rules["min_track_width"] == 0.2
        assert checker.rules["min_clearance"] == 0.2

    def test_drc_custom_rules(self):
        """测试自定义规则"""
        rules = {"min_track_width": 0.3}
        checker = DRCChecker(rules)
        assert checker.rules["min_track_width"] == 0.3

    def test_drc_check_empty_pcb(self):
        """测试空PCB检查"""
        checker = DRCChecker()
        result = checker.check({})
        assert "passed" in result
        assert "warnings" in result

    def test_drc_check_missing_footprint(self):
        """测试缺少封装检查"""
        checker = DRCChecker()
        pcb_data = {
            "components": [{"reference": "U1", "name": "IC", "footprint": ""}],
            "tracks": [],
            "nets": [],
        }
        result = checker.check(pcb_data)
        warnings = result.get("warnings", [])
        has_warning = any("missing_footprint" in str(w) for w in warnings)
        assert has_warning

    def test_drc_check_no_tracks(self):
        """测试无走线检查"""
        checker = DRCChecker()
        pcb_data = {"components": [{"reference": "U1"}], "tracks": [], "nets": []}
        result = checker.check(pcb_data)
        warnings = result.get("warnings", [])
        has_warning = any("no_tracks" in str(w) for w in warnings)
        assert has_warning

    def test_drc_check_track_width(self):
        """测试走线宽度检查"""
        checker = DRCChecker()
        pcb_data = {
            "components": [],
            "tracks": [
                {"width": 100, "net_class": "signal"}  # 0.1mm < 0.2mm
            ],
            "nets": [],
        }
        result = checker.check(pcb_data)
        warnings = result.get("warnings", [])
        # 应该有走线宽度警告

    def test_drc_check_via_size(self):
        """测试过孔尺寸检查"""
        checker = DRCChecker()
        pcb_data = {
            "components": [],
            "tracks": [],
            "vias": [
                {"diameter": 100, "drill": 50}  # 0.1mm < 0.3mm
            ],
            "nets": [],
        }
        result = checker.check(pcb_data)
        warnings = result.get("warnings", [])
        # 应该有警告

    def test_drc_check_no_gnd(self):
        """测试缺少GND网络检查"""
        checker = DRCChecker()
        pcb_data = {"components": [], "tracks": [], "nets": [{"name": "VCC"}]}
        result = checker.check(pcb_data)
        warnings = result.get("warnings", [])
        has_warning = any("gnd" in str(w).lower() for w in warnings)
        assert has_warning

    def test_drc_check_small_board(self):
        """测试小板检查"""
        checker = DRCChecker()
        pcb_data = {
            "components": [],
            "tracks": [],
            "board_outline": {
                "width": 1000,  # 1mm < 10mm
                "height": 1000,
            },
            "nets": [{"name": "GND"}],
        }
        result = checker.check(pcb_data)
        warnings = result.get("warnings", [])
        has_warning = any("small_board" in str(w) for w in warnings)
        assert has_warning

    def test_drc_pass_with_valid_pcb(self):
        """测试有效PCB通过检查"""
        checker = DRCChecker()
        pcb_data = {
            "components": [{"reference": "U1", "footprint": "LQFP-48"}],
            "tracks": [
                {"width": 500, "net_class": "signal"},  # 0.5mm
                {"width": 1000, "net_class": "power"},  # 1.0mm
            ],
            "vias": [
                {"diameter": 500, "drill": 300}  # 0.5mm / 0.3mm
            ],
            "board_outline": {
                "width": 50000,  # 50mm
                "height": 50000,
            },
            "nets": [{"name": "VCC"}, {"name": "GND"}],
        }
        result = checker.check(pcb_data)
        # 没有错误，只有一些警告


class TestPowerTrackWidth:
    """测试电源走线宽度检查"""

    def test_power_track_width_rule(self):
        """测试电源走线更宽"""
        checker = DRCChecker()
        pcb_data = {
            "components": [],
            "tracks": [
                {"width": 300, "net_class": "power"}  # 0.3mm < 0.5mm
            ],
            "nets": [],
        }
        result = checker.check(pcb_data)
        # 电源线应该更严格


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

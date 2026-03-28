"""
component_calculator 单元测试
测试电路参数计算功能
"""

import pytest
from component_calculator import (
    calculate_led_resistor,
    calculate_voltage_divider,
    calculate_decoupling_capacitor,
    E24_SERIES,
    E12_SERIES,
    E24_MULTIPLIERS,
    E12_MULTIPLIERS,
)


class TestLEDResistor:
    """LED限流电阻计算测试"""

    def test_calculate_led_resistor_basic(self):
        """基本LED电阻计算"""
        result = calculate_led_resistor(
            vcc=5.0,
            vf=2.0,
            if_current=20.0,  # 20mA
        )
        assert result.calculated_value > 0
        assert result.standard_value > 0

    def test_calculate_led_resistor_12v(self):
        """12V电源LED计算"""
        result = calculate_led_resistor(vcc=12.0, vf=3.0, if_current=15.0)
        assert result.calculated_value > 0

    def test_calculate_led_resistor_default(self):
        """默认参数"""
        result = calculate_led_resistor(vcc=5.0)
        assert result.calculated_value > 0


class TestVoltageDivider:
    """分压电阻计算测试"""

    def test_voltage_divider_basic(self):
        """基本分压计算"""
        result = calculate_voltage_divider(5.0, 3.3, 0.001)
        assert result.calculated_value > 0

    def test_voltage_divider_no_load(self):
        """无负载分压"""
        result = calculate_voltage_divider(12.0, 5.0)
        assert result.calculated_value > 0


class TestDecouplingCapacitor:
    """去耦电容计算测试"""

    def test_decoupling_capacitor_basic(self):
        """基本去耦电容计算"""
        result = calculate_decoupling_capacitor(5.0, 100.0)
        assert result is not None

    def test_decoupling_capacitor_mcu(self):
        """MCU去耦电容"""
        result = calculate_decoupling_capacitor(3.3, 50.0)
        assert result is not None


class TestStandardValues:
    """标准值系列测试"""

    def test_e24_series_length(self):
        """E24系列长度"""
        assert len(E24_SERIES) == 48

    def test_e12_series_length(self):
        """E12系列长度"""
        assert len(E12_SERIES) == 12

    def test_e24_multipliers(self):
        """E24倍率"""
        assert 1.0 in E24_MULTIPLIERS
        assert 1000.0 in E24_MULTIPLIERS

    def test_e12_multipliers(self):
        """E12倍率"""
        assert 1.0 in E12_MULTIPLIERS
        assert 1000.0 in E12_MULTIPLIERS

    def test_e24_values_range(self):
        """E24值范围"""
        assert min(E24_SERIES) >= 1.0
        assert max(E24_SERIES) <= 100.0

    def test_e12_values_range(self):
        """E12值范围"""
        assert min(E12_SERIES) >= 1.0
        assert max(E12_SERIES) <= 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

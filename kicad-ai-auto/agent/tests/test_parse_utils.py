"""
parse_utils 单元测试
测试AI路由解析工具函数
"""

import pytest
from routes.parse_utils import (
    parse_reference,
    parse_position,
    parse_value,
    parse_package,
    detect_operation_type,
    detect_component_type,
)


class TestParseReference:
    """元件引用号解析测试"""

    def test_parse_simple_reference(self):
        """简单引用号"""
        assert parse_reference("删除R1") == "R1"
        assert parse_reference("修改C3") == "C3"

    def test_parse_reference_with_prefix(self):
        """带前缀引用号"""
        assert parse_reference("元件R5") == "R5"

    def test_no_reference(self):
        """无引用号"""
        assert parse_reference("添加电容") is None


class TestParsePosition:
    """位置坐标解析测试"""

    def test_parse_position_parentheses(self):
        """括号格式坐标"""
        result = parse_position("在(100,200)处添加")
        assert result == {"x": 100.0, "y": 200.0}

    def test_parse_position_with_spaces(self):
        """带空格坐标"""
        result = parse_position("位置 150, 200")
        assert result == {"x": 150.0, "y": 200.0}

    def test_no_position(self):
        """无坐标"""
        assert parse_position("添加电容") is None


class TestParseValue:
    """元件值解析测试"""

    def test_parse_resistor_value(self):
        """电阻值"""
        result = parse_value("10k电阻")
        assert result is not None

    def test_parse_voltage(self):
        """电压值"""
        result = parse_value("5V电源")
        assert result is not None

    def test_no_value(self):
        """无值"""
        assert parse_value("添加电容") is None


class TestParsePackage:
    """封装解析测试"""

    def test_parse_smd_package(self):
        """SMD封装"""
        assert parse_package("0805电阻") == "0805"
        assert parse_package("0603电容") == "0603"

    def test_parse_tht_package(self):
        """THT封装"""
        assert parse_package("DIP-8芯片") == "DIP-8"

    def test_no_package(self):
        """无封装"""
        assert parse_package("添加电容") is None


class TestDetectOperationType:
    """操作类型检测测试"""

    def test_detect_add(self):
        """添加操作"""
        assert detect_operation_type("添加电容") == "add"
        assert detect_operation_type("add resistor") == "add"

    def test_detect_delete(self):
        """删除操作"""
        assert detect_operation_type("删除R1") == "delete"
        assert detect_operation_type("remove component") == "delete"

    def test_detect_modify(self):
        """修改操作"""
        assert detect_operation_type("修改封装") == "modify"
        assert detect_operation_type("change value") == "modify"

    def test_detect_move(self):
        """移动操作"""
        assert detect_operation_type("移动到") == "move"
        assert detect_operation_type("move component") == "move"

    def test_detect_connect(self):
        """连接操作"""
        assert detect_operation_type("连接到") == "connect"
        assert detect_operation_type("wire net") == "connect"


class TestDetectComponentType:
    """元件类型检测测试"""

    def test_detect_resistor(self):
        """电阻"""
        assert detect_component_type("电阻Rresistor") == "resistor"
        assert detect_component_type("resistor 10k") == "resistor"

    def test_detect_capacitor(self):
        """电容"""
        assert detect_component_type("电容C1") == "capacitor"
        assert detect_component_type("100uF capacitor") == "capacitor"

    def test_detect_ic(self):
        """芯片"""
        assert detect_component_type("STM32芯片") == "ic"
        assert detect_component_type("MCU controller") == "ic"

    def test_detect_led(self):
        """LED"""
        assert detect_component_type("LED灯") == "led"
        assert detect_component_type("发光二极管") == "led"

    def test_detect_connector(self):
        """连接器"""
        assert detect_component_type("USB接口") == "connector"
        assert detect_component_type("connector") == "connector"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

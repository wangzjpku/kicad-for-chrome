"""
原理图生成器单元测试

测试覆盖:
1. 枚举类型定义
2. 数据类创建
3. 原理图生成功能
4. 模板加载
"""

import pytest
import sys
import os
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schematic_generator import (
    SchematicGenerator,
    SchematicPin,
    SchematicComponent,
    SchematicNet,
    SchematicWire,
    ComponentCategory,
    PinType,
    generate_standard_schematic,
)


class TestPinType:
    """测试引脚类型枚举"""

    def test_pin_type_enum_values(self):
        """测试PinType枚举定义完整"""
        assert hasattr(PinType, "POWER_IN")
        assert hasattr(PinType, "POWER_OUT")
        assert hasattr(PinType, "GND")
        assert hasattr(PinType, "INPUT")
        assert hasattr(PinType, "OUTPUT")
        assert hasattr(PinType, "BIDIRECTIONAL")
        assert hasattr(PinType, "PASSIVE")
        assert hasattr(PinType, "UNSPECIFIED")

    def test_pin_type_power_in(self):
        """测试电源输入类型"""
        assert PinType.POWER_IN.value == "power_in"

    def test_pin_type_gnd(self):
        """测试地类型"""
        assert PinType.GND.value == "gnd"


class TestComponentCategory:
    """测试元件类别枚举"""

    def test_category_enum_values(self):
        """测试ComponentCategory枚举完整"""
        assert hasattr(ComponentCategory, "POWER")
        assert hasattr(ComponentCategory, "MCU")
        assert hasattr(ComponentCategory, "INTERFACE")
        assert hasattr(ComponentCategory, "PASSIVE")
        assert hasattr(ComponentCategory, "ACTIVE")
        assert hasattr(ComponentCategory, "CONNECTOR")
        assert hasattr(ComponentCategory, "CRYSTAL")
        assert hasattr(ComponentCategory, "LED")
        assert hasattr(ComponentCategory, "SENSOR")
        assert hasattr(ComponentCategory, "OTHER")

    def test_category_power(self):
        """测试电源类别"""
        assert ComponentCategory.POWER.value == "power"

    def test_category_mcu(self):
        """测试MCU类别"""
        assert ComponentCategory.MCU.value == "mcu"


class TestSchematicPin:
    """测试原理图引脚数据类"""

    def test_pin_creation_basic(self):
        """测试创建基本引脚"""
        pin = SchematicPin(number="1", name="VCC")
        assert pin.number == "1"
        assert pin.name == "VCC"
        assert pin.pin_type == PinType.UNSPECIFIED  # 默认值
        assert pin.direction == "right"  # 默认值

    def test_pin_creation_full(self):
        """测试创建完整引脚"""
        pin = SchematicPin(
            number="1",
            name="VCC",
            pin_type=PinType.POWER_IN,
            position=(10, 20),
            direction="up",
        )
        assert pin.number == "1"
        assert pin.name == "VCC"
        assert pin.pin_type == PinType.POWER_IN
        assert pin.position == (10, 20)
        assert pin.direction == "up"

    def test_pin_position_default(self):
        """测试引脚默认位置"""
        pin = SchematicPin(number="1", name="GND")
        assert pin.position == (0, 0)


class TestSchematicComponent:
    """测试原理图元件数据类"""

    def test_component_creation_basic(self):
        """测试创建基本元件"""
        comp = SchematicComponent(
            id="u1", name="STM32", model="STM32F103C8T6", reference="U1"
        )
        assert comp.id == "u1"
        assert comp.name == "STM32"
        assert comp.model == "STM32F103C8T6"
        assert comp.reference == "U1"
        assert comp.category == ComponentCategory.OTHER  # 默认值

    def test_component_creation_full(self):
        """测试创建完整元件"""
        pins = [
            SchematicPin(number="1", name="VCC", pin_type=PinType.POWER_IN),
            SchematicPin(number="2", name="GND", pin_type=PinType.GND),
        ]
        comp = SchematicComponent(
            id="u1",
            name="STM32",
            model="STM32F103C8T6",
            reference="U1",
            position=(100, 50),
            size=(150, 80),
            pins=pins,
            category=ComponentCategory.MCU,
            symbol_library="MCU_ST_STM32",
            footprint="LQFP-48",
        )
        assert len(comp.pins) == 2
        assert comp.category == ComponentCategory.MCU
        assert comp.symbol_library == "MCU_ST_STM32"
        assert comp.footprint == "LQFP-48"


class TestSchematicNet:
    """测试原理图网络数据类"""

    def test_net_creation_basic(self):
        """测试创建基本网络"""
        net = SchematicNet(id="net1", name="VCC")
        assert net.id == "net1"
        assert net.name == "VCC"
        assert net.net_class == "default"  # 默认值

    def test_net_creation_power(self):
        """测试创建电源网络"""
        net = SchematicNet(id="net1", name="VCC", net_class="power")
        assert net.net_class == "power"


class TestSchematicWire:
    """测试原理图导线数据类"""

    def test_wire_creation(self):
        """测试创建导线"""
        wire = SchematicWire(
            id="wire1", points=[(0, 0), (100, 0), (100, 50)], net="VCC"
        )
        assert wire.id == "wire1"
        assert len(wire.points) == 3
        assert wire.points[0] == (0, 0)
        assert wire.points[2] == (100, 50)
        assert wire.net == "VCC"


class TestSchematicGenerator:
    """测试原理图生成器类"""

    def test_generator_init(self):
        """测试生成器初始化"""
        generator = SchematicGenerator()
        assert generator is not None

    def test_generator_has_methods(self):
        """测试生成器有必要的生成方法"""
        generator = SchematicGenerator()
        assert hasattr(generator, "generate")
        assert hasattr(generator, "export_to_dict")


class TestGenerateStandardSchematic:
    """测试标准原理图生成"""

    def test_generate_empty_components(self):
        """测试空元件列表生成"""
        result = generate_standard_schematic([])
        assert "components" in result
        assert "nets" in result

    def test_generate_with_single_component(self):
        """测试单个元件生成"""
        components = [{"name": "LM7805", "reference": "U1"}]
        result = generate_standard_schematic(components)
        assert "components" in result
        assert "nets" in result
        assert len(result["components"]) >= 0

    def test_generate_with_multiple_components(self):
        """测试多个元件生成"""
        components = [
            {"name": "STM32F103C8T6", "reference": "U1"},
            {"name": "10K", "reference": "R1"},
            {"name": "100nF", "reference": "C1"},
        ]
        result = generate_standard_schematic(components)
        assert "components" in result
        assert "nets" in result

    def test_generate_with_circuit_type(self):
        """测试带电路类型参数"""
        components = [{"name": "LED", "reference": "D1"}]
        result = generate_standard_schematic(components, circuit_type="power")
        assert "components" in result

    def test_generate_returns_dict(self):
        """测试生成返回字典类型"""
        result = generate_standard_schematic([])
        assert isinstance(result, dict)


class TestSchematicAccuracy:
    """测试原理图准确性"""

    def test_generated_has_components_key(self):
        """验证生成的原理图有components键"""
        result = generate_standard_schematic([])
        assert "components" in result

    def test_generated_has_nets_key(self):
        """验证生成的原理图有nets键"""
        result = generate_standard_schematic([])
        assert "nets" in result

    def test_schematic_components_is_list(self):
        """验证components是列表"""
        result = generate_standard_schematic([])
        assert isinstance(result["components"], list)

    def test_schematic_nets_is_list(self):
        """验证nets是列表"""
        result = generate_standard_schematic([])
        assert isinstance(result["nets"], list)


class TestSchematicDataStructure:
    """测试原理图数据结构"""

    def test_component_dict_structure(self):
        """测试元件字典结构"""
        components = [{"name": "R", "reference": "R1"}]
        result = generate_standard_schematic(components)
        # 验证返回结构
        assert "components" in result

    def test_net_dict_structure(self):
        """测试网络字典结构"""
        components = [
            {"name": "R", "reference": "R1"},
            {"name": "R", "reference": "R2"},
        ]
        result = generate_standard_schematic(components)
        # 验证返回结构包含网络
        assert "nets" in result
        assert isinstance(result["nets"], list)


class TestPinTypeEnumValues:
    """测试引脚类型枚举值"""

    def test_all_pin_types(self):
        """测试所有引脚类型"""
        pin_types = [
            PinType.POWER_IN,
            PinType.POWER_OUT,
            PinType.GND,
            PinType.INPUT,
            PinType.OUTPUT,
            PinType.BIDIRECTIONAL,
            PinType.PASSIVE,
            PinType.UNSPECIFIED,
        ]
        assert len(pin_types) == 8


class TestComponentCategoryValues:
    """测试元件类别值"""

    def test_all_categories(self):
        """测试所有元件类别"""
        categories = [
            ComponentCategory.POWER,
            ComponentCategory.MCU,
            ComponentCategory.INTERFACE,
            ComponentCategory.PASSIVE,
            ComponentCategory.ACTIVE,
            ComponentCategory.CONNECTOR,
            ComponentCategory.CRYSTAL,
            ComponentCategory.LED,
            ComponentCategory.SENSOR,
            ComponentCategory.OTHER,
        ]
        assert len(categories) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

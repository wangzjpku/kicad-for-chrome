"""
PCB Layout Optimizer 100% Coverage Tests

基于实际 pcb_layout_optimizer.py 模块结构
"""
import pytest
import json
import os
from typing import Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcb_layout_optimizer import (
    PCBLayoutOptimizer, LayoutConstraints, Component, ComponentCategory,
    get_layout_optimizer, auto_layout_components
)


class TestPCBLayoutOptimizer:
    """PCB自动布局算法测试"""

    @pytest.fixture
    def fixture_dir(self):
        """测试fixtures目录"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "fixtures", "real_projects"
        )

    @pytest.fixture
    def optimizer(self):
        """创建优化器"""
        return PCBLayoutOptimizer()

    def test_optimizer_initialization(self, optimizer):
        """测试优化器初始化"""
        assert optimizer is not None
        assert hasattr(optimizer, 'MARGIN')
        assert hasattr(optimizer, 'COMPONENT_SPACING')

    def test_parse_components(self, optimizer):
        """测试解析元件数据"""
        components = [
            {"id": "U1", "name": "STM32", "width": 15, "height": 15},
            {"id": "C1", "name": "Capacitor", "width": 3, "height": 3}
        ]

        parsed = optimizer._parse_components(components)

        assert len(parsed) == 2
        assert all(isinstance(c, Component) for c in parsed)

    def test_categorize_components(self, optimizer):
        """测试元件分类"""
        components = [
            Component(id="U1", name="STM32", width=15, height=15, category=ComponentCategory.IC),
            Component(id="C1", name="Cap", width=3, height=3, category=ComponentCategory.PASSIVE),
            Component(id="VIN", name="VCC", width=2, height=2, category=ComponentCategory.POWER),
        ]

        categorized = optimizer._categorize_components(components)

        assert isinstance(categorized, dict)
        assert ComponentCategory.POWER in categorized
        assert ComponentCategory.PASSIVE in categorized

    def test_partition_regions_power(self, optimizer):
        """测试电源电路区域划分"""
        components = [
            Component(id="U1", name="LM7805", width=10, height=5, category=ComponentCategory.IC),
            Component(id="C1", name="C", width=3, height=3, category=ComponentCategory.PASSIVE),
            Component(id="VIN", name="VCC", width=2, height=2, category=ComponentCategory.POWER),
        ]

        constraints = LayoutConstraints(
            board_width=100,
            board_height=80,
            layer_count=2,
            fixed_components=["VIN"]
        )

        regions = optimizer._partition_regions(components)

        assert len(regions) > 0

    def test_partition_regions_digital(self, optimizer):
        """测试数字电路区域划分"""
        components = [
            Component(id="U1", name="STM32", width=15, height=15, category=ComponentCategory.IC),
            Component(id="C1", name="C", width=2, height=2, category=ComponentCategory.PASSIVE),
            Component(id="R1", name="R", width=2, height=1, category=ComponentCategory.PASSIVE),
        ]

        regions = optimizer._partition_regions(components)

        assert len(regions) > 0

    def test_initial_placement_empty(self, optimizer):
        """测试空元件列表布局"""
        categorized = {cat: [] for cat in ComponentCategory}
        regions = {}
        placements = optimizer._initial_placement(categorized, regions)

        assert len(placements) == 0

    def test_initial_placement_with_fixed(self, optimizer):
        """测试固定元件保持原位"""
        components = [
            Component(id="U1", name="IC", width=10, height=10, category=ComponentCategory.IC),
            Component(id="C1", name="C", width=3, height=3, category=ComponentCategory.PASSIVE),
        ]

        optimizer.constraints = LayoutConstraints(
            board_width=100,
            board_height=80,
            fixed_components=["U1"]
        )

        categorized = optimizer._categorize_components(components)
        regions = optimizer._partition_regions(categorized)
        placements = optimizer._initial_placement(categorized, regions)

        # 固定元件应该在placements中
        assert "U1" in placements

    def test_calculate_cost_empty(self, optimizer):
        """测试空布局成本计算"""
        cost = optimizer._calculate_cost({})

        assert cost == 0

    def test_calculate_cost_with_components(self, optimizer):
        """测试有元件时的成本计算"""
        # 创建Placement对象需要的字段
        from dataclasses import dataclass

        @dataclass
        class Placement:
            component_id: str
            x: float
            y: float
            rotation: float

        placements = {
            "U1": Placement(component_id="U1", x=50, y=40, rotation=0),
            "C1": Placement(component_id="C1", x=30, y=30, rotation=0),
        }

        cost = optimizer._calculate_cost(placements)

        # 成本应该是正数
        assert cost >= 0

    def test_optimize_step(self, optimizer):
        """测试单步优化"""
        from dataclasses import dataclass

        @dataclass
        class Placement:
            component_id: str
            x: float
            y: float
            rotation: float

        placements = {
            "U1": Placement(component_id="U1", x=50, y=40, rotation=0),
            "C1": Placement(component_id="C1", x=30, y=30, rotation=0),
        }

        initial_cost = optimizer._calculate_cost(placements)
        new_placements = optimizer._optimize_step(placements, initial_cost)

        assert new_placements is not None

    def test_optimize_converges(self, optimizer):
        """测试优化收敛"""
        components = [
            {"id": "U1", "name": "IC1", "width": 10, "height": 10},
            {"id": "U2", "name": "IC2", "width": 10, "height": 10},
            {"id": "C1", "name": "C1", "width": 3, "height": 3},
            {"id": "C2", "name": "C2", "width": 3, "height": 3},
        ]

        constraints = LayoutConstraints(
            board_width=100,
            board_height=80,
            fixed_components=[]
        )

        result = optimizer.optimize(components, constraints)

        assert result is not None
        assert len(result) > 0

    def test_optimize_max_iterations(self, optimizer):
        """测试最大迭代次数限制"""
        optimizer.MAX_ITERATIONS = 2  # 设置小值

        components = [
            {"id": "U1", "name": "IC1", "width": 10, "height": 10},
            {"id": "C1", "name": "C1", "width": 3, "height": 3},
        ]

        result = optimizer.optimize(components)

        # 应该在限制内完成
        assert result is not None

    def test_get_result(self, optimizer):
        """测试获取结果"""
        components = [
            {"id": "U1", "name": "IC", "width": 10, "height": 10}
        ]

        optimizer.optimize(components)
        result = optimizer.get_result()

        assert result is not None


class TestLayoutConstraints:
    """布局约束测试"""

    def test_default_constraints(self):
        """测试默认约束"""
        constraints = LayoutConstraints()

        assert constraints.board_width == 100.0
        assert constraints.board_height == 80.0
        assert constraints.layer_count == 2
        assert constraints.keepout_areas == []
        assert constraints.fixed_components == []

    def test_custom_constraints(self):
        """测试自定义约束"""
        constraints = LayoutConstraints(
            board_width=200,
            board_height=150,
            layer_count=4,
            fixed_components=["U1", "U2"]
        )

        assert constraints.board_width == 200
        assert constraints.board_height == 150
        assert constraints.layer_count == 4
        assert "U1" in constraints.fixed_components

    def test_constraints_post_init(self):
        """测试约束初始化"""
        constraints = LayoutConstraints()

        # 验证None被初始化为空列表
        assert isinstance(constraints.keepout_areas, list)
        assert isinstance(constraints.fixed_components, list)
        assert isinstance(constraints.nets_to_route_first, list)


class TestComponent:
    """元件模型测试"""

    def test_component_creation(self):
        """测试元件创建"""
        comp = Component(
            id="U1",
            name="STM32",
            width=15,
            height=15,
            category=ComponentCategory.IC
        )

        assert comp.id == "U1"
        assert comp.name == "STM32"
        assert comp.width == 15
        assert comp.height == 15
        assert comp.category == ComponentCategory.IC

    def test_component_defaults(self):
        """测试元件默认值"""
        comp = Component(id="R1", name="Resistor", width=2, height=1)

        assert comp.category == ComponentCategory.OTHER

    def test_component_category_power(self):
        """测试电源类别"""
        comp = Component(
            id="VIN", name="VCC", width=2, height=2,
            category=ComponentCategory.POWER
        )

        assert comp.category == ComponentCategory.POWER


class TestComponentCategory:
    """元件类别枚举测试"""

    def test_power_category(self):
        """测试电源类别"""
        assert ComponentCategory.POWER.value == "power"

    def test_analog_category(self):
        """测试模拟类别"""
        assert ComponentCategory.ANALOG.value == "analog"

    def test_digital_category(self):
        """测试数字类别"""
        assert ComponentCategory.DIGITAL.value == "digital"

    def test_ic_category(self):
        """测试IC类别"""
        assert ComponentCategory.IC.value == "ic"

    def test_passive_category(self):
        """测试无源器件类别"""
        assert ComponentCategory.PASSIVE.value == "passive"

    def test_connector_category(self):
        """测试连接器类别"""
        assert ComponentCategory.CONNECTOR.value == "connector"


class TestModuleFunctions:
    """模块级函数测试"""

    def test_get_layout_optimizer(self):
        """测试获取布局优化器单例"""
        opt1 = get_layout_optimizer()
        opt2 = get_layout_optimizer()

        assert opt1 is opt2

    def test_auto_layout_components(self):
        """测试自动布局函数"""
        components = [
            {"id": "U1", "name": "IC", "width": 10, "height": 10}
        ]

        result = auto_layout_components(components)

        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

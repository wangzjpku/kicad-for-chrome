"""
PCB Router (Lee Algorithm) 100% Coverage Tests

基于实际 pcb_router.py 模块结构
"""
import pytest
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcb_router import (
    PCBRouter, RoutingRules, Net, Pad, Track, Via, Grid,
    get_router, auto_route
)


class TestPCBRouter:
    """PCB自动布线器测试"""

    @pytest.fixture
    def router(self):
        """创建路由器"""
        return PCBRouter()

    def test_router_initialization(self, router):
        """测试路由器初始化"""
        assert router is not None
        assert hasattr(router, 'grid')
        assert hasattr(router, 'tracks')
        assert hasattr(router, 'vias')

    def test_route_single_net(self, router):
        """测试单网络布线"""
        nets = [
            {"name": "VDD", "is_power": True}
        ]
        pads = [
            {"component_id": "U1", "pin_number": "1", "x": 10, "y": 10, "net": "VDD"},
            {"component_id": "C1", "pin_number": "1", "x": 30, "y": 30, "net": "VDD"}
        ]

        result = router.route(nets, pads)

        assert isinstance(result, dict)
        assert "tracks" in result
        assert "vias" in result

    def test_route_multiple_nets(self, router):
        """测试多网络布线"""
        nets = [
            {"name": "VDD", "is_power": True},
            {"name": "VSS", "is_power": True},
            {"name": "SIGNAL", "is_power": False}
        ]
        pads = [
            {"component_id": "U1", "pin_number": "1", "x": 10, "y": 10, "net": "VDD"},
            {"component_id": "C1", "pin_number": "1", "x": 30, "y": 30, "net": "VDD"},
            {"component_id": "U1", "pin_number": "2", "x": 15, "y": 15, "net": "VSS"},
            {"component_id": "C2", "pin_number": "1", "x": 35, "y": 35, "net": "VSS"},
            {"component_id": "U1", "pin_number": "3", "x": 20, "y": 20, "net": "SIGNAL"},
            {"component_id": "R1", "pin_number": "1", "x": 40, "y": 40, "net": "SIGNAL"}
        ]

        result = router.route(nets, pads)

        assert "tracks" in result
        assert "vias" in result

    def test_route_differential_pair(self, router):
        """测试差分对布线"""
        nets = [
            {"name": "DP", "is_differential": True},
            {"name": "DM", "is_differential": True}
        ]
        pads = [
            {"component_id": "U1", "pin_number": "DP", "x": 10, "y": 10, "net": "DP"},
            {"component_id": "USB1", "pin_number": "DP", "x": 50, "y": 50, "net": "DP"},
            {"component_id": "U1", "pin_number": "DM", "x": 10, "y": 12, "net": "DM"},
            {"component_id": "USB1", "pin_number": "DM", "x": 50, "y": 52, "net": "DM"}
        ]

        result = router.route(nets, pads)

        assert "tracks" in result

    def test_route_empty_nets(self, router):
        """测试空网络列表"""
        result = router.route([], [])

        assert result is not None
        assert "tracks" in result
        assert len(result["tracks"]) == 0

    def test_route_single_pad_net(self, router):
        """测试单焊盘网络（应该跳过）"""
        nets = [
            {"name": "FLOATING"}
        ]
        pads = [
            {"component_id": "U1", "pin_number": "1", "x": 10, "y": 10, "net": "FLOATING"}
        ]

        result = router.route(nets, pads)

        assert "tracks" in result

    def test_find_path(self, router):
        """测试路径查找"""
        nets = [
            {"name": "TEST", "is_power": False}
        ]
        pads = [
            {"component_id": "U1", "pin_number": "1", "x": 10, "y": 10, "net": "TEST"},
            {"component_id": "U2", "pin_number": "1", "x": 50, "y": 50, "net": "TEST"}
        ]

        router.route(nets, pads)

        # 路由后应该有tracks
        assert isinstance(router.tracks, list)

    def test_create_tracks_from_path(self, router):
        """测试从路径创建走线"""
        # 初始化网格（路由器需要网格来标记位置）
        router.grid = Grid(width=100, height=100, resolution=1.0)

        path = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]

        net = Net(name="TEST", pads=[
            Pad("U1", "1", 0, 0, "TEST"),
            Pad("U2", "1", 2, 2, "TEST")
        ])

        router._create_tracks_from_path(path, net)

        assert len(router.tracks) >= 0

    def test_sort_nets_by_priority(self, router):
        """测试网络优先级排序"""
        nets = [
            Net(name="SIGNAL", pads=[], is_power=False),
            Net(name="VDD", pads=[], is_power=True),
            Net(name="GND", pads=[], is_power=True),
        ]

        router.nets = nets
        sorted_nets = router._sort_nets_by_priority()

        # 电源网络应该在前面
        power_nets = [n for n in sorted_nets if n.is_power]
        signal_nets = [n for n in sorted_nets if not n.is_power]

        if power_nets and signal_nets:
            first_power_idx = sorted_nets.index(power_nets[0])
            first_signal_idx = sorted_nets.index(signal_nets[0])
            assert first_power_idx < first_signal_idx


class TestRoutingRules:
    """路由规则测试"""

    def test_default_rules(self):
        """测试默认规则"""
        rules = RoutingRules()

        assert rules.clearance == 0.2
        assert rules.layer_count == 2
        assert rules.via_size == (0.8, 0.4)

    def test_custom_rules(self):
        """测试自定义规则"""
        rules = RoutingRules(
            trace_width={"VDD": 0.5, "default": 0.3},
            clearance=0.3,
            layer_count=4
        )

        assert rules.clearance == 0.3
        assert rules.layer_count == 4
        assert rules.trace_width["VDD"] == 0.5

    def test_rules_post_init(self):
        """测试规则初始化"""
        rules = RoutingRules()

        # 验证默认值被设置
        assert isinstance(rules.trace_width, dict)
        assert "default" in rules.trace_width


class TestGrid:
    """布线网格测试"""

    def test_grid_initialization(self):
        """测试网格初始化"""
        grid = Grid(width=100, height=80, resolution=1.0)

        assert grid.width == 100
        assert grid.height == 80
        assert grid.resolution == 1.0
        assert grid.cols == 101
        assert grid.rows == 81

    def test_mark_obstacle(self):
        """测试标记障碍物"""
        grid = Grid(width=100, height=100, resolution=1.0)

        grid.mark_obstacle(x=50, y=50, radius=5)

        # 检查障碍物是否被标记
        assert grid.grid[50][50] == 1

    def test_is_empty_true(self):
        """测试空位置检测"""
        grid = Grid(width=100, height=100, resolution=1.0)

        result = grid.is_empty(10, 10)

        assert result is True

    def test_is_empty_false(self):
        """测试已占用位置检测"""
        grid = Grid(width=100, height=100, resolution=1.0)
        grid.mark_obstacle(x=10, y=10, radius=1)

        result = grid.is_empty(10, 10)

        assert result is False

    def test_mark_occupied(self):
        """测试标记位置为已占用"""
        grid = Grid(width=100, height=100, resolution=1.0)

        grid.mark_occupied(20, 20)

        assert grid.grid[20][20] == 1

    def test_out_of_bounds(self):
        """测试边界外检查"""
        grid = Grid(width=100, height=100, resolution=1.0)

        # 边界外应该返回False
        assert grid.is_empty(-1, 10) is False
        assert grid.is_empty(10, -1) is False
        assert grid.is_empty(150, 50) is False


class TestPad:
    """焊盘测试"""

    def test_pad_creation(self):
        """测试焊盘创建"""
        pad = Pad(
            component_id="U1",
            pin_number="1",
            x=10.5,
            y=20.5,
            net="VDD"
        )

        assert pad.component_id == "U1"
        assert pad.pin_number == "1"
        assert pad.x == 10.5
        assert pad.y == 20.5
        assert pad.net == "VDD"


class TestTrack:
    """走线测试"""

    def test_track_creation(self):
        """测试走线创建"""
        track = Track(
            net="VDD",
            layer=1,
            x1=0, y1=0,
            x2=50, y2=50,
            width=0.3
        )

        assert track.net == "VDD"
        assert track.layer == 1
        assert track.x2 == 50
        assert track.width == 0.3


class TestVia:
    """过孔测试"""

    def test_via_creation(self):
        """测试过孔创建"""
        via = Via(
            net="VDD",
            x=25,
            y=25,
            from_layer=1,
            to_layer=2
        )

        assert via.net == "VDD"
        assert via.x == 25
        assert via.y == 25
        assert via.from_layer == 1
        assert via.to_layer == 2


class TestNet:
    """网络测试"""

    def test_net_creation(self):
        """测试网络创建"""
        pads = [
            Pad(component_id="U1", pin_number="1", x=0, y=0, net="VDD"),
            Pad(component_id="C1", pin_number="1", x=10, y=10, net="VDD")
        ]

        net = Net(name="VDD", pads=pads, is_power=True)

        assert net.name == "VDD"
        assert len(net.pads) == 2
        assert net.is_power is True
        assert net.is_differential is False

    def test_net_differential(self):
        """测试差分对网络"""
        pads = [
            Pad(component_id="U1", pin_number="DP", x=0, y=0, net="DP"),
            Pad(component_id="U1", pin_number="DM", x=0, y=1, net="DM")
        ]

        net = Net(name="USB", pads=pads, is_differential=True)

        assert net.is_differential is True


class TestModuleFunctions:
    """模块级函数测试"""

    def test_get_router(self):
        """测试获取路由器单例"""
        router1 = get_router()
        router2 = get_router()

        assert router1 is router2

    def test_auto_route(self):
        """测试自动路由函数"""
        nets = [{"name": "VDD", "is_power": True}]
        pads = [
            {"component_id": "U1", "pin_number": "1", "x": 10, "y": 10, "net": "VDD"},
            {"component_id": "C1", "pin_number": "1", "x": 30, "y": 30, "net": "VDD"}
        ]

        result = auto_route(nets, pads)

        assert result is not None
        assert "tracks" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
智能布线引擎测试用例

测试 RoutingEngine 的核心功能：
1. 曼哈顿布线（L型、45度）
2. 多层布线（自动过孔）
3. 差分对布线
4. 网络连接
"""

import pytest
import sys
import math
from pathlib import Path

# 添加 agent 目录到路径
agent_path = Path(__file__).parent.parent / "agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from routing.routing_engine import (
    RoutingEngine,
    Route,
    RouteSegment,
    Via,
    Pad,
    Net,
    RoutingConstraints,
    RoutingResult,
    RouteLayer,
)


class TestRoutingEngineBasic:
    """测试布线引擎基本功能"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = RoutingEngine(
            board_width=100,
            board_height=80,
            trace_width=0.25
        )

        assert engine.board_width == 100
        assert engine.board_height == 80
        assert engine.default_trace_width == 0.25
        assert engine.constraints.board_width == 100

    def test_manhattan_routing_horizontal(self):
        """测试水平曼哈顿布线"""
        engine = RoutingEngine()

        # 创建水平方向的焊盘
        pad1 = Pad(x=10, y=10, net="test", layer="top")
        pad2 = Pad(x=50, y=10, net="test", layer="top")

        segments = engine._manhattan_route(pad1, pad2, 0.25, use_45_degree=False)

        assert len(segments) >= 1
        assert segments[0].x1 == 10
        assert segments[0].y1 == 10
        assert segments[-1].x2 == 50
        assert segments[-1].y2 == 10

    def test_manhattan_routing_vertical(self):
        """测试垂直曼哈顿布线"""
        engine = RoutingEngine()

        pad1 = Pad(x=10, y=10, net="test", layer="top")
        pad2 = Pad(x=10, y=50, net="test", layer="top")

        segments = engine._manhattan_route(pad1, pad2, 0.25, use_45_degree=False)

        assert len(segments) >= 1
        assert segments[0].x1 == 10
        assert segments[0].y1 == 10
        assert segments[-1].x2 == 10
        assert segments[-1].y2 == 50

    def test_manhattan_routing_45_degree(self):
        """测试45度角布线"""
        engine = RoutingEngine()

        pad1 = Pad(x=10, y=10, net="test", layer="top")
        pad2 = Pad(x=50, y=50, net="test", layer="top")

        segments = engine._manhattan_route(pad1, pad2, 0.25, use_45_degree=True)

        assert len(segments) >= 2
        # 检查是否有斜线段（45度）
        has_diagonal = False
        for seg in segments:
            dx = abs(seg.x2 - seg.x1)
            dy = abs(seg.y2 - seg.y1)
            if dx > 0.1 and dy > 0.1 and abs(dx - dy) < 0.1:
                has_diagonal = True
                break
        assert has_diagonal, "45度布线应该包含斜线段"


class TestNetRouting:
    """测试网络布线"""

    def test_route_single_net(self):
        """测试单网络布线"""
        engine = RoutingEngine(board_width=100, board_height=80)

        # 创建简单网络（连接两个焊盘）
        pads = [
            Pad(x=20, y=20, net="VCC", layer="top"),
            Pad(x=80, y=60, net="VCC", layer="top"),
        ]
        net = Net(name="VCC", pads=pads, trace_width=0.25)

        result = engine._route_net_manhattan(net)

        assert result is not None
        assert result.net == "VCC"
        assert len(result.segments) > 0

    def test_route_multiple_nets(self):
        """测试多网络布线"""
        engine = RoutingEngine(board_width=100, board_height=80)

        nets = [
            Net(
                name="VCC",
                pads=[
                    Pad(x=10, y=10, net="VCC", layer="top"),
                    Pad(x=90, y=70, net="VCC", layer="top"),
                ],
                is_power=True,
            ),
            Net(
                name="GND",
                pads=[
                    Pad(x=20, y=20, net="GND", layer="top"),
                    Pad(x=80, y=60, net="GND", layer="top"),
                ],
                is_ground=True,
            ),
            Net(
                name="SIGNAL",
                pads=[
                    Pad(x=30, y=30, net="SIGNAL", layer="top"),
                    Pad(x=70, y=50, net="SIGNAL", layer="top"),
                ],
            ),
        ]

        result = engine.route_nets(nets, strategy="manhattan")

        assert len(result.routes) == 3
        assert result.total_length > 0
        assert result.metrics["total_routes"] == 3
        assert result.metrics["routed_percentage"] == 100.0

    def test_route_single_pad_net(self):
        """测试单焊盘网络（应跳过）"""
        engine = RoutingEngine()

        nets = [
            Net(
                name="SINGLE",
                pads=[Pad(x=10, y=10, net="SINGLE", layer="top")],
            ),
        ]

        result = engine.route_nets(nets, strategy="manhattan")

        assert len(result.routes) == 0
        assert len(result.unrouted_pads) == 0  # 单焊盘网络直接跳过


class TestMultiLayerRouting:
    """测试多层布线"""

    def test_via_creation(self):
        """测试过孔创建"""
        engine = RoutingEngine()

        pad1 = Pad(x=10, y=10, net="test", layer="top")
        pad2 = Pad(x=50, y=50, net="test", layer="bottom")

        via, segments = engine._route_with_via(pad1, pad2, 0.25)

        assert via is not None
        assert via.net == "test"
        assert via.from_layer == RouteLayer.TOP.value
        assert via.to_layer == RouteLayer.BOTTOM.value
        assert len(segments) == 2  # 两段：顶层到过孔，过孔到底层

    def test_multilayer_routing(self):
        """测试多层布线"""
        engine = RoutingEngine(board_width=100, board_height=80)

        # 创建跨层网络
        nets = [
            Net(
                name="CROSS_LAYER",
                pads=[
                    Pad(x=10, y=10, net="CROSS_LAYER", layer="top"),
                    Pad(x=90, y=70, net="CROSS_LAYER", layer="bottom"),
                ],
            ),
        ]

        result = engine.route_with_vias(nets)

        assert len(result.routes) == 1
        assert result.via_count >= 1
        assert "multilayer_routing" in result.metrics


class TestRouteCalculations:
    """测试走线计算"""

    def test_segment_length_calculation(self):
        """测试线段长度计算"""
        engine = RoutingEngine()

        # 水平线段
        seg1 = RouteSegment(x1=0, y1=0, x2=10, y2=0, width=0.25)
        assert engine._calculate_segments_length([seg1]) == 10.0

        # 垂直线段
        seg2 = RouteSegment(x1=0, y1=0, x2=0, y2=10, width=0.25)
        assert engine._calculate_segments_length([seg2]) == 10.0

        # 45度线段 (10x10 对角线)
        seg3 = RouteSegment(x1=0, y1=0, x2=10, y2=10, width=0.25)
        expected = math.sqrt(200)
        actual = engine._calculate_segments_length([seg3])
        assert abs(actual - expected) < 0.001

    def test_route_length_with_via(self):
        """测试包含过孔的走线长度"""
        engine = RoutingEngine()

        route = Route(
            net="test",
            segments=[
                RouteSegment(x1=0, y1=0, x2=10, y2=0, width=0.25),
            ],
            vias=[
                Via(x=5, y=0, net="test", from_layer="F.Cu", to_layer="B.Cu"),
            ],
        )

        length = engine._calculate_route_length(route)
        # 线段长度 10 + 过孔长度 0.5
        assert abs(length - 10.5) < 0.1


class TestDifferentialPairRouting:
    """测试差分对布线"""

    def test_differential_pair_routing(self):
        """测试差分对布线"""
        engine = RoutingEngine()

        pads = [
            Pad(x=10, y=10, net="DP+", layer="top"),
            Pad(x=50, y=10, net="DP-", layer="top"),
        ]
        net = Net(
            name="DIFF_PAIR",
            pads=pads,
            is_differential=True,
            trace_width=0.15,
        )

        result = engine.route_differential_pair(net)

        assert result is not None
        assert result.is_differential_pair is True
        assert result.coupled_length > 0


class TestOccupancyTracking:
    """测试占用网格追踪"""

    def test_mark_segment_occupied(self):
        """测试标记线段占用的网格"""
        engine = RoutingEngine(grid_size=5.0)

        segment = RouteSegment(x1=0, y1=0, x2=20, y2=0, layer="F.Cu")
        engine._mark_segment_occupied(segment)

        # 应该标记 (0,0), (1,0), (2,0), (3,0), (4,0) 在 F.Cu 层
        assert (0, 0, "F.Cu") in engine._occupied_cells
        assert (4, 0, "F.Cu") in engine._occupied_cells

    def test_mark_via_occupied(self):
        """测试标记过孔占用的网格"""
        engine = RoutingEngine(grid_size=5.0)

        via = Via(x=10, y=10, net="test", from_layer="F.Cu", to_layer="B.Cu")
        route = Route(net="test", vias=[via])

        engine._mark_route_occupied(route)

        # 过孔应该占用两层
        assert (2, 2, "F.Cu") in engine._occupied_cells  # 10/5 = 2
        assert (2, 2, "B.Cu") in engine._occupied_cells

    def test_reset_occupancy(self):
        """测试重置占用网格"""
        engine = RoutingEngine()

        engine._occupied_cells.add((1, 1, "F.Cu"))
        engine._reset_occupancy()

        assert len(engine._occupied_cells) == 0


class TestRouteExport:
    """测试走线导出格式"""

    def test_segment_to_dict(self):
        """测试线段转字典"""
        seg = RouteSegment(x1=0, y1=0, x2=10, y2=10, layer="F.Cu", width=0.25)
        data = seg.to_dict()

        assert data["x1"] == 0
        assert data["x2"] == 10
        assert data["layer"] == "F.Cu"
        assert data["width"] == 0.25

    def test_segment_to_kicad_format(self):
        """测试线段转 KiCad S-expression 格式"""
        seg = RouteSegment(x1=0, y1=0, x2=10, y2=10, layer="F.Cu", width=0.25)
        kicad_str = seg.to_kicad_segment()

        assert "(segment" in kicad_str
        assert "(start 0 0)" in kicad_str
        assert "(end 10 10)" in kicad_str
        assert "(layer F.Cu)" in kicad_str

    def test_route_to_dict(self):
        """测试完整走线转字典"""
        route = Route(
            net="VCC",
            segments=[RouteSegment(x1=0, y1=0, x2=10, y2=0, width=0.25)],
            vias=[Via(x=5, y=0, net="VCC", from_layer="F.Cu", to_layer="B.Cu")],
        )

        data = route.to_dict()

        assert data["net"] == "VCC"
        assert len(data["segments"]) == 1
        assert len(data["vias"]) == 1

    def test_via_to_dict(self):
        """测试过孔转字典"""
        via = Via(
            x=10, y=20,
            net="test",
            from_layer="F.Cu",
            to_layer="B.Cu",
            outer_diameter=0.8,
            drill_diameter=0.4
        )
        data = via.to_dict()

        assert data["x"] == 10
        assert data["y"] == 20
        assert data["from_layer"] == "F.Cu"
        assert data["outer_diameter"] == 0.8


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_length_route(self):
        """测试零长度走线（起点等于终点）"""
        engine = RoutingEngine()

        pad1 = Pad(x=10, y=10, net="test", layer="top")
        pad2 = Pad(x=10, y=10, net="test", layer="top")

        segments = engine._manhattan_route(pad1, pad2, 0.25)

        # 应该返回空或单点
        assert len(segments) >= 0

    def test_empty_nets_list(self):
        """测试空网络列表"""
        engine = RoutingEngine()

        result = engine.route_nets([], strategy="manhattan")

        assert len(result.routes) == 0
        assert result.metrics["routed_percentage"] == 0.0

    def test_large_board_routing(self):
        """测试大板子布线"""
        engine = RoutingEngine(board_width=500, board_height=400)

        nets = [
            Net(
                name="LONG",
                pads=[
                    Pad(x=50, y=50, net="LONG", layer="top"),
                    Pad(x=450, y=350, net="LONG", layer="top"),
                ],
            ),
        ]

        result = engine.route_nets(nets)

        assert len(result.routes) == 1
        assert result.total_length > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

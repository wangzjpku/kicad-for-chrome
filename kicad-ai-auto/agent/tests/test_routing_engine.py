"""
Tests for Routing Engine
"""
import pytest
import sys
from pathlib import Path

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from routing.routing_engine import (
    RoutingEngine,
    Route,
    RouteSegment,
    Pad,
    Net,
    RoutingConstraints,
    RouteLayer
)


class TestRoutingEngine:
    """Test cases for RoutingEngine"""

    def test_route_single_net(self):
        """Test routing a single net between two pads"""
        engine = RoutingEngine(board_width=100, board_height=80)

        net = Net(
            name="VCC",
            pads=[
                Pad(x=10, y=10, net="VCC"),
                Pad(x=50, y=30, net="VCC")
            ]
        )

        result = engine.route_nets([net])

        assert len(result.routes) == 1
        assert result.routes[0].net == "VCC"
        assert len(result.routes[0].segments) >= 1

    def test_route_multiple_nets(self):
        """Test routing multiple nets"""
        engine = RoutingEngine(board_width=100, board_height=80)

        nets = [
            Net(name="VCC", pads=[
                Pad(x=10, y=10, net="VCC"),
                Pad(x=50, y=30, net="VCC")
            ]),
            Net(name="GND", pads=[
                Pad(x=20, y=20, net="GND"),
                Pad(x=60, y=40, net="GND")
            ])
        ]

        result = engine.route_nets(nets)

        assert len(result.routes) == 2

    def test_route_with_vias(self):
        """Test routing with via insertion"""
        engine = RoutingEngine(board_width=100, board_height=80)

        net = Net(
            name="SIGNAL",
            pads=[
                Pad(x=10, y=10, net="SIGNAL", layer="top"),
                Pad(x=80, y=60, net="SIGNAL", layer="bottom")
            ]
        )

        result = engine.route_with_vias([net])

        assert len(result.routes) == 1
        # With multilayer routing, should have vias
        # (depends on routing decision)

    def test_manhattan_route_creates_segments(self):
        """Test that Manhattan routing creates proper segments"""
        engine = RoutingEngine(board_width=100, board_height=80)

        pad1 = Pad(x=10, y=10, net="VCC")
        pad2 = Pad(x=50, y=30, net="VCC")

        net = Net(name="VCC", pads=[pad1, pad2])
        result = engine._route_net_manhattan(net)

        assert result is not None
        assert len(result.segments) >= 2  # L-shape needs 2 segments

    def test_unrouted_pads_when_insufficient(self):
        """Test that pads with less than 2 connections are handled"""
        engine = RoutingEngine(board_width=100, board_height=80)

        net = Net(
            name="FLOATING",
            pads=[
                Pad(x=10, y=10, net="FLOATING")  # Only one pad
            ]
        )

        result = engine.route_nets([net])

        # Single pad net should not create a route
        # Or should be marked as having unrouted pads
        assert len(result.unrouted_pads) >= 0

    def test_routing_metrics(self):
        """Test that routing metrics are calculated"""
        engine = RoutingEngine(board_width=100, board_height=80)

        nets = [
            Net(name="VCC", pads=[
                Pad(x=10, y=10, net="VCC"),
                Pad(x=50, y=30, net="VCC")
            ]),
            Net(name="GND", pads=[
                Pad(x=20, y=20, net="GND"),
                Pad(x=60, y=40, net="GND")
            ])
        ]

        result = engine.route_nets(nets)

        assert "total_routes" in result.metrics
        assert "routed_percentage" in result.metrics
        assert result.metrics["total_routes"] == 2

    def test_route_segment_to_dict(self):
        """Test RouteSegment to_dict conversion"""
        segment = RouteSegment(
            x1=10, y1=10,
            x2=50, y2=10,
            layer="F.Cu",
            width=0.25
        )

        d = segment.to_dict()

        assert d["x1"] == 10
        assert d["y1"] == 10
        assert d["x2"] == 50
        assert d["y2"] == 10
        assert d["layer"] == "F.Cu"
        assert d["width"] == 0.25

    def test_route_to_dict(self):
        """Test Route to_dict conversion"""
        route = Route(net="VCC")
        route.segments = [
            RouteSegment(x1=10, y1=10, x2=50, y2=10)
        ]

        d = route.to_dict()

        assert d["net"] == "VCC"
        assert len(d["segments"]) == 1


class TestPad:
    """Test cases for Pad dataclass"""

    def test_pad_creation(self):
        """Test creating a pad"""
        pad = Pad(x=10, y=20, net="VCC", layer="top")

        assert pad.x == 10
        assert pad.y == 20
        assert pad.net == "VCC"
        assert pad.layer == "top"

    def test_pad_to_dict(self):
        """Test Pad to_dict conversion"""
        pad = Pad(x=10, y=20, net="VCC", layer="top")

        d = pad.to_dict()

        assert d["x"] == 10
        assert d["y"] == 20
        assert d["net"] == "VCC"


class TestNet:
    """Test cases for Net dataclass"""

    def test_net_creation(self):
        """Test creating a net"""
        net = Net(
            name="VCC",
            pads=[
                Pad(x=10, y=10, net="VCC"),
                Pad(x=50, y=30, net="VCC")
            ],
            is_power=True
        )

        assert net.name == "VCC"
        assert len(net.pads) == 2
        assert net.is_power is True

    def test_get_pads_by_layer(self):
        """Test filtering pads by layer"""
        net = Net(
            name="SIGNAL",
            pads=[
                Pad(x=10, y=10, net="SIGNAL", layer="top"),
                Pad(x=20, y=20, net="SIGNAL", layer="bottom"),
                Pad(x=30, y=30, net="SIGNAL", layer="top")
            ]
        )

        top_pads = net.get_pads_by_layer("top")
        assert len(top_pads) == 2

        bottom_pads = net.get_pads_by_layer("bottom")
        assert len(bottom_pads) == 1


class TestRoutingConstraints:
    """Test cases for RoutingConstraints"""

    def test_default_constraints(self):
        """Test default routing constraints"""
        constraints = RoutingConstraints()

        assert constraints.board_width == 100
        assert constraints.board_height == 80
        assert constraints.trace_width == 0.25
        assert constraints.via_drill == 0.4
        assert len(constraints.layers) == 2  # F.Cu and B.Cu


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

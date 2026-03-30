"""
PCB Routing Engine

Handles trace routing on PCB boards with support for:
- Manhattan routing (L-shaped and Z-shaped routes)
- Multi-layer routing with automatic via insertion
- Differential pair routing
- High-speed signal optimization
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum
import math
import random


class RouteLayer(Enum):
    """PCB layer types"""
    TOP = "F.Cu"           # Top copper layer
    BOTTOM = "B.Cu"        # Bottom copper layer
    INNER1 = "In1.Cu"     # Inner layer 1
    INNER2 = "In2.Cu"     # Inner layer 2
    POWER = "F.Cu"         # Power plane


@dataclass
class Pad:
    """Represents a component pad to connect"""
    x: float
    y: float
    net: str
    layer: str = "top"
    width: float = 0.0  # Pad width (for SMD) or 0 for through-hole
    height: float = 0.0
    drill: float = 0.0  # Drill diameter for through-hole

    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "net": self.net,
            "layer": self.layer
        }


@dataclass
class Via:
    """Represents a PCB via"""
    x: float
    y: float
    net: str
    from_layer: str
    to_layer: str
    outer_diameter: float = 0.8  # Default 0.8mm
    drill_diameter: float = 0.4  # Default 0.4mm

    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "net": self.net,
            "from_layer": self.from_layer,
            "to_layer": self.to_layer,
            "outer_diameter": self.outer_diameter,
            "drill_diameter": self.drill_diameter
        }


@dataclass
class RouteSegment:
    """A single straight line segment"""
    x1: float
    y1: float
    x2: float
    y2: float
    layer: str = "F.Cu"
    width: float = 0.25  # Default trace width 0.25mm

    def to_dict(self) -> Dict:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "layer": self.layer,
            "width": self.width
        }

    def to_kicad_segment(self) -> str:
        """Convert to KiCad S-expression format"""
        return f"(segment (start {self.x1} {self.y1}) (end {self.x2} {self.y2}) (layer {self.layer}) (width {self.width}))"


@dataclass
class Route:
    """Complete route for a net"""
    net: str
    segments: List[RouteSegment] = field(default_factory=list)
    vias: List[Via] = field(default_factory=list)
    is_differential_pair: bool = False
    coupled_length: float = 0.0  # For differential pairs

    def to_dict(self) -> Dict:
        return {
            "net": self.net,
            "segments": [s.to_dict() for s in self.segments],
            "vias": [v.to_dict() for v in self.vias],
            "is_differential_pair": self.is_differential_pair,
            "coupled_length": self.coupled_length
        }

    def to_kicad_wires(self) -> str:
        """Convert to KiCad S-expression wire format"""
        wires = []
        for seg in self.segments:
            wires.append(f"(wire (pts (xy {seg.x1} {seg.y1}) (xy {seg.x2} {seg.y2})) (layer {seg.layer}) (width {seg.width}))")
        return "\n".join(wires)


@dataclass
class Net:
    """Represents an electrical net to be routed"""
    name: str
    pads: List[Pad] = field(default_factory=list)
    is_power: bool = False
    is_ground: bool = False
    is_high_speed: bool = False
    is_differential: bool = False
    target_impedance: Optional[float] = None  # Ohms
    trace_width: float = 0.25  # mm
    clearance: float = 0.2  # mm

    def get_pads_by_layer(self, layer: str) -> List[Pad]:
        return [p for p in self.pads if p.layer == layer]


@dataclass
class RoutingConstraints:
    """Constraints for routing"""
    board_width: float = 100
    board_height: float = 80
    margin: float = 2.0
    grid_size: float = 2.5  # KiCad default
    trace_width: float = 0.25
    via_size: float = 0.8
    via_drill: float = 0.4
    clearance: float = 0.2
    layers: List[str] = field(default_factory=lambda: ["F.Cu", "B.Cu"])
    min_via_spacing: float = 0.5


@dataclass
class RoutingResult:
    """Result of routing operation"""
    routes: List[Route]
    unrouted_pads: List[Pad]
    total_length: float
    via_count: int
    metrics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "routes": [r.to_dict() for r in self.routes],
            "unrouted_pads": [p.to_dict() for p in self.unrouted_pads],
            "total_length": self.total_length,
            "via_count": self.via_count,
            "metrics": self.metrics
        }


class RoutingEngine:
    """
    PCB Routing Engine

    Provides intelligent trace routing with support for:
    - Manhattan routing (L-shaped, Z-shaped routes)
    - Multi-layer routing with automatic via insertion
    - Differential pair routing
    - High-speed signal optimization
    """

    def __init__(
        self,
        board_width: float = 100,
        board_height: float = 80,
        grid_size: float = 2.5,
        trace_width: float = 0.25
    ):
        self.board_width = board_width
        self.board_height = board_height
        self.grid_size = grid_size
        self.default_trace_width = trace_width

        self.constraints = RoutingConstraints(
            board_width=board_width,
            board_height=board_height,
            grid_size=grid_size,
            trace_width=trace_width
        )

        # Track occupied grid cells for collision avoidance
        self._occupied_cells: Set[Tuple[int, int, str]] = set()

    def route_nets(
        self,
        nets: List[Net],
        strategy: str = "manhattan"
    ) -> RoutingResult:
        """
        Route all nets on the board

        Args:
            nets: List of nets to route
            strategy: Routing strategy ("manhattan", "auto")

        Returns:
            RoutingResult with routes and metrics
        """
        self._reset_occupancy()
        routes = []
        unrouted_pads = []

        for net in nets:
            if len(net.pads) < 2:
                continue

            if strategy == "manhattan":
                result = self._route_net_manhattan(net)
            else:
                result = self._route_net_manhattan(net)

            if result:
                routes.append(result)
                self._mark_route_occupied(result)
            else:
                unrouted_pads.extend(net.pads)

        # Calculate metrics
        total_length = sum(
            self._calculate_route_length(r) for r in routes
        )
        via_count = sum(len(r.vias) for r in routes)

        metrics = {
            "total_routes": len(routes),
            "total_nets": len(nets),
            "routed_percentage": len(routes) / len(nets) * 100 if nets else 0,
            "average_length": total_length / len(routes) if routes else 0
        }

        return RoutingResult(
            routes=routes,
            unrouted_pads=unrouted_pads,
            total_length=total_length,
            via_count=via_count,
            metrics=metrics
        )

    def route_with_vias(
        self,
        nets: List[Net]
    ) -> RoutingResult:
        """
        Route nets with automatic layer changes via vias

        Uses both layers (F.Cu and B.Cu) for routing.
        Inserts vias when a more efficient route is possible.

        Args:
            nets: List of nets to route

        Returns:
            RoutingResult with multi-layer routes
        """
        self._reset_occupancy()
        routes = []
        unrouted_pads = []

        for net in nets:
            if len(net.pads) < 2:
                continue

            result = self._route_net_multilayer(net)

            if result:
                routes.append(result)
                self._mark_route_occupied(result)
            else:
                unrouted_pads.extend(net.pads)

        total_length = sum(self._calculate_route_length(r) for r in routes)
        via_count = sum(len(r.vias) for r in routes)

        metrics = {
            "total_routes": len(routes),
            "routed_percentage": len(routes) / len(nets) * 100 if nets else 0,
            "multilayer_routing": True
        }

        return RoutingResult(
            routes=routes,
            unrouted_pads=unrouted_pads,
            total_length=total_length,
            via_count=via_count,
            metrics=metrics
        )

    def _route_net_manhattan(self, net: Net) -> Optional[Route]:
        """Route a single net using Manhattan (L-shaped) routing"""
        if len(net.pads) < 2:
            return None

        route = Route(net=net.name)
        pads = net.pads.copy()

        # Connect first pad to all others
        source = pads[0]
        for target in pads[1:]:
            segments = self._manhattan_route(source, target, net.trace_width)
            route.segments.extend(segments)
            source = target  # Continue from last connected point

        return route

    def _route_net_multilayer(self, net: Net) -> Optional[Route]:
        """Route a single net using multi-layer with vias"""
        if len(net.pads) < 2:
            return None

        route = Route(net=net.name)
        pads = net.pads.copy()

        source = pads[0]
        for target in pads[1:]:
            # Try single layer first
            single_layer = self._manhattan_route(source, target, net.trace_width)

            # Calculate route length
            single_length = self._calculate_segments_length(single_layer)

            # Try with via
            via, via_route = self._route_with_via(source, target, net.trace_width)
            via_length = self._calculate_segments_length(via_route) if via_route else float('inf')

            # Choose shorter route
            if single_length <= via_length:
                route.segments.extend(single_layer)
            else:
                route.segments.extend(via_route)
                if via:
                    route.vias.append(via)

            source = target

        return route

    def _manhattan_route(
        self,
        pad1: Pad,
        pad2: Pad,
        trace_width: float,
        use_45_degree: bool = True
    ) -> List[RouteSegment]:
        """
        Create route between two pads

        Args:
            pad1: Starting pad
            pad2: Ending pad
            trace_width: Width of the trace
            use_45_degree: If True, use 45-degree angles instead of 90-degree
        """
        segments = []

        x1, y1 = pad1.x, pad1.y
        x2, y2 = pad2.x, pad2.y

        layer = RouteLayer.TOP.value if pad1.layer == "top" else RouteLayer.BOTTOM.value

        dx = x2 - x1
        dy = y2 - y1

        if use_45_degree and abs(dx) > 0.1 and abs(dy) > 0.1:
            # 45-degree routing: create diagonal segment then straight
            if abs(dx) > abs(dy):
                # More horizontal: diagonal first, then horizontal
                diag_len = abs(dy)
                diag_x = x1 + (diag_len if dx > 0 else -diag_len)
                segments.append(RouteSegment(
                    x1=x1, y1=y1,
                    x2=diag_x, y2=y2,
                    layer=layer, width=trace_width
                ))
                segments.append(RouteSegment(
                    x1=diag_x, y1=y2,
                    x2=x2, y2=y2,
                    layer=layer, width=trace_width
                ))
            else:
                # More vertical: diagonal first, then vertical
                diag_len = abs(dx)
                diag_y = y1 + (diag_len if dy > 0 else -diag_len)
                segments.append(RouteSegment(
                    x1=x1, y1=y1,
                    x2=x2, y2=diag_y,
                    layer=layer, width=trace_width
                ))
                segments.append(RouteSegment(
                    x1=x2, y1=diag_y,
                    x2=x2, y2=y2,
                    layer=layer, width=trace_width
                ))
        else:
            # Standard Manhattan (L-shaped) routing
            if random.choice([True, False]):
                mid_x = x2
                segments.append(RouteSegment(
                    x1=x1, y1=y1,
                    x2=mid_x, y2=y1,
                    layer=layer, width=trace_width
                ))
                segments.append(RouteSegment(
                    x1=mid_x, y1=y1,
                    x2=mid_x, y2=y2,
                    layer=layer, width=trace_width
                ))
            else:
                mid_y = y2
                segments.append(RouteSegment(
                    x1=x1, y1=y1,
                    x2=x1, y2=mid_y,
                    layer=layer, width=trace_width
                ))
                segments.append(RouteSegment(
                    x1=x1, y1=mid_y,
                    x2=x2, y2=mid_y,
                    layer=layer, width=trace_width
                ))

        return segments

    def _route_with_via(
        self,
        pad1: Pad,
        pad2: Pad,
        trace_width: float
    ) -> Tuple[Optional[Via], List[RouteSegment]]:
        """Route between pads using a via for layer change"""
        x1, y1 = pad1.x, pad1.y
        x2, y2 = pad2.x, pad2.y

        # Choose via position (middle of the board)
        via_x = (x1 + x2) / 2
        via_y = (y1 + y2) / 2

        # Snap to grid
        via_x = round(via_x / self.grid_size) * self.grid_size
        via_y = round(via_y / self.grid_size) * self.grid_size

        via = Via(
            x=via_x, y=via_y,
            net=pad1.net,
            from_layer=RouteLayer.TOP.value,
            to_layer=RouteLayer.BOTTOM.value
        )

        segments = []

        # Top layer: pad1 to via
        segments.append(RouteSegment(
            x1=x1, y1=y1,
            x2=via_x, y2=via_y,
            layer=RouteLayer.TOP.value,
            width=trace_width
        ))

        # Bottom layer: via to pad2
        segments.append(RouteSegment(
            x1=via_x, y1=via_y,
            x2=x2, y2=y2,
            layer=RouteLayer.BOTTOM.value,
            width=trace_width
        ))

        return via, segments

    def route_differential_pair(
        self,
        net: Net,
        target_length_mismatch: float = 0.1  # mm
    ) -> Optional[Route]:
        """
        Route a differential pair with length matching

        Args:
            net: Differential pair net
            target_length_mismatch: Maximum allowed length mismatch in mm

        Returns:
            Route with matched differential pair traces
        """
        if not net.is_differential or len(net.pads) < 2:
            return None

        route = Route(net=net.name, is_differential_pair=True)
        pads = net.pads.copy()

        # Simple implementation: route both traces with same path
        source = pads[0]
        for target in pads[1:]:
            # Route positive trace
            pos_segments = self._manhattan_route(source, target, net.trace_width)
            route.segments.extend(pos_segments)

            # Route negative trace (offset by 2*trace_width + clearance)
            offset = net.trace_width * 2 + self.constraints.clearance
            neg_source = Pad(
                x=source.x + offset,
                y=source.y,
                net=source.net,
                layer=source.layer
            )
            neg_target = Pad(
                x=target.x + offset,
                y=target.y,
                net=target.net,
                layer=target.layer
            )
            neg_segments = self._manhattan_route(neg_source, neg_target, net.trace_width)
            route.segments.extend(neg_segments)

            # Calculate coupled length
            route.coupled_length = self._calculate_segments_length(pos_segments)

        return route

    def _calculate_route_length(self, route: Route) -> float:
        """Calculate total route length"""
        segment_length = self._calculate_segments_length(route.segments)
        via_length = len(route.vias) * 0.5  # Approximate via length (0.5mm per via)
        return segment_length + via_length

    def _calculate_segments_length(self, segments: List[RouteSegment]) -> float:
        """Calculate total length of segments"""
        total = 0.0
        for seg in segments:
            total += math.sqrt((seg.x2 - seg.x1) ** 2 + (seg.y2 - seg.y1) ** 2)
        return total

    def _reset_occupancy(self):
        """Reset occupied cell tracking"""
        self._occupied_cells = set()

    def _mark_route_occupied(self, route: Route):
        """Mark cells as occupied by a route"""
        for segment in route.segments:
            self._mark_segment_occupied(segment)

        for via in route.vias:
            gx = int(via.x / self.grid_size)
            gy = int(via.y / self.grid_size)
            self._occupied_cells.add((gx, gy, via.from_layer))
            self._occupied_cells.add((gx, gy, via.to_layer))

    def _mark_segment_occupied(self, segment: RouteSegment):
        """Mark cells occupied by a segment"""
        steps = max(
            abs(int((segment.x2 - segment.x1) / self.grid_size)),
            abs(int((segment.y2 - segment.y1) / self.grid_size))
        )
        steps = max(steps, 1)

        for i in range(steps + 1):
            t = i / steps
            x = segment.x1 + (segment.x2 - segment.x1) * t
            y = segment.y1 + (segment.y2 - segment.y1) * t
            gx = int(x / self.grid_size)
            gy = int(y / self.grid_size)
            self._occupied_cells.add((gx, gy, segment.layer))

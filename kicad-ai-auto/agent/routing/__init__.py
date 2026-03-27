"""
PCB Routing Engine

Provides AI-powered routing for PCB designs with support for:
- Manhattan routing (horizontal/vertical)
- Multi-layer routing with vias
- Differential pair routing
- High-speed signal routing
"""

from .routing_engine import (
    RoutingEngine,
    Route,
    RouteSegment,
    Pad,
    Net,
    RoutingConstraints,
    RoutingResult
)

__all__ = [
    "RoutingEngine",
    "Route",
    "RouteSegment",
    "Pad",
    "Net",
    "RoutingConstraints",
    "RoutingResult"
]

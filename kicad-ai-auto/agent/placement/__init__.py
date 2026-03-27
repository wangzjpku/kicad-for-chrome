"""
PCB Component Placement Engine

Provides AI-powered component placement for PCB designs with support for:
- Grid-based placement with collision avoidance
- Thermal-aware placement
- Signal integrity optimization
- Multi-board support
"""

from .placement_engine import (
    PlacementEngine,
    Placement,
    Component,
    BoardConstraints,
    PlacementResult
)

__all__ = [
    "PlacementEngine",
    "Placement",
    "Component",
    "BoardConstraints",
    "PlacementResult"
]

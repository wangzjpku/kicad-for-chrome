# -*- coding: utf-8 -*-
"""
Layout Candidate Generator - Generate multiple layout strategies for comparison.

Produces 3 candidate layouts with different optimization goals:
1. Compact: Minimize board area
2. Balanced: Trade-off area, routing, and thermal
3. Thermal: Prioritize heat dissipation and routing ease
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

from placement.smart_placement_engine import SmartPlacementEngine, Component

logger = logging.getLogger(__name__)


class LayoutStrategy(Enum):
    COMPACT = "compact"
    BALANCED = "balanced"
    THERMAL = "thermal"


@dataclass
class LayoutCandidate:
    """A single layout candidate"""
    strategy: LayoutStrategy
    positions: Dict[str, Dict[str, float]]
    board_utilization: float = 0.0
    estimated_wire_length: float = 0.0
    thermal_score: float = 0.0
    routing_score: float = 0.0
    overall_score: float = 0.0
    description: str = ""


class LayoutCandidateGenerator:
    """Generate multiple layout candidates for comparison."""

    def __init__(self, board_width=100.0, board_height=80.0):
        self.board_width = board_width
        self.board_height = board_height

    def generate_candidates(
        self,
        components: List[Component],
        net_connections: Optional[List[Tuple[str, str, str]]] = None,
    ) -> List[LayoutCandidate]:
        """
        Generate 3 layout candidates with different strategies.

        Args:
            components: List of components to place
            net_connections: List of (net_name, ref1, ref2) tuples for wire length estimation

        Returns:
            List of 3 LayoutCandidate objects
        """
        candidates = []

        # Candidate 1: Compact (tight packing)
        c1 = self._generate_compact(components, net_connections)
        candidates.append(c1)

        # Candidate 2: Balanced (spacing for routing)
        c2 = self._generate_balanced(components, net_connections)
        candidates.append(c2)

        # Candidate 3: Thermal (spread out for cooling)
        c3 = self._generate_thermal(components, net_connections)
        candidates.append(c3)

        return candidates

    def _generate_compact(
        self,
        components: List[Component],
        net_connections: Optional[List[Tuple[str, str, str]]],
    ) -> LayoutCandidate:
        """Compact layout: minimize board area, tight spacing."""
        engine = SmartPlacementEngine(
            board_width=self.board_width * 0.8,  # Tighter board
            board_height=self.board_height * 0.8,
            margin=2.0,
            spacing=0.5,  # Minimal spacing
        )
        result = engine.place(components)

        wire_len = self._estimate_wire_length(result.positions, net_connections)
        util = self._calc_utilization(result.positions, components, engine)
        thermal = self._calc_thermal_score(result.positions, components, engine)
        routing = self._calc_routing_score(wire_len, len(components))

        overall = (
            util * 0.40 +       # Area efficiency weighted high
            routing * 0.35 +
            thermal * 0.15 +
            (100 - result.score) * 0.10  # Invert overlap penalty
        )

        return LayoutCandidate(
            strategy=LayoutStrategy.COMPACT,
            positions=result.positions,
            board_utilization=util,
            estimated_wire_length=wire_len,
            thermal_score=thermal,
            routing_score=routing,
            overall_score=max(0, min(100, overall)),
            description=f"Compact: {util:.0f}% utilization, {wire_len:.0f}mm wire, tight 0.5mm spacing",
        )

    def _generate_balanced(
        self,
        components: List[Component],
        net_connections: Optional[List[Tuple[str, str, str]]],
    ) -> LayoutCandidate:
        """Balanced layout: reasonable spacing for routing."""
        engine = SmartPlacementEngine(
            board_width=self.board_width,
            board_height=self.board_height,
            margin=3.0,
            spacing=2.0,  # Standard spacing
        )
        result = engine.place(components)

        wire_len = self._estimate_wire_length(result.positions, net_connections)
        util = self._calc_utilization(result.positions, components, engine)
        thermal = self._calc_thermal_score(result.positions, components, engine)
        routing = self._calc_routing_score(wire_len, len(components))

        overall = (
            util * 0.25 +
            routing * 0.35 +
            thermal * 0.25 +
            result.score * 0.15
        )

        return LayoutCandidate(
            strategy=LayoutStrategy.BALANCED,
            positions=result.positions,
            board_utilization=util,
            estimated_wire_length=wire_len,
            thermal_score=thermal,
            routing_score=routing,
            overall_score=max(0, min(100, overall)),
            description=f"Balanced: {util:.0f}% utilization, {wire_len:.0f}mm wire, 2mm spacing",
        )

    def _generate_thermal(
        self,
        components: List[Component],
        net_connections: Optional[List[Tuple[str, str, str]]],
    ) -> LayoutCandidate:
        """Thermal layout: spread components for heat dissipation."""
        engine = SmartPlacementEngine(
            board_width=self.board_width * 1.1,  # Slightly larger
            board_height=self.board_height * 1.1,
            margin=5.0,
            spacing=3.0,  # Generous spacing
        )
        result = engine.place(components)

        # Spread hot components to edges
        positions = self._spread_hot_components(
            result.positions, components, engine
        )

        wire_len = self._estimate_wire_length(positions, net_connections)
        util = self._calc_utilization(positions, components, engine)
        thermal = self._calc_thermal_score(positions, components, engine)
        routing = self._calc_routing_score(wire_len, len(components))

        overall = (
            util * 0.15 +
            routing * 0.25 +
            thermal * 0.45 +
            result.score * 0.15
        )

        return LayoutCandidate(
            strategy=LayoutStrategy.THERMAL,
            positions=positions,
            board_utilization=util,
            estimated_wire_length=wire_len,
            thermal_score=thermal,
            routing_score=routing,
            overall_score=max(0, min(100, overall)),
            description=f"Thermal: {util:.0f}% utilization, {wire_len:.0f}mm wire, 3mm spacing, hot parts spread",
        )

    def _spread_hot_components(
        self,
        positions: Dict[str, Dict[str, float]],
        components: List[Component],
        engine: SmartPlacementEngine,
    ) -> Dict[str, Dict[str, float]]:
        """Move hot components toward board edges for better cooling."""
        hot_keywords = ["ldo", "dcdc", "mosfet", "fet", "regulator", "bridge", "rectifier"]
        positions = {k: v.copy() for k, v in positions.items()}

        for comp in components:
            val = (comp.value or "").lower()
            if any(kw in val for kw in hot_keywords):
                if comp.reference in positions:
                    pos = positions[comp.reference]
                    # Move toward nearest edge
                    margin = engine.margin + 2
                    if pos["x"] < engine.board_width / 2:
                        pos["x"] = max(margin, pos["x"] - 5)
                    else:
                        pos["x"] = min(engine.board_width - margin, pos["x"] + 5)

        return positions

    def _estimate_wire_length(
        self,
        positions: Dict[str, Dict[str, float]],
        net_connections: Optional[List[Tuple[str, str, str]]],
    ) -> float:
        """Estimate total wire length (Manhattan distance)."""
        if not net_connections:
            return 0.0

        total = 0.0
        for net, ref1, ref2 in net_connections:
            if ref1 in positions and ref2 in positions:
                p1 = positions[ref1]
                p2 = positions[ref2]
                total += abs(p1["x"] - p2["x"]) + abs(p1["y"] - p2["y"])

        return total

    def _calc_utilization(
        self,
        positions: Dict[str, Dict[str, float]],
        components: List[Component],
        engine: SmartPlacementEngine,
    ) -> float:
        """Calculate board utilization percentage."""
        comp_area = sum(c.width * c.height for c in components)
        board_area = engine.board_width * engine.board_height
        return min(100, (comp_area / board_area) * 100) if board_area > 0 else 0

    def _calc_thermal_score(
        self,
        positions: Dict[str, Dict[str, float]],
        components: List[Component],
        engine: SmartPlacementEngine,
    ) -> float:
        """Score thermal performance (higher = better heat dissipation)."""
        if not positions:
            return 50.0

        comp_dict = {c.reference: c for c in components}
        total_spacing = 0.0
        count = 0

        refs = list(positions.keys())
        for i, r1 in enumerate(refs):
            for r2 in refs[i + 1:]:
                if r1 in positions and r2 in positions:
                    p1, p2 = positions[r1], positions[r2]
                    dist = math.sqrt((p1["x"] - p2["x"])**2 + (p1["y"] - p2["y"])**2)
                    total_spacing += dist
                    count += 1

        avg_spacing = total_spacing / count if count > 0 else 0
        # More spacing = better thermal (but diminishing returns)
        if avg_spacing >= 15:
            return 95.0
        elif avg_spacing >= 10:
            return 80.0
        elif avg_spacing >= 5:
            return 60.0
        else:
            return max(20, avg_spacing * 10)

    def _calc_routing_score(self, wire_length: float, num_components: int) -> float:
        """Score routing feasibility (shorter = better)."""
        if num_components == 0:
            return 100.0

        # Normalize by number of components
        avg_len = wire_length / max(num_components, 1)

        if avg_len <= 10:
            return 95.0
        elif avg_len <= 20:
            return 80.0
        elif avg_len <= 40:
            return 60.0
        else:
            return max(20, 100 - avg_len)

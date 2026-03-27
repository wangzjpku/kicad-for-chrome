"""
PCB Placement Engine

Handles component placement on PCB boards with collision avoidance,
thermal awareness, and signal integrity considerations.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum
import math
import random


class PlacementStrategy(Enum):
    """Placement strategy types"""
    GRID = "grid"                    # Simple grid-based placement
    THERMAL_AWARE = "thermal"       # Thermal optimization
    SIGNAL_INTEGRITY = "signal"      # Signal integrity optimization
    BALANCED = "balanced"           # Balanced approach


@dataclass
class Component:
    """Represents a PCB component to be placed"""
    ref: str                          # Reference designator (e.g., "R1", "U1")
    width: float                       # Width in mm
    height: float                      # Height in mm
    thermal_load: float = 0.0         # Thermal output 0.0-1.0
    is_high_speed: bool = False       # High-speed signal component
    is_power: bool = False            # Power component
    is_through_hole: bool = False     # Through-hole vs SMD
    rotation: float = 0.0             # Current rotation in degrees
    pins: List[Tuple[float, float]] = field(default_factory=list)  # Pin positions relative to origin

    def get_footprint_size(self) -> Tuple[float, float]:
        """Get the actual footprint size considering rotation"""
        if self.rotation in [90, 270]:
            return (self.height, self.width)
        return (self.width, self.height)

    def get_bounding_box(self, x: float, y: float) -> Tuple[float, float, float, float]:
        """Get bounding box at given position: (x1, y1, x2, y2)"""
        w, h = self.get_footprint_size()
        return (x, y, x + w, y + h)


@dataclass
class Placement:
    """Represents a placed component"""
    ref: str
    x: float
    y: float
    rotation: float = 0.0
    layer: str = "top"  # "top" or "bottom"

    def to_dict(self) -> Dict:
        return {
            "ref": self.ref,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "layer": self.layer
        }


@dataclass
class BoardConstraints:
    """Board constraints for placement"""
    width: float                       # Board width in mm
    height: float                      # Board height in mm
    margin: float = 2.0               # Edge margin in mm
    grid_size: float = 2.5            # Placement grid size in mm (KiCad default)
    keepout_areas: List[Tuple[float, float, float, float]] = field(default_factory=list)  # [(x1,y1,x2,y2), ...]
    thermal_relief_areas: List[Tuple[float, float, float]] = field(default_factory=list)  # [(x,y,radius), ...]


@dataclass
class PlacementResult:
    """Result of placement operation"""
    placements: List[Placement]
    unplaced: List[str]  # References that couldn't be placed
    strategy: PlacementStrategy
    metrics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "placements": [p.to_dict() for p in self.placements],
            "unplaced": self.unplaced,
            "strategy": self.strategy.value,
            "metrics": self.metrics
        }


class PlacementEngine:
    """
    PCB Component Placement Engine

    Provides intelligent component placement with support for:
    - Grid-based placement with collision avoidance
    - Thermal-aware placement for heat-sensitive designs
    - Signal integrity optimization for high-speed designs
    """

    def __init__(
        self,
        board_width: float = 100,
        board_height: float = 80,
        margin: float = 2.0,
        grid_size: float = 2.5
    ):
        self.board_width = board_width
        self.board_height = board_height
        self.margin = margin
        self.grid_size = grid_size

        self.constraints = BoardConstraints(
            width=board_width,
            height=board_height,
            margin=margin,
            grid_size=grid_size
        )

        self._placement_grid: Set[Tuple[int, int]] = set()

    def place(
        self,
        components: List[Component],
        strategy: PlacementStrategy = PlacementStrategy.GRID,
        seed: Optional[int] = None
    ) -> PlacementResult:
        """
        Place components on the board using specified strategy

        Args:
            components: List of components to place
            strategy: Placement strategy to use
            seed: Random seed for reproducibility

        Returns:
            PlacementResult with placements and metrics
        """
        if seed is not None:
            random.seed(seed)

        # Sort components by size (largest first) for better packing
        sorted_components = sorted(
            components,
            key=lambda c: c.width * c.height,
            reverse=True
        )

        placements = []
        unplaced = []
        occupied_cells = set()

        for comp in sorted_components:
            pos = self._find_position(
                comp,
                placements,
                occupied_cells,
                strategy
            )

            if pos:
                placement = Placement(
                    ref=comp.ref,
                    x=pos[0],
                    y=pos[1],
                    rotation=comp.rotation
                )
                placements.append(placement)
                self._mark_occupied(placement, comp, occupied_cells)
            else:
                unplaced.append(comp.ref)

        # Calculate metrics
        metrics = self._calculate_metrics(placements, components, unplaced)

        return PlacementResult(
            placements=placements,
            unplaced=unplaced,
            strategy=strategy,
            metrics=metrics
        )

    def place_thermal_aware(
        self,
        components: List[Component],
        ambient_temps: Optional[List[float]] = None,
        seed: Optional[int] = None
    ) -> PlacementResult:
        """
        Place components with thermal optimization

        High thermal components are placed near board edges or thermal relief areas.
        Heat-sensitive components are placed away from heat sources.

        Args:
            components: List of components to place
            ambient_temps: Optional list of ambient temperature zones [(x, y, temp), ...]
            seed: Random seed

        Returns:
            PlacementResult with thermal-optimized placements
        """
        if seed is not None:
            random.seed(seed)

        # Sort: high thermal load first
        sorted_components = sorted(
            components,
            key=lambda c: c.thermal_load,
            reverse=True
        )

        placements = []
        unplaced = []
        occupied_cells = set()

        # Create thermal zones (edges are cooler in typical designs)
        thermal_zones = self._create_thermal_zones(ambient_temps or [])

        for comp in sorted_components:
            pos = self._find_thermal_position(
                comp,
                placements,
                occupied_cells,
                thermal_zones
            )

            if pos:
                placement = Placement(
                    ref=comp.ref,
                    x=pos[0],
                    y=pos[1],
                    rotation=comp.rotation
                )
                placements.append(placement)
                self._mark_occupied(placement, comp, occupied_cells)
            else:
                unplaced.append(comp.ref)

        metrics = self._calculate_metrics(placements, components, unplaced)
        metrics["thermal_optimized"] = True

        return PlacementResult(
            placements=placements,
            unplaced=unplaced,
            strategy=PlacementStrategy.THERMAL_AWARE,
            metrics=metrics
        )

    def _create_thermal_zones(
        self,
        ambient_temps: List[Tuple[float, float, float]]
    ) -> Dict[Tuple[int, int], float]:
        """Create thermal zone map for placement decisions"""
        zones = {}

        # Default: edges are cooler (assuming forced air cooling from edges)
        for gy in range(int(self.board_height / self.grid_size)):
            for gx in range(int(self.board_width / self.grid_size)):
                x = gx * self.grid_size
                y = gy * self.grid_size

                # Distance from nearest edge
                dist_left = x
                dist_right = self.board_width - x
                dist_top = y
                dist_bottom = self.board_height - y
                min_edge_dist = min(dist_left, dist_right, dist_top, dist_bottom)

                # Normalize to 0-1 (1 = cool, 0 = warm)
                max_dist = min(self.board_width, self.board_height) / 2
                temp_score = min(min_edge_dist / max_dist, 1.0)

                zones[(gx, gy)] = temp_score

        # Apply custom temperature zones
        for tx, ty, temp in ambient_temps:
            gx = int(tx / self.grid_size)
            gy = int(ty / self.grid_size)
            if (gx, gy) in zones:
                # Lower score for hot zones
                zones[(gx, gy)] = min(zones[(gx, gy)], 1.0 - temp / 100)

        return zones

    def _find_position(
        self,
        comp: Component,
        existing_placements: List[Placement],
        occupied_cells: Set[Tuple[int, int]],
        strategy: PlacementStrategy
    ) -> Optional[Tuple[float, float]]:
        """Find a valid position for component using grid-based search"""
        w, h = comp.get_footprint_size()
        max_x = self.board_width - self.margin - w
        max_y = self.board_height - self.margin - h

        if max_x < self.margin or max_y < self.margin:
            return None

        best_pos = None
        best_score = float('-inf')

        # Try positions in a shuffled order for variety
        positions = []
        y = self.margin
        while y <= max_y:
            x = self.margin
            while x <= max_x:
                positions.append((x, y))
                x += self.grid_size
            y += self.grid_size

        random.shuffle(positions)

        for x, y in positions:
            if self._is_valid_position(x, y, comp, occupied_cells):
                # Score based on strategy
                score = self._score_position(x, y, comp, existing_placements, strategy)
                if score > best_score:
                    best_score = score
                    best_pos = (x, y)

        return best_pos

    def _find_thermal_position(
        self,
        comp: Component,
        existing_placements: List[Placement],
        occupied_cells: Set[Tuple[int, int]],
        thermal_zones: Dict[Tuple[int, int], float]
    ) -> Optional[Tuple[float, float]]:
        """Find position optimized for thermal behavior"""
        w, h = comp.get_footprint_size()
        max_x = self.board_width - self.margin - w
        max_y = self.board_height - self.margin - h

        if max_x < self.margin or max_y < self.margin:
            return None

        best_pos = None
        best_score = float('-inf')

        positions = []
        y = self.margin
        while y <= max_y:
            x = self.margin
            while x <= max_x:
                positions.append((x, y))
                x += self.grid_size
            y += self.grid_size

        random.shuffle(positions)

        for x, y in positions:
            if self._is_valid_position(x, y, comp, occupied_cells):
                # Calculate thermal score
                gx = int(x / self.grid_size)
                gy = int(y / self.grid_size)
                zone_temp = thermal_zones.get((gx, gy), 0.5)

                # High thermal components want low zone_temp (cooler areas)
                # Low thermal components don't care
                if comp.thermal_load > 0.5:
                    score = -zone_temp * 100  # Prefer cooler areas
                else:
                    score = zone_temp * 10  # Prefer normal areas

                # Small position penalty for spreading out
                score -= (x + y) * 0.01

                if score > best_score:
                    best_score = score
                    best_pos = (x, y)

        return best_pos

    def _is_valid_position(
        self,
        x: float,
        y: float,
        comp: Component,
        occupied_cells: Set[Tuple[int, int]]
    ) -> bool:
        """Check if position is valid (within bounds and no collision)"""
        w, h = comp.get_footprint_size()

        # Check bounds
        if x < self.margin or y < self.margin:
            return False
        if x + w > self.board_width - self.margin:
            return False
        if y + h > self.board_height - self.margin:
            return False

        # Check keepout areas
        for kx1, ky1, kx2, ky2 in self.constraints.keepout_areas:
            if (x < kx2 and x + w > kx1 and y < ky2 and y + h > ky1):
                return False

        # Check collision with occupied cells
        gx1 = int(x / self.grid_size)
        gy1 = int(y / self.grid_size)
        gx2 = int((x + w) / self.grid_size) + 1
        gy2 = int((y + h) / self.grid_size) + 1

        for gy in range(gy1, gy2):
            for gx in range(gx1, gx2):
                if (gx, gy) in occupied_cells:
                    return False

        return True

    def _score_position(
        self,
        x: float,
        y: float,
        comp: Component,
        existing_placements: List[Placement],
        strategy: PlacementStrategy
    ) -> float:
        """Score a position based on strategy"""
        score = 0.0

        if strategy == PlacementStrategy.GRID:
            # Simple density score - prefer more open areas
            score = -len(existing_placements) * 0.1

        elif strategy == PlacementStrategy.SIGNAL_INTEGRITY:
            # For high-speed components, prefer center (less EMI)
            if comp.is_high_speed:
                cx, cy = self.board_width / 2, self.board_height / 2
                dist_from_center = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                score = -dist_from_center * 0.1

        elif strategy == PlacementStrategy.BALANCED:
            # Prefer spreading components evenly
            avg_x = sum(p.x for p in existing_placements) / (len(existing_placements) + 1) if existing_placements else x
            avg_y = sum(p.y for p in existing_placements) / (len(existing_placements) + 1) if existing_placements else y
            dist_from_avg = math.sqrt((x - avg_x) ** 2 + (y - avg_y) ** 2)
            score = -dist_from_avg * 0.1

        return score

    def _mark_occupied(
        self,
        placement: Placement,
        comp: Component,
        occupied_cells: Set[Tuple[int, int]]
    ):
        """Mark cells as occupied by placed component"""
        w, h = comp.get_footprint_size()
        gx1 = int(placement.x / self.grid_size)
        gy1 = int(placement.y / self.grid_size)
        gx2 = int((placement.x + w) / self.grid_size) + 1
        gy2 = int((placement.y + h) / self.grid_size) + 1

        for gy in range(gy1, gy2):
            for gx in range(gx1, gx2):
                occupied_cells.add((gx, gy))

    def _calculate_metrics(
        self,
        placements: List[Placement],
        components: List[Component],
        unplaced: List[str]
    ) -> Dict:
        """Calculate placement quality metrics"""
        total_components = len(components)
        placed_count = len(placements)

        # Calculate utilization
        total_area = self.board_width * self.board_height
        component_area = sum(c.width * c.height for c in components)
        utilization = component_area / total_area if total_area > 0 else 0

        # Calculate spread (how evenly distributed)
        if placements:
            avg_x = sum(p.x for p in placements) / len(placements)
            avg_y = sum(p.y for p in placements) / len(placements)
            variance_x = sum((p.x - avg_x) ** 2 for p in placements) / len(placements)
            variance_y = sum((p.y - avg_y) ** 2 for p in placements) / len(placements)
            spread = math.sqrt(variance_x + variance_y)
        else:
            spread = 0

        return {
            "total_components": total_components,
            "placed_count": placed_count,
            "placement_rate": placed_count / total_components if total_components > 0 else 0,
            "utilization": utilization,
            "spread": spread,
            "unplaced_count": len(unplaced)
        }

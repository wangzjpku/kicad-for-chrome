"""
Thermal Via Generator for PCB Design

Phase 8: Generates thermal via arrays under power components:
- Calculate number of vias needed based on thermal resistance target
- Place vias in grid pattern under IC thermal pad
- Avoid signal pins
- Connect to bottom copper pour

Physics reference:
- Single via thermal resistance (0.3 mm drill, 1.6 mm FR4): ~50-100 degC/W
- Parallel via resistance: Rth_total = Rth_single / N
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set

logger = logging.getLogger(__name__)

# Default thermal resistance of a single via (degC / W)
# 0.3 mm drill, 0.6 mm pad, 1.6 mm FR-4, copper-filled
DEFAULT_SINGLE_VIA_RTH = 75.0  # degC/W

# Typical targets for power ICs (degC / W)
TYPICAL_TARGET_RTH = 15.0

# Recommended via spacing in mm
RECOMMENDED_SPACING = 1.0  # mm centre-to-centre
MIN_SPACING = 0.8  # mm


@dataclass
class ThermalVia:
    """A single thermal via position.

    Attributes:
        x: X coordinate in mm.
        y: Y coordinate in mm.
        drill: Drill diameter in mm.
        size: Outer pad diameter in mm.
    """
    x: float
    y: float
    drill: float = 0.3
    size: float = 0.6


@dataclass
class ThermalViaResult:
    """Result of thermal via generation.

    Attributes:
        vias: List of generated thermal via positions.
        target_rth: Target thermal resistance in degC/W.
        estimated_rth: Estimated total thermal resistance with all vias.
        via_count: Number of vias generated.
        grid_rows: Number of grid rows.
        grid_cols: Number of grid columns.
    """
    vias: List[ThermalVia] = field(default_factory=list)
    target_rth: float = TYPICAL_TARGET_RTH
    estimated_rth: float = 0.0
    via_count: int = 0
    grid_rows: int = 0
    grid_cols: int = 0


class ThermalViaGenerator:
    """Generates thermal via arrays for power component heat dissipation.

    The generator places vias in a grid pattern beneath a component's
    thermal pad, automatically avoiding signal pin locations.  The number
    of vias is derived from the target thermal resistance.
    """

    def __init__(self, single_via_rth: float = DEFAULT_SINGLE_VIA_RTH):
        """Initialize the generator.

        Args:
            single_via_rth: Thermal resistance of one via in degC/W.
                            Default 75 degC/W for a 0.3 mm drill via
                            through 1.6 mm FR-4.
        """
        self.single_via_rth = single_via_rth
        self._results: List[ThermalViaResult] = []
        logger.info(
            "ThermalViaGenerator initialized (single_via_rth=%.1f degC/W)",
            single_via_rth,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_thermal_vias(
        self,
        component_x: float,
        component_y: float,
        component_width: float,
        component_height: float,
        thermal_resistance_target: float = TYPICAL_TARGET_RTH,
        via_drill: float = 0.3,
        via_size: float = 0.6,
        avoid_pins: Optional[List[Tuple[float, float, float]]] = None,
        spacing: float = RECOMMENDED_SPACING,
        net: str = "GND",
    ) -> ThermalViaResult:
        """Generate a thermal via array under a component thermal pad.

        Args:
            component_x: Component centre X in mm.
            component_y: Component centre Y in mm.
            component_width: Component body width in mm.
            component_height: Component body height in mm.
            thermal_resistance_target: Desired total Rth in degC/W.
            via_drill: Drill diameter for each via in mm.
            via_size: Outer pad diameter for each via in mm.
            avoid_pins: Optional list of (x, y, radius) for signal pins
                        that vias must not overlap.
            spacing: Grid spacing between vias in mm.
            net: Net name assigned to vias (default "GND").

        Returns:
            ThermalViaResult containing all generated vias and metadata.
        """
        # 1. Determine how many vias are needed
        needed = self._calculate_via_count(
            thermal_resistance_target, self.single_via_rth
        )
        logger.info(
            "Target Rth=%.1f degC/W requires %d vias",
            thermal_resistance_target, needed,
        )

        # 2. Generate grid positions inside component footprint
        half_w = component_width / 2
        half_h = component_height / 2
        positions = self._generate_grid(
            component_x, component_y,
            component_width - spacing * 0.2,  # slight inset
            component_height - spacing * 0.2,
            spacing=spacing,
        )

        # 3. Filter out positions that collide with signal pins
        if avoid_pins:
            positions = self._avoid_pin_positions(
                positions, avoid_pins, via_size / 2
            )

        # 4. Trim to the number actually needed (keep centre-most)
        positions = self._select_central_vias(positions, needed,
                                              component_x, component_y)

        # 5. Build ThermalVia objects
        vias = [
            ThermalVia(x=px, y=py, drill=via_drill, size=via_size)
            for px, py in positions
        ]

        # Estimate final thermal resistance
        actual_count = len(vias)
        estimated_rth = (
            self.single_via_rth / actual_count if actual_count > 0
            else float("inf")
        )

        # Compute grid dimensions for reporting
        grid_rows, grid_cols = self._grid_dimensions(
            component_width - spacing * 0.2,
            component_height - spacing * 0.2,
            spacing,
        )

        result = ThermalViaResult(
            vias=vias,
            target_rth=thermal_resistance_target,
            estimated_rth=round(estimated_rth, 2),
            via_count=actual_count,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
        )
        self._results.append(result)

        logger.info(
            "Generated %d thermal vias (estimated Rth=%.2f degC/W) "
            "under component at (%.2f, %.2f)",
            actual_count, estimated_rth, component_x, component_y,
        )
        return result

    def to_kicad_vias(
        self, result: ThermalViaResult, net: str = "GND",
    ) -> str:
        """Export thermal vias as KiCad S-expression string.

        Args:
            result: The ThermalViaResult to export.
            net: Net name for the vias.

        Returns:
            KiCad S-expression via definitions.
        """
        lines: List[str] = []
        lines.append(f"(comment \"Thermal via array: {result.via_count} vias, "
                      f"estimated Rth={result.estimated_rth} degC/W\")")
        for v in result.vias:
            lines.append("  (via")
            lines.append(f"    (at {v.x:.4f} {v.y:.4f})")
            lines.append(f"    (size {v.size:.4f})")
            lines.append(f"    (drill {v.drill:.4f})")
            lines.append(f"    (net \"{net}\")")
            lines.append("    (layers \"F.Cu\" \"B.Cu\")")
            lines.append("    (thermal_bridge_width 0.5)")
            lines.append("  )")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_via_count(
        target_rth: float,
        single_via_rth: float = DEFAULT_SINGLE_VIA_RTH,
    ) -> int:
        """Calculate the number of parallel vias to meet a thermal target.

        N = ceil(Rth_single / Rth_target)

        Args:
            target_rth: Desired total thermal resistance (degC/W).
            single_via_rth: Thermal resistance of one via (degC/W).

        Returns:
            Minimum number of vias needed.
        """
        if target_rth <= 0:
            return 1
        return max(1, math.ceil(single_via_rth / target_rth))

    @staticmethod
    def _generate_grid(
        center_x: float,
        center_y: float,
        width: float,
        height: float,
        spacing: float = RECOMMENDED_SPACING,
    ) -> List[Tuple[float, float]]:
        """Generate a grid of (x, y) positions within a rectangular area.

        Args:
            center_x: Rectangle centre X in mm.
            center_y: Rectangle centre Y in mm.
            width: Rectangle width in mm.
            height: Rectangle height in mm.
            spacing: Grid spacing in mm.

        Returns:
            List of (x, y) tuples on the grid.
        """
        positions: List[Tuple[float, float]] = []
        half_w = width / 2
        half_h = height / 2

        cols = max(1, int(width / spacing) + 1)
        rows = max(1, int(height / spacing) + 1)

        # Centre the grid on (center_x, center_y)
        start_x = center_x - (cols - 1) * spacing / 2
        start_y = center_y - (rows - 1) * spacing / 2

        for r in range(rows):
            for c in range(cols):
                x = start_x + c * spacing
                y = start_y + r * spacing
                # Keep only positions inside the rectangle
                if (center_x - half_w <= x <= center_x + half_w
                        and center_y - half_h <= y <= center_y + half_h):
                    positions.append((x, y))

        return positions

    @staticmethod
    def _avoid_pin_positions(
        positions: List[Tuple[float, float]],
        pins: List[Tuple[float, float, float]],
        via_radius: float,
    ) -> List[Tuple[float, float]]:
        """Remove grid positions that overlap with signal pin locations.

        Args:
            positions: Candidate (x, y) positions.
            pins: List of (x, y, radius) for signal pins.
            via_radius: Half of the via pad diameter.

        Returns:
            Filtered list of positions that do not collide with pins.
        """
        safe: List[Tuple[float, float]] = []
        for px, py in positions:
            collides = False
            for pin_x, pin_y, pin_r in pins:
                dist = math.sqrt((px - pin_x) ** 2 + (py - pin_y) ** 2)
                if dist < pin_r + via_radius:
                    collides = True
                    break
            if not collides:
                safe.append((px, py))
        return safe

    @staticmethod
    def _select_central_vias(
        positions: List[Tuple[float, float]],
        count: int,
        cx: float,
        cy: float,
    ) -> List[Tuple[float, float]]:
        """Keep the *count* positions closest to the component centre.

        Args:
            positions: Full list of candidate positions.
            count: Number of vias to keep.
            cx: Component centre X.
            cy: Component centre Y.

        Returns:
            Trimmed list with at most *count* entries.
        """
        if len(positions) <= count:
            return positions
        # Sort by distance to centre, ascending
        positions_sorted = sorted(
            positions,
            key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2,
        )
        return positions_sorted[:count]

    @staticmethod
    def _grid_dimensions(
        width: float, height: float, spacing: float,
    ) -> Tuple[int, int]:
        """Return (rows, cols) for a grid filling the given rectangle."""
        cols = max(1, int(width / spacing) + 1)
        rows = max(1, int(height / spacing) + 1)
        return rows, cols


# ── Auto-recommendation for hot components ──────────────────

# Components that typically need thermal vias
HOT_COMPONENT_PATTERNS = {
    # (keyword_patterns, typical_power_W, typical_pad_size_mm)
    "ldo": (["ldo", "ams1117", "lm7805", "lt1083", "lt1084", "lm317"], 1.5, 3.0),
    "mosfet": (["mosfet", "fet", "irf", "si", "ao3400", "ao4407"], 2.0, 4.0),
    "dcdc": (["dcdc", "buck", "boost", "mp1584", "lm2596", "xl4015", "tps5430"], 3.0, 5.0),
    "pmic": (["pmic", "power_management", "max170", "bq24"], 2.5, 5.0),
    "rectifier": (["bridge", "rectifier", "kbp", "gbj"], 2.0, 6.0),
    "controller": (["pwm", "controller", "uc3842", "ncp1200", "l6561"], 1.0, 4.0),
    "charger": (["charger", "tp4056", "bq24", "mp266"], 2.0, 4.0),
    "led_driver": (["led_driver", "ws2812", "p9813"], 1.5, 3.0),
}


@dataclass
class ThermalRecommendation:
    """Thermal via recommendation for a component."""
    reference: str
    component_type: str
    estimated_power: float  # W
    thermal_pad_size: float  # mm (square side)
    recommended_via_count: int
    via_drill: float  # mm
    via_size: float   # mm
    spacing: float    # mm
    priority: str = "medium"  # low/medium/high/critical

    @property
    def estimated_rth(self) -> float:
        """Estimated total thermal resistance with recommended vias."""
        if self.recommended_via_count <= 0:
            return float("inf")
        return DEFAULT_SINGLE_VIA_RTH / self.recommended_via_count


def recommend_thermal_vias(components: List[Dict]) -> List[ThermalRecommendation]:
    """
    Automatically recommend thermal via configurations for hot components.

    Args:
        components: List of component dicts with keys:
            reference, type/name, value, power (optional), pad_size (optional)

    Returns:
        List of ThermalRecommendation for components that need thermal vias.
    """
    recommendations = []

    for comp in components:
        ref = comp.get("reference", "")
        comp_type = (comp.get("type", "") or comp.get("name", "") or "").lower()
        value = str(comp.get("value", "")).lower()
        search_text = f"{ref} {comp_type} {value}".lower()

        # Match against hot component patterns
        best_match = None
        best_score = 0

        for category, (keywords, power, pad_size) in HOT_COMPONENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in search_text)
            if score > best_score:
                best_score = score
                best_match = (category, power, pad_size)

        if best_match is None:
            continue

        category, default_power, default_pad = best_match

        # Override with explicit values if provided
        power = float(comp.get("power", default_power))
        pad_size = float(comp.get("pad_size", default_pad))

        # Calculate required vias
        target_rth = TYPICAL_TARGET_RTH
        n_vias = max(1, math.ceil(DEFAULT_SINGLE_VIA_RTH / target_rth))

        # Adjust for power level
        if power > 5.0:
            n_vias = max(n_vias, math.ceil(power * 2))
            priority = "critical"
        elif power > 2.0:
            n_vias = max(n_vias, math.ceil(power * 1.5))
            priority = "high"
        elif power > 1.0:
            priority = "medium"
        else:
            priority = "low"

        rec = ThermalRecommendation(
            reference=ref,
            component_type=category,
            estimated_power=power,
            thermal_pad_size=pad_size,
            recommended_via_count=n_vias,
            via_drill=0.3,
            via_size=0.6,
            spacing=RECOMMENDED_SPACING,
            priority=priority,
        )
        recommendations.append(rec)

    # Sort by priority (critical first)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

    return recommendations

"""
Safety Isolation Generator for PCB Design

Phase 8: Generates safety isolation features for PCBs including:
- Physical isolation slots (Edge.Cuts layer)
- No-copper clearance zones
- Creepage distance barriers with sawtooth patterns
- KiCad S-expression output

Based on IEC 60950-1 / IEC 62368-1 safety standards.
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# IEC 60950-1 creepage/clearance requirements by voltage level (mm)
IEC_60950_CREEPAGE: dict[float, float] = {
    50.0: 0.6,
    150.0: 3.0,
    220.0: 6.0,
    300.0: 6.0,
    600.0: 12.5,
}

# IEC 62368-1 replacement values (supersedes IEC 60950-1)
IEC_62368_CREEPAGE: dict[float, float] = {
    50.0: 0.5,
    150.0: 2.5,
    220.0: 5.0,
    300.0: 5.5,
    600.0: 11.0,
}

# Standard slot width for isolation (mm)
DEFAULT_SLOT_WIDTH = 1.0

# Sawtooth barrier defaults
SAWTOOTH_TOOTH_DEPTH = 1.0  # mm
SAWTOOTH_TOOTH_WIDTH = 2.0  # mm


@dataclass
class IsolationSlot:
    """Represents a physical isolation slot on the PCB.

    Attributes:
        x: Bottom-left X coordinate (mm).
        y: Bottom-left Y coordinate (mm).
        width: Slot width in mm.
        height: Slot height in mm.
        voltage_label: Human-readable voltage label, e.g. "220V AC".
        standard: Safety standard reference, e.g. "IEC 60950-1".
        slot_type: Type of isolation ("slot", "milling", "routing").
    """
    x: float
    y: float
    width: float
    height: float
    voltage_label: str = ""
    standard: str = "IEC 60950-1"
    slot_type: str = "slot"


@dataclass
class CreepageBarrier:
    """Sawtooth creepage barrier inside an isolation zone.

    Attributes:
        points: List of (x, y) coordinate tuples forming the sawtooth.
        height_mm: The barrier extension height in mm.
    """
    points: List[Tuple[float, float]] = field(default_factory=list)
    height_mm: float = SAWTOOTH_TOOTH_DEPTH


@dataclass
class IsolationZone:
    """Complete isolation zone containing slot and optional barriers.

    Attributes:
        slot: The main isolation slot.
        barriers: Creepage barriers inside the zone.
        no_copper_margin: No-copper clearance margin around slot (mm).
        primary_net: Network name on the primary (high-voltage) side.
        secondary_net: Network name on the secondary (SELV) side.
    """
    slot: IsolationSlot
    barriers: List[CreepageBarrier] = field(default_factory=list)
    no_copper_margin: float = 0.5
    primary_net: str = ""
    secondary_net: str = ""


class IsolationGenerator:
    """Generates safety isolation features for PCB layout.

    Supports IEC 60950-1 and IEC 62368-1 creepage/clearance standards.
    Produces Edge.Cuts geometry and no-copper keepout zones that can be
    exported as KiCad S-expression data.
    """

    def __init__(self, standard: str = "IEC 60950-1"):
        """Initialize the isolation generator.

        Args:
            standard: Safety standard to follow. Accepts "IEC 60950-1"
                      or "IEC 62368-1".
        """
        self.standard = standard
        self.zones: List[IsolationZone] = []
        self._creepage_table = (
            IEC_62368_CREEPAGE if "62368" in standard else IEC_60950_CREEPAGE
        )
        logger.info("IsolationGenerator initialized with standard %s", standard)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_isolation_slot(
        self,
        board_width: float,
        board_height: float,
        primary_zone: Tuple[float, float, float, float],
        secondary_zone: Tuple[float, float, float, float],
        min_creepage_mm: float = 6.0,
        voltage_label: str = "220V AC",
        primary_net: str = "",
        secondary_net: str = "",
    ) -> IsolationSlot:
        """Create an isolation slot between primary and secondary zones.

        The slot is placed on the Edge.Cuts layer as a rectangular cutout
        that separates the two zones.  Its position is calculated as the
        midpoint between the closest edges of the two zones.

        Args:
            board_width: PCB width in mm.
            board_height: PCB height in mm.
            primary_zone: (x, y, width, height) of the primary (HV) zone.
            secondary_zone: (x, y, width, height) of the secondary (SELV) zone.
            min_creepage_mm: Minimum creepage distance in mm (default 6.0
                             for 220 V AC per IEC 60950-1).
            voltage_label: Label for documentation, e.g. "220V AC".
            primary_net: Net name on the primary side.
            secondary_net: Net name on the secondary side.

        Returns:
            An IsolationSlot describing the cutout.
        """
        px, py, pw, ph = primary_zone
        sx, sy, sw, sh = secondary_zone

        # Determine the boundary between zones (find the closest edges)
        slot = self._compute_slot_between_zones(
            px, py, pw, ph, sx, sy, sw, sh, min_creepage_mm
        )

        slot.voltage_label = voltage_label
        slot.standard = self.standard

        zone = IsolationZone(
            slot=slot,
            primary_net=primary_net,
            secondary_net=secondary_net,
        )
        self.zones.append(zone)

        logger.info(
            "Generated isolation slot at (%.2f, %.2f) size %.2fx%.2f mm "
            "for %s clearance %.1f mm",
            slot.x, slot.y, slot.width, slot.height,
            voltage_label, min_creepage_mm,
        )
        return slot

    def generate_creepage_barriers(
        self,
        slot: IsolationSlot,
        num_barriers: int = 5,
    ) -> List[CreepageBarrier]:
        """Add sawtooth creepage barriers inside the isolation zone.

        The sawtooth pattern extends the effective creepage path length
        beyond the straight-line distance.

        Args:
            slot: The isolation slot to add barriers to.
            num_barriers: Number of sawtooth barriers (default 5).

        Returns:
            List of CreepageBarrier objects.
        """
        barriers: List[CreepageBarrier] = []
        is_horizontal = slot.width >= slot.height

        for idx in range(num_barriers):
            if is_horizontal:
                barrier = self._horizontal_sawtooth(slot, idx, num_barriers)
            else:
                barrier = self._vertical_sawtooth(slot, idx, num_barriers)
            barriers.append(barrier)

        # Attach barriers to the matching zone
        for zone in self.zones:
            if zone.slot is slot:
                zone.barriers = barriers
                break

        logger.info(
            "Generated %d creepage barriers for slot at (%.2f, %.2f)",
            num_barriers, slot.x, slot.y,
        )
        return barriers

    def to_kicad_format(self) -> str:
        """Export all isolation zones as KiCad S-expression string.

        Returns:
            KiCad S-expression suitable for Edge.Cuts layer and
            keepout zones.
        """
        lines: List[str] = []
        lines.append("(module \"Isolation_Zones\" (layer Edge.Cuts)")

        for zone_idx, zone in enumerate(self.zones):
            s = zone.slot
            lines.append(f"  (zone_ref {zone_idx}")
            lines.append(
                f"    (comment \"{s.voltage_label} isolation, {s.standard}\")"
            )

            # Edge.Cuts rectangle (the physical slot)
            lines.append("    (gr_rect")
            lines.append(f"      (start {s.x:.4f} {s.y:.4f})")
            lines.append(f"      (end {s.x + s.width:.4f} {s.y + s.height:.4f})")
            lines.append("      (layer Edge.Cuts)")
            lines.append(f"      (width {DEFAULT_SLOT_WIDTH:.4f})")
            lines.append("      (fill none)")
            lines.append("    )")

            # No-copper keepout zone around the slot
            margin = zone.no_copper_margin
            lines.append("    (zone_keepout")
            lines.append(
                f"      (start {s.x - margin:.4f} {s.y - margin:.4f})"
            )
            lines.append(
                f"      (end {s.x + s.width + margin:.4f} "
                f"{s.y + s.height + margin:.4f})"
            )
            lines.append("      (layer F.Cu)")
            lines.append("      (keepout_tracks not_allowed)")
            lines.append("      (keepout_vias not_allowed)")
            lines.append("      (keepout_copperpour not_allowed)")
            lines.append("    )")
            lines.append("    (zone_keepout")
            lines.append(
                f"      (start {s.x - margin:.4f} {s.y - margin:.4f})"
            )
            lines.append(
                f"      (end {s.x + s.width + margin:.4f} "
                f"{s.y + s.height + margin:.4f})"
            )
            lines.append("      (layer B.Cu)")
            lines.append("      (keepout_tracks not_allowed)")
            lines.append("      (keepout_vias not_allowed)")
            lines.append("      (keepout_copperpour not_allowed)")
            lines.append("    )")

            # Creepage barriers as line segments on Edge.Cuts
            for b_idx, barrier in enumerate(zone.barriers):
                lines.append(
                    f"    (comment \"Creepage barrier {b_idx}\")"
                )
                for p_idx in range(len(barrier.points) - 1):
                    x1, y1 = barrier.points[p_idx]
                    x2, y2 = barrier.points[p_idx + 1]
                    lines.append("    (gr_line")
                    lines.append(f"      (start {x1:.4f} {y1:.4f})")
                    lines.append(f"      (end {x2:.4f} {y2:.4f})")
                    lines.append("      (layer Edge.Cuts)")
                    lines.append(f"      (width {DEFAULT_SLOT_WIDTH:.4f})")
                    lines.append("    )")

            lines.append("  )")  # zone_ref close

        lines.append(")")  # module close
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_slot_between_zones(
        self,
        px: float, py: float, pw: float, ph: float,
        sx: float, sy: float, sw: float, sh: float,
        creepage: float,
    ) -> IsolationSlot:
        """Calculate slot position between two rectangular zones.

        Determines which edges of the two zones are closest and places
        a rectangular slot spanning that gap.
        """
        # Centres
        pcx = px + pw / 2
        pcy = py + ph / 2
        scx = sx + sw / 2
        scy = sy + sh / 2

        dx = scx - pcx
        dy = scy - pcy

        slot_w = DEFAULT_SLOT_WIDTH

        if abs(dx) >= abs(dy):
            # Zones are side-by-side horizontally
            if dx > 0:
                left = px + pw
                right = sx
            else:
                left = sx + sw
                right = px
            mid_x = (left + right) / 2 - slot_w / 2
            y_start = min(py, sy)
            y_end = max(py + ph, sy + sh)
            return IsolationSlot(
                x=mid_x, y=y_start,
                width=slot_w, height=y_end - y_start,
            )
        else:
            # Zones are stacked vertically
            if dy > 0:
                top = py + ph
                bottom = sy
            else:
                top = sy + sh
                bottom = py
            mid_y = (top + bottom) / 2 - slot_w / 2
            x_start = min(px, sx)
            x_end = max(px + pw, sx + sw)
            return IsolationSlot(
                x=x_start, y=mid_y,
                width=x_end - x_start, height=slot_w,
            )

    def _horizontal_sawtooth(
        self, slot: IsolationSlot, idx: int, total: int,
    ) -> CreepageBarrier:
        """Generate a horizontal sawtooth barrier inside *slot*."""
        segment = slot.height / (total + 1)
        y_base = slot.y + segment * (idx + 1)
        points: List[Tuple[float, float]] = [(slot.x, y_base)]

        teeth = max(2, int(slot.width / SAWTOOTH_TOOTH_WIDTH))
        tooth_dx = slot.width / teeth
        for t in range(1, teeth + 1):
            x = slot.x + tooth_dx * t
            direction = 1 if t % 2 == 1 else -1
            y = y_base + direction * SAWTOOTH_TOOTH_DEPTH
            points.append((x, y))
            if t < teeth:
                points.append((x, y_base))

        return CreepageBarrier(points=points, height_mm=SAWTOOTH_TOOTH_DEPTH)

    def _vertical_sawtooth(
        self, slot: IsolationSlot, idx: int, total: int,
    ) -> CreepageBarrier:
        """Generate a vertical sawtooth barrier inside *slot*."""
        segment = slot.width / (total + 1)
        x_base = slot.x + segment * (idx + 1)
        points: List[Tuple[float, float]] = [(x_base, slot.y)]

        teeth = max(2, int(slot.height / SAWTOOTH_TOOTH_WIDTH))
        tooth_dy = slot.height / teeth
        for t in range(1, teeth + 1):
            y = slot.y + tooth_dy * t
            direction = 1 if t % 2 == 1 else -1
            x = x_base + direction * SAWTOOTH_TOOTH_DEPTH
            points.append((x, y))
            if t < teeth:
                points.append((x_base, y))

        return CreepageBarrier(points=points, height_mm=SAWTOOTH_TOOTH_DEPTH)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def get_creepage_for_voltage(
        voltage: float, standard: str = "IEC 60950-1",
    ) -> float:
        """Return the minimum creepage distance for a given voltage.

        Args:
            voltage: Working voltage in volts.
            standard: "IEC 60950-1" or "IEC 62368-1".

        Returns:
            Minimum creepage distance in mm.
        """
        table = (
            IEC_62368_CREEPAGE if "62368" in standard else IEC_60950_CREEPAGE
        )
        result = 0.0
        for v, d in sorted(table.items()):
            if voltage <= v:
                return d
            result = d
        return result  # highest entry if above max key

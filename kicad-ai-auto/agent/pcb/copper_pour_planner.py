# -*- coding: utf-8 -*-
"""
Copper Pour Planner - Automatically plan copper pour zones for SMPS designs.

Separates AGND (analog ground / primary side) from DGND/GND (secondary side),
and plans copper pour zones with proper isolation gaps.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PourZone(Enum):
    """Copper pour zone type"""
    PRIMARY_GROUND = "primary_ground"    # AGND / hot side ground
    SECONDARY_GROUND = "secondary_ground"  # GND / cold side ground
    POWER_PLANE = "power_plane"          # VCC/VDD plane
    SHIELD = "shield"                    # EMI shield
    THERMAL = "thermal"                  # Thermal relief


@dataclass
class CopperPourZone:
    """A planned copper pour zone"""
    zone_type: PourZone
    net_name: str
    layer: str = "F.Cu"
    # Zone bounds
    x_min: float = 0.0
    y_min: float = 0.0
    x_max: float = 100.0
    y_max: float = 100.0
    # Pour settings
    clearance: float = 0.3  # mm clearance to other nets
    thermal_spoke_width: float = 0.5  # mm
    thermal_gap: float = 0.2  # mm
    # Isolation
    isolation_gap: float = 0.0  # mm gap to adjacent zones
    # Style
    hatch_style: str = "solid"  # solid/hatched
    hatch_gap: float = 1.0  # mm (for hatched)
    hatch_width: float = 0.3  # mm (for hatched)

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_kicad_zone(self) -> Dict:
        """Convert to KiCad zone dict for export."""
        return {
            "type": "zone",
            "net": self.net_name,
            "layer": self.layer,
            "fill": self.hatch_style,
            "clearance": self.clearance,
            "points": [
                {"x": self.x_min, "y": self.y_min},
                {"x": self.x_max, "y": self.y_min},
                {"x": self.x_max, "y": self.y_max},
                {"x": self.x_min, "y": self.y_max},
            ],
        }


@dataclass
class CopperPourPlan:
    """Complete copper pour plan for a PCB"""
    zones: List[CopperPourZone] = field(default_factory=list)
    via_stitching: bool = True
    via_pitch: float = 2.0  # mm
    via_drill: float = 0.4  # mm
    message: str = ""

    @property
    def total_copper_area(self) -> float:
        return sum(z.area for z in self.zones)

    def to_kicad_zones(self) -> List[Dict]:
        """Convert all zones to KiCad format."""
        return [z.to_kicad_zone() for z in self.zones]


class CopperPourPlanner:
    """Plan copper pour zones based on safety zones and board layout."""

    def __init__(
        self,
        board_width: float = 100.0,
        board_height: float = 80.0,
        margin: float = 2.0,
    ):
        self.board_width = board_width
        self.board_height = board_height
        self.margin = margin

    def plan_smps(
        self,
        isolation_boundary_y: float,
        creepage: float = 6.0,
        primary_nets: Optional[List[str]] = None,
        secondary_nets: Optional[List[str]] = None,
    ) -> CopperPourPlan:
        """
        Plan copper pour zones for SMPS design.

        Args:
            isolation_boundary_y: Y coordinate of isolation boundary
            creepage: Required creepage distance (mm)
            primary_nets: Net names on primary side
            secondary_nets: Net names on secondary side
        """
        plan = CopperPourPlan()
        margin = self.margin

        if primary_nets is None:
            primary_nets = ["AGND"]
        if secondary_nets is None:
            secondary_nets = ["GND"]

        # Zone 1: Primary side ground (bottom half, below isolation)
        primary_ground = CopperPourZone(
            zone_type=PourZone.PRIMARY_GROUND,
            net_name=primary_nets[0],
            layer="B.Cu",
            x_min=margin,
            y_min=margin,
            x_max=self.board_width - margin,
            y_max=isolation_boundary_y - creepage / 2,
            clearance=0.5,
            thermal_spoke_width=0.8,
            hatch_style="hatched",
            hatch_gap=1.5,
            hatch_width=0.3,
            isolation_gap=creepage,
        )
        plan.zones.append(primary_ground)

        # Zone 2: Secondary side ground (top half, above isolation)
        secondary_ground = CopperPourZone(
            zone_type=PourZone.SECONDARY_GROUND,
            net_name=secondary_nets[0],
            layer="B.Cu",
            x_min=margin,
            y_min=isolation_boundary_y + creepage / 2,
            x_max=self.board_width - margin,
            y_max=self.board_height - margin,
            clearance=0.3,
            thermal_spoke_width=0.5,
            hatch_style="solid",
            isolation_gap=creepage,
        )
        plan.zones.append(secondary_ground)

        # Zone 3: Top layer VCC plane on secondary side (optional)
        if len(secondary_nets) > 1:
            power_plane = CopperPourZone(
                zone_type=PourZone.POWER_PLANE,
                net_name=secondary_nets[1],
                layer="F.Cu",
                x_min=margin,
                y_min=isolation_boundary_y + creepage / 2 + 2,
                x_max=self.board_width - margin,
                y_max=self.board_height - margin - 2,
                clearance=0.3,
                hatch_style="solid",
            )
            plan.zones.append(power_plane)

        # Zone 4: EMI shield around primary switching area
        shield = CopperPourZone(
            zone_type=PourZone.SHIELD,
            net_name=primary_nets[0],
            layer="F.Cu",
            x_min=margin,
            y_min=margin,
            x_max=self.board_width / 2,
            y_max=isolation_boundary_y - creepage / 2,
            clearance=0.8,
            hatch_style="hatched",
            hatch_gap=2.0,
            hatch_width=0.3,
        )
        plan.zones.append(shield)

        plan.message = (
            f"Planned {len(plan.zones)} copper pour zones: "
            f"primary AGND={primary_ground.area:.0f}mm², "
            f"secondary GND={secondary_ground.area:.0f}mm², "
            f"isolation gap={creepage:.1f}mm"
        )

        return plan

    def plan_standard(
        self,
        ground_net: str = "GND",
        power_nets: Optional[List[str]] = None,
    ) -> CopperPourPlan:
        """
        Plan copper pour zones for standard (non-SMPS) design.

        Simple approach: full bottom layer ground pour.
        """
        plan = CopperPourPlan()
        margin = self.margin

        # Full bottom layer ground pour
        ground = CopperPourZone(
            zone_type=PourZone.SECONDARY_GROUND,
            net_name=ground_net,
            layer="B.Cu",
            x_min=margin,
            y_min=margin,
            x_max=self.board_width - margin,
            y_max=self.board_height - margin,
            clearance=0.3,
            thermal_spoke_width=0.5,
            hatch_style="solid",
        )
        plan.zones.append(ground)

        # Power planes on internal layers (if 4+ layer)
        if power_nets:
            for i, net in enumerate(power_nets[:2]):
                layer = f"In{i + 1}.Cu"
                power = CopperPourZone(
                    zone_type=PourZone.POWER_PLANE,
                    net_name=net,
                    layer=layer,
                    x_min=margin,
                    y_min=margin,
                    x_max=self.board_width - margin,
                    y_max=self.board_height - margin,
                    clearance=0.3,
                )
                plan.zones.append(power)

        plan.message = f"Planned {len(plan.zones)} copper pour zones for standard design"

        return plan

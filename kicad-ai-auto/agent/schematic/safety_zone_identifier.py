# -*- coding: utf-8 -*-
"""
Safety Zone Identifier - Automatically classify primary/secondary side
components in SMPS (Switched-Mode Power Supply) designs.

Identifies high-voltage (primary) and low-voltage (secondary) components
based on component types, names, and network connectivity.

IEC 62368-1 / IEC 60950-1 compliance zones.
"""

import logging
import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyZone(Enum):
    """Safety zone classification"""
    PRIMARY = "primary"        # High voltage side (AC mains input)
    SECONDARY = "secondary"    # Low voltage side (regulated output)
    ISOLATION = "isolation"    # Isolation barrier (transformer, optocoupler)
    PROTECTIVE = "protective"  # Protective devices (fuse, MOV)
    UNKNOWN = "unknown"


@dataclass
class ZoneComponent:
    """Component with safety zone classification"""
    reference: str
    component_type: str
    zone: SafetyZone = SafetyZone.UNKNOWN
    voltage_max: float = 0.0  # V
    confidence: float = 0.0   # 0-1 classification confidence
    reason: str = ""


@dataclass
class SafetyZoneResult:
    """Complete zone identification result"""
    primary_components: List[ZoneComponent] = field(default_factory=list)
    secondary_components: List[ZoneComponent] = field(default_factory=list)
    isolation_components: List[ZoneComponent] = field(default_factory=list)
    protective_components: List[ZoneComponent] = field(default_factory=list)
    unknown_components: List[ZoneComponent] = field(default_factory=list)
    boundary_line_y: float = 0.0  # Y coordinate of isolation boundary
    creepage_required: float = 0.0  # mm
    clearance_required: float = 0.0  # mm
    message: str = ""

    @property
    def total_components(self) -> int:
        return (len(self.primary_components) + len(self.secondary_components) +
                len(self.isolation_components) + len(self.protective_components) +
                len(self.unknown_components))

    @property
    def classification_rate(self) -> float:
        classified = (len(self.primary_components) + len(self.secondary_components) +
                      len(self.isolation_components) + len(self.protective_components))
        total = self.total_components
        return classified / total if total > 0 else 0.0


# ── Component type keywords ────────────────────────────────

# Primary side component patterns
PRIMARY_KEYWORDS = [
    # Rectification
    "bridge", "rectifier", "bd1", "nbd1", "dbr",
    # Input filtering
    "varistor", "mov", "ntc", "th1",
    # X/Y capacitors (EMI filter)
    "cx1", "cx2", "cy1", "cy2",
    # Bulk capacitor
    "bulk", "ce1", "ce2", "ce3",
    # Primary controller
    "pwm", "controller", "uc3842", "ncp1200", "l6561", "top",
    # Primary MOSFET/switch
    "switch", "mosfet", "fet", "q1",
    # Input fuse
    "fuse", "f1",
    # PFC
    "pfc", "boost",
    # Snubber
    "snubber", "dclamp",
]

# Secondary side component patterns
SECONDARY_KEYWORDS = [
    # Output connector
    "usb", "output", "vout", "connector_out",
    # Secondary rectification
    "sr", "sync_rect", "schottky", "d4",
    # Output filter
    "cout", "l3", "lf1",
    # Regulator
    "ldo", "regulator_out", "ams1117", "tl431",
    # Output capacitor
    "ce3", "co1", "c_out",
    # Feedback
    "optocoupler", "opto", "pc817", "4n35",
    # Load
    "load", "r_load",
]

# Isolation components (span both sides)
ISOLATION_KEYWORDS = [
    "transformer", "xfmr", "t1", "t2",
    "optocoupler", "opto", "pc817",
    "y_capacitor", "y_cap", "cy1", "cy2",
]

# Protective components
PROTECTIVE_KEYWORDS = [
    "fuse", "varistor", "mov", "ntc",
    "protection", "ovp", "ocp", "scp",
]


class SafetyZoneIdentifier:
    """Identify primary/secondary zones in power supply designs."""

    def __init__(
        self,
        input_voltage: float = 220.0,  # V AC
        output_voltage: float = 5.0,   # V DC
        pollution_degree: int = 2,
        insulation_type: str = "basic",  # basic/reinforced
    ):
        self.input_voltage = input_voltage
        self.output_voltage = output_voltage
        self.pollution_degree = pollution_degree
        self.insulation_type = insulation_type

    def identify_zones(
        self,
        components: List[Dict],
    ) -> SafetyZoneResult:
        """
        Classify all components into safety zones.

        Args:
            components: List of component dicts with keys:
                reference, type/name, value, footprint, category

        Returns:
            SafetyZoneResult with all classifications
        """
        result = SafetyZoneResult()

        # Classify each component
        for comp in components:
            ref = comp.get("reference", "")
            comp_type = (comp.get("type", "") or comp.get("name", "") or "").lower()
            category = (comp.get("category", "") or "").lower()
            value = str(comp.get("value", "")).lower()

            zone_comp = self._classify_component(ref, comp_type, category, value)
            self._add_to_result(result, zone_comp)

        # Refine using connectivity analysis
        self._refine_by_connectivity(result, components)

        # Calculate isolation requirements
        self._calculate_isolation_requirements(result)

        # Calculate boundary line
        self._estimate_boundary(result, components)

        # Set message
        result.message = (
            f"Identified {len(result.primary_components)} primary, "
            f"{len(result.secondary_components)} secondary, "
            f"{len(result.isolation_components)} isolation components. "
            f"Creepage: {result.creepage_required:.1f}mm, "
            f"Clearance: {result.clearance_required:.1f}mm"
        )

        return result

    def _classify_component(
        self,
        ref: str,
        comp_type: str,
        category: str,
        value: str,
    ) -> ZoneComponent:
        """Classify a single component by keyword matching."""
        search_text = f"{ref} {comp_type} {category} {value}".lower()

        # Check isolation first (highest priority)
        for kw in ISOLATION_KEYWORDS:
            if kw in search_text:
                return ZoneComponent(
                    reference=ref, component_type=comp_type,
                    zone=SafetyZone.ISOLATION,
                    confidence=0.85,
                    reason=f"Matched isolation keyword: {kw}",
                )

        # Check primary
        primary_score = sum(1 for kw in PRIMARY_KEYWORDS if kw in search_text)
        secondary_score = sum(1 for kw in SECONDARY_KEYWORDS if kw in search_text)

        # Check protective
        protective_score = sum(1 for kw in PROTECTIVE_KEYWORDS if kw in search_text)

        if protective_score > 0 and primary_score > 0:
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.PROTECTIVE,
                confidence=0.7 + min(protective_score * 0.1, 0.3),
                reason=f"Protective device ({protective_score} matches)",
            )

        if primary_score > secondary_score:
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.PRIMARY,
                confidence=0.6 + min(primary_score * 0.1, 0.4),
                reason=f"Primary side ({primary_score} keyword matches)",
            )

        if secondary_score > primary_score:
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.SECONDARY,
                confidence=0.6 + min(secondary_score * 0.1, 0.4),
                reason=f"Secondary side ({secondary_score} keyword matches)",
            )

        # Heuristics by component reference prefix
        ref_upper = ref.upper()
        if any(x in ref_upper for x in ["F1", "FUSE"]):
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.PROTECTIVE, confidence=0.7,
                reason="Fuse device",
            )

        if any(x in ref_upper for x in ["T1", "T2", "XFMR", "TR"]):
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.ISOLATION, confidence=0.8,
                reason="Transformer/inductor",
            )

        # USB/output connectors are always secondary
        if any(x in search_text for x in ["usb", "output", "conn_out", "jack"]):
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.SECONDARY, confidence=0.8,
                reason="Output connector",
            )

        # AC input is always primary
        if any(x in search_text for x in ["ac_in", "mains", "line_in", "ac_line"]):
            return ZoneComponent(
                reference=ref, component_type=comp_type,
                zone=SafetyZone.PRIMARY, confidence=0.9,
                reason="AC input",
            )

        return ZoneComponent(
            reference=ref, component_type=comp_type,
            zone=SafetyZone.UNKNOWN, confidence=0.0,
            reason="Could not classify",
        )

    def _refine_by_connectivity(
        self,
        result: SafetyZoneResult,
        components: List[Dict],
    ):
        """
        Refine classifications using network connectivity.

        Strategy: Build a net→component map, then propagate zone labels.
        If an unknown component shares a net with a high-confidence primary
        component, reclassify it as primary (and vice versa for secondary).
        Isolation components (transformers, optocouplers) act as barriers —
        nets on opposite sides are not propagated across them.
        """
        # Build ref → component data lookup (including nets)
        ref_to_nets: Dict[str, Set[str]] = {}
        for comp in components:
            ref = comp.get("reference", "")
            nets = comp.get("nets", [])
            if isinstance(nets, list):
                ref_to_nets[ref] = set(str(n) for n in nets)
            elif isinstance(nets, str):
                ref_to_nets[ref] = {nets}
            else:
                ref_to_nets[ref] = set()

        # Build net → set of refs (inverse map)
        net_to_refs: Dict[str, Set[str]] = {}
        for ref, nets in ref_to_nets.items():
            for net in nets:
                net_to_refs.setdefault(net, set()).add(ref)

        # Collect known-zone refs with their zones
        zone_map: Dict[str, SafetyZone] = {}
        confidence_map: Dict[str, float] = {}

        for zc in result.primary_components:
            zone_map[zc.reference] = SafetyZone.PRIMARY
            confidence_map[zc.reference] = zc.confidence
        for zc in result.secondary_components:
            zone_map[zc.reference] = SafetyZone.SECONDARY
            confidence_map[zc.reference] = zc.confidence
        for zc in result.isolation_components:
            zone_map[zc.reference] = SafetyZone.ISOLATION
            confidence_map[zc.reference] = zc.confidence
        for zc in result.protective_components:
            zone_map[zc.reference] = SafetyZone.PROTECTIVE
            confidence_map[zc.reference] = zc.confidence

        # Isolation component refs — these act as propagation barriers
        isolation_refs = {zc.reference for zc in result.isolation_components}

        # Identify nets that touch isolation components (barrier nets)
        barrier_nets: Set[str] = set()
        for ref in isolation_refs:
            barrier_nets.update(ref_to_nets.get(ref, set()))

        # Propagate zone labels through shared non-barrier nets
        # Only reclassify UNKNOWN components
        changed = True
        max_iterations = 3  # Prevent infinite loops
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            for zc in list(result.unknown_components):
                nets = ref_to_nets.get(zc.reference, set())
                if not nets:
                    continue

                # Count zone votes from connected components
                primary_votes = 0
                secondary_votes = 0
                sample_reason = ""

                for net in nets:
                    # Skip barrier nets (cross isolation boundary)
                    if net in barrier_nets:
                        continue

                    for connected_ref in net_to_refs.get(net, set()):
                        if connected_ref == zc.reference:
                            continue
                        if connected_ref in isolation_refs:
                            continue

                        connected_zone = zone_map.get(connected_ref)
                        if connected_zone == SafetyZone.PRIMARY:
                            primary_votes += 1
                        elif connected_zone == SafetyZone.SECONDARY:
                            secondary_votes += 1

                # Reclassify if there's a clear majority (≥2 votes advantage)
                if primary_votes >= 2 and primary_votes > secondary_votes + 1:
                    zc.zone = SafetyZone.PRIMARY
                    zc.confidence = 0.5
                    zc.reason = f"Inferred primary by connectivity ({primary_votes} primary neighbors)"
                    result.unknown_components.remove(zc)
                    result.primary_components.append(zc)
                    zone_map[zc.reference] = SafetyZone.PRIMARY
                    confidence_map[zc.reference] = 0.5
                    changed = True
                elif secondary_votes >= 2 and secondary_votes > primary_votes + 1:
                    zc.zone = SafetyZone.SECONDARY
                    zc.confidence = 0.5
                    zc.reason = f"Inferred secondary by connectivity ({secondary_votes} secondary neighbors)"
                    result.unknown_components.remove(zc)
                    result.secondary_components.append(zc)
                    zone_map[zc.reference] = SafetyZone.SECONDARY
                    confidence_map[zc.reference] = 0.5
                    changed = True

        # Log refinement results
        still_unknown = len(result.unknown_components)
        if still_unknown > 0:
            logger.info(f"After connectivity refinement: {still_unknown} components remain unclassified")
        else:
            logger.info("Connectivity refinement: all components classified")

    def _calculate_isolation_requirements(self, result: SafetyZoneResult):
        """Calculate required creepage and clearance distances."""
        # IEC 62368-1 tables (simplified)
        # Creepage depends on voltage, pollution degree, and material group
        voltage = self.input_voltage * math.sqrt(2) * 1.1  # Peak + 10% margin

        # Pollution degree 2, material group III (default)
        creepage_table = {
            # voltage_range: (basic, reinforced)
            (0, 50): (0.4, 0.8),
            (50, 150): (0.8, 1.6),
            (150, 300): (1.5, 3.0),
            (300, 600): (3.0, 6.0),
            (600, 1000): (5.0, 10.0),
        }

        clearance_table = {
            (0, 50): (0.2, 0.4),
            (50, 150): (0.5, 1.0),
            (150, 300): (1.0, 2.0),
            (300, 600): (2.0, 4.0),
            (600, 1000): (3.3, 6.6),
        }

        # Find applicable range
        for (vmin, vmax), (basic, reinforced) in creepage_table.items():
            if vmin <= voltage < vmax:
                if self.insulation_type == "reinforced":
                    result.creepage_required = reinforced
                else:
                    result.creepage_required = basic
                break
        else:
            result.creepage_required = 6.0  # Fallback for >1kV

        for (vmin, vmax), (basic, reinforced) in clearance_table.items():
            if vmin <= voltage < vmax:
                if self.insulation_type == "reinforced":
                    result.clearance_required = reinforced
                else:
                    result.clearance_required = basic
                break
        else:
            result.clearance_required = 4.0

        # Pollution degree multiplier
        if self.pollution_degree == 3:
            result.creepage_required *= 1.5
            result.clearance_required *= 1.25

    def _estimate_boundary(
        self,
        result: SafetyZoneResult,
        components: List[Dict],
    ):
        """Estimate the Y coordinate of the isolation boundary."""
        primary_y_positions = []
        secondary_y_positions = []

        for comp in components:
            ref = comp.get("reference", "")
            y = comp.get("y", 0) or comp.get("position", [0, 0])
            if isinstance(y, (list, tuple)):
                y = y[1]

            # Check if this ref is in primary or secondary
            for zc in result.primary_components:
                if zc.reference == ref:
                    primary_y_positions.append(y)
            for zc in result.secondary_components:
                if zc.reference == ref:
                    secondary_y_positions.append(y)

        if primary_y_positions and secondary_y_positions:
            avg_primary = sum(primary_y_positions) / len(primary_y_positions)
            avg_secondary = sum(secondary_y_positions) / len(secondary_y_positions)
            result.boundary_line_y = (avg_primary + avg_secondary) / 2.0
        else:
            result.boundary_line_y = 0.0

    def _add_to_result(self, result: SafetyZoneResult, comp: ZoneComponent):
        """Add classified component to the appropriate list."""
        if comp.zone == SafetyZone.PRIMARY:
            result.primary_components.append(comp)
        elif comp.zone == SafetyZone.SECONDARY:
            result.secondary_components.append(comp)
        elif comp.zone == SafetyZone.ISOLATION:
            result.isolation_components.append(comp)
        elif comp.zone == SafetyZone.PROTECTIVE:
            result.protective_components.append(comp)
        else:
            result.unknown_components.append(comp)

# -*- coding: utf-8 -*-
"""
Layout Scorer - Professional 4-dimension PCB layout quality assessment.

Phase 9C-2: Scoring dimensions:
  - Area utilization (25%): Board space efficiency
  - Wire length (30%): Estimated Manhattan wire length
  - Thermal distribution (25%): Heat dissipation quality
  - Manufacturability (20%): DFM score (spacing, edge clearance, assembly)

Generates structured reports with grades (A-F) and actionable improvement suggestions.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# ─── Data Structures ────────────────────────────────────────────


@dataclass
class DimensionDetail:
    """Score breakdown for one dimension."""
    name: str
    score: float          # 0-100
    weight: float         # 0-1
    details: str = ""
    sub_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ThermalHotspot:
    """A region with high thermal density."""
    x: float
    y: float
    power_density: float  # mW/mm^2
    severity: str = "ok"  # ok / warning / critical


@dataclass
class LayoutScoringInput:
    """Input data for layout scoring."""
    board_width: float = 100.0
    board_height: float = 80.0
    components: List[Dict] = field(default_factory=list)
    # Each component dict: {reference, x, y, width, height, value, category, power_mw}
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # ref -> {x, y}
    net_connections: Optional[List[Tuple[str, str, str]]] = None
    # [(net_name, ref1, ref2), ...]
    min_clearance_mm: float = 0.5
    edge_clearance_mm: float = 3.0


@dataclass
class LayoutScoringReport:
    """Complete layout quality assessment."""
    total_score: float
    dimensions: List[DimensionDetail] = field(default_factory=list)
    hotspots: List[ThermalHotspot] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    grade: str = ""
    summary: str = ""
    weights: Dict[str, float] = field(default_factory=dict)

    @property
    def is_passing(self) -> bool:
        return self.total_score >= 60

    @property
    def is_production_ready(self) -> bool:
        return self.total_score >= 80


# ─── Power estimation lookup ────────────────────────────────────

# Keywords -> typical power dissipation (mW) for thermal analysis
_POWER_ESTIMATES: Dict[str, float] = {
    "ldo": 500, "regulator": 400, "dcdc": 300, "buck": 300,
    "boost": 300, "mosfet": 800, "fet": 600, "bridge": 400,
    "rectifier": 350, "transistor": 200, "diode": 150,
    "led": 100, "opamp": 50, "mcu": 200, "esp32": 250,
    "stm32": 150, "wifi": 300, "bluetooth": 200, "nrf": 150,
    "usb": 100, "charger": 400, "tp4056": 500, "ams1117": 600,
    "lm7805": 800, "lm317": 700,
}


def _estimate_power(value: str, category: str = "") -> float:
    """Estimate component power dissipation from value/category text."""
    text = (value or "").lower() + " " + (category or "").lower()
    for kw, power in _POWER_ESTIMATES.items():
        if kw in text:
            return power
    # Category-based fallback
    cat = (category or "").lower()
    if "power" in cat:
        return 300
    if "mcu" in cat or "wireless" in cat:
        return 200
    return 50  # Default passive


# ─── LayoutScorer ───────────────────────────────────────────────


class LayoutScorer:
    """
    Professional 4-dimension PCB layout scorer.

    Usage:
        scorer = LayoutScorer()
        report = scorer.score(input_data)
        print(report.grade, report.total_score)
        for s in report.improvements:
            print("-", s)
    """

    DEFAULT_WEIGHTS = {
        "area": 0.25,
        "wire_length": 0.30,
        "thermal": 0.25,
        "manufacturability": 0.20,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def score(self, data: LayoutScoringInput) -> LayoutScoringReport:
        """Score a layout and return a full report."""
        dimensions = []

        # 1. Area utilization
        area = self._score_area(data)
        dimensions.append(area)

        # 2. Wire length
        wire = self._score_wire_length(data)
        dimensions.append(wire)

        # 3. Thermal distribution
        thermal, hotspots = self._score_thermal(data)
        dimensions.append(thermal)

        # 4. Manufacturability
        mfg = self._score_manufacturability(data)
        dimensions.append(mfg)

        total = sum(d.weighted_score for d in dimensions)
        total = max(0, min(100, total))

        grade = self._to_grade(total)
        improvements = self._generate_improvements(dimensions, data)

        return LayoutScoringReport(
            total_score=round(total, 1),
            dimensions=dimensions,
            hotspots=hotspots,
            improvements=improvements,
            grade=grade,
            summary=self._make_summary(dimensions, total, grade),
            weights=self.weights.copy(),
        )

    # ── Area utilization (25%) ──────────────────────────────────

    def _score_area(self, data: LayoutScoringInput) -> DimensionDetail:
        """Score board area utilization."""
        positions = data.positions
        if not positions:
            return DimensionDetail("Area Utilization", 0, self.weights["area"])

        board_area = data.board_width * data.board_height

        # Component area
        comp_area = 0.0
        comp_dict = {c.get("reference"): c for c in data.components}
        for ref in positions:
            c = comp_dict.get(ref, {})
            w = c.get("width", 5.0)
            h = c.get("height", 5.0)
            comp_area += w * h

        # Bounding box
        xs = [p.get("x", 0) for p in positions.values()]
        ys = [p.get("y", 0) for p in positions.values()]
        bbox_w = max(xs) - min(xs) + 10
        bbox_h = max(ys) - min(ys) + 10
        bbox_area = bbox_w * bbox_h

        utilization = comp_area / board_area if board_area > 0 else 0
        bbox_util = bbox_area / board_area if board_area > 0 else 0

        # Scoring: 60-80% component utilization is optimal
        if 0.6 <= utilization <= 0.8:
            util_score = 95.0
        elif 0.4 <= utilization < 0.6:
            util_score = 80.0
        elif 0.8 < utilization <= 0.9:
            util_score = 75.0
        elif utilization > 0:
            util_score = 50.0
        else:
            util_score = 0.0

        # Bounding box compactness bonus
        compactness = comp_area / bbox_area if bbox_area > 0 else 0
        if compactness >= 0.5:
            compact_score = 95.0
        elif compactness >= 0.3:
            compact_score = 80.0
        else:
            compact_score = 60.0

        final = util_score * 0.6 + compact_score * 0.4

        return DimensionDetail(
            name="Area Utilization",
            score=round(final, 1),
            weight=self.weights["area"],
            details=f"Component utilization: {utilization:.0%}, bounding box compactness: {compactness:.0%}",
            sub_scores={
                "component_utilization": round(util_score, 1),
                "compactness": round(compact_score, 1),
            },
        )

    # ── Wire length (30%) ───────────────────────────────────────

    def _score_wire_length(self, data: LayoutScoringInput) -> DimensionDetail:
        """Score estimated wire length."""
        positions = data.positions
        nets = data.net_connections

        if not nets or not positions:
            return DimensionDetail(
                "Wire Length", 70.0, self.weights["wire_length"],
                details="No net data available",
            )

        total_manhattan = 0.0
        max_len = 0.0
        min_len = float("inf")
        count = 0
        long_nets = []

        for net_name, ref1, ref2 in nets:
            p1 = positions.get(ref1)
            p2 = positions.get(ref2)
            if p1 and p2:
                dx = abs(p1.get("x", 0) - p2.get("x", 0))
                dy = abs(p1.get("y", 0) - p2.get("y", 0))
                length = dx + dy
                total_manhattan += length
                max_len = max(max_len, length)
                min_len = min(min_len, length)
                count += 1
                if length > 50:
                    long_nets.append(f"{net_name}({length:.0f}mm)")

        if count == 0:
            return DimensionDetail(
                "Wire Length", 70.0, self.weights["wire_length"],
                details="No valid connections",
            )

        avg_len = total_manhattan / count

        # Scoring based on average Manhattan distance
        if avg_len <= 15:
            score = 95.0
        elif avg_len <= 25:
            score = 85.0
        elif avg_len <= 40:
            score = 70.0
        elif avg_len <= 60:
            score = 55.0
        else:
            score = max(15, 100 - avg_len * 0.8)

        # Penalty for outlier long nets
        if long_nets:
            penalty = min(15, len(long_nets) * 5)
            score -= penalty

        details = f"Avg: {avg_len:.1f}mm, range: {min_len:.0f}-{max_len:.0f}mm"
        if long_nets:
            details += f", long nets: {', '.join(long_nets[:3])}"

        return DimensionDetail(
            name="Wire Length",
            score=round(max(0, score), 1),
            weight=self.weights["wire_length"],
            details=details,
            sub_scores={
                "avg_length": round(avg_len, 1),
                "max_length": round(max_len, 1),
                "long_net_count": len(long_nets),
            },
        )

    # ── Thermal distribution (25%) ──────────────────────────────

    def _score_thermal(
        self, data: LayoutScoringInput
    ) -> Tuple[DimensionDetail, List[ThermalHotspot]]:
        """Score thermal distribution and detect hotspots."""
        positions = data.positions
        if not positions or len(positions) < 2:
            return (
                DimensionDetail("Thermal", 80.0, self.weights["thermal"]),
                [],
            )

        comp_dict = {c.get("reference"): c for c in data.components}

        # Build thermal map: assign power to each component
        comp_powers: Dict[str, float] = {}
        for ref, pos in positions.items():
            c = comp_dict.get(ref, {})
            value = c.get("value", "")
            category = c.get("category", "")
            comp_powers[ref] = _estimate_power(value, category)

        # Grid-based thermal density (10mm grid)
        grid_size = 10.0
        grid: Dict[Tuple[int, int], float] = {}  # (gx, gy) -> total power
        for ref, pos in positions.items():
            gx = int(pos.get("x", 0) / grid_size)
            gy = int(pos.get("y", 0) / grid_size)
            grid[(gx, gy)] = grid.get((gx, gy), 0) + comp_powers.get(ref, 50)

        # Detect hotspots
        hotspots = []
        for (gx, gy), power in grid.items():
            cell_area = grid_size * grid_size
            density = power / cell_area  # mW/mm^2
            cx = (gx + 0.5) * grid_size
            cy = (gy + 0.5) * grid_size

            if density > 10:
                severity = "critical"
            elif density > 5:
                severity = "warning"
            else:
                severity = "ok"

            hotspots.append(ThermalHotspot(
                x=cx, y=cy,
                power_density=round(density, 2),
                severity=severity,
            ))

        # Score based on hotspot analysis
        critical_count = sum(1 for h in hotspots if h.severity == "critical")
        warning_count = sum(1 for h in hotspots if h.severity == "warning")

        if critical_count == 0 and warning_count == 0:
            thermal_score = 95.0
        elif critical_count == 0 and warning_count <= 2:
            thermal_score = 80.0
        elif critical_count == 0:
            thermal_score = 65.0
        elif critical_count <= 1:
            thermal_score = 45.0
        else:
            thermal_score = 25.0

        # Hot component spacing analysis
        hot_refs = [
            ref for ref, p in comp_powers.items()
            if p >= 300
        ]
        min_hot_dist = float("inf")
        if len(hot_refs) >= 2:
            for i in range(len(hot_refs)):
                for j in range(i + 1, len(hot_refs)):
                    p1 = positions.get(hot_refs[i], {})
                    p2 = positions.get(hot_refs[j], {})
                    dx = p1.get("x", 0) - p2.get("x", 0)
                    dy = p1.get("y", 0) - p2.get("y", 0)
                    dist = math.sqrt(dx * dx + dy * dy)
                    min_hot_dist = min(min_hot_dist, dist)

        spacing_score = 100.0
        if min_hot_dist < float("inf"):
            if min_hot_dist >= 20:
                spacing_score = 95.0
            elif min_hot_dist >= 10:
                spacing_score = 75.0
            elif min_hot_dist >= 5:
                spacing_score = 50.0
            else:
                spacing_score = 25.0

        final = thermal_score * 0.6 + spacing_score * 0.4

        details = f"Hotspots: {critical_count} critical, {warning_count} warning"
        if min_hot_dist < float("inf"):
            details += f", min hot-component spacing: {min_hot_dist:.1f}mm"

        return (
            DimensionDetail(
                name="Thermal Distribution",
                score=round(final, 1),
                weight=self.weights["thermal"],
                details=details,
                sub_scores={
                    "density_score": round(thermal_score, 1),
                    "hot_spacing_score": round(spacing_score, 1),
                    "critical_hotspots": critical_count,
                    "warning_hotspots": warning_count,
                },
            ),
            hotspots,
        )

    # ── Manufacturability (20%) ─────────────────────────────────

    def _score_manufacturability(self, data: LayoutScoringInput) -> DimensionDetail:
        """Score DFM: edge clearance, component spacing, assembly feasibility."""
        positions = data.positions
        if not positions:
            return DimensionDetail("Manufacturability", 0, self.weights["manufacturability"])

        score = 100.0
        issues = []

        # 1. Edge clearance check
        edge_violations = 0
        for ref, pos in positions.items():
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            if x < data.edge_clearance_mm or y < data.edge_clearance_mm:
                edge_violations += 1
            if x > data.board_width - data.edge_clearance_mm:
                edge_violations += 1
            if y > data.board_height - data.edge_clearance_mm:
                edge_violations += 1

        if edge_violations > 0:
            penalty = min(30, edge_violations * 5)
            score -= penalty
            issues.append(f"{edge_violations} edge clearance violations (<{data.edge_clearance_mm}mm)")

        # 2. Minimum spacing check
        pos_list = list(positions.values())
        min_spacing = float("inf")
        spacing_violations = 0
        # Check limited pairs to avoid O(n^2) blowup
        check_limit = min(len(pos_list), 50)
        for i in range(check_limit):
            for j in range(i + 1, check_limit):
                dx = pos_list[i].get("x", 0) - pos_list[j].get("x", 0)
                dy = pos_list[i].get("y", 0) - pos_list[j].get("y", 0)
                dist = math.sqrt(dx * dx + dy * dy)
                min_spacing = min(min_spacing, dist)
                if dist < data.min_clearance_mm:
                    spacing_violations += 1

        if spacing_violations > 0:
            score -= min(25, spacing_violations * 5)
            issues.append(f"{spacing_violations} spacing violations (<{data.min_clearance_mm}mm)")
        elif min_spacing < 2.0:
            score -= 10
            issues.append(f"Minimum spacing {min_spacing:.1f}mm is tight (recommend >2mm)")

        # 3. Assembly feasibility: check component density
        board_area = data.board_width * data.board_height
        density = len(positions) / board_area * 100 if board_area > 0 else 0
        # components per 100mm^2
        if density > 0.5:
            score -= 10
            issues.append(f"High component density ({density:.2f}/100mm^2) may challenge assembly")
        elif density > 0.3:
            score -= 5

        # 4. Board aspect ratio check
        aspect = max(data.board_width, data.board_height) / max(min(data.board_width, data.board_height), 1)
        if aspect > 3:
            score -= 10
            issues.append(f"Unusual aspect ratio {aspect:.1f}:1 (recommend <3:1)")

        score = max(0, score)
        details = f"Score: {score:.0f}"
        if issues:
            details += f", issues: {'; '.join(issues[:3])}"

        return DimensionDetail(
            name="Manufacturability",
            score=round(score, 1),
            weight=self.weights["manufacturability"],
            details=details,
            sub_scores={
                "edge_clearance": max(0, 100 - edge_violations * 5),
                "min_spacing_mm": round(min_spacing, 2) if min_spacing < float("inf") else 0,
                "spacing_violations": spacing_violations,
                "density": round(density, 3),
            },
        )

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _to_grade(score: float) -> str:
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_improvements(
        self, dimensions: List[DimensionDetail], data: LayoutScoringInput
    ) -> List[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        for dim in dimensions:
            if dim.score >= 80:
                continue

            if dim.name == "Area Utilization":
                util = dim.sub_scores.get("component_utilization", 0)
                compact = dim.sub_scores.get("compactness", 0)
                if util < 60:
                    suggestions.append(
                        "Board area is underutilized. Consider reducing board size or adding "
                        "ground/copper pour for EMI improvement."
                    )
                elif util > 85:
                    suggestions.append(
                        "Board is very dense. Consider increasing board size or using "
                        "smaller component packages (0402 instead of 0603)."
                    )
                if compact < 60:
                    suggestions.append(
                        "Components are spread out. Group related components closer together "
                        "to reduce routing complexity."
                    )

            elif dim.name == "Wire Length":
                long = dim.sub_scores.get("long_net_count", 0)
                avg = dim.sub_scores.get("avg_length", 0)
                if long > 0:
                    suggestions.append(
                        f"{long} nets have excessive length (>50mm). Move connected "
                        "components closer or add vias for shorter layer transitions."
                    )
                if avg > 40:
                    suggestions.append(
                        f"Average wire length is {avg:.0f}mm. Reorganize layout to cluster "
                        "high-connectivity components."
                    )

            elif dim.name == "Thermal Distribution":
                critical = dim.sub_scores.get("critical_hotspots", 0)
                warning = dim.sub_scores.get("warning_hotspots", 0)
                hot_spacing = dim.sub_scores.get("hot_spacing_score", 100)
                if critical > 0:
                    suggestions.append(
                        f"{critical} thermal hotspot(s) detected. Spread high-power components "
                        "and add thermal vias / copper pour for heat dissipation."
                    )
                elif warning > 0:
                    suggestions.append(
                        f"{warning} thermal warning(s). Consider adding thermal relief pads "
                        "or increasing spacing between heat-generating components."
                    )
                if hot_spacing < 60:
                    suggestions.append(
                        "High-power components are too close. Separate them by at least "
                        "20mm for adequate cooling."
                    )

            elif dim.name == "Manufacturability":
                issues = dim.details
                if "edge clearance" in issues.lower():
                    suggestions.append(
                        "Move components at least 3mm from board edges for reliable "
                        "assembly and V-scoring compatibility."
                    )
                if "spacing" in issues.lower():
                    suggestions.append(
                        "Increase minimum component spacing to at least 2mm for "
                        "pick-and-place machine clearance."
                    )
                if "density" in issues.lower():
                    suggestions.append(
                        "Component density is high. Consider using both sides of the "
                        "board or increasing board size."
                    )

        if not suggestions:
            suggestions.append("Layout quality is excellent. Ready for routing and manufacturing.")

        return suggestions

    def _make_summary(
        self, dimensions: List[DimensionDetail], total: float, grade: str
    ) -> str:
        """Generate a human-readable summary."""
        parts = [f"Grade {grade} ({total:.0f}/100)"]
        for d in dimensions:
            parts.append(f"  {d.name}: {d.score:.0f}/100 (weight {d.weight:.0%})")
        return "\n".join(parts)

    # ── Quick scoring API for LayoutCandidateGenerator ──────────

    def quick_score(
        self,
        board_width: float,
        board_height: float,
        components: list,
        positions: Dict[str, Dict[str, float]],
        net_connections=None,
    ) -> Dict[str, float]:
        """
        Quick scoring API returning a simple dict (backward compatible
        with StandardLayoutScorer.score() interface).
        """
        comp_dicts = []
        for c in components:
            comp_dicts.append({
                "reference": c.reference,
                "width": c.width,
                "height": c.height,
                "value": getattr(c, "value", ""),
                "category": getattr(c, "category", "").value if hasattr(getattr(c, "category", ""), "value") else str(getattr(c, "category", "")),
            })

        data = LayoutScoringInput(
            board_width=board_width,
            board_height=board_height,
            components=comp_dicts,
            positions=positions,
            net_connections=net_connections,
        )

        report = self.score(data)
        return {
            "area_score": report.dimensions[0].score,
            "wire_length_score": report.dimensions[1].score,
            "thermal_score": report.dimensions[2].score,
            "manufacturability_score": report.dimensions[3].score,
            "total_score": report.total_score,
            "grade": report.grade,
            "weights": self.weights,
        }

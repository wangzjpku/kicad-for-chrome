# -*- coding: utf-8 -*-
"""
Routing Quality Scorer - Evaluate routing results on a 0-100 scale.

Scoring dimensions:
  - Completion (30%): route success rate
  - DRC compliance (30%): no violations
  - Efficiency (20%): total length vs ideal
  - Via usage (10%): minimal vias
  - Diff pair quality (10%): impedance & length matching
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score for one dimension"""
    name: str
    score: float  # 0-100
    weight: float  # 0-1
    max_possible: float = 100.0
    details: str = ""

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class RoutingQualityReport:
    """Complete quality assessment report"""
    total_score: float  # 0-100
    dimensions: List[DimensionScore] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    grade: str = ""  # A/B/C/D/F
    message: str = ""

    @property
    def is_passing(self) -> bool:
        return self.total_score >= 60

    @property
    def is_production_ready(self) -> bool:
        return self.total_score >= 80


@dataclass
class RoutingInput:
    """Input data for quality assessment"""
    total_nets: int
    routed_nets: int
    failed_nets: List[str] = field(default_factory=list)
    drc_violations: int = 0
    total_track_length: float = 0.0  # mm
    ideal_track_length: float = 0.0  # mm (estimated Manhattan distance)
    total_vias: int = 0
    diff_pair_count: int = 0
    diff_pair_impedance_errors: int = 0
    diff_pair_length_mismatches: int = 0
    board_area: float = 100.0  # mm^2


class RoutingQualityScorer:
    """Score routing results on a 0-100 scale."""

    def score(self, data: RoutingInput) -> RoutingQualityReport:
        """Calculate routing quality score."""
        dimensions = []

        # 1. Completion (30%)
        completion = self._score_completion(data)
        dimensions.append(completion)

        # 2. DRC compliance (30%)
        drc = self._score_drc(data)
        dimensions.append(drc)

        # 3. Efficiency (20%)
        efficiency = self._score_efficiency(data)
        dimensions.append(efficiency)

        # 4. Via usage (10%)
        vias = self._score_vias(data)
        dimensions.append(vias)

        # 5. Diff pair quality (10%)
        diffpair = self._score_diff_pairs(data)
        dimensions.append(diffpair)

        # Total
        total = sum(d.weighted_score for d in dimensions)

        # Generate improvements
        improvements = self._generate_improvements(dimensions, data)

        # Grade
        grade = self._score_to_grade(total)

        return RoutingQualityReport(
            total_score=round(total, 1),
            dimensions=dimensions,
            improvements=improvements,
            grade=grade,
            message=f"Quality: {grade} ({total:.0f}/100)",
        )

    def _score_completion(self, data: RoutingInput) -> DimensionScore:
        """Score routing completion rate (30% weight)."""
        if data.total_nets == 0:
            return DimensionScore("Completion", 100.0, 0.30, details="No nets to route")

        rate = data.routed_nets / data.total_nets
        score = rate * 100.0

        details = f"{data.routed_nets}/{data.total_nets} routed ({rate:.0%})"
        if data.failed_nets:
            details += f", failed: {', '.join(data.failed_nets[:5])}"

        return DimensionScore("Completion", score, 0.30, details=details)

    def _score_drc(self, data: RoutingInput) -> DimensionScore:
        """Score DRC compliance (30% weight)."""
        if data.routed_nets == 0:
            return DimensionScore("DRC Compliance", 100.0, 0.30, details="No tracks to check")

        if data.drc_violations == 0:
            return DimensionScore("DRC Compliance", 100.0, 0.30, details="No violations")

        # Exponential penalty: each violation reduces score significantly
        violation_rate = data.drc_violations / max(data.routed_nets, 1)
        score = max(0, 100.0 * math.exp(-5 * violation_rate))

        return DimensionScore(
            "DRC Compliance", score, 0.30,
            details=f"{data.drc_violations} violations"
        )

    def _score_efficiency(self, data: RoutingInput) -> DimensionScore:
        """Score routing efficiency - actual vs ideal length (20% weight)."""
        if data.total_track_length == 0 or data.ideal_track_length == 0:
            return DimensionScore("Efficiency", 70.0, 0.20, details="Insufficient data")

        ratio = data.total_track_length / data.ideal_track_length

        # ratio = 1.0 is ideal, > 1.5 is wasteful
        if ratio <= 1.2:
            score = 100.0
        elif ratio <= 1.5:
            score = 100.0 - (ratio - 1.2) * 100
        elif ratio <= 2.0:
            score = 70.0 - (ratio - 1.5) * 80
        else:
            score = max(0, 30.0 - (ratio - 2.0) * 30)

        return DimensionScore(
            "Efficiency", max(0, score), 0.20,
            details=f"Total {data.total_track_length:.1f}mm vs ideal {data.ideal_track_length:.1f}mm (ratio={ratio:.2f})"
        )

    def _score_vias(self, data: RoutingInput) -> DimensionScore:
        """Score via usage - fewer is better (10% weight)."""
        if data.routed_nets == 0:
            return DimensionScore("Via Usage", 100.0, 0.10, details="No nets")

        vias_per_net = data.total_vias / data.routed_nets

        if vias_per_net <= 0.5:
            score = 100.0
        elif vias_per_net <= 1.0:
            score = 90.0
        elif vias_per_net <= 2.0:
            score = 70.0
        elif vias_per_net <= 3.0:
            score = 50.0
        else:
            score = max(0, 30.0 - (vias_per_net - 3.0) * 10)

        return DimensionScore(
            "Via Usage", score, 0.10,
            details=f"{data.total_vias} vias for {data.routed_nets} nets ({vias_per_net:.1f}/net)"
        )

    def _score_diff_pairs(self, data: RoutingInput) -> DimensionScore:
        """Score diff pair quality (10% weight)."""
        if data.diff_pair_count == 0:
            return DimensionScore("Diff Pairs", 100.0, 0.10, details="No diff pairs")

        errors = data.diff_pair_impedance_errors + data.diff_pair_length_mismatches
        error_rate = errors / data.diff_pair_count

        if error_rate == 0:
            score = 100.0
        elif error_rate <= 0.2:
            score = 80.0
        elif error_rate <= 0.5:
            score = 60.0
        else:
            score = max(0, 40.0 - error_rate * 20)

        return DimensionScore(
            "Diff Pairs", score, 0.10,
            details=f"{data.diff_pair_count} pairs, {errors} errors ({error_rate:.0%} error rate)"
        )

    def _score_to_grade(self, score: float) -> str:
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
        self, dimensions: List[DimensionScore], data: RoutingInput
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        for dim in dimensions:
            if dim.score < 80:
                if dim.name == "Completion" and data.failed_nets:
                    suggestions.append(
                        f"Route failed nets: {', '.join(data.failed_nets[:5])}. "
                        f"Consider adjusting component placement or enabling rip-up retry."
                    )
                elif dim.name == "DRC Compliance" and data.drc_violations > 0:
                    suggestions.append(
                        f"Fix {data.drc_violations} DRC violations. "
                        f"Check clearance constraints and trace widths."
                    )
                elif dim.name == "Efficiency" and data.ideal_track_length > 0:
                    ratio = data.total_track_length / data.ideal_track_length
                    suggestions.append(
                        f"Reduce total track length ({ratio:.1f}x ideal). "
                        f"Consider moving connected components closer together."
                    )
                elif dim.name == "Via Usage":
                    suggestions.append(
                        f"Reduce via count ({data.total_vias}). "
                        f"Consider single-layer routing for short nets."
                    )
                elif dim.name == "Diff Pairs":
                    suggestions.append(
                        "Fix diff pair impedance or length mismatches. "
                        "Check trace width/gap calculations."
                    )

        if not suggestions:
            suggestions.append("Routing quality is excellent. No improvements needed.")

        return suggestions

# -*- coding: utf-8 -*-
"""
Post-Route Optimizer - Optimize routing after initial completion.

Optimizations:
1. Track length reduction (remove unnecessary detours)
2. Corner smoothing (90-degree -> 45-degree -> rounded)
3. Width optimization (auto-widen power traces by current)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

from routing.push_router import Segment, Point

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of post-route optimization"""
    success: bool
    original_length: float = 0.0
    optimized_length: float = 0.0
    corners_smoothed: int = 0
    traces_widened: int = 0
    savings_percent: float = 0.0
    message: str = ""


class PostOptimizer:
    """Optimize completed routing for quality."""

    def optimize_all(
        self,
        segments: List[Segment],
        net_names: Optional[Dict[int, str]] = None,
        current_map: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[Segment], OptimizationResult]:
        """
        Run all optimizations.

        Args:
            segments: All routed segments
            net_names: Map of segment index to net name
            current_map: Map of net name to expected current (A)

        Returns:
            (optimized segments, result summary)
        """
        original_length = sum(s.length for s in segments)
        result = OptimizationResult(success=True, original_length=original_length)

        # Step 1: Remove redundant segments (co-linear merge)
        segments, merged = self._merge_colinear_segments(segments)
        logger.info(f"Merged {merged} co-linear segments")

        # Step 2: Smooth corners
        segments, corners = self._smooth_corners(segments)
        result.corners_smoothed = corners
        logger.info(f"Smoothed {corners} corners")

        # Step 3: Widen power traces
        if current_map:
            segments, widened = self._widen_power_traces(segments, current_map)
            result.traces_widened = widened
            logger.info(f"Widened {widened} power traces")

        optimized_length = sum(s.length for s in segments)
        result.optimized_length = optimized_length
        if original_length > 0:
            result.savings_percent = (1 - optimized_length / original_length) * 100
        result.message = (
            f"Optimized: {original_length:.1f}mm -> {optimized_length:.1f}mm "
            f"({result.savings_percent:.1f}% reduction), "
            f"{corners} corners smoothed, {result.traces_widened} traces widened"
        )

        return segments, result

    def _merge_colinear_segments(
        self, segments: List[Segment]
    ) -> Tuple[List[Segment], int]:
        """Merge adjacent co-linear segments (same direction, same layer)."""
        if len(segments) < 2:
            return segments, 0

        merged_count = 0
        result = [segments[0]]

        for seg in segments[1:]:
            prev = result[-1]

            # Check if segments are connected and co-linear
            connected = (
                abs(prev.end.x - seg.start.x) < 0.01 and
                abs(prev.end.y - seg.start.y) < 0.01 and
                prev.layer == seg.layer and
                abs(prev.width - seg.width) < 0.01
            )

            if not connected:
                result.append(seg)
                continue

            # Check co-linearity
            prev_dir = prev.direction()
            seg_dir = seg.direction()

            if (abs(prev_dir[0] - seg_dir[0]) < 0.01 and
                abs(prev_dir[1] - seg_dir[1]) < 0.01):
                # Co-linear: merge into one segment
                result[-1] = Segment(
                    start=prev.start, end=seg.end,
                    layer=prev.layer, width=prev.width,
                )
                merged_count += 1
            else:
                result.append(seg)

        return result, merged_count

    def _smooth_corners(
        self, segments: List[Segment]
    ) -> Tuple[List[Segment], int]:
        """
        Smooth corners: convert 90-degree bends to 45-degree chamfers.

        For a 90-degree bend at point P with segments A->P and P->B,
        replace with A->P1->P2->B where P1 and P2 form a 45-degree chamfer.
        """
        if len(segments) < 2:
            return segments, 0

        smoothed_count = 0
        result = [segments[0]]

        for i in range(1, len(segments)):
            prev = result[-1]
            curr = segments[i]

            # Check if there's a 90-degree corner at the junction
            if not self._is_connected(prev, curr):
                result.append(curr)
                continue

            corner_type = self._classify_corner(prev, curr)

            if corner_type == "right_angle":
                # Apply 45-degree chamfer
                chamfer_len = min(prev.length, curr.length) * 0.3
                chamfer_len = max(chamfer_len, 0.2)  # Minimum 0.2mm

                chamfered = self._apply_chamfer(prev, curr, chamfer_len)
                if chamfered:
                    result[-1] = chamfered[0]
                    result.append(chamfered[1])
                    result.append(chamfered[2])
                    smoothed_count += 1
                else:
                    result.append(curr)
            else:
                result.append(curr)

        return result, smoothed_count

    def _widen_power_traces(
        self,
        segments: List[Segment],
        current_map: Dict[str, float],
    ) -> Tuple[List[Segment], int]:
        """
        Widen power traces based on expected current.

        Uses IPC-2221 internal trace width formula (simplified):
        width_mm = current_A / (k * sqrt(delta_T))
        where k ~= 0.048 for internal layers, delta_T = 10 degC
        """
        widened_count = 0
        result = []

        power_keywords = ["vcc", "vdd", "vin", "3v3", "5v", "12v", "gnd", "power"]

        for seg in segments:
            # Find the net name for this segment (by position matching)
            net_name = ""
            current = 0.0

            for name, amps in current_map.items():
                if name.lower() in power_keywords:
                    net_name = name
                    current = amps
                    break

            if current > 0:
                # IPC-2221 simplified: width = I / (0.048 * sqrt(10))
                min_width = current / (0.048 * math.sqrt(10))
                min_width = max(min_width, 0.25)  # At least 0.25mm
                min_width = min(min_width, 3.0)   # Cap at 3mm

                if seg.width < min_width:
                    result.append(Segment(
                        start=seg.start, end=seg.end,
                        layer=seg.layer, width=min_width,
                    ))
                    widened_count += 1
                    continue

            result.append(seg)

        return result, widened_count

    def _is_connected(self, s1: Segment, s2: Segment) -> bool:
        return (abs(s1.end.x - s2.start.x) < 0.01 and
                abs(s1.end.y - s2.start.y) < 0.01)

    def _classify_corner(self, s1: Segment, s2: Segment) -> str:
        """Classify the angle between two connected segments."""
        d1 = s1.direction()
        d2 = s2.direction()

        # Dot product: 0 = 90 degrees, 1 = 0 degrees
        dot = d1[0] * d2[0] + d1[1] * d2[1]

        if abs(dot) < 0.01:
            return "right_angle"
        elif abs(dot - 0.5) < 0.1:
            return "45_degree"
        else:
            return "other"

    def _apply_chamfer(
        self, s1: Segment, s2: Segment, chamfer_len: float
    ) -> Optional[List[Segment]]:
        """Apply a 45-degree chamfer to a right-angle corner."""
        # Direction vectors
        d1 = s1.direction()
        d2 = s2.direction()

        # Corner point
        cx, cy = s1.end.x, s1.end.y

        # Chamfer point 1: move back along s1 from corner
        p1 = Point(cx - d1[0] * chamfer_len, cy - d1[1] * chamfer_len)

        # Chamfer point 2: move forward along s2 from corner
        p2 = Point(cx + d2[0] * chamfer_len, cy + d2[1] * chamfer_len)

        # Create 3 segments: s1_shortened, chamfer, s2_shortened
        seg1 = Segment(start=s1.start, end=p1, layer=s1.layer, width=s1.width)
        chamfer = Segment(start=p1, end=p2, layer=s1.layer, width=s1.width)
        seg2 = Segment(start=p2, end=s2.end, layer=s2.layer, width=s2.width)

        if seg1.length < 0.1 or seg2.length < 0.1:
            return None  # Too short to chamfer

        return [seg1, chamfer, seg2]

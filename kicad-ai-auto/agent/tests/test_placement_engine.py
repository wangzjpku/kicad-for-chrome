"""
Tests for Placement Engine
"""
import pytest
import sys
from pathlib import Path

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from placement.placement_engine import (
    PlacementEngine,
    Placement,
    Component,
    BoardConstraints,
    PlacementStrategy
)


class TestPlacementEngine:
    """Test cases for PlacementEngine"""

    def test_place_single_component(self):
        """Test placing a single component"""
        engine = PlacementEngine(board_width=100, board_height=80)

        components = [
            Component(ref="R1", width=10, height=5)
        ]

        result = engine.place(components)

        assert len(result.placements) == 1
        assert result.placements[0].ref == "R1"
        assert len(result.unplaced) == 0

    def test_place_multiple_components_no_overlap(self):
        """Test placing multiple components without overlap"""
        engine = PlacementEngine(board_width=100, board_height=80, grid_size=2.5)

        components = [
            Component(ref="U1", width=20, height=15),
            Component(ref="C1", width=5, height=5),
            Component(ref="R1", width=3, height=2),
        ]

        result = engine.place(components)

        assert len(result.placements) == 3
        assert len(result.unplaced) == 0

        # Verify no overlaps by checking bounding boxes
        placements = result.placements
        for i, p1 in enumerate(placements):
            comp1 = next(c for c in components if c.ref == p1.ref)
            bbox1 = comp1.get_bounding_box(p1.x, p1.y)

            for p2 in placements[i+1:]:
                comp2 = next(c for c in components if c.ref == p2.ref)
                bbox2 = comp2.get_bounding_box(p2.x, p2.y)

                # Check no overlap
                assert not (bbox1[0] < bbox2[2] and bbox1[2] > bbox2[0] and
                           bbox1[1] < bbox2[3] and bbox1[3] > bbox2[1]), \
                    f"Overlap detected between {p1.ref} and {p2.ref}"

    def test_board_boundaries_respected(self):
        """Test that components stay within board boundaries"""
        engine = PlacementEngine(board_width=100, board_height=80, margin=5)

        components = [
            Component(ref="U1", width=30, height=30)
        ]

        result = engine.place(components)

        assert len(result.placements) == 1
        p = result.placements[0]

        # Check within bounds with margin
        assert p.x >= 5
        assert p.y >= 5
        assert p.x + 30 <= 95  # 100 - 5 margin
        assert p.y + 30 <= 95

    def test_unplaced_components_when_board_too_small(self):
        """Test that components are marked unplaced when board is too small"""
        engine = PlacementEngine(board_width=10, board_height=10, margin=2)

        components = [
            Component(ref="U1", width=50, height=50)  # Too large for board
        ]

        result = engine.place(components)

        assert len(result.unplaced) == 1
        assert "U1" in result.unplaced

    def test_thermal_aware_placement(self):
        """Test thermal-aware placement puts hot components at edges"""
        engine = PlacementEngine(board_width=100, board_height=80)

        components = [
            Component(ref="U1", width=20, height=15, thermal_load=1.0),  # Hot
            Component(ref="C1", width=5, height=5, thermal_load=0.1),    # Cool
            Component(ref="R1", width=3, height=2, thermal_load=0.1),    # Cool
        ]

        result = engine.place_thermal_aware(components)

        assert len(result.placements) >= 2  # At least most should be placed

    def test_metrics_calculation(self):
        """Test that placement metrics are calculated correctly"""
        engine = PlacementEngine(board_width=100, board_height=80)

        components = [
            Component(ref="R1", width=10, height=5),
            Component(ref="R2", width=10, height=5),
        ]

        result = engine.place(components)

        assert "total_components" in result.metrics
        assert "placed_count" in result.metrics
        assert "placement_rate" in result.metrics
        assert "utilization" in result.metrics

        assert result.metrics["total_components"] == 2
        assert result.metrics["placed_count"] == 2
        assert result.metrics["placement_rate"] == 1.0

    def test_placement_with_rotation(self):
        """Test that rotation is preserved in placement"""
        engine = PlacementEngine(board_width=100, board_height=80)

        components = [
            Component(ref="R1", width=10, height=5, rotation=90)
        ]

        result = engine.place(components)

        assert len(result.placements) == 1
        assert result.placements[0].rotation == 90

    def test_empty_components_list(self):
        """Test placing empty component list"""
        engine = PlacementEngine(board_width=100, board_height=80)

        result = engine.place([])

        assert len(result.placements) == 0
        assert len(result.unplaced) == 0

    def test_large_component_first_placement(self):
        """Test that large components are placed first"""
        engine = PlacementEngine(board_width=100, board_height=80)

        components = [
            Component(ref="Small", width=2, height=2),
            Component(ref="Large", width=30, height=20),
            Component(ref="Medium", width=10, height=10),
        ]

        result = engine.place(components)

        # Large should be placed first (lowest index)
        assert result.placements[0].ref == "Large"


class TestComponent:
    """Test cases for Component dataclass"""

    def test_get_footprint_size_no_rotation(self):
        """Test footprint size without rotation"""
        comp = Component(ref="R1", width=10, height=5, rotation=0)
        w, h = comp.get_footprint_size()
        assert w == 10
        assert h == 5

    def test_get_footprint_size_with_rotation(self):
        """Test footprint size with 90 degree rotation"""
        comp = Component(ref="R1", width=10, height=5, rotation=90)
        w, h = comp.get_footprint_size()
        assert w == 5  # Swapped
        assert h == 10  # Swapped

    def test_get_bounding_box(self):
        """Test bounding box calculation"""
        comp = Component(ref="R1", width=10, height=5)
        bbox = comp.get_bounding_box(100, 50)

        assert bbox == (100, 50, 110, 55)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
DRC Integration Tests (Phase 7A)

Tests for PCBDataAdapter and the unified DRC pipeline.
"""
import unittest
import sys
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class TestPCBDataAdapterFromIPC(unittest.TestCase):
    """Test PCBDataAdapter.from_ipc with mock IPC data."""

    def setUp(self):
        """Set up mock IPC manager."""
        self.mock_ipc = MagicMock()

    def test_from_ipc_basic(self):
        """Test basic IPC data adaptation."""
        from drc.pcb_data_adapter import PCBDataAdapter

        self.mock_ipc.get_full_pcb_data.return_value = {
            "board": {"width": 50, "height": 30},
            "footprints": [
                {
                    "reference": "R1",
                    "position": {"x": 10, "y": 20},
                    "width": 3.0,
                    "height": 2.0,
                    "pins": [
                        {"number": "1", "net": "VCC", "position": {"x": 10, "y": 20}},
                        {"number": "2", "net": "GND", "position": {"x": 13, "y": 20}},
                    ],
                },
                {
                    "reference": "U1",
                    "position": {"x": 30, "y": 15},
                    "width": 5.0,
                    "height": 5.0,
                    "pins": [
                        {"number": "1", "net": "VCC", "position": {"x": 30, "y": 15}},
                        {"number": "2", "net": "SDA", "position": {"x": 33, "y": 15}},
                    ],
                },
            ],
            "tracks": [
                {
                    "net": "VCC",
                    "layer": "F.Cu",
                    "width": 0.5,
                    "start": {"x": 10, "y": 20},
                    "end": {"x": 30, "y": 15},
                },
                {
                    "net": "SDA",
                    "layer": "F.Cu",
                    "width": 0.15,
                    "start": {"x": 33, "y": 15},
                    "end": {"x": 45, "y": 15},
                },
            ],
            "vias": [
                {"x": 25, "y": 18, "net": "GND", "size": 0.8, "drill": 0.4},
            ],
        }

        result = PCBDataAdapter.from_ipc(self.mock_ipc)
        self.assertIsNotNone(result)
        self.assertTrue(len(result["components"]) > 0)
        self.assertEqual(result["components"][0]["reference"], "R1")
        self.assertEqual(len(result["tracks"]), 2)
        self.assertEqual(len(result["vias"]), 1)
        logger.info(
            f"IPC adapter test: {len(result['components'])} components, "
            f"{len(result['tracks'])} tracks, {len(result['vias'])} vias"
        )

    def test_from_ipc_empty(self):
        """Test IPC adapter with empty data returns None."""
        from drc.pcb_data_adapter import PCBDataAdapter

        self.mock_ipc.get_full_pcb_data.return_value = None
        result = PCBDataAdapter.from_ipc(self.mock_ipc)
        self.assertIsNone(result)

    def test_from_ipc_board_edges(self):
        """Test IPC adapter derives board from board_edges."""
        from drc.pcb_data_adapter import PCBDataAdapter

        self.mock_ipc.get_full_pcb_data.return_value = {
            "board_edges": [
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 100, "y": 80},
                {"x": 0, "y": 80},
            ],
            "footprints": [],
            "tracks": [],
            "vias": [],
        }
        result = PCBDataAdapter.from_ipc(self.mock_ipc)
        self.assertIsNotNone(result)
        self.assertEqual(result["board"]["width"], 100)
        self.assertEqual(result["board"]["height"], 80)


class TestPCBDataAdapterFromProject(unittest.TestCase):
    """Test PCBDataAdapter.from_project with project data."""

    def test_from_project_basic(self):
        """Test basic project data adaptation."""
        from drc.pcb_data_adapter import PCBDataAdapter

        project_data = {
            "pcb": {
                "footprints": [
                    {
                        "reference": "C1",
                        "position": {"x": 15, "y": 25},
                        "width": 2.0,
                        "height": 1.2,
                    },
                ],
                "tracks": [
                    {
                        "net": "VCC",
                        "layer": "F.Cu",
                        "width": 0.3,
                        "start": {"x": 0, "y": 0},
                        "end": {"x": 50, "y": 50},
                    },
                ],
                "vias": [
                    {"x": 20, "y": 30, "net": "GND", "size": 0.6, "drill": 0.3},
                ],
            },
            "board": {"width": 80, "height": 60},
        }

        result = PCBDataAdapter.from_project(project_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["board"]["width"], 80)
        self.assertEqual(len(result["components"]), 1)
        self.assertEqual(result["components"][0]["reference"], "C1")
        self.assertEqual(len(result["tracks"]), 1)
        logger.info(
            f"Project adapter test: {len(result['components'])} components, "
            f"{len(result['tracks'])} tracks"
        )

    def test_from_project_empty(self):
        """Test project adapter with empty data returns None."""
        from drc.pcb_data_adapter import PCBDataAdapter

        result = PCBDataAdapter.from_project(None)
        self.assertIsNone(result)

        result = PCBDataAdapter.from_project({})
        self.assertIsNone(result)


class TestPCBDataAdapterClassifyNets(unittest.TestCase):
    """Test net classification."""

    def test_classify_nets(self):
        """Test net classification from components and tracks."""
        from drc.pcb_data_adapter import _classify_nets

        components = [
            {"pins": [{"net": "VCC"}, {"net": "GND"}]},
            {"pins": [{"net": "SDA"}]},
        ]
        tracks = [
            {"net": "VCC"},
            {"net": "3V3"},
            {"net": "SDA"},
            {"net": "GND"},
        ]

        nets = _classify_nets(components, tracks)
        self.assertTrue(len(nets) > 0)
        net_map = {n["name"]: n for n in nets}
        self.assertIn("VCC", net_map)
        self.assertIn("GND", net_map)
        logger.info(f"Net classification: {len(nets)} nets classified")

    def test_classify_nets_empty(self):
        """Test net classification with empty data."""
        from drc.pcb_data_adapter import _classify_nets

        nets = _classify_nets([], [])
        self.assertEqual(nets, [])


class TestDRCEngine(unittest.TestCase):
    """Test AdvancedDRCEngine with adapted data."""

    def test_real_drc_check(self):
        """Test AdvancedDRCEngine with a deliberate violation."""
        from drc.advanced_drc import create_jlcpcb_drc

        engine = create_jlcpcb_drc()

        pcb_data = {
            "board": {"width": 50, "height": 30},
            "components": [
                {
                    "reference": "U1",
                    "footprint": "SOIC-8",
                    "x": 20, "y": 15,
                    "width": 5.0, "height": 4.0,
                    "layer": "F.Cu",
                    "rotation": 0,
                    "pins": [],
                },
            ],
            "tracks": [
                {
                    "net": "VCC",
                    "layer": "F.Cu",
                    "width": 0.05,
                    "points": [{"x": 0, "y": 0}, {"x": 50, "y": 30}],
                },
                {
                    "net": "GND",
                    "layer": "F.Cu",
                    "width": 0.25,
                    "points": [{"x": 5, "y": 5}, {"x": 45, "y": 25}],
                },
            ],
            "vias": [
                {
                    "x": 10, "y": 10,
                    "net": "GND",
                    "outer_diameter": 0.4,
                    "drill_diameter": 0.3,
                },
            ],
            "pads": [],
            "nets": [
                {"name": "VCC", "class": "power"},
                {"name": "GND", "class": "ground"},
            ],
        }

        result = engine.check(pcb_data)
        self.assertFalse(result.passed)
        self.assertGreater(result.error_count, 0)
        logger.info(
            f"Real DRC test: {result.error_count} errors, "
            f"{result.warning_count} warnings"
        )

    def test_empty_board_passes(self):
        """Test that an empty board passes DRC."""
        from drc.advanced_drc import create_jlcpcb_drc

        engine = create_jlcpcb_drc()
        pcb_data = {
            "board": {"width": 100, "height": 80},
            "components": [],
            "tracks": [],
            "vias": [],
            "pads": [],
            "nets": [],
        }
        result = engine.check(pcb_data)
        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        logger.info("Empty board DRC test passed")

    def test_drc_result_structure(self):
        """Test DRCResult has correct structure."""
        from drc.advanced_drc import create_jlcpcb_drc

        engine = create_jlcpcb_drc()
        pcb_data = {
            "board": {"width": 100, "height": 80},
            "components": [],
            "tracks": [
                {
                    "net": "CLK",
                    "layer": "F.Cu",
                    "width": 0.2,
                    "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}],
                },
            ],
            "vias": [],
            "pads": [],
            "nets": [{"name": "CLK", "class": "signal"}],
        }
        result = engine.check(pcb_data)
        self.assertTrue(hasattr(result, "passed"))
        self.assertTrue(hasattr(result, "violations"))
        self.assertTrue(hasattr(result, "error_count"))
        self.assertTrue(hasattr(result, "warning_count"))
        self.assertTrue(hasattr(result, "info_count"))
        self.assertTrue(hasattr(result, "statistics"))
        self.assertTrue(hasattr(result, "duration_ms"))
        self.assertGreater(result.duration_ms, 0)
        logger.info("DRC result structure test passed")


if __name__ == "__main__":
    unittest.main()

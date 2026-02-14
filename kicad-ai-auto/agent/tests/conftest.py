"""
Pytest configuration and fixtures
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_kicad_controller():
    """Create a mock KiCad controller for testing"""
    from unittest.mock import Mock

    controller = Mock()
    controller.is_running.return_value = True
    controller.start = Mock()
    controller.close = Mock()
    controller.save_project = Mock()
    controller.get_project_info = Mock(return_value={
        "path": "/projects/test.kicad_pro",
        "name": "test",
        "modified": "2024-01-01T00:00:00"
    })
    controller.get_screenshot = Mock(return_value=b"fake_png_data")
    controller.get_screenshot_base64 = Mock(return_value="base64encodedstring")
    controller.click_menu = Mock()
    controller.activate_tool = Mock()
    controller.mouse_click = Mock()
    controller.mouse_double_click = Mock()
    controller.mouse_move = Mock()
    controller.mouse_drag = Mock()
    controller.mouse_down = Mock()
    controller.mouse_up = Mock()
    controller.press_keys = Mock()
    controller.type_text = Mock()
    controller.run_drc = Mock(return_value={
        "error_count": 0,
        "warning_count": 0,
        "errors": [],
        "warnings": []
    })
    controller.get_drc_report = Mock(return_value={
        "error_count": 0,
        "warning_count": 0
    })
    controller.open_project = Mock()
    controller.export_gerber = Mock(return_value={
        "success": True,
        "files": ["test-F_Cu.gbr", "test-B_Cu.gbr"],
        "output_dir": "/output/gerber"
    })
    controller.export_drill = Mock(return_value={
        "success": True,
        "files": ["test.drl"],
        "output_dir": "/output/drill"
    })
    controller.export_bom = Mock(return_value={
        "success": True,
        "file": "/output/bom.csv"
    })

    return controller


@pytest.fixture
def mock_state_monitor(mock_kicad_controller):
    """Create a mock state monitor"""
    from unittest.mock import Mock

    monitor = Mock()
    monitor.controller = mock_kicad_controller
    monitor.get_state = Mock(return_value={
        "tool": "pointer",
        "cursor": {"x": 100, "y": 100},
        "layer": "F.Cu",
        "zoom": 1.0,
        "errors": [],
        "timestamp": "2024-01-01T00:00:00"
    })
    monitor.get_current_tool = Mock(return_value="pointer")
    monitor.get_cursor_coords = Mock(return_value={"x": 100, "y": 100})
    monitor.get_errors = Mock(return_value=[])

    return monitor


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with a test project"""
    project_dir = tmp_path / "projects"
    project_dir.mkdir()

    # Create a dummy project file
    project_file = project_dir / "test.kicad_pro"
    project_file.write_text('{"name": "test"}')

    return str(project_dir)

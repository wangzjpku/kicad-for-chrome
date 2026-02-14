"""
Tests for StateMonitor module
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from state_monitor import (
    StateMonitor,
    KiCadState,
    EditorType,
)


class TestKiCadState:
    """Test KiCadState dataclass"""

    def test_default_values(self):
        """Test default state values"""
        state = KiCadState()

        assert state.tool is None
        assert state.cursor_x == 0.0
        assert state.cursor_y == 0.0
        assert state.layer is None
        assert state.zoom == 100.0
        assert state.errors == []
        assert state.editor_type == "unknown"
        assert state.project_name is None
        assert state.grid_size is None
        assert state.selected_items == []
        assert state.is_modified is False

    def test_post_init_creates_timestamp(self):
        """Test that timestamp is created in post_init"""
        state = KiCadState()

        assert state.timestamp is not None
        assert isinstance(state.timestamp, datetime)

    def test_post_init_creates_empty_lists(self):
        """Test that None lists are converted to empty lists"""
        state = KiCadState(errors=None, selected_items=None)

        assert state.errors == []
        assert state.selected_items == []

    def test_custom_values(self):
        """Test state with custom values"""
        state = KiCadState(
            tool="route",
            cursor_x=100.5,
            cursor_y=200.5,
            layer="F.Cu",
            zoom=150.0,
            errors=["Error 1"],
            editor_type="pcb",
            project_name="test_project",
        )

        assert state.tool == "route"
        assert state.cursor_x == 100.5
        assert state.cursor_y == 200.5
        assert state.layer == "F.Cu"
        assert state.zoom == 150.0
        assert state.errors == ["Error 1"]
        assert state.editor_type == "pcb"
        assert state.project_name == "test_project"


class TestEditorType:
    """Test EditorType enum"""

    def test_editor_types_exist(self):
        """Test all editor types are defined"""
        assert EditorType.UNKNOWN.value == "unknown"
        assert EditorType.SCHEMATIC.value == "schematic"
        assert EditorType.PCB.value == "pcb"
        assert EditorType.SYMBOL_EDITOR.value == "symbol_editor"
        assert EditorType.FOOTPRINT_EDITOR.value == "footprint_editor"
        assert EditorType.GERBER_VIEWER.value == "gerber_viewer"
        assert EditorType.VIEWER_3D.value == "3d_viewer"


class TestStateMonitor:
    """Test StateMonitor class"""

    @pytest.fixture
    def mock_controller(self):
        """Create a mock controller"""
        controller = Mock()
        controller.get_screenshot = Mock(return_value=b"fake_screenshot_data")
        controller.is_running = Mock(return_value=True)
        return controller

    @pytest.fixture
    def monitor(self, mock_controller):
        """Create a StateMonitor instance"""
        return StateMonitor(mock_controller, update_interval=0.1)

    def test_initialization(self, monitor, mock_controller):
        """Test monitor initialization"""
        assert monitor.controller == mock_controller
        assert monitor.update_interval == 0.1
        assert isinstance(monitor.current_state, KiCadState)
        assert monitor.error_history == []
        assert monitor._running is False
        assert monitor._monitor_thread is None

    def test_get_state(self, monitor):
        """Test get_state returns correct structure"""
        state = monitor.get_state()

        assert "tool" in state
        assert "cursor" in state
        assert "layer" in state
        assert "zoom" in state
        assert "errors" in state
        assert "timestamp" in state
        assert "editor_type" in state
        assert "project_name" in state
        assert "grid_size" in state
        assert "selected_items" in state
        assert "is_modified" in state

        # Cursor should have x and y
        assert "x" in state["cursor"]
        assert "y" in state["cursor"]

    def test_get_current_tool(self, monitor):
        """Test getting current tool"""
        tool = monitor.get_current_tool()

        assert tool is None  # Default is None

    def test_get_cursor_coords(self, monitor):
        """Test getting cursor coordinates"""
        coords = monitor.get_cursor_coords()

        assert "x" in coords
        assert "y" in coords
        assert coords["x"] == 0.0
        assert coords["y"] == 0.0

    def test_get_errors(self, monitor):
        """Test getting errors"""
        errors = monitor.get_errors()

        assert isinstance(errors, list)
        assert errors == []

    def test_add_error(self, monitor):
        """Test adding an error"""
        monitor.add_error("Test error")

        assert "Test error" in monitor.current_state.errors
        assert len(monitor.error_history) == 1
        assert monitor.error_history[0]["error"] == "Test error"

    def test_add_multiple_errors(self, monitor):
        """Test adding multiple errors"""
        monitor.add_error("Error 1")
        monitor.add_error("Error 2")
        monitor.add_error("Error 3")

        assert len(monitor.current_state.errors) == 3
        assert len(monitor.error_history) == 3

    def test_clear_errors(self, monitor):
        """Test clearing errors"""
        monitor.add_error("Error 1")
        monitor.add_error("Error 2")

        monitor.clear_errors()

        assert monitor.current_state.errors == []

    def test_error_history_limit(self, monitor):
        """Test error history is limited to max_history"""
        monitor.max_history = 10

        for i in range(15):
            monitor.add_error(f"Error {i}")

        assert len(monitor.error_history) == 10
        # Should keep the most recent
        assert monitor.error_history[-1]["error"] == "Error 14"

    def test_start_monitoring(self, monitor):
        """Test starting monitoring"""
        monitor.start_monitoring()

        assert monitor._running is True
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()

        # Clean up
        monitor.stop_monitoring()

    def test_stop_monitoring(self, monitor):
        """Test stopping monitoring"""
        monitor.start_monitoring()
        monitor.stop_monitoring()

        assert monitor._running is False

    def test_state_callbacks(self, monitor):
        """Test state change callbacks"""
        callback_called = []

        def test_callback(state):
            callback_called.append(state)

        monitor.add_state_callback(test_callback)

        # Trigger a state update
        monitor._notify_callbacks()

        assert len(callback_called) == 1
        assert isinstance(callback_called[0], KiCadState)

    def test_remove_state_callback(self, monitor):
        """Test removing state callback"""
        callback_called = []

        def test_callback(state):
            callback_called.append(state)

        monitor.add_state_callback(test_callback)
        monitor.remove_state_callback(test_callback)

        monitor._notify_callbacks()

        assert len(callback_called) == 0

    def test_callback_exception_handling(self, monitor):
        """Test that callback exceptions are handled"""

        def bad_callback(state):
            raise Exception("Callback error")

        good_callback_called = []

        def good_callback(state):
            good_callback_called.append(state)

        monitor.add_state_callback(bad_callback)
        monitor.add_state_callback(good_callback)

        # Should not raise, and good callback should still be called
        monitor._notify_callbacks()

        assert len(good_callback_called) == 1

    def test_state_changed_detection(self, monitor):
        """Test state change detection"""
        old_state = KiCadState(tool="select", cursor_x=0, cursor_y=0)
        new_state = KiCadState(tool="route", cursor_x=0, cursor_y=0)

        assert monitor._state_changed(old_state, new_state) is True

    def test_state_unchanged_detection(self, monitor):
        """Test state unchanged detection"""
        old_state = KiCadState(tool="select", cursor_x=100, cursor_y=200)
        new_state = KiCadState(tool="select", cursor_x=100, cursor_y=200)

        assert monitor._state_changed(old_state, new_state) is False


class TestStateMonitorWithMocks:
    """Test StateMonitor with mocked external dependencies"""

    @pytest.fixture
    def mock_controller(self):
        controller = Mock()
        controller.get_screenshot = Mock(return_value=b"fake_screenshot")
        return controller

    def test_update_from_pcbnew_not_available(self, mock_controller):
        """Test state update when pcbnew is not available"""
        with patch("state_monitor.HAS_PCBNEW", False):
            monitor = StateMonitor(mock_controller)
            state = monitor.get_state()

            # Should still return a valid state
            assert state is not None

    def test_update_from_screenshot_no_cv2(self, mock_controller):
        """Test screenshot analysis when OpenCV is not available"""
        with patch("state_monitor.HAS_CV2", False):
            monitor = StateMonitor(mock_controller)
            state = monitor.get_state()

            # Should still return a valid state
            assert state is not None

    def test_detect_ui_changes_no_cv2(self, mock_controller):
        """Test UI change detection without OpenCV"""
        with patch("state_monitor.HAS_CV2", False):
            monitor = StateMonitor(mock_controller)
            changes = monitor.detect_ui_changes(b"before", b"after")

            assert changes == []

    def test_get_layer_list_without_pcbnew(self, mock_controller):
        """Test getting layer list without pcbnew"""
        with patch("state_monitor.HAS_PCBNEW", False):
            monitor = StateMonitor(mock_controller)
            layers = monitor.get_layer_list()

            # Should return default layer
            assert len(layers) == 1
            assert layers[0]["name"] == "F.Cu"


class TestStateMonitorThreading:
    """Test StateMonitor threading behavior"""

    @pytest.fixture
    def mock_controller(self):
        controller = Mock()
        controller.get_screenshot = Mock(return_value=b"screenshot")
        return controller

    def test_monitoring_updates_state(self, mock_controller):
        """Test that monitoring thread updates state"""
        monitor = StateMonitor(mock_controller, update_interval=0.05)

        # Record initial timestamp
        initial_timestamp = monitor.current_state.timestamp

        monitor.start_monitoring()

        # Wait for at least one update cycle
        time.sleep(0.15)

        monitor.stop_monitoring()

        # Timestamp should have changed
        assert monitor.current_state.timestamp != initial_timestamp

    def test_multiple_start_calls_safe(self, mock_controller):
        """Test that multiple start calls are safe"""
        monitor = StateMonitor(mock_controller)

        monitor.start_monitoring()
        monitor.start_monitoring()  # Should not create another thread

        # Only one thread should exist
        assert monitor._monitor_thread is not None

        monitor.stop_monitoring()


class TestStateMonitorLayerNames:
    """Test layer name mappings"""

    @pytest.fixture
    def mock_controller(self):
        return Mock()

    @pytest.fixture
    def monitor(self, mock_controller):
        return StateMonitor(mock_controller)

    def test_layer_names_mapping(self, monitor):
        """Test that common layers are mapped"""
        assert monitor.LAYER_NAMES[0] == "F.Cu"
        assert monitor.LAYER_NAMES[31] == "B.Cu"
        assert monitor.LAYER_NAMES[37] == "F.SilkS"
        assert monitor.LAYER_NAMES[39] == "F.Mask"
        assert monitor.LAYER_NAMES[44] == "Edge.Cuts"

    def test_tool_names_mapping(self, monitor):
        """Test tool name mappings exist"""
        assert "select" in monitor.TOOL_NAMES
        assert "route" in monitor.TOOL_NAMES
        assert "move" in monitor.TOOL_NAMES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

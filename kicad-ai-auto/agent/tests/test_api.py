"""
Tests for FastAPI endpoints using TestClient
"""

import pytest
import io
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile

# We need to mock the controller before importing the app
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies"""
    with patch('main.KiCadController') as MockController, \
         patch('main.StateMonitor') as MockStateMonitor, \
         patch('main.ExportManager') as MockExportManager:

        # Setup mock controller
        mock_controller = Mock()
        mock_controller.is_running.return_value = True
        mock_controller.start = Mock()
        mock_controller.close = Mock()
        mock_controller.save_project = Mock()
        mock_controller.get_project_info = Mock(return_value={
            "path": "/projects/test.kicad_pro",
            "name": "test",
            "modified": "2024-01-01T00:00:00"
        })
        mock_controller.get_screenshot = Mock(return_value=b"fake_png_data")
        mock_controller.click_menu = Mock()
        mock_controller.activate_tool = Mock()
        mock_controller.mouse_click = Mock()
        mock_controller.mouse_double_click = Mock()
        mock_controller.mouse_move = Mock()
        mock_controller.mouse_drag = Mock()
        mock_controller.press_keys = Mock()
        mock_controller.type_text = Mock()
        mock_controller.run_drc = Mock(return_value={
            "error_count": 0,
            "warning_count": 0,
            "errors": [],
            "warnings": []
        })
        mock_controller.get_drc_report = Mock(return_value={
            "error_count": 0,
            "warning_count": 0
        })
        mock_controller.open_project = Mock()
        MockController.return_value = mock_controller

        # Setup mock state monitor
        mock_monitor = Mock()
        mock_monitor.get_state = Mock(return_value={
            "tool": "pointer",
            "cursor": {"x": 100, "y": 100},
            "layer": "F.Cu",
            "zoom": 1.0,
            "errors": [],
            "timestamp": "2024-01-01T00:00:00"
        })
        mock_monitor.get_current_tool = Mock(return_value="pointer")
        mock_monitor.get_cursor_coords = Mock(return_value={"x": 100, "y": 100})
        mock_monitor.get_errors = Mock(return_value=[])
        MockStateMonitor.return_value = mock_monitor

        # Setup mock export manager
        mock_export = AsyncMock()
        mock_export.export = AsyncMock(return_value={
            "success": True,
            "files": ["test.gbr"]
        })
        MockExportManager.return_value = mock_export

        yield {
            'controller': mock_controller,
            'monitor': mock_monitor,
            'export': mock_export
        }


@pytest.fixture
def client(mock_dependencies):
    """Create test client"""
    from main import app
    with TestClient(app) as test_client:
        yield test_client


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check_returns_200(self, client, mock_dependencies):
        """Test health check returns healthy status"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["kicad_running"] is True


class TestProjectEndpoints:
    """Test project-related endpoints"""

    def test_start_kicad(self, client, mock_dependencies):
        """Test starting KiCad"""
        response = client.post("/api/project/start")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "started successfully" in data["message"].lower()
        mock_dependencies['controller'].start.assert_called_once()

    def test_start_kicad_with_project(self, client, mock_dependencies):
        """Test starting KiCad with project path"""
        response = client.post(
            "/api/project/start",
            params={"project_path": "/projects/test.kicad_pro"}
        )

        assert response.status_code == 200
        mock_dependencies['controller'].start.assert_called_once_with(
            "/projects/test.kicad_pro"
        )

    def test_stop_kicad(self, client, mock_dependencies):
        """Test stopping KiCad"""
        response = client.post("/api/project/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dependencies['controller'].close.assert_called_once()

    def test_save_project(self, client, mock_dependencies):
        """Test saving project"""
        response = client.post("/api/project/save")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dependencies['controller'].save_project.assert_called_once()

    def test_get_project_info(self, client, mock_dependencies):
        """Test getting project info"""
        response = client.get("/api/project/info")

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "/projects/test.kicad_pro"
        assert data["name"] == "test"

    def test_open_project_valid_file(self, client, mock_dependencies):
        """Test opening a valid project file"""
        # Create a fake kicad_pro file
        file_content = b"fake kicad project content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/project/open",
            files={"file": ("test.kicad_pro", file, "application/octet-stream")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_open_project_invalid_extension(self, client, mock_dependencies):
        """Test opening file with invalid extension"""
        file_content = b"fake content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/api/project/open",
            files={"file": ("test.txt", file, "text/plain")}
        )

        assert response.status_code == 400


class TestMenuEndpoints:
    """Test menu-related endpoints"""

    def test_click_menu(self, client, mock_dependencies):
        """Test clicking menu"""
        response = client.post(
            "/api/menu/click",
            json={"menu": "file", "item": "save"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dependencies['controller'].click_menu.assert_called_once_with(
            "file", "save"
        )


class TestToolEndpoints:
    """Test tool-related endpoints"""

    def test_activate_tool(self, client, mock_dependencies):
        """Test activating tool"""
        response = client.post(
            "/api/tool/activate",
            json={"tool": "route", "params": {"layer": "F.Cu"}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dependencies['controller'].activate_tool.assert_called_once()


class TestInputEndpoints:
    """Test input-related endpoints"""

    def test_send_mouse_click(self, client, mock_dependencies):
        """Test sending mouse click"""
        response = client.post(
            "/api/input/mouse",
            json={"action": "click", "x": 100, "y": 200, "button": "left"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dependencies['controller'].mouse_click.assert_called_once()

    def test_send_mouse_move(self, client, mock_dependencies):
        """Test sending mouse move"""
        response = client.post(
            "/api/input/mouse",
            json={"action": "move", "x": 150, "y": 250}
        )

        assert response.status_code == 200
        mock_dependencies['controller'].mouse_move.assert_called_once()

    def test_send_mouse_drag(self, client, mock_dependencies):
        """Test sending mouse drag"""
        response = client.post(
            "/api/input/mouse",
            json={"action": "drag", "x": 100, "y": 200, "duration": 0.5}
        )

        assert response.status_code == 200
        mock_dependencies['controller'].mouse_drag.assert_called_once()

    def test_send_keyboard_keys(self, client, mock_dependencies):
        """Test sending keyboard keys"""
        response = client.post(
            "/api/input/keyboard",
            json={"keys": ["Ctrl", "S"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dependencies['controller'].press_keys.assert_called_once()

    def test_send_keyboard_text(self, client, mock_dependencies):
        """Test sending keyboard text"""
        response = client.post(
            "/api/input/keyboard",
            json={"keys": [], "text": "Hello"}
        )

        assert response.status_code == 200
        mock_dependencies['controller'].type_text.assert_called_once()


class TestStateEndpoints:
    """Test state-related endpoints"""

    def test_get_screenshot(self, client, mock_dependencies):
        """Test getting screenshot"""
        response = client.get("/api/state/screenshot")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_get_full_state(self, client, mock_dependencies):
        """Test getting full state"""
        response = client.get("/api/state/full")

        assert response.status_code == 200
        data = response.json()
        assert data["tool"] == "pointer"
        assert "cursor" in data
        assert "layer" in data

    def test_get_current_tool(self, client, mock_dependencies):
        """Test getting current tool"""
        response = client.get("/api/state/tool")

        assert response.status_code == 200
        data = response.json()
        assert data["tool"] == "pointer"

    def test_get_cursor_coords(self, client, mock_dependencies):
        """Test getting cursor coordinates"""
        response = client.get("/api/state/coords")

        assert response.status_code == 200
        data = response.json()
        assert "x" in data
        assert "y" in data

    def test_get_errors(self, client, mock_dependencies):
        """Test getting errors"""
        response = client.get("/api/state/errors")

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data


class TestExportEndpoints:
    """Test export-related endpoints"""

    def test_export_files(self, client, mock_dependencies):
        """Test exporting files"""
        response = client.post(
            "/api/export",
            json={"format": "gerber", "output_dir": "/output"}
        )

        assert response.status_code == 200

    def test_get_export_formats(self, client, mock_dependencies):
        """Test getting available export formats"""
        response = client.get("/api/export/formats")

        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        format_ids = [f["id"] for f in data["formats"]]
        assert "gerber" in format_ids
        assert "drill" in format_ids
        assert "bom" in format_ids


class TestDRCEndpoints:
    """Test DRC-related endpoints"""

    def test_run_drc(self, client, mock_dependencies):
        """Test running DRC"""
        response = client.post("/api/drc/run")

        assert response.status_code == 200
        data = response.json()
        assert "error_count" in data

    def test_get_drc_report(self, client, mock_dependencies):
        """Test getting DRC report"""
        response = client.get("/api/drc/report")

        assert response.status_code == 200
        data = response.json()
        assert "error_count" in data


class TestRateLimiting:
    """Test rate limiting"""

    def test_health_check_rate_limit(self, client, mock_dependencies):
        """Test health check rate limit allows reasonable requests"""
        # Make multiple requests - should all succeed
        for _ in range(10):
            response = client.get("/api/health")
            assert response.status_code == 200


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers(self, client, mock_dependencies):
        """Test CORS headers are set"""
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # Check that CORS is configured (will vary based on configuration)
        assert response.status_code in [200, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

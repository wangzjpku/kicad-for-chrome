"""
Tests for ExportManager module
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from export_manager import ExportManager


class TestExportManager:
    """Test ExportManager class"""

    @pytest.fixture
    def mock_controller(self):
        """Create a mock KiCad controller"""
        controller = Mock()
        controller.export_gerber = Mock(
            return_value={
                "success": True,
                "files": ["test.gbr"],
                "output_dir": "/output",
            }
        )
        controller.export_drill = Mock(
            return_value={
                "success": True,
                "files": ["test.drl"],
                "output_dir": "/output",
            }
        )
        controller.export_bom = Mock(
            return_value={"success": True, "file": "/output/bom.csv"}
        )
        # 这些导出方法已实现，但为了测试回退行为，让它们返回失败
        controller.export_pickplace = Mock(
            return_value={
                "success": False,
                "error": "Pick & Place export not yet implemented",
            }
        )
        controller.export_pdf = Mock(
            return_value={"success": False, "error": "PDF export not yet implemented"}
        )
        controller.export_svg = Mock(
            return_value={"success": False, "error": "SVG export not yet implemented"}
        )
        controller.export_step = Mock(
            return_value={"success": False, "error": "STEP export not yet implemented"}
        )
        return controller

    @pytest.fixture
    def export_manager(self, mock_controller):
        """Create an ExportManager instance"""
        return ExportManager(mock_controller)

    @pytest.mark.asyncio
    async def test_export_gerber(self, export_manager, mock_controller):
        """Test Gerber export"""
        result = await export_manager.export("gerber", "/output/gerber")

        assert result["success"] is True
        mock_controller.export_gerber.assert_called_once_with("/output/gerber", None)

    @pytest.mark.asyncio
    async def test_export_gerber_with_layers(self, export_manager, mock_controller):
        """Test Gerber export with specific layers"""
        result = await export_manager.export(
            "gerber", "/output/gerber", {"layers": ["F.Cu", "B.Cu"]}
        )

        assert result["success"] is True
        mock_controller.export_gerber.assert_called_once_with(
            "/output/gerber", ["F.Cu", "B.Cu"]
        )

    @pytest.mark.asyncio
    async def test_export_drill(self, export_manager, mock_controller):
        """Test drill file export"""
        result = await export_manager.export("drill", "/output/drill")

        assert result["success"] is True
        mock_controller.export_drill.assert_called_once_with("/output/drill")

    @pytest.mark.asyncio
    async def test_export_bom(self, export_manager, mock_controller):
        """Test BOM export"""
        result = await export_manager.export("bom", "/output")

        assert result["success"] is True
        # BOM should create file in output directory
        expected_path = os.path.join("/output", "bom.csv")
        mock_controller.export_bom.assert_called_once_with(expected_path)

    @pytest.mark.asyncio
    async def test_export_pickplace_not_implemented(self, export_manager):
        """Test Pick & Place export (not implemented)"""
        result = await export_manager.export("pickplace", "/output")

        assert result["success"] is False
        assert "not yet implemented" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_export_pdf_not_implemented(self, export_manager):
        """Test PDF export (not implemented)"""
        result = await export_manager.export("pdf", "/output")

        assert result["success"] is False
        assert "not yet implemented" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_export_svg_not_implemented(self, export_manager):
        """Test SVG export (not implemented)"""
        result = await export_manager.export("svg", "/output")

        assert result["success"] is False
        assert "not yet implemented" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_export_step_not_implemented(self, export_manager):
        """Test STEP export (not implemented)"""
        result = await export_manager.export("step", "/output")

        assert result["success"] is False
        assert "not yet implemented" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_export_unknown_format(self, export_manager):
        """Test unknown export format"""
        result = await export_manager.export("unknown", "/output")

        assert result["success"] is False
        assert "unknown" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_export_creates_output_directory(
        self, export_manager, mock_controller
    ):
        """Test that export creates output directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "new_subdir", "gerber")

            with patch("os.makedirs") as mock_makedirs:
                await export_manager.export("gerber", output_path)
                mock_makedirs.assert_called_once_with(output_path, exist_ok=True)

    @pytest.mark.asyncio
    async def test_export_all(self, export_manager, mock_controller):
        """Test export all formats"""
        result = await export_manager.export_all("/output")

        assert "results" in result
        assert "gerber" in result["results"]
        assert "drill" in result["results"]
        assert "bom" in result["results"]
        assert "pickplace" in result["results"]

        # Gerber, drill, and bom should succeed
        assert result["results"]["gerber"]["success"] is True
        assert result["results"]["drill"]["success"] is True
        assert result["results"]["bom"]["success"] is True
        # pickplace is not implemented
        assert result["results"]["pickplace"]["success"] is False

    @pytest.mark.asyncio
    async def test_export_all_with_failure(self, export_manager, mock_controller):
        """Test export all with some failures"""
        # Make gerber export fail
        mock_controller.export_gerber.side_effect = Exception("Gerber export failed")

        result = await export_manager.export_all("/output")

        assert result["success"] is False
        assert result["results"]["gerber"]["success"] is False
        assert "error" in result["results"]["gerber"]

    @pytest.mark.asyncio
    async def test_export_empty_options(self, export_manager, mock_controller):
        """Test export with empty options dict"""
        result = await export_manager.export("gerber", "/output", {})

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_export_none_options(self, export_manager, mock_controller):
        """Test export with None options"""
        result = await export_manager.export("gerber", "/output", None)

        assert result["success"] is True


class TestExportManagerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def mock_controller(self):
        controller = Mock()
        controller.export_gerber = Mock(side_effect=Exception("Export failed"))
        controller.export_drill = Mock(return_value={"success": True})
        controller.export_bom = Mock(return_value={"success": True})
        return controller

    @pytest.fixture
    def export_manager(self, mock_controller):
        return ExportManager(mock_controller)

    @pytest.mark.asyncio
    async def test_controller_exception_handling(self, export_manager):
        """Test that controller exceptions are propagated"""
        with pytest.raises(Exception) as exc_info:
            await export_manager.export("gerber", "/output")

        assert "Export failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_exports(self, mock_controller):
        """Test multiple concurrent exports"""
        import asyncio

        # Reset the mock to return success
        mock_controller.export_gerber = Mock(return_value={"success": True})
        mock_controller.export_drill = Mock(return_value={"success": True})
        mock_controller.export_bom = Mock(return_value={"success": True})

        export_manager = ExportManager(mock_controller)

        # Run multiple exports concurrently
        tasks = [export_manager.export("gerber", f"/output/{i}") for i in range(5)]

        results = await asyncio.gather(*tasks)

        assert all(r["success"] for r in results)
        assert mock_controller.export_gerber.call_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

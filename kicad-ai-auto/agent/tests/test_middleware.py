"""
Tests for middleware module
"""

import pytest
import logging
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request
from fastapi.responses import JSONResponse

from middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    setup_logging,
    KiCadError,
    KiCadNotRunningError,
    KiCadTimeoutError,
    KiCadCommandError,
    ProjectNotFoundError,
    ExportError,
)


class TestCustomExceptions:
    """Test custom exception classes"""

    def test_kicad_error_base(self):
        """Test base KiCadError"""
        error = KiCadError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_kicad_not_running_error(self):
        """Test KiCadNotRunningError"""
        error = KiCadNotRunningError("KiCad is not running")
        assert "not running" in str(error).lower()
        assert isinstance(error, KiCadError)

    def test_kicad_timeout_error(self):
        """Test KiCadTimeoutError"""
        error = KiCadTimeoutError("Operation timed out")
        assert "timed out" in str(error).lower()
        assert isinstance(error, KiCadError)

    def test_kicad_command_error(self):
        """Test KiCadCommandError with command info"""
        error = KiCadCommandError("export", "File not found")
        assert error.command == "export"
        assert "export" in str(error)
        assert "File not found" in str(error)
        assert isinstance(error, KiCadError)

    def test_project_not_found_error(self):
        """Test ProjectNotFoundError with path info"""
        error = ProjectNotFoundError("/projects/test.kicad_pro")
        assert error.path == "/projects/test.kicad_pro"
        assert "test.kicad_pro" in str(error)
        assert isinstance(error, KiCadError)

    def test_export_error(self):
        """Test ExportError with format info"""
        error = ExportError("gerber", "Invalid layer")
        assert error.format == "gerber"
        assert "gerber" in str(error)
        assert "Invalid layer" in str(error)
        assert isinstance(error, KiCadError)


class TestSetupLogging:
    """Test logging setup"""

    def test_setup_logging_default(self):
        """Test default logging setup"""
        with patch('logging.basicConfig') as mock_config:
            setup_logging()
            mock_config.assert_called_once()
            call_args = mock_config.call_args
            assert call_args.kwargs['level'] == logging.INFO

    def test_setup_logging_debug(self):
        """Test debug level logging setup"""
        with patch('logging.basicConfig') as mock_config:
            setup_logging("DEBUG")
            call_args = mock_config.call_args
            assert call_args.kwargs['level'] == logging.DEBUG

    def test_setup_logging_error(self):
        """Test error level logging setup"""
        with patch('logging.basicConfig') as mock_config:
            setup_logging("ERROR")
            call_args = mock_config.call_args
            assert call_args.kwargs['level'] == logging.ERROR

    def test_third_party_log_levels(self):
        """Test that third party loggers are suppressed"""
        setup_logging("INFO")

        # Check third party loggers are set to WARNING
        assert logging.getLogger("uvicorn").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("PIL").level == logging.WARNING


class TestRequestLoggingMiddleware:
    """Test request logging middleware"""

    @pytest.fixture
    def middleware(self):
        app = Mock()
        return RequestLoggingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test/api/health")
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"content-type": "application/json"}
        return request

    @pytest.mark.asyncio
    async def test_dispatch_success(self, middleware, mock_request):
        """Test successful request dispatch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        call_next = AsyncMock(return_value=mock_response)

        with patch('middleware.logger') as mock_logger:
            response = await middleware.dispatch(mock_request, call_next)

            assert response.status_code == 200
            assert "X-Process-Time" in response.headers
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_dispatch_with_error(self, middleware, mock_request):
        """Test request dispatch with error"""
        call_next = AsyncMock(side_effect=Exception("Test error"))

        with patch('middleware.logger') as mock_logger:
            response = await middleware.dispatch(mock_request, call_next)

            assert response.status_code == 500
            assert isinstance(response, JSONResponse)
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_headers_sanitization(self, middleware, mock_request):
        """Test that sensitive headers are not logged"""
        mock_request.headers = {
            "content-type": "application/json",
            "authorization": "Bearer token123",
            "x-api-key": "secret-key",
            "cookie": "session=abc123",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        with patch('middleware.logger') as mock_logger:
            await middleware.dispatch(mock_request, call_next)

            # Check that debug log was called with sanitized headers
            debug_calls = mock_logger.debug.call_args_list
            for call in debug_calls:
                if "Headers" in str(call):
                    # Sensitive headers should not be in the log
                    call_str = str(call)
                    assert "Bearer token123" not in call_str
                    assert "secret-key" not in call_str
                    assert "session=abc123" not in call_str


class TestErrorHandlingMiddleware:
    """Test error handling middleware"""

    @pytest.fixture
    def middleware(self):
        app = Mock()
        return ErrorHandlingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test/api/project")
        return request

    @pytest.mark.asyncio
    async def test_dispatch_success(self, middleware, mock_request):
        """Test successful request"""
        mock_response = Mock()
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_value_error_returns_400(self, middleware, mock_request):
        """Test ValueError returns 400"""
        call_next = AsyncMock(side_effect=ValueError("Invalid input"))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 400
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_file_not_found_returns_404(self, middleware, mock_request):
        """Test FileNotFoundError returns 404"""
        call_next = AsyncMock(side_effect=FileNotFoundError("File missing"))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 404
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_permission_error_returns_403(self, middleware, mock_request):
        """Test PermissionError returns 403"""
        call_next = AsyncMock(side_effect=PermissionError("Access denied"))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 403
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_generic_error_returns_500(self, middleware, mock_request):
        """Test generic exception returns 500"""
        call_next = AsyncMock(side_effect=RuntimeError("Something went wrong"))

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 500
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_error_response_format(self, middleware, mock_request):
        """Test error response format"""
        call_next = AsyncMock(side_effect=ValueError("Test error"))

        response = await middleware.dispatch(mock_request, call_next)

        # JSONResponse body would need to be parsed to check content
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

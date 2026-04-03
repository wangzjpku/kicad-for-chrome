"""
Middleware for KiCad AI Auto Control Agent
Includes request logging and error handling middleware

Phase 3.1 Enhanced:
- Unified error response format with request_id and timestamp
- Custom exception hierarchy for domain-specific errors
- Pydantic validation error formatting
- Configurable error detail exposure (debug vs production)
"""

import time
import logging
import uuid
from datetime import datetime
from typing import Callable, Optional, Any

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ============================================================================
# Error Response Format
# ============================================================================
def _make_error_response(
    error_type: str,
    detail: str,
    status_code: int,
    request_id: Optional[str] = None,
    **extra: Any
) -> dict:
    """Create a standardized error response body."""
    return {
        "error": error_type,
        "detail": detail,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status_code": status_code,
        **extra
    }
# ============================================================================
# Exception Hierarchy
# ============================================================================
class KiCadError(Exception):
    """KiCad 操作错误基类"""
    def __init__(self, message: str, error_code: str = "KICAD_ERROR"):
        self.error_code = error_code
        super().__init__(message)
class KiCadNotRunningError(KiCadError):
    """KiCad 未运行"""
    def __init__(self, message: str = "KiCad is not running"):
        super().__init__(message, "KICAD_NOT_RUNNING")
class KiCadTimeoutError(KiCadError):
    """KiCad 操作超时"""
    def __init__(self, operation: str = "operation", timeout: float = 30.0):
        self.timeout = timeout
        super().__init__(
            f"KiCad {operation} timed out after {timeout}s",
            "KICAD_TIMEOUT"
        )
class KiCadCommandError(KiCadError):
    """KiCad 命令执行失败"""
    def __init__(self, command: str, message: str = ""):
        self.command = command
        super().__init__(
            f"Command '{command}' failed: {message}",
            "KICAD_COMMAND_ERROR"
        )
class ProjectNotFoundError(KiCadError):
    """项目未找到"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Project not found: {path}", "PROJECT_NOT_FOUND")
class ExportError(KiCadError):
    """导出错误"""
    def __init__(self, format: str, message: str = ""):
        self.format = format
        super().__init__(
            f"Export to {format} failed: {message}",
            "EXPORT_ERROR"
        )
# Phase 3.1: Additional Domain Exceptions
class ValidationError(Exception):
    """数据验证错误"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(f"Validation error on '{field}': {message}")
class AuthenticationError(Exception):
    """认证错误"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)
class AuthorizationError(Exception):
    """授权错误"""
    def __init__(self, resource: str = "resource", action: str = "access"):
        self.resource = resource
        self.action = action
        super().__init__(f"Not authorized to {action} {resource}")
class ResourceNotFoundError(Exception):
    """资源未找到"""
    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} '{resource_id}' not found")
class RateLimitError(Exception):
    """请求频率限制"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")
class ServiceUnavailableError(Exception):
    """服务不可用"""
    def __init__(self, service: str, reason: str = ""):
        self.service = service
        super().__init__(f"Service '{service}' unavailable: {reason}")
# ============================================================================
# Request Logging Middleware
# ============================================================================
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录所有 HTTP 请求的详细信息，生成唯一请求ID
    Phase 3.1 Enhanced:
    - Uses UUID for request_id (not Python id())
    - Adds X-Request-ID header to response
    - Stores request_id in request.state for downstream use
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()
        # 生成唯一请求ID (优先使用客户端提供的ID)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        # 存储到 request.state 供下游使用
        request.state.request_id = request_id
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"
        # 记录请求开始
        logger.info(
            f"[{request_id}] → {method} {url} from {client_host}"
        )
        # 记录请求头（排除敏感信息）
        safe_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ['authorization', 'x-api-key', 'cookie']
        }
        logger.debug(f"[{request_id}] Headers: {safe_headers}")
        try:
            # 处理请求
            response = await call_next(request)
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000
            # 记录响应
            logger.info(
                f"[{request_id}] ← {method} {url} "
                f"-> {response.status_code} ({process_time:.2f}ms)"
            )
            # 添加处理时间和请求ID头
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            return response
        except (HTTPException, StarletteHTTPException):
            raise  # Let FastAPI/Starlette handle HTTPException
        except Exception as e:
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000
            # 记录完整错误到日志（仅服务端可见)
            logger.error(
                f"[{request_id}] ✗ {method} {url} "
                f"-> {type(e).__name__}: {str(e)} ({process_time:.2f}ms)",
                exc_info=True
            )
            # 返回通用错误响应(不暴露敏感信息)
            return JSONResponse(
                status_code=500,
                content=_make_error_response(
                    error_type="InternalServerError",
                    detail="An unexpected error occurred. Please try again later.",
                    status_code=500,
                    request_id=request_id
                ),
                headers={"X-Request-ID": request_id}
            )
# ============================================================================
# Error Handling Middleware
# ============================================================================
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    错误处理中间件
    统一处理所有未捕获的异常,返回标准化错误响应
    Phase 3.1 Enhanced:
    - Handles custom exception hierarchy
    - Returns standardized error format with request_id
    - Maps domain exceptions to appropriate HTTP status codes
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            # Pydantic 验证错误
            request_id = getattr(request.state, "request_id", "unknown")
            errors = []
            for err in e.errors():
                errors.append({
                    "field": ".".join(str(loc) for loc in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"]
                })
            logger.warning(f"[{request_id}] Validation error: {errors}")
            return JSONResponse(
                status_code=422,
                content=_make_error_response(
                    error_type="ValidationError",
                    detail="Request validation failed",
                    status_code=422,
                    request_id=request_id,
                    errors=errors
                ),
                headers={"X-Request-ID": request_id}
            )
        except (HTTPException, StarletteHTTPException):
            raise  # Let FastAPI/Starlette handle HTTPException
        # --- Domain-specific exceptions ---
        except KiCadNotRunningError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] KiCad not running: {e}")
            return JSONResponse(
                status_code=503,
                content=_make_error_response(
                    error_type="KiCadNotRunning",
                    detail=str(e),
                    status_code=503,
                    request_id=request_id,
                    error_code=e.error_code
                ),
                headers={"X-Request-ID": request_id, "Retry-After": "5"}
            )
        except KiCadTimeoutError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] KiCad timeout: {e}")
            return JSONResponse(
                status_code=504,
                content=_make_error_response(
                    error_type="KiCadTimeout",
                    detail=str(e),
                    status_code=504,
                    request_id=request_id,
                    error_code=e.error_code,
                    timeout=e.timeout
                ),
                headers={"X-Request-ID": request_id}
            )
        except KiCadCommandError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(f"[{request_id}] KiCad command error: {e}")
            return JSONResponse(
                status_code=500,
                content=_make_error_response(
                    error_type="KiCadCommandError",
                    detail=str(e),
                    status_code=500,
                    request_id=request_id,
                    error_code=e.error_code,
                    command=e.command
                ),
                headers={"X-Request-ID": request_id}
            )
        except ProjectNotFoundError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(f"[{request_id}] Project not found: {e.path}")
            return JSONResponse(
                status_code=404,
                content=_make_error_response(
                    error_type="ProjectNotFound",
                    detail=str(e),
                    status_code=404,
                    request_id=request_id,
                    error_code=e.error_code,
                    path=e.path
                ),
                headers={"X-Request-ID": request_id}
            )
        except ExportError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(f"[{request_id}] Export error: {e}")
            return JSONResponse(
                status_code=500,
                content=_make_error_response(
                    error_type="ExportError",
                    detail=str(e),
                    status_code=500,
                    request_id=request_id,
                    error_code=e.error_code,
                    format=e.format
                ),
                headers={"X-Request-ID": request_id}
            )
        except ValidationError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Validation error: {e}")
            return JSONResponse(
                status_code=400,
                content=_make_error_response(
                    error_type="ValidationError",
                    detail=str(e),
                    status_code=400,
                    request_id=request_id,
                    field=e.field
                ),
                headers={"X-Request-ID": request_id}
            )
        except AuthenticationError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Authentication error: {e}")
            return JSONResponse(
                status_code=401,
                content=_make_error_response(
                    error_type="AuthenticationError",
                    detail=str(e),
                    status_code=401,
                    request_id=request_id
                ),
                headers={"X-Request-ID": request_id}
            )
        except AuthorizationError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Authorization error: {e}")
            return JSONResponse(
                status_code=403,
                content=_make_error_response(
                    error_type="AuthorizationError",
                    detail=str(e),
                    status_code=403,
                    request_id=request_id,
                    resource=e.resource,
                    action=e.action
                ),
                headers={"X-Request-ID": request_id}
            )
        except ResourceNotFoundError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(f"[{request_id}] Resource not found: {e}")
            return JSONResponse(
                status_code=404,
                content=_make_error_response(
                    error_type="ResourceNotFound",
                    detail=str(e),
                    status_code=404,
                    request_id=request_id,
                    resource_type=e.resource_type,
                    resource_id=e.resource_id
                ),
                headers={"X-Request-ID": request_id}
            )
        except RateLimitError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Rate limit exceeded")
            return JSONResponse(
                status_code=429,
                content=_make_error_response(
                    error_type="RateLimitExceeded",
                    detail=str(e),
                    status_code=429,
                    request_id=request_id,
                    retry_after=e.retry_after
                ),
                headers={
                    "X-Request-ID": request_id,
                    "Retry-After": str(e.retry_after)
                }
            )
        except ServiceUnavailableError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Service unavailable: {e}")
            return JSONResponse(
                status_code=503,
                content=_make_error_response(
                    error_type="ServiceUnavailable",
                    detail=str(e),
                    status_code=503,
                    request_id=request_id,
                    service=e.service
                ),
                headers={"X-Request-ID": request_id, "Retry-After": "30"}
            )
        # --- Standard Python exceptions ---
        except ValueError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Value error: {e}")
            return JSONResponse(
                status_code=400,
                content=_make_error_response(
                    error_type="ValidationError",
                    detail=str(e),
                    status_code=400,
                    request_id=request_id
                ),
                headers={"X-Request-ID": request_id}
            )
        except FileNotFoundError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(f"[{request_id}] File not found: {e}")
            return JSONResponse(
                status_code=404,
                content=_make_error_response(
                    error_type="FileNotFound",
                    detail=str(e),
                    status_code=404,
                    request_id=request_id
                ),
                headers={"X-Request-ID": request_id}
            )
        except PermissionError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{request_id}] Permission error: {e}")
            return JSONResponse(
                status_code=403,
                content=_make_error_response(
                    error_type="PermissionDenied",
                    detail=str(e),
                    status_code=403,
                    request_id=request_id
                ),
                headers={"X-Request-ID": request_id}
            )
        except Exception as e:
            # 未知异常 - 记录完整堆栈，返回通用错误
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception(f"[{request_id}] Unhandled exception: {type(e).__name__}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content=_make_error_response(
                    error_type="InternalServerError",
                    detail="An unexpected error occurred. Please try again later.",
                    status_code=500,
                    request_id=request_id
                ),
                headers={"X-Request-ID": request_id}
            )
# ============================================================================
# Logging Configuration
# ============================================================================
def setup_logging(log_level: str = "INFO"):
    """
    配置日志格式
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 控制台输出
            logging.StreamHandler(),
        ],
    )
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logger.info(f"Logging configured with level: {log_level}")

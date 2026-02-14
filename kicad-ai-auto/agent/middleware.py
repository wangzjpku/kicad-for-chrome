"""
Middleware for KiCad AI Auto Control Agent
Includes request logging and error handling middleware
"""

import time
import logging
import json
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录所有 HTTP 请求的详细信息
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        request_id = id(request)
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        # 记录请求开始
        logger.info(
            f"[{request_id}] Request started: {method} {url} from {client_host}"
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
                f"[{request_id}] Request completed: {method} {url} "
                f"-> {response.status_code} ({process_time:.2f}ms)"
            )

            # 添加处理时间头
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

            return response

        except Exception as e:
            # 计算处理时间
            process_time = (time.time() - start_time) * 1000

            # 记录错误
            logger.error(
                f"[{request_id}] Request failed: {method} {url} "
                f"-> {type(e).__name__}: {str(e)} ({process_time:.2f}ms)"
            )

            # 返回错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": str(e),
                    "request_id": request_id,
                },
            )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    错误处理中间件
    统一处理所有未捕获的异常
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception(f"Unhandled exception: {type(e).__name__}: {str(e)}")

            # 根据异常类型返回不同的状态码
            status_code = 500
            error_type = "InternalError"

            if isinstance(e, ValueError):
                status_code = 400
                error_type = "ValidationError"
            elif isinstance(e, FileNotFoundError):
                status_code = 404
                error_type = "NotFoundError"
            elif isinstance(e, PermissionError):
                status_code = 403
                error_type = "PermissionDenied"

            return JSONResponse(
                status_code=status_code,
                content={
                    "error": error_type,
                    "detail": str(e),
                    "type": type(e).__name__,
                },
            )


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


class KiCadError(Exception):
    """KiCad 操作错误基类"""
    pass


class KiCadNotRunningError(KiCadError):
    """KiCad 未运行"""
    pass


class KiCadTimeoutError(KiCadError):
    """KiCad 操作超时"""
    pass


class KiCadCommandError(KiCadError):
    """KiCad 命令执行失败"""
    def __init__(self, command: str, message: str = ""):
        self.command = command
        super().__init__(f"Command '{command}' failed: {message}")


class ProjectNotFoundError(KiCadError):
    """项目未找到"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Project not found: {path}")


class ExportError(KiCadError):
    """导出错误"""
    def __init__(self, format: str, message: str = ""):
        self.format = format
        super().__init__(f"Export to {format} failed: {message}")

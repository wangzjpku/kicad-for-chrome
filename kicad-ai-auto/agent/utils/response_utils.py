"""
API响应标准化工具
提供统一的响应格式
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """标准API响应格式"""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ApiError(BaseModel):
    """标准错误响应格式"""
    success: bool = False
    error: str
    detail: Optional[str] = None


def success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
    """成功响应"""
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return response


def error_response(error: str, detail: str = None, status_code: int = 400) -> Dict[str, Any]:
    """错误响应"""
    response = {
        "success": False,
        "error": error
    }
    if detail:
        response["detail"] = detail
    return response


def paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """分页响应"""
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }

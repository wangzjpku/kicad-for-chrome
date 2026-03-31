"""
Template API Routes - 模板 API 路由

Phase 6: 项目模板系统

Author: Claude Code
Date: 2026-03-30
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from templates.template_manager import get_template_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])


# ============== 请求模型 ==============

class CreateTemplateRequest(BaseModel):
    """创建自定义模板请求"""
    name: str = Field(..., description="模板名称")
    name_cn: str = Field(..., description="中文名称")
    description: str = Field("", description="描述")
    category: str = Field("custom", description="类别")
    tags: List[str] = Field(default_factory=list, description="标签")
    schematic_data: Dict[str, Any] = Field(default_factory=dict, description="原理图数据")
    pcb_data: Dict[str, Any] = Field(default_factory=dict, description="PCB 数据")
    author: str = Field("User", description="作者")


class UpdateTemplateRequest(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    name_cn: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    schematic_data: Optional[Dict[str, Any]] = None
    pcb_data: Optional[Dict[str, Any]] = None


class CreateProjectFromTemplateRequest(BaseModel):
    """基于模板创建项目请求"""
    template_id: str = Field(..., description="模板 ID")
    project_name: str = Field(..., description="项目名称")
    schematic_overrides: Optional[Dict[str, Any]] = Field(None, description="原理图覆盖参数")
    pcb_overrides: Optional[Dict[str, Any]] = Field(None, description="PCB 覆盖参数")


# ============== API 端点 ==============

@router.get("")
async def list_templates(
    category: Optional[str] = Query(None, description="类别过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    include_predefined: bool = Query(True, description="包含预定义模板"),
):
    """
    列出所有模板

    支持类别过滤和搜索
    """
    manager = get_template_manager()

    if search:
        results = manager.search_templates_api(search, category)
    else:
        results = manager.list_templates(category, include_predefined)

    return {
        "success": True,
        "templates": results,
        "count": len(results),
    }


@router.get("/categories")
async def list_categories():
    """
    获取所有模板类别
    """
    from templates.template_data import TemplateCategory

    return {
        "success": True,
        "categories": [
            {"value": c.value, "label": c.name}
            for c in TemplateCategory
        ],
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """
    获取模板详情
    """
    manager = get_template_manager()
    template = manager.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "success": True,
        "template": template,
    }


@router.post("")
async def create_template(request: CreateTemplateRequest):
    """
    创建自定义模板
    """
    manager = get_template_manager()

    result = manager.create_custom_template(
        name=request.name,
        name_cn=request.name_cn,
        description=request.description,
        category=request.category,
        tags=request.tags,
        schematic_data=request.schematic_data,
        pcb_data=request.pcb_data,
        author=request.author,
    )

    if result.get("success") is False:
        raise HTTPException(status_code=400, detail=result.get("message", "创建失败"))

    return {
        "success": True,
        "template_id": result["template_id"],
        "message": "模板创建成功",
    }


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
):
    """
    更新自定义模板
    """
    manager = get_template_manager()

    # 构建更新参数字典
    update_kwargs = {
        k: v for k, v in request.model_dump().items()
        if v is not None
    }

    result = manager.update_custom_template(template_id, **update_kwargs)

    if result.get("success") is False:
        raise HTTPException(status_code=400, detail=result.get("message", "更新失败"))

    return {
        "success": True,
        "message": "模板更新成功",
    }


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """
    删除自定义模板

    预定义模板不能删除
    """
    # 检查是否是预定义模板
    from templates.template_data import get_template_by_id
    if get_template_by_id(template_id):
        raise HTTPException(status_code=403, detail="预定义模板不能删除")

    manager = get_template_manager()
    result = manager.delete_custom_template(template_id)

    if result.get("success") is False:
        raise HTTPException(status_code=404, detail=result.get("message", "模板不存在"))

    return {
        "success": True,
        "message": "模板删除成功",
    }


@router.post("/create-project")
async def create_project_from_template(request: CreateProjectFromTemplateRequest):
    """
    基于模板创建新项目

    返回项目数据，可用于初始化项目
    """
    manager = get_template_manager()

    # 处理覆盖参数
    overrides = {}
    if request.schematic_overrides:
        overrides["schematic"] = request.schematic_overrides
    if request.pcb_overrides:
        overrides["pcb"] = request.pcb_overrides

    result = manager.create_project_from_template(
        template_id=request.template_id,
        project_name=request.project_name,
        **overrides,
    )

    if result.get("success") is False:
        raise HTTPException(status_code=400, detail=result.get("message", "创建失败"))

    return {
        "success": True,
        "project_id": result["project_id"],
        "project_name": result["project_name"],
        "template_id": result["template_id"],
        "schematic": result.get("schematic", {}),
        "pcb": result.get("pcb", {}),
        "message": "项目创建成功",
    }

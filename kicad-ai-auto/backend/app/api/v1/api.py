"""
API 路由聚合
"""

from fastapi import APIRouter

from app.api.v1.endpoints import projects, schematic, pcb, library, export, drc

api_router = APIRouter()

# 项目路由
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# 原理图路由
api_router.include_router(
    schematic.router, prefix="/projects/{project_id}/schematic", tags=["schematic"]
)

# PCB 路由
api_router.include_router(pcb.router, prefix="/projects/{project_id}/pcb", tags=["pcb"])

# 库路由
api_router.include_router(library.router, prefix="/libraries", tags=["libraries"])

# 导出路由
api_router.include_router(
    export.router, prefix="/projects/{project_id}/export", tags=["export"]
)

# DRC 路由
api_router.include_router(drc.router, prefix="/projects/{project_id}/drc", tags=["drc"])

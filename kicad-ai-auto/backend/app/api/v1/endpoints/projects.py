"""
项目管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
from uuid import UUID
import os
import shutil

from app.core.database import get_db
from app.models.models import Project
from app.schemas.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectList,
)
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=ProjectList)
async def list_projects(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """列出所有项目"""
    result = await db.execute(
        select(Project).where(Project.status == "active").offset(skip).limit(limit)
    )
    projects = result.scalars().all()

    # 获取总数
    count_result = await db.execute(select(Project).where(Project.status == "active"))
    total = len(count_result.scalars().all())

    return ProjectList(total=total, items=projects)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """创建新项目"""
    # 创建项目目录
    project_id = UUID(os.urandom(16).hex()[:32])
    project_dir = os.path.join(settings.PROJECTS_DIR, str(project_id))
    os.makedirs(project_dir, exist_ok=True)

    # 创建数据库记录
    db_project = Project(
        id=project_id,
        name=project.name,
        description=project.description,
        project_file=os.path.join(project_dir, f"{project.name}.kicad_pro"),
        schematic_file=os.path.join(project_dir, f"{project.name}.kicad_sch"),
        pcb_file=os.path.join(project_dir, f"{project.name}.kicad_pcb"),
    )

    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)

    return db_project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID, project_update: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    """更新项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # 更新字段
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return project


@router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # 标记为删除状态
    project.status = "deleted"
    await db.commit()

    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/import")
async def import_project(
    project_id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """导入项目文件"""
    # 检查项目是否存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # 保存上传的文件
    project_dir = os.path.join(settings.PROJECTS_DIR, str(project_id))
    os.makedirs(project_dir, exist_ok=True)

    file_path = os.path.join(project_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "File imported successfully",
        "filename": file.filename,
        "path": file_path,
    }


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """复制项目"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # 创建新项目
    new_project_id = UUID(os.urandom(16).hex()[:32])
    new_project_dir = os.path.join(settings.PROJECTS_DIR, str(new_project_id))
    os.makedirs(new_project_dir, exist_ok=True)

    # 复制文件
    old_project_dir = os.path.join(settings.PROJECTS_DIR, str(project_id))
    if os.path.exists(old_project_dir):
        for item in os.listdir(old_project_dir):
            src = os.path.join(old_project_dir, item)
            dst = os.path.join(new_project_dir, item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

    # 创建新记录
    new_project = Project(
        id=new_project_id,
        name=f"{project.name} (Copy)",
        description=project.description,
        project_file=os.path.join(
            new_project_dir, os.path.basename(project.project_file)
        ),
        schematic_file=os.path.join(
            new_project_dir, os.path.basename(project.schematic_file)
        ),
        pcb_file=os.path.join(new_project_dir, os.path.basename(project.pcb_file)),
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return new_project

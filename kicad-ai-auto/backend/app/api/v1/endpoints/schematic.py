"""
原理图 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db

router = APIRouter()


@router.get("/sheets")
async def get_schematic_sheets(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取原理图页列表"""
    return {"message": "Not implemented yet", "project_id": str(project_id)}


@router.post("/sheets")
async def create_schematic_sheet(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """创建原理图页"""
    return {"message": "Not implemented yet", "project_id": str(project_id)}

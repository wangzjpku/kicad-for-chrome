"""
库管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db

router = APIRouter()


@router.get("/footprints")
async def list_footprint_libraries(db: AsyncSession = Depends(get_db)):
    """列出封装库"""
    return {"message": "Not implemented yet"}


@router.get("/symbols")
async def list_symbol_libraries(db: AsyncSession = Depends(get_db)):
    """列出符号库"""
    return {"message": "Not implemented yet"}

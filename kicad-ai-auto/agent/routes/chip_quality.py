"""
芯片质量门控API端点
检查芯片资料完整度，驱动用户提供缺失资料
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field
import aiofiles

from chip_data_checker import ChipDataChecker, get_chip_checker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chip", tags=["芯片质量门控"])


# ========== 请求/响应模型 ==========


class ChipQualityCheckRequest(BaseModel):
    """芯片质量检查请求"""

    chip_name: str = Field(..., description="芯片名称", example="STM32F103C8T6")
    full_name: Optional[str] = Field(None, description="芯片完整名称")
    manufacturer: Optional[str] = Field(None, description="制造商")


class ChipQualityBatchCheckRequest(BaseModel):
    """批量芯片质量检查请求"""

    chips: List[Dict[str, str]] = Field(
        ...,
        description="芯片列表",
        example=[
            {
                "name": "STM32F103C8T6",
                "full_name": "STM32F103C8T6",
                "manufacturer": "ST",
            },
            {"name": "AMS1117-5V", "full_name": "AMS1117-5V", "manufacturer": "AMS"},
        ],
    )


class ChipQualityResponse(BaseModel):
    """芯片质量检查响应"""

    chip_name: str
    chip_full_name: str
    manufacturer: str
    total_score: int
    can_proceed: bool
    has_blockers: bool
    scores: Dict[str, int]
    missing_items: List[Dict[str, Any]]


class ChipQualityBatchResponse(BaseModel):
    """批量芯片质量检查响应"""

    chips: List[ChipQualityResponse]
    overall_score: int
    can_proceed_all: bool
    all_blockers: List[Dict[str, Any]]


# ========== API端点 ==========


@router.post("/check-quality", response_model=ChipQualityResponse)
async def check_chip_quality(request: ChipQualityCheckRequest):
    """
    检查单个芯片资料完整度

    返回芯片的datasheet、符号、封装等资料的完整度评分，
    以及缺失资料清单和修复建议。
    """
    logger.info(f"检查芯片资料完整度: {request.chip_name}")

    checker = get_chip_checker()
    score = await checker.check_chip(
        request.chip_name, request.full_name or "", request.manufacturer or ""
    )

    return ChipQualityResponse(
        chip_name=score.chip_name,
        chip_full_name=score.chip_full_name,
        manufacturer=score.manufacturer,
        total_score=score.total_score,
        can_proceed=score.can_proceed,
        has_blockers=score.has_blockers,
        scores={
            "datasheet": score.datasheet_score,
            "symbol": score.symbol_score,
            "footprint": score.footprint_score,
            "reference": score.reference_score,
            "price": score.price_score,
            "application_note": score.application_note_score,
        },
        missing_items=[
            {
                "type": item.data_type,
                "severity": item.severity.value,
                "message": item.message,
                "search_url": item.search_url,
                "upload_enabled": item.upload_enabled,
                "alternatives": item.alternatives,
            }
            for item in score.missing_items
        ],
    )


@router.post("/check-quality-batch", response_model=ChipQualityBatchResponse)
async def check_chips_quality_batch(request: ChipQualityBatchCheckRequest):
    """
    批量检查多个芯片资料完整度

    用于检查整个BOM的完整性。
    """
    logger.info(f"批量检查芯片资料完整度: {len(request.chips)}个芯片")

    checker = get_chip_checker()
    scores = await checker.check_multiple_chips(request.chips)

    responses = []
    all_blockers = []

    for score in scores:
        responses.append(
            ChipQualityResponse(
                chip_name=score.chip_name,
                chip_full_name=score.chip_full_name,
                manufacturer=score.manufacturer,
                total_score=score.total_score,
                can_proceed=score.can_proceed,
                has_blockers=score.has_blockers,
                scores={
                    "datasheet": score.datasheet_score,
                    "symbol": score.symbol_score,
                    "footprint": score.footprint_score,
                    "reference": score.reference_score,
                    "price": score.price_score,
                    "application_note": score.application_note_score,
                },
                missing_items=[
                    {
                        "type": item.data_type,
                        "severity": item.severity.value,
                        "message": item.message,
                        "search_url": item.search_url,
                        "upload_enabled": item.upload_enabled,
                        "alternatives": item.alternatives,
                    }
                    for item in score.missing_items
                ],
            )
        )

        # 收集所有阻断级问题
        for item in score.missing_items:
            if item.severity.value == "blocker":
                all_blockers.append(
                    {
                        "chip": score.chip_name,
                        "type": item.data_type,
                        "message": item.message,
                        "alternatives": item.alternatives,
                    }
                )

    # 计算总体评分
    overall_score = sum(s.total_score for s in scores) // len(scores) if scores else 0

    return ChipQualityBatchResponse(
        chips=responses,
        overall_score=overall_score,
        can_proceed_all=all(len(all_blockers) == 0),
        all_blockers=all_blockers,
    )


@router.post("/upload-datasheet/{chip_name}")
async def upload_datasheet(chip_name: str, file: UploadFile = File(...)):
    """
    上传芯片datasheet

    用户上传datasheet后，系统会缓存并重新评估芯片资料完整度。
    """
    logger.info(f"上传datasheet: {chip_name}, 文件: {file.filename}")

    # 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF格式的datasheet")

    # 读取文件内容
    content = await file.read()

    # 检查文件大小 (最大10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

    # 保存到缓存
    checker = get_chip_checker()
    success = await checker.upload_datasheet(chip_name, content, file.filename)

    if not success:
        raise HTTPException(status_code=500, detail="保存datasheet失败")

    # 重新检查
    score = await checker.check_chip(chip_name)

    return {
        "success": True,
        "message": f"成功上传 {file.filename}",
        "new_score": score.total_score,
        "can_proceed": score.can_proceed,
        "missing_items": [
            {
                "type": item.data_type,
                "severity": item.severity.value,
                "message": item.message,
            }
            for item in score.missing_items
        ],
    }


@router.get("/alternatives/{chip_name}")
async def get_chip_alternatives(chip_name: str):
    """
    获取芯片替代方案

    当某个芯片缺少资料或供货紧张时，提供替代芯片建议。
    """
    from chip_data_checker import ChipDataChecker

    alternatives = ChipDataChecker.CHIP_ALTERNATIVES.get(chip_name.upper(), [])

    # 如果没有预设的替代方案，尝试查找相似芯片
    if not alternatives:
        # 简单模糊匹配
        checker = get_chip_checker()
        for key in checker.CHIP_ALTERNATIVES:
            if key.lower() in chip_name.lower() or chip_name.lower() in key.lower():
                alternatives = checker.CHIP_ALTERNATIVES[key]
                break

    return {
        "chip_name": chip_name,
        "alternatives": alternatives,
        "message": "以下芯片可作为替代方案" if alternatives else "未找到替代方案",
    }


@router.get("/search-links/{chip_name}")
async def get_search_links(chip_name: str):
    """
    获取芯片资料搜索链接

    返回各种资料源的搜索链接，方便用户快速查找。
    """
    checker = get_chip_checker()

    links = {
        "chip_name": chip_name,
        "datasheet": {
            "name": "Alldatasheet",
            "url": f"https://www.alldatasheet.com/search.jsp?searchwords={chip_name}",
        },
        "symbol": {
            "name": "SamacSys",
            "url": "https://www.samacsys.com/kicad-library-loader/",
        },
        "footprint": {
            "name": "Ultra Librarian",
            "url": "https://www.ultralibrarian.com/",
        },
        "price": {
            "name": "DigiKey",
            "url": f"https://www.digikey.com/en/products?keyword={chip_name}",
        },
        "lcsc": {
            "name": "LCSC",
            "url": f"https://www.lcsc.com/products/{chip_name}.html",
        },
    }

    return links

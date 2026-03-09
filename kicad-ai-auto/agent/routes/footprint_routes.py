"""
封装库 API 路由
提供封装搜索、获取等接口
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/footprints", tags=["Footprints"])

# KiCad官方封装库路径
KICAD_FOOTPRINTS = r"E:\0-007-MyAIOS\projects\1-kicad-for-chrome\kicad-footprints"


def list_footprint_libraries() -> List[str]:
    """列出所有可用的封装库"""
    if not os.path.exists(KICAD_FOOTPRINTS):
        return []
    libraries = []
    for item in os.listdir(KICAD_FOOTPRINTS):
        if item.endswith('.pretty'):
            libraries.append(item.replace('.pretty', ''))
    return libraries


def list_footprints_in_library(lib_name: str) -> List[str]:
    """列出指定库中的所有封装"""
    lib_path = os.path.join(KICAD_FOOTPRINTS, f"{lib_name}.pretty")
    if not os.path.exists(lib_path):
        return []
    footprints = []
    for item in os.listdir(lib_path):
        if item.endswith('.kicad_mod'):
            footprints.append(item.replace('.kicad_mod', ''))
    return footprints


@router.get("/libraries")
async def list_libraries():
    """列出所有可用的封装库"""
    libraries = list_footprint_libraries()
    return {"success": True, "libraries": libraries, "count": len(libraries)}


@router.get("/libraries/{lib_name}")
async def get_library_footprints(lib_name: str):
    """获取指定库中的所有封装"""
    footprints = list_footprints_in_library(lib_name)
    return {
        "success": True,
        "library": lib_name,
        "footprints": footprints,
        "count": len(footprints),
    }


@router.get("/search")
async def search_footprints(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
):
    """搜索封装"""
    from footprint_parser import get_footprint_data
    import re

    results = []
    count = 0
    libraries = list_footprint_libraries()

    for library in libraries:
        if count >= limit:
            break
        footprints = list_footprints_in_library(library)
        for fp in footprints:
            if count >= limit:
                break
            # 改进的搜索逻辑：支持多种匹配方式
            kw_lower = keyword.lower()
            fp_lower = fp.lower()
            # 1. 精确包含
            # 2. 单词匹配 (SOIC, QFN, DIP等)
            # 3. 型号部分匹配 (ATmega -> ATmega328P)
            kw_words = re.split(r'[-_\s]+', kw_lower)
            match = kw_lower in fp_lower
            if not match:
                for word in kw_words:
                    if word and len(word) > 1:
                        # 检查是否匹配单词开头
                        if fp_lower.startswith(word) or any(fp_lower.startswith(w) for w in kw_words if w):
                            match = True
                            break
                        # 检查是否用下划线或连字符分隔
                        if re.search(rf'{re.escape(word)}', fp_lower):
                            match = True
                            break
            if match:
                results.append({"library": library, "name": fp})
                count += 1

    return {
        "success": True,
        "keyword": keyword,
        "footprints": results,
        "count": len(results),
    }


@router.get("/{lib_name}/{footprint_name}")
async def get_footprint(lib_name: str, footprint_name: str):
    """获取指定封装的详细信息"""
    from footprint_parser import get_footprint_data
    import re

    # URL解码
    import urllib.parse
    footprint_name = urllib.parse.unquote(footprint_name)

    # 构造完整封装名
    full_name = f"{lib_name}:{footprint_name}" if lib_name else footprint_name

    footprint = get_footprint_data(full_name)
    if footprint is None:
        raise HTTPException(status_code=404, detail=f"Footprint not found: {lib_name}/{footprint_name}")

    return {"success": True, "footprint": footprint}


@router.get("/find")
async def find_footprint_route(
    name: str = Query(..., description="封装名称"),
):
    """根据名称查找封装（搜索所有库）"""
    from footprint_parser import get_footprint_data
    import re
    import urllib.parse
    name = urllib.parse.unquote(name)

    footprint = get_footprint_data(name)

    if footprint is None:
        raise HTTPException(status_code=404, detail=f"Footprint not found: {name}")

    return {"success": True, "footprint": footprint}


# 别名端点 - 支持keyword参数
@router.get("/find-by-keyword")
async def find_footprint_by_keyword(
    keyword: str = Query(..., description="封装关键词"),
):
    """根据关键词查找封装"""
    from footprint_parser import get_footprint_data
    import urllib.parse
    keyword = urllib.parse.unquote(keyword)

    footprint = get_footprint_data(keyword)

    if footprint is None:
        return {"success": False, "keyword": keyword, "message": "Footprint not found"}

    return {"success": True, "keyword": keyword, "footprint": footprint}

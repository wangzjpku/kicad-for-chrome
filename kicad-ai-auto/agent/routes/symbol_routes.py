"""
符号库 API 路由
提供符号搜索、获取等接口
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from symbol_lib_parser import get_symbol_parser, symbol_to_dict, KiCadSymbol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/symbols", tags=["Symbols"])


@router.get("/libraries")
async def list_libraries():
    """列出所有可用的符号库"""
    parser = get_symbol_parser()
    libraries = parser.list_available_libraries()

    return {"success": True, "libraries": libraries, "count": len(libraries)}


@router.get("/libraries/{lib_name}")
async def get_library_symbols(lib_name: str):
    """获取指定库中的所有符号"""
    parser = get_symbol_parser()
    symbols = parser.get_library_symbols(lib_name)

    return {
        "success": True,
        "library": lib_name,
        "symbols": [symbol_to_dict(s) for s in symbols],
        "count": len(symbols),
    }


@router.get("/search")
async def search_symbols(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
):
    """搜索符号"""
    parser = get_symbol_parser()
    results = parser.search_symbols(keyword, limit)

    return {
        "success": True,
        "keyword": keyword,
        "symbols": [symbol_to_dict(s) for s in results],
        "count": len(results),
    }


# 别名端点 - library的简写形式
@router.get("/libraries/{lib_name}")
async def get_library_alias(lib_name: str):
    """获取指定符号库的简写形式"""
    parser = get_symbol_parser()
    symbols = parser.list_symbols(lib_name)
    return {
        "success": True,
        "library": lib_name,
        "symbols": [symbol_to_dict(s) for s in symbols],
        "count": len(symbols)
    }

# 别名端点 - 支持query参数
@router.get("/search-by-query")
async def search_symbols_by_query(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
):
    """搜索符号(使用query参数)"""
    parser = get_symbol_parser()
    results = parser.search_symbols(query, limit)

    return {
        "success": True,
        "keyword": query,
        "symbols": [symbol_to_dict(s) for s in results],
        "count": len(results),
    }


@router.get("/{lib_name}/{symbol_name}")
async def get_symbol(lib_name: str, symbol_name: str):
    """获取指定符号的详细信息"""
    parser = get_symbol_parser()
    symbol = parser.get_symbol(lib_name, symbol_name)

    if not symbol:
        raise HTTPException(
            status_code=404, detail=f"符号未找到: {lib_name}:{symbol_name}"
        )

    return {"success": True, "symbol": symbol_to_dict(symbol)}


@router.get("/find")
async def find_symbol_for_component(
    name: str = Query(..., description="元件名称"),
    model: str = Query("", description="元件型号"),
):
    """根据元件名称/型号自动查找合适的符号"""
    parser = get_symbol_parser()
    symbol = parser.find_symbol_for_component(name, model)

    if not symbol:
        return {"success": False, "message": "未找到匹配的符号", "symbol": None}

    return {"success": True, "symbol": symbol_to_dict(symbol)}


@router.get("/{lib_name}/{symbol_name}/graphics")
async def get_symbol_graphics(lib_name: str, symbol_name: str):
    """获取符号的图形数据（用于前端渲染）"""
    parser = get_symbol_parser()
    symbol = parser.get_symbol(lib_name, symbol_name)

    if not symbol:
        raise HTTPException(
            status_code=404, detail=f"符号未找到: {lib_name}:{symbol_name}"
        )

    # 转换图形数据为前端友好格式
    graphics_data = []
    for g in symbol.graphics:
        graphic_item = {
            "type": g.type,
            "strokeWidth": g.stroke_width,
            "fill": g.fill_type,
        }

        if g.type == "rectangle":
            graphic_item["x"] = g.start["x"] if g.start else 0
            graphic_item["y"] = g.start["y"] if g.start else 0
            graphic_item["width"] = (
                (g.end["x"] - g.start["x"]) if g.start and g.end else 0
            )
            graphic_item["height"] = (
                (g.end["y"] - g.start["y"]) if g.start and g.end else 0
            )

        elif g.type == "polyline":
            graphic_item["points"] = g.points

        elif g.type == "circle":
            graphic_item["cx"] = g.center["x"] if g.center else 0
            graphic_item["cy"] = g.center["y"] if g.center else 0
            graphic_item["radius"] = g.radius

        elif g.type == "arc":
            graphic_item["start"] = g.start
            graphic_item["end"] = g.end
            graphic_item["center"] = g.center

        graphics_data.append(graphic_item)

    # 转换引脚数据
    pins_data = []
    for p in symbol.pins:
        pins_data.append(
            {
                "number": p.number,
                "name": p.name,
                "x": p.position["x"],
                "y": p.position["y"],
                "length": p.length,
                "rotation": p.direction,
                "type": p.pin_type,
            }
        )

    return {
        "success": True,
        "library": lib_name,
        "name": symbol_name,
        "reference": symbol.reference,
        "graphics": graphics_data,
        "pins": pins_data,
    }

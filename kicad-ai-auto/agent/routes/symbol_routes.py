"""
符号库 API 路由
提供符号搜索、获取等接口

Phase 6: 增强符号搜索功能，支持模糊匹配、类别过滤、分页
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from symbol_lib_parser import get_symbol_parser, symbol_to_dict, KiCadSymbol
from schematic.symbol_search import (
    SymbolSearchEngine,
    get_symbol_search_engine,
    search_symbols,
    SymbolCategory,
)
from schematic.bulk_placement import (
    BulkPlacementEngine,
    BOMItem,
    PlacementStrategy,
    parse_bom_text,
)

logger = logging.getLogger(__name__)


# ============== Phase 6: 新搜索模型 ==============

class SymbolSearchFilters(BaseModel):
    """搜索过滤条件"""
    category: Optional[str] = None
    library: Optional[str] = None
    package: Optional[str] = None
    pin_count_min: Optional[int] = None
    pin_count_max: Optional[int] = None
    manufacturer: Optional[str] = None


class SymbolSearchRequest(BaseModel):
    """符号搜索请求"""
    query: str = Field(..., description="搜索关键词")
    filters: Optional[SymbolSearchFilters] = None
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")

router = APIRouter(prefix="/api/v1/symbols", tags=["Symbols"])


# ============== Phase 6: 新搜索端点 ==============

@router.post("/search")
async def search_symbols_post(request: SymbolSearchRequest) -> Dict[str, Any]:
    """
    符号搜索 (POST)

    支持:
    - 模糊匹配（名称、描述、关键词）
    - 类别/库/封装过滤
    - 分页
    """
    filters_dict = None
    if request.filters:
        filters_dict = {
            "category": request.filters.category,
            "library": request.filters.library,
            "package": request.filters.package,
            "pin_count_min": request.filters.pin_count_min,
            "pin_count_max": request.filters.pin_count_max,
            "manufacturer": request.filters.manufacturer,
        }

    result = search_symbols(
        query=request.query,
        filters=filters_dict,
        page=request.page,
        page_size=request.page_size,
    )

    return {
        "success": True,
        "symbols": result["symbols"],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "query": result["query"],
    }


@router.get("/categories")
async def list_categories():
    """获取所有符号类别"""
    engine = get_symbol_search_engine()
    categories = engine.get_categories()
    return {
        "success": True,
        "categories": [c.value for c in categories],
        "count": len(categories),
    }


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
async def search_symbols_get(
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


# ============== Phase 6: 批量放置端点 ==============

class BulkPlacementRequest(BaseModel):
    """批量放置请求"""
    bom_text: Optional[str] = Field(None, description="BOM 文本 (CSV 格式)")
    bom_items: Optional[List[Dict[str, Any]]] = Field(None, description="BOM 元件列表")
    strategy: str = Field("auto", description="放置策略: grid, horizontal, vertical, auto")
    start_x: float = Field(100.0, description="起始 X 坐标")
    start_y: float = Field(100.0, description="起始 Y 坐标")
    spacing_x: float = Field(50.0, description="X 间距")
    spacing_y: float = Field(30.0, description="Y 间距")
    max_cols: int = Field(10, description="最大列数 (网格策略)")


@router.post("/bulk-place")
async def bulk_place_components(request: BulkPlacementRequest):
    """
    批量放置元件

    支持:
    - 从 BOM 文本解析
    - 直接指定 BOM 元件列表
    - 多种放置策略
    """
    engine = BulkPlacementEngine(
        start_x=request.start_x,
        start_y=request.start_y,
        spacing_x=request.spacing_x,
        spacing_y=request.spacing_y,
    )

    # 解析 BOM
    if request.bom_text:
        bom_items = parse_bom_text(request.bom_text)
    elif request.bom_items:
        bom_items = [
            BOMItem(
                reference=item.get("reference", ""),
                value=item.get("value", ""),
                footprint=item.get("footprint", ""),
                symbol=item.get("symbol", ""),
                quantity=item.get("quantity", 1),
            )
            for item in request.bom_items
        ]
    else:
        raise HTTPException(
            status_code=400, detail="必须提供 bom_text 或 bom_items"
        )

    # 策略转换
    strategy_map = {
        "grid": PlacementStrategy.GRID,
        "horizontal": PlacementStrategy.HORIZONTAL,
        "vertical": PlacementStrategy.VERTICAL,
        "auto": PlacementStrategy.AUTO,
    }
    strategy = strategy_map.get(request.strategy, PlacementStrategy.AUTO)

    # 执行放置
    result = engine.place_from_bom(bom_items, strategy, request.max_cols)

    return {
        "success": True,
        "components": [
            {
                "reference": c.reference,
                "symbol_name": c.symbol_name,
                "library": c.library,
                "x": c.x,
                "y": c.y,
                "rotation": c.rotation,
                "properties": c.properties,
            }
            for c in result.components
        ],
        "total": result.total,
        "strategy": result.strategy.value,
        "grid_cols": result.grid_cols,
        "grid_rows": result.grid_rows,
    }


@router.post("/bulk-place/update-positions")
async def update_placement_positions(
    components: List[Dict[str, Any]],
    start_x: float = Query(100.0),
    start_y: float = Query(100.0),
    spacing_x: float = Query(50.0),
    spacing_y: float = Query(30.0),
    strategy: str = Query("grid"),
    max_cols: int = Query(10),
):
    """更新已放置元件的位置"""
    from schematic.bulk_placement import PlacedComponent

    placed = [
        PlacedComponent(
            reference=c.get("reference", ""),
            symbol_name=c.get("symbol_name", ""),
            library=c.get("library", ""),
            x=c.get("x", 0),
            y=c.get("y", 0),
            rotation=c.get("rotation", 0),
            properties=c.get("properties", {}),
        )
        for c in components
    ]

    engine = BulkPlacementEngine(
        start_x=start_x,
        start_y=start_y,
        spacing_x=spacing_x,
        spacing_y=spacing_y,
    )

    strategy_map = {
        "grid": PlacementStrategy.GRID,
        "horizontal": PlacementStrategy.HORIZONTAL,
        "vertical": PlacementStrategy.VERTICAL,
    }
    strat = strategy_map.get(strategy, PlacementStrategy.GRID)

    result = engine.update_positions(placed, strategy=strat, max_cols=max_cols)

    return {
        "success": True,
        "components": [
            {
                "reference": c.reference,
                "symbol_name": c.symbol_name,
                "library": c.library,
                "x": c.x,
                "y": c.y,
                "rotation": c.rotation,
                "properties": c.properties,
            }
            for c in result.components
        ],
        "total": result.total,
        "strategy": result.strategy.value,
    }

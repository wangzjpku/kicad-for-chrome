"""
Knowledge Base API - 元件知识库和电路模板 API
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])

# 知识库路径
KNOWLEDGE_DIR = Path(__file__).parent.parent / "component_knowledge"
COMPONENT_DB_PATH = KNOWLEDGE_DIR / "component_db.json"

# 缓存
_component_db: Optional[Dict[str, Any]] = None


def get_component_db() -> Dict[str, Any]:
    """获取元件数据库"""
    global _component_db
    if _component_db is None:
        if COMPONENT_DB_PATH.exists():
            try:
                with open(COMPONENT_DB_PATH, "r", encoding="utf-8") as f:
                    _component_db = json.load(f)
                    logger.info(
                        f"已加载元件知识库: {len(_component_db.get('components', {}))} 个元件"
                    )
            except Exception as e:
                logger.error(f"加载元件知识库失败: {e}")
                _component_db = {"components": {}, "templates": {}}
        else:
            logger.warning(f"元件知识库文件不存在: {COMPONENT_DB_PATH}")
            _component_db = {"components": {}, "templates": {}}
    return _component_db


def reload_component_db() -> Dict[str, Any]:
    """重新加载元件数据库"""
    global _component_db
    _component_db = None
    return get_component_db()


# ========== 响应模型 ==========


class ComponentPin(BaseModel):
    number: str
    name: str
    type: str
    description: Optional[str] = None


class ComponentInfo(BaseModel):
    name: str
    symbol_library: Optional[str] = None
    symbol_name: Optional[str] = None
    pins: List[ComponentPin] = []
    footprint: Optional[str] = None
    power_pins: List[str] = []
    typical_circuits: List[str] = []


class ComponentSearchResult(BaseModel):
    name: str
    symbol_library: Optional[str] = None
    footprint: Optional[str] = None
    match_score: float = 0.0


class CircuitTemplateInfo(BaseModel):
    name: str
    description: str
    components: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]


# ========== API 端点 ==========


@router.get("/health")
async def knowledge_health():
    """知识库健康检查"""
    db = get_component_db()
    return {
        "status": "ok",
        "service": "knowledge-base",
        "components_count": len(db.get("components", {})),
        "templates_count": len(db.get("templates", {})),
    }


@router.get("/components")
async def list_components():
    """列出所有元件"""
    db = get_component_db()
    components = db.get("components", {})

    result = []
    for name, data in components.items():
        result.append(
            {
                "name": name,
                "symbol_library": data.get("symbol_library"),
                "footprint": data.get("footprint"),
                "typical_circuits": data.get("typical_circuits", []),
            }
        )

    return {"success": True, "count": len(result), "components": result}


@router.get("/components/{component_name}")
async def get_component(component_name: str):
    """获取单个元件详情"""
    db = get_component_db()
    components = db.get("components", {})

    # 精确匹配
    if component_name in components:
        data = components[component_name]
        return {
            "success": True,
            "component": {
                "name": component_name,
                "symbol_library": data.get("symbol_library"),
                "symbol_name": data.get("symbol_name"),
                "pins": data.get("pins", []),
                "footprint": data.get("footprint"),
                "power_pins": data.get("power_pins", []),
                "typical_circuits": data.get("typical_circuits", []),
            },
        }

    # 模糊匹配
    component_name_lower = component_name.lower()
    for name, data in components.items():
        if component_name_lower in name.lower():
            return {
                "success": True,
                "component": {
                    "name": name,
                    "symbol_library": data.get("symbol_library"),
                    "symbol_name": data.get("symbol_name"),
                    "pins": data.get("pins", []),
                    "footprint": data.get("footprint"),
                    "power_pins": data.get("power_pins", []),
                    "typical_circuits": data.get("typical_circuits", []),
                },
                "match_type": "fuzzy",
            }

    return JSONResponse(
        status_code=404,
        content={"success": False, "error": f"未找到元件: {component_name}"},
    )


@router.get("/components/search/{keyword}")
async def search_components(keyword: str, limit: int = 10):
    """搜索元件"""
    db = get_component_db()
    components = db.get("components", {})

    keyword_lower = keyword.lower()
    results = []

    for name, data in components.items():
        score = 0.0
        name_lower = name.lower()

        # 精确匹配
        if keyword_lower == name_lower:
            score = 100.0
        # 开头匹配
        elif name_lower.startswith(keyword_lower):
            score = 80.0
        # 包含匹配
        elif keyword_lower in name_lower:
            score = 60.0
        # 符号库匹配
        elif keyword_lower in data.get("symbol_library", "").lower():
            score = 40.0
        # 引脚名匹配
        else:
            for pin in data.get("pins", []):
                if keyword_lower in pin.get("name", "").lower():
                    score = 30.0
                    break

        if score > 0:
            results.append(
                {
                    "name": name,
                    "symbol_library": data.get("symbol_library"),
                    "footprint": data.get("footprint"),
                    "match_score": score,
                }
            )

    # 按匹配分数排序
    results.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "success": True,
        "keyword": keyword,
        "count": len(results[:limit]),
        "results": results[:limit],
    }


@router.get("/templates")
async def list_templates():
    """列出所有电路模板"""
    db = get_component_db()
    templates = db.get("templates", {})

    result = []
    for name, data in templates.items():
        result.append(
            {
                "name": name,
                "description": data.get("description"),
                "components_count": len(data.get("components", [])),
            }
        )

    return {"success": True, "count": len(result), "templates": result}


@router.get("/templates/{template_name}")
async def get_template(template_name: str):
    """获取单个电路模板详情"""
    db = get_component_db()
    templates = db.get("templates", {})

    if template_name in templates:
        return {
            "success": True,
            "template": {"name": template_name, **templates[template_name]},
        }

    return JSONResponse(
        status_code=404,
        content={"success": False, "error": f"未找到模板: {template_name}"},
    )


@router.get("/categories")
async def list_categories():
    """列出元件类别"""
    db = get_component_db()
    components = db.get("components", {})

    # 提取所有符号库作为类别
    libraries = set()
    for data in components.values():
        lib = data.get("symbol_library")
        if lib:
            libraries.add(lib)

    return {
        "success": True,
        "count": len(libraries),
        "categories": sorted(list(libraries)),
    }


@router.get("/typical-circuits")
async def list_typical_circuits():
    """列出所有典型电路"""
    db = get_component_db()
    components = db.get("components", {})
    templates = db.get("templates", {})

    # 从元件中提取典型电路
    circuits = set()
    for data in components.values():
        for circuit in data.get("typical_circuits", []):
            circuits.add(circuit)

    # 从模板中提取
    for name in templates.keys():
        circuits.add(name)

    return {"success": True, "count": len(circuits), "circuits": sorted(list(circuits))}


@router.post("/reload")
async def reload_knowledge():
    """重新加载知识库"""
    try:
        db = reload_component_db()
        return {
            "success": True,
            "message": "知识库已重新加载",
            "components_count": len(db.get("components", {})),
            "templates_count": len(db.get("templates", {})),
        }
    except Exception as e:
        logger.error(f"重新加载知识库失败: {e}")


@router.get("/recommend")
async def recommend_component(component: str = Query(..., description="元件名称")):
    """推荐元件封装/电路"""
    try:
        from smart_footprint_finder import find_footprint
        result = find_footprint(component)
        return {
            "success": True,
            "component": component,
            "recommendation": result.get("footprint", ""),
            "confidence": result.get("confidence", 0),
        }
    except Exception as e:
        logger.error(f"推荐失败: {e}")
        return {"success": False, "component": component, "error": str(e)}
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )

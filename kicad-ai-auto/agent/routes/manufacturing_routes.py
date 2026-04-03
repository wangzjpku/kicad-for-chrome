"""
Manufacturing & Supply Chain Routes (Phase 11)

Combines:
- Phase 11A: Component search, BOM optimization, LCSC inventory
- Phase 11B: Manufacturing order packages (JLCPCB, PCBWay)
- Phase 11B-3: Enhanced DFM checks
- Phase 11B-4: Manufacturing cost estimation
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 导入缓存模块
try:
    from services.memory_cache import get_cache, cached
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/manufacturing", tags=["Manufacturing"])


# ========== Pydantic Models ==========

class ComponentSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class BOMOptimizeRequest(BaseModel):
    bom_items: List[Dict[str, Any]]
    prefer_in_stock: bool = True
    max_alternatives: int = Field(default=3, ge=1, le=10)


class ManufacturingCheckRequest(BaseModel):
    pcb_data: Dict[str, Any]
    manufacturer: str = "jlcpcb"  # jlcpcb | pcbway | generic
    tier: str = "standard"  # economy | standard | premium


class OrderPackageRequest(BaseModel):
    pcb_data: Dict[str, Any]
    manufacturer: str = "jlcpcb"
    include_bom: bool = True
    include_pnp: bool = True
    include_gerber: bool = True


class CostEstimateRequest(BaseModel):
    pcb_data: Dict[str, Any]
    quantity: int = Field(default=5, ge=1)
    manufacturer: str = "jlcpcb"
    shipping_country: str = "CN"


# ========== Phase 11A: Component Search & BOM ==========

@router.post("/components/search")
async def search_components(request: ComponentSearchRequest):
    """Search components from LCSC inventory"""
    try:
        from services.lcsc_api import get_lcsc_client
        client = get_lcsc_client()
        results = client.search(request.query, category=request.category, limit=request.limit)
        return {"success": True, "components": [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]}
    except Exception as e:
        logger.error(f"Component search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bom/optimize")
async def optimize_bom(request: BOMOptimizeRequest):
    """Optimize BOM with alternative components"""
    try:
        from services.bom_optimizer import get_bom_optimizer
        optimizer = get_bom_optimizer()
        report = optimizer.optimize(request.bom_items, prefer_in_stock=request.prefer_in_stock)
        return {"success": True, "report": report.to_dict() if hasattr(report, 'to_dict') else report}
    except Exception as e:
        logger.error(f"BOM optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/components/alternatives")
async def find_alternatives(request: ComponentSearchRequest):
    """Find alternative components"""
    try:
        from services.component_alternative import get_alternative_recommender
        recommender = get_alternative_recommender()
        results = recommender.find_alternatives(request.query, max_results=request.limit)
        return {"success": True, "alternatives": results}
    except Exception as e:
        logger.error(f"Alternative search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Phase 11B: Manufacturing Order Packages ==========

@router.post("/order/jlcpcb")
async def generate_jlcpcb_order(request: OrderPackageRequest):
    """Generate JLCPCB-compatible manufacturing package"""
    try:
        from export.jlcpcb_order import get_jlcpcb_generator
        generator = get_jlcpcb_generator()
        package = generator.generate(
            request.pcb_data,
            include_bom=request.include_bom,
            include_pnp=request.include_pnp,
        )
        return {"success": True, "package": package.to_dict() if hasattr(package, 'to_dict') else package}
    except Exception as e:
        logger.error(f"JLCPCB order generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order/pcbway")
async def generate_pcbway_order(request: OrderPackageRequest):
    """Generate PCBWay-compatible manufacturing package"""
    try:
        from export.pcbway_order import get_pcbway_generator
        generator = get_pcbway_generator()
        package = generator.generate(
            request.pcb_data,
            include_bom=request.include_bom,
            include_pnp=request.include_pnp,
        )
        return {"success": True, "package": package.to_dict() if hasattr(package, 'to_dict') else package}
    except Exception as e:
        logger.error(f"PCBWay order generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Phase 11B-3: Manufacturing DFM Checks ==========

@router.post("/check")
async def manufacturing_check(request: ManufacturingCheckRequest):
    """Run manufacturing feasibility check (DFM)"""
    try:
        from export.manufacturing_checker import ManufacturingChecker
        checker = ManufacturingChecker(request.pcb_data)
        if request.manufacturer == "jlcpcb":
            report = checker.check_jlcpcb()
        elif request.manufacturer == "pcbway":
            report = checker.check_pcbway()
        else:
            report = checker.check_generic()

        # Also run advanced checks
        advanced_report = checker.check_advanced(manufacturer=request.manufacturer)
        return {
            "success": True,
            "basic": report.to_dict() if hasattr(report, 'to_dict') else report,
            "advanced": advanced_report.to_dict() if hasattr(advanced_report, 'to_dict') else advanced_report,
        }
    except Exception as e:
        logger.error(f"Manufacturing check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Phase 11B-4: Cost Estimation ==========

@router.post("/cost-estimate")
async def cost_estimate(request: CostEstimateRequest):
    """Estimate manufacturing cost"""
    try:
        from export.manufacturing_checker import ManufacturingChecker
        checker = ManufacturingChecker(request.pcb_data)
        report = checker.check_jlcpcb() if request.manufacturer == "jlcpcb" else checker.check_pcbway()

        # Extract cost info from report
        cost_data = {}
        if hasattr(report, 'to_dict'):
            report_dict = report.to_dict()
            cost_data = report_dict.get("cost_estimate", {})
        elif isinstance(report, dict):
            cost_data = report.get("cost_estimate", {})

        return {
            "success": True,
            "manufacturer": request.manufacturer,
            "quantity": request.quantity,
            "cost": cost_data,
        }
    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Utility ==========

# 静态制造商列表（可缓存10分钟）
_MANUFACTURERS_CACHE = None
_MANUFACTURERS_CACHE_TIME = 0
_MANUFACTURERS_CACHE_TTL = 600  # 10分钟

@router.get("/manufacturers")
async def list_manufacturers():
    """List supported manufacturers (cached for 10 minutes)"""
    global _MANUFACTURERS_CACHE, _MANUFACTURERS_CACHE_TIME

    import time
    now = time.time()

    # 检查缓存
    if _MANUFACTURERS_CACHE and (now - _MANUFACTURERS_CACHE_TIME) < _MANUFACTURERS_CACHE_TTL:
        return _MANUFACTURERS_CACHE

    # 生成新数据
    result = {
        "manufacturers": [
            {"id": "jlcpcb", "name": "JLCPCB", "tiers": ["economy", "standard", "premium"]},
            {"id": "pcbway", "name": "PCBWay", "tiers": ["standard", "premium"]},
            {"id": "generic", "name": "Generic", "tiers": ["standard"]},
        ]
    }

    # 更新缓存
    _MANUFACTURERS_CACHE = result
    _MANUFACTURERS_CACHE_TIME = now

    return result


@router.get("/health")
async def manufacturing_health():
    """Health check for manufacturing services"""
    available = {}
    for name, module_path in [
        ("lcsc_api", "services.lcsc_api"),
        ("bom_optimizer", "services.bom_optimizer"),
        ("jlcpcb_order", "export.jlcpcb_order"),
        ("pcbway_order", "export.pcbway_order"),
        ("manufacturing_checker", "export.manufacturing_checker"),
    ]:
        try:
            __import__(module_path)
            available[name] = True
        except ImportError:
            available[name] = False

    return {"status": "ok", "services": available}

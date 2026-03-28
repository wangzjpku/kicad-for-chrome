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


def _merge_components_to_kb(
    kb_components: List[Dict[str, Any]], source: str
) -> Dict[str, Any]:
    """
    将解析出的元件合并到 component_db.json。

    策略:
    - 新元件: 直接添加
    - 已存在元件: 仅更新 symbol_library / symbol_name / footprint / pins
      (保留原有 datasheet_url, category, status)
    - 保留原有 custom 标记（symbol_library=custom 的元件不被覆盖）
    """
    db = get_component_db()
    components = db.get("components", {})
    added = []
    updated = []
    skipped = []

    for entry in kb_components:
        name = entry.get("name", "")
        if not name:
            continue

        # 跳过 custom 元件（不在 KiCad 官方库中，由人工维护）
        if entry.get("symbol_library") == "custom":
            skipped.append(name)
            continue

        if name in components:
            existing = components[name]
            # 不覆盖 datasheet_url / category / status
            changed = False
            for field in ("symbol_library", "symbol_name", "footprint", "source"):
                if entry.get(field) and entry.get(field) != existing.get(field):
                    existing[field] = entry.get(field)
                    changed = True
            # 更新 pins（如果 entry 有 pins 数据）
            if entry.get("pins"):
                existing["pins"] = entry.get("pins", [])
                changed = True
            # 标记数据来源
            existing["source"] = entry.get("source", source)
            if changed:
                updated.append(name)
        else:
            components[name] = entry
            added.append(name)

    # 写回文件
    try:
        with open(COMPONENT_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        write_ok = True
    except Exception as e:
        logger.error(f"Failed to write component_db.json: {e}")
        write_ok = False

    # 重新加载缓存
    reload_component_db()

    return {
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "total_added": len(added),
        "total_updated": len(updated),
        "total_skipped": len(skipped),
        "file_written": write_ok,
    }


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
        return JSONResponse(
            status_code=500, content={"success": False, "component": component, "error": str(e)}
        )


# ========== 质量保障 API ==========


@router.get("/quality/summary")
async def quality_summary():
    """知识库质量摘要（快速，非详细校验）"""
    db = get_component_db()
    components = db.get("components", {})

    # 快速统计
    stats = {
        "total": len(components),
        "by_category": {},
        "with_datasheet": 0,
        "with_footprint": 0,
        "with_symbol_lib": 0,
        "missing_datasheet": 0,
        "missing_footprint": 0,
        "missing_symbol_lib": 0,
    }

    for name, comp in components.items():
        cat = comp.get("category", "unknown")
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        if comp.get("datasheet_url"):
            stats["with_datasheet"] += 1
        else:
            stats["missing_datasheet"] += 1

        if comp.get("footprint"):
            stats["with_footprint"] += 1
        else:
            stats["missing_footprint"] += 1

        if comp.get("symbol_library"):
            stats["with_symbol_lib"] += 1
        else:
            stats["missing_symbol_lib"] += 1

    return {
        "success": True,
        "service": "kb_quality",
        "version": "0.9.12",
        "stats": stats,
        "quality_coverage": {
            "datasheet": f"{stats['with_datasheet'] / max(stats['total'], 1) * 100:.1f}%",
            "footprint": f"{stats['with_footprint'] / max(stats['total'], 1) * 100:.1f}%",
            "symbol_lib": f"{stats['with_symbol_lib'] / max(stats['total'], 1) * 100:.1f}%",
        },
    }


@router.post("/quality/validate")
async def quality_validate(
    component_name: str = Query(..., description="元件名称"),
    check_datasheet: bool = Query(False, description="是否检查 datasheet URL"),
):
    """校验单个元件质量"""
    try:
        from kb_quality import validate_component

        result = validate_component(
            component_name,
            check_datasheet=check_datasheet,
            cross_check=True,
        )

        return {
            "success": True,
            "component": component_name,
            "result": result.to_dict(),
        }
    except Exception as e:
        logger.error(f"Quality validation failed for {component_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "component": component_name, "error": str(e)},
        )


@router.post("/quality/run-gate")
async def quality_run_gate(
    check_datasheet: bool = Query(False, description="是否检查 datasheet URL（较慢）"),
):
    """运行全量质量门控检查"""
    import asyncio

    try:
        from kb_quality import run_quality_gate

        # 在线程池中运行（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None,
            lambda: run_quality_gate(
                check_datasheet=check_datasheet,
                cross_check=True,
                build_cache=True,
                save_report=True,
            )
        )

        return {
            "success": True,
            "report": report.to_dict(),
            "gate_passed": report.errors_p0 == 0,
        }
    except Exception as e:
        logger.error(f"Quality gate failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/quality/cache/build")
async def quality_build_cache():
    """构建 KiCad 符号/封装缓存"""
    import asyncio

    try:
        from kb_quality import CrossChecker

        async def _build():
            checker = CrossChecker()
            checker.build_symbol_cache(force=True)
            checker.build_footprint_cache(force=True)
            checker.save_caches()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _build)

        return {
            "success": True,
            "message": "KiCad cache built and saved",
        }
    except Exception as e:
        logger.error(f"Cache build failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/quality/validate-selection")
async def quality_validate_selection(
    body: dict = None,
):
    """校验 AI 选型结果（原理图生成前门控）"""
    if body is None:
        body = {}

    selected_chips = body.get("chips", [])
    results = []

    try:
        from kb_quality import validate_component

        for chip_name in selected_chips:
            result = validate_component(
                chip_name,
                check_datasheet=False,
                cross_check=True,
            )
            results.append({
                "chip": chip_name,
                "passed": not result.has_errors,
                "worst_severity": result.worst_severity,
                "errors": [i.to_dict() for i in result.issues],
                "warnings": [i.to_dict() for i in result.warnings],
            })

        failed = [r for r in results if not r["passed"]]
        gate_passed = all(r["passed"] for r in results)

        return {
            "success": True,
            "gate_passed": gate_passed,
            "total": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Selection validation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


# ========== Phase 3: 外部数据源解析 API ==========


class ADParseRequest(BaseModel):
    file_path: Optional[str] = None
    xml_content: Optional[str] = None
    merge_to_kb: bool = False  # 是否合并到 component_db.json


class JLCParseRequest(BaseModel):
    file_path: Optional[str] = None
    json_content: Optional[dict] = None
    merge_to_kb: bool = False  # 是否合并到 component_db.json


class LCSCDatasheetRequest(BaseModel):
    part_number: str


class LCSCChipSearchRequest(BaseModel):
    keyword: str
    limit: int = 10


class PCBCheckRequest(BaseModel):
    pcb_data: Dict[str, Any]


@router.post("/parse/ad")
async def parse_altium_schematic(req: ADParseRequest):
    """解析 Altium Designer 原理图 XML，提取元件和连接关系，并可入库"""
    if not req.file_path and not req.xml_content:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "file_path or xml_content required"},
        )

    try:
        from kb_quality.ad_parser import AltiumSchParser

        parser = AltiumSchParser()
        if req.file_path:
            result = parser.parse(req.file_path)
        else:
            result = parser.parse_from_string(req.xml_content)

        response = {
            "success": True,
            "components_count": len(result.components),
            "nets_count": len(result.nets),
            "components": [c.__dict__ for c in result.components],
            "nets": [n.__dict__ for n in result.nets],
        }

        # 转换为 component_db.json 格式
        kb_components = parser.to_kb_format(result)
        response["kb_components"] = kb_components
        response["kb_components_count"] = len(kb_components)

        # 可选：合并到 component_db.json
        if req.merge_to_kb and kb_components:
            merge_result = _merge_components_to_kb(kb_components, source="altium")
            response["merge_result"] = merge_result

        return response
    except Exception as e:
        logger.error(f"Altium parse failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/parse/jlc")
async def parse_jlc_eda(req: JLCParseRequest):
    """解析嘉立创 EDA JSON 项目文件，提取元件和连接，并可入库"""
    if not req.file_path and not req.json_content:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "file_path or json_content required"},
        )

    try:
        from kb_quality.jlc_parser import JLCEdaParser

        parser = JLCEdaParser()
        if req.file_path:
            result = parser.parse(req.file_path)
        else:
            result = parser.parse_from_string(req.json_content)

        response = {
            "success": True,
            "project_name": result.project_name,
            "components_count": len(result.components),
            "nets_count": len(result.nets),
            "components": [c.__dict__ for c in result.components],
            "nets": [n.__dict__ for n in result.nets],
        }

        # 转换为 component_db.json 格式
        kb_components = parser.to_kb_format(result)
        response["kb_components"] = kb_components
        response["kb_components_count"] = len(kb_components)

        # 可选：合并到 component_db.json
        if req.merge_to_kb and kb_components:
            merge_result = _merge_components_to_kb(kb_components, source="lcsc")
            response["merge_result"] = merge_result

        return response
    except Exception as e:
        logger.error(f"JLC EDA parse failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.get("/lcsc/connectivity")
async def lcsc_check_connectivity():
    """检查 LCSC API 连接状态"""
    try:
        from kb_quality.lcsc_fetcher import LcscFetcher

        fetcher = LcscFetcher()
        connected, latency = fetcher.verify_connectivity()
        return {
            "success": True,
            "connected": connected,
            "latency_ms": latency,
        }
    except Exception as e:
        logger.error(f"LCSC connectivity check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/lcsc/fetch")
async def lcsc_fetch_component(req: LCSCDatasheetRequest):
    """从 LCSC API 获取单个元件数据"""
    try:
        from kb_quality.lcsc_fetcher import LcscFetcher

        fetcher = LcscFetcher()
        result = fetcher.fetch_component(req.part_number)

        if result:
            return {
                "success": True,
                "found": True,
                "data": result,
            }
        return {
            "success": True,
            "found": False,
            "part_number": req.part_number,
        }
    except Exception as e:
        logger.error(f"LCSC fetch failed for {req.part_number}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/lcsc/search")
async def lcsc_search_components(req: LCSCChipSearchRequest):
    """从 LCSC 搜索元件"""
    try:
        from kb_quality.lcsc_fetcher import LcscFetcher

        fetcher = LcscFetcher()
        results = fetcher.search_components(req.keyword, req.limit)

        return {
            "success": True,
            "keyword": req.keyword,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"LCSC search failed for {req.keyword}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/lcsc/batch-sync")
async def lcsc_batch_sync(
    part_numbers: List[str] = Query(..., description="LCSC 料号列表"),
    dry_run: bool = Query(False, description="仅返回差异，不写入数据库"),
):
    """批量从 LCSC 同步元件数据到 component_db.json"""
    try:
        from kb_quality.lcsc_fetcher import LcscFetcher

        fetcher = LcscFetcher()
        results = fetcher.batch_sync(part_numbers, dry_run=dry_run)

        return {
            "success": True,
            "dry_run": dry_run,
            "total": len(part_numbers),
            "found": results.get("found", 0),
            "not_found": results.get("not_found", []),
            "updated": results.get("updated", 0),
            "skipped": results.get("skipped", 0),
        }
    except Exception as e:
        logger.error(f"LCSC batch sync failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/pcb/check-rules")
async def pcb_check_rules(req: PCBCheckRequest):
    """根据 JLCPCB 制程规则检查 PCB 设计数据"""
    try:
        from kb_quality.pcb_rules import PCBRulesChecker, JLC_RULES

        checker = PCBRulesChecker("jlcpcb")
        issues = checker.check_pcb(req.pcb_data)

        passed = all(i.severity != "error" for i in issues)

        return {
            "success": True,
            "passed": passed,
            "rule_set": "JLCPCB",
            "total_rules": len(JLC_RULES),
            "issue_count": len(issues),
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "location": i.location,
                    "value": i.value,
                    "rule": i.rule,
                }
                for i in issues
            ],
        }
    except Exception as e:
        logger.error(f"PCB rules check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


# ========== Phase 4: 全链路验证 API ==========


class TriangleValidateRequest(BaseModel):
    component_name: str
    schematic_symbol: Optional[str] = None  # 原理图符号名
    pcb_footprint: Optional[str] = None   # PCB 封装名


class NetlistValidateRequest(BaseModel):
    schematic_nets: Optional[List[Dict[str, Any]]] = None
    pcb_nets: Optional[List[Dict[str, Any]]] = None
    schematic_file: Optional[str] = None
    pcb_file: Optional[str] = None


@router.post("/triangle/validate")
async def triangle_validate(req: TriangleValidateRequest):
    """
    三角验证: Schematic Symbol 引脚 ↔ component_db Pins ↔ PCB Footprint Pads

    检查三个维度的引脚/焊盘数量一致性，识别原理图-PCB不匹配问题。
    """
    try:
        from kb_quality.cross_checker import CrossChecker

        checker = CrossChecker()
        db = get_component_db()
        components = db.get("components", {})

        # 获取 component_db 数据
        comp = components.get(req.component_name)
        if not comp:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"Component '{req.component_name}' not found in knowledge base"},
            )

        result = checker.triangle_validate(comp, req.component_name)

        # 额外检查：symbol 引脚数 vs component_db 引脚数
        symbol_lib = comp.get("symbol_library", "")
        symbol_name = req.schematic_symbol or comp.get("symbol_name", req.component_name)
        kicad_count = checker.get_symbol_pin_count(symbol_lib, symbol_name)
        kb_count = len(comp.get("pins", []))

        pin_aligned = result.get("pin_count_aligned", True)
        if kicad_count is not None and kicad_count != kb_count:
            pin_aligned = False
            result["issues"].append(
                f"Symbol pin mismatch: KB={kb_count}, KiCad={kicad_count}"
            )

        passed = pin_aligned and len(result.get("issues", [])) == 0

        return {
            "success": True,
            "component": req.component_name,
            "passed": passed,
            "symbol_checked": result.get("symbol_checked", False),
            "footprint_checked": result.get("footprint_checked", False),
            "pin_count_aligned": pin_aligned,
            "pin_count_kb": kb_count,
            "pin_count_kicad": kicad_count,
            "issues": result.get("issues", []),
        }
    except Exception as e:
        logger.error(f"Triangle validation failed for {req.component_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/netlist/validate")
async def netlist_validate(req: NetlistValidateRequest):
    """
    网表验证: 原理图网表 ↔ PCB 网表交叉验证

    1. 网络一致性检查（两端都有相同的网络）
    2. 未连接引脚检查
    3. 电源网络完整性
    4. 封装匹配检查
    """
    try:
        from netlist_validator import NetlistValidator

        validator = NetlistValidator()

        # 方式1: 直接传入网表数据
        if req.schematic_nets is not None or req.pcb_nets is not None:
            # NetlistValidator expects dict with "nets" key; wrap inline list data
            if req.schematic_nets:
                validator.load_schematic_nets({"nets": req.schematic_nets})
            if req.pcb_nets:
                validator.load_pcb_nets({"nets": req.pcb_nets})

            result = validator.validate()
            return {
                "success": True,
                "mode": "inline",
                "is_valid": result.is_valid,
                "summary": result.summary,
                "issues": [
                    {
                        "severity": i.severity.value,
                        "category": i.category,
                        "message": i.message,
                        "details": i.details,
                    }
                    for i in result.issues
                ],
            }

        # 方式2: 从文件路径加载
        if req.schematic_file or req.pcb_file:
            result = validator.validate_netlists(
                schematic_file=req.schematic_file,
                pcb_file=req.pcb_file,
            )
            return {
                "success": True,
                "mode": "file",
                "is_valid": result.is_valid,
                "summary": result.summary,
                "issues": [
                    {
                        "severity": i.severity.value,
                        "category": i.category,
                        "message": i.message,
                        "details": i.details,
                    }
                    for i in result.issues
                ],
            }

        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Provide either nets data or file paths"},
        )
    except Exception as e:
        logger.error(f"Netlist validation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/ai/selection-gate")
async def ai_selection_gate(
    body: Dict[str, Any] = None,
):
    """
    AI 选型质量门控 - 原理图生成前强制校验

    在 AI 选型完成后、生成原理图之前调用，
    确保所有选型元件通过 kb_quality 三层校验。
    """
    if body is None:
        body = {}

    selected_chips = body.get("chips", [])
    project_name = body.get("project_name", "unknown")

    try:
        from kb_quality import validate_component

        results = []
        failed_chips = []
        warnings = []

        for chip_name in selected_chips:
            result = validate_component(
                chip_name,
                check_datasheet=False,
                cross_check=True,
            )
            chip_result = {
                "chip": chip_name,
                "passed": not result.has_errors,
                "worst_severity": result.worst_severity,
                "p0_errors": len([i for i in result.issues if i.severity == "P0"]),
                "p1_errors": len([i for i in result.issues if i.severity == "P1"]),
                "p2_warnings": len([i for i in result.issues if i.severity == "P2"]),
                "p3_info": len([i for i in result.issues if i.severity == "P3"]),
                "errors": [
                    {"code": i.code, "message": i.message, "suggestion": i.suggestion}
                    for i in result.issues if i.severity in ("P0", "P1")
                ],
            }
            results.append(chip_result)
            if not result.has_errors:
                pass
            else:
                failed_chips.append(chip_result)

        gate_passed = len([r for r in results if not r["passed"]]) == 0

        # 如果有 P1 错误，禁止生成原理图
        blocking_errors = [r for r in results if r["p1_errors"] > 0]
        p0_errors = [r for r in results if r["p0_errors"] > 0]

        return {
            "success": True,
            "project_name": project_name,
            "gate_passed": gate_passed,
            "can_generate": len(blocking_errors) == 0 and len(p0_errors) == 0,
            "blocking_reason": (
                f"{len(blocking_errors)} component(s) have P1 errors"
                if blocking_errors else (
                    f"{len(p0_errors)} component(s) have P0 errors"
                    if p0_errors else None
                )
            ),
            "total": len(results),
            "passed": len(results) - len(failed_chips),
            "failed": len(failed_chips),
            "results": results,
        }
    except Exception as e:
        logger.error(f"AI selection gate failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )

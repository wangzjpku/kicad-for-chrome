"""
Phase 12C: Plugin Ecosystem API Routes

REST endpoints for:
- Template marketplace (CRUD, search, rating, download)
- Custom DRC rules (CRUD, execution, templates)
- OpenAPI SDK generation
- i18n translations
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from services.marketplace_service import get_marketplace
from services.custom_drc_service import get_custom_drc_service
from services.sdk_generator import get_sdk_generator
from services.i18n_service import get_i18n_service
from routes.auth_v2_routes import get_current_user

router = APIRouter(prefix="/api/v1", tags=["ecosystem"])


# ---- Models ----

class TemplateCreateRequest(BaseModel):
    name: str
    description: str
    category: str
    tags: List[str]
    schematic_data: Dict[str, Any]
    pcb_data: Dict[str, Any]
    bom_data: List[Dict[str, Any]]
    board_layers: int = 2
    board_size: str = ""
    thumbnail: str = ""

class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None

class RatingRequest(BaseModel):
    stars: int
    review: str = ""

class DRCCreateRequest(BaseModel):
    name: str
    description: str
    category: str
    severity: str
    check_function: str
    parameters: Dict[str, Any]
    item_types: List[str]
    condition: str = ""
    is_public: bool = False

class DRCRunRequest(BaseModel):
    pcb_items: List[Dict[str, Any]]
    rule_ids: Optional[List[str]] = None


# ---- Marketplace ----

@router.post("/marketplace/templates", summary="Create template")
async def create_template(req: TemplateCreateRequest, user: dict = Depends(get_current_user)):
    mp = get_marketplace()
    return mp.create_template(
        name=req.name, description=req.description,
        author_id=user["user_id"], author_name=user.get("username", ""),
        category=req.category, tags=req.tags,
        schematic_data=req.schematic_data, pcb_data=req.pcb_data,
        bom_data=req.bom_data, board_layers=req.board_layers,
        board_size=req.board_size, thumbnail=req.thumbnail,
    )


@router.get("/marketplace/templates", summary="Search templates")
async def search_templates(
    query: str = "",
    category: Optional[str] = None,
    tags: Optional[str] = None,
    board_layers: Optional[int] = None,
    sort_by: str = "newest",
    limit: int = 20,
    offset: int = 0,
):
    mp = get_marketplace()
    tag_list = tags.split(",") if tags else None
    return mp.search(query, category, tag_list, board_layers, sort_by, limit, offset)


@router.get("/marketplace/templates/featured", summary="Get featured templates")
async def featured_templates():
    return {"templates": get_marketplace().get_featured()}


@router.get("/marketplace/templates/{template_id}", summary="Get template")
async def get_template(template_id: str):
    result = get_marketplace().get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.put("/marketplace/templates/{template_id}", summary="Update template")
async def update_template(template_id: str, req: TemplateUpdateRequest, user: dict = Depends(get_current_user)):
    mp = get_marketplace()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = mp.update_template(template_id, user["user_id"], **updates)
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.delete("/marketplace/templates/{template_id}", summary="Delete template")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    result = get_marketplace().delete_template(template_id, user["user_id"])
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.post("/marketplace/templates/{template_id}/rate", summary="Rate template")
async def rate_template(template_id: str, req: RatingRequest, user: dict = Depends(get_current_user)):
    result = get_marketplace().rate_template(template_id, user["user_id"], req.stars, req.review)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/marketplace/templates/{template_id}/download", summary="Download template")
async def download_template(template_id: str):
    result = get_marketplace().download_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.get("/marketplace/categories", summary="List categories")
async def list_categories():
    return {"categories": get_marketplace().get_categories()}


# ---- Custom DRC ----

@router.post("/custom-drc/rules", summary="Create custom DRC rule")
async def create_drc_rule(req: DRCCreateRequest, user: dict = Depends(get_current_user)):
    svc = get_custom_drc_service()
    return svc.create_rule(
        name=req.name, description=req.description,
        category=req.category, severity=req.severity,
        check_function=req.check_function, parameters=req.parameters,
        item_types=req.item_types, condition=req.condition,
        author_id=user["user_id"], is_public=req.is_public,
    )


@router.get("/custom-drc/rules", summary="List custom DRC rules")
async def list_drc_rules(category: Optional[str] = None):
    return {"rules": get_custom_drc_service().list_rules(category)}


@router.get("/custom-drc/rules/{rule_id}", summary="Get custom DRC rule")
async def get_drc_rule(rule_id: str):
    result = get_custom_drc_service().get_rule(rule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    return result


@router.delete("/custom-drc/rules/{rule_id}", summary="Delete custom DRC rule")
async def delete_drc_rule(rule_id: str, user: dict = Depends(get_current_user)):
    if not get_custom_drc_service().delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "ok"}


@router.post("/custom-drc/run", summary="Run custom DRC checks")
async def run_custom_drc(req: DRCRunRequest):
    return get_custom_drc_service().run_checks(req.pcb_items, req.rule_ids)


@router.get("/custom-drc/templates", summary="Get DRC rule templates")
async def drc_templates():
    return {"templates": get_custom_drc_service().get_templates()}


# ---- SDK ----

@router.get("/sdk/openapi.json", summary="Get OpenAPI specification")
async def get_openapi_spec():
    """Get the full OpenAPI 3.0 specification."""
    # This will be handled by FastAPI's built-in OpenAPI endpoint
    return {"message": "See /docs for interactive API docs or /openapi.json for spec"}


@router.get("/sdk/python", summary="Download Python SDK")
async def download_python_sdk():
    gen = get_sdk_generator()
    code = gen.generate_python_sdk({})
    return {"language": "python", "code": code, "filename": "kicad_ai_client.py"}


@router.get("/sdk/typescript", summary="Download TypeScript SDK")
async def download_typescript_sdk():
    gen = get_sdk_generator()
    code = gen.generate_typescript_sdk({})
    return {"language": "typescript", "code": code, "filename": "kicadAiClient.ts"}


# ---- i18n ----

@router.get("/i18n/{lang}", summary="Get translations for a language")
async def get_translations(lang: str):
    svc = get_i18n_service()
    return {"language": lang, "translations": svc.get_all(lang)}


@router.get("/i18n/languages", summary="List supported languages")
async def list_languages():
    return {"languages": get_i18n_service().get_languages()}


@router.get("/i18n/detect", summary="Detect language from Accept-Language header")
async def detect_language(accept_language: str = Header(None, alias="Accept-Language")):
    svc = get_i18n_service()
    detected = svc.detect_language(accept_language or "")
    return {"detected": detected, "header": accept_language}

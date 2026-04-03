"""
Phase 12A-1: Spatial Index API Routes

Provides REST endpoints for spatial queries on PCB data:
- Collision detection
- Clearance checks
- Region queries
- Net adjacency
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Set

from services.spatial_index import (
    BBox,
    PCBSpatialIndex,
    get_spatial_index,
    reset_spatial_index,
)

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])


# ---- Request/Response Models ----

class BBoxModel(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class ComponentAddRequest(BaseModel):
    ref: str
    x: float
    y: float
    width: float
    height: float
    layer: str = "F.Cu"
    rotation: float = 0.0

class TrackAddRequest(BaseModel):
    track_id: str
    points: List[List[float]]
    width: float
    layer: str = "F.Cu"
    net: str = ""

class ViaAddRequest(BaseModel):
    via_id: str
    x: float
    y: float
    drill: float
    pad: float
    net: str = ""

class ZoneAddRequest(BaseModel):
    zone_id: str
    bbox: BBoxModel
    layer: str = "F.Cu"
    net: str = ""

class PadAddRequest(BaseModel):
    pad_id: str
    x: float
    y: float
    width: float
    height: float
    layer: str = "F.Cu"
    net: str = ""

class ClearanceCheckRequest(BaseModel):
    bbox: BBoxModel
    clearance: float
    layer: str = "F.Cu"
    exclude_ids: Optional[List[str]] = None

class NearbyQueryRequest(BaseModel):
    x: float
    y: float
    radius: float
    layer: Optional[str] = None
    item_type: Optional[str] = None

class RegionQueryRequest(BaseModel):
    bbox: BBoxModel
    layer: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    item_type: str
    layer: str
    bbox: Dict[str, float]
    data: Dict[str, Any] = {}

class CollisionResponse(BaseModel):
    collisions: List[Dict[str, Any]]

class ClearanceResponse(BaseModel):
    violations: List[Dict[str, Any]]

class StatsResponse(BaseModel):
    total_items: int
    by_type: Dict[str, int]
    by_layer: Dict[str, int]
    index_type: str


# ---- Endpoints ----

@router.post("/components", summary="Add component to spatial index")
async def add_component(req: ComponentAddRequest):
    idx = get_spatial_index()
    idx.add_component(
        ref=req.ref, x=req.x, y=req.y,
        width=req.width, height=req.height,
        layer=req.layer, rotation=req.rotation,
    )
    return {"status": "ok", "id": req.ref}


@router.post("/tracks", summary="Add track to spatial index")
async def add_track(req: TrackAddRequest):
    idx = get_spatial_index()
    points = [tuple(p) for p in req.points]
    idx.add_track(
        track_id=req.track_id, points=points,
        width=req.width, layer=req.layer, net=req.net,
    )
    return {"status": "ok", "id": req.track_id}


@router.post("/vias", summary="Add via to spatial index")
async def add_via(req: ViaAddRequest):
    idx = get_spatial_index()
    idx.add_via(
        via_id=req.via_id, x=req.x, y=req.y,
        drill=req.drill, pad=req.pad, net=req.net,
    )
    return {"status": "ok", "id": req.via_id}


@router.post("/zones", summary="Add zone to spatial index")
async def add_zone(req: ZoneAddRequest):
    idx = get_spatial_index()
    bbox = BBox(req.bbox.x1, req.bbox.y1, req.bbox.x2, req.bbox.y2)
    idx.add_zone(zone_id=req.zone_id, bbox=bbox, layer=req.layer, net=req.net)
    return {"status": "ok", "id": req.zone_id}


@router.post("/pads", summary="Add pad to spatial index")
async def add_pad(req: PadAddRequest):
    idx = get_spatial_index()
    idx.add_pad(
        pad_id=req.pad_id, x=req.x, y=req.y,
        width=req.width, height=req.height,
        layer=req.layer, net=req.net,
    )
    return {"status": "ok", "id": req.pad_id}


@router.delete("/items/{item_id}", summary="Remove item from spatial index")
async def remove_item(item_id: str):
    idx = get_spatial_index()
    removed = idx.remove(item_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
    return {"status": "ok", "removed": item_id}


@router.get("/collisions", summary="Find all collisions")
async def find_collisions(clearance: float = 0.0):
    idx = get_spatial_index()
    collisions = idx.find_collisions(clearance)
    return {"collisions": [
        {"id_a": a, "id_b": b, "distance": d}
        for a, b, d in collisions
    ]}


@router.post("/clearance-check", summary="Check clearance for a region")
async def check_clearance(req: ClearanceCheckRequest):
    idx = get_spatial_index()
    bbox = BBox(req.bbox.x1, req.bbox.y1, req.bbox.x2, req.bbox.y2)
    exclude = set(req.exclude_ids) if req.exclude_ids else None
    violations = idx.check_clearance(bbox, req.clearance, req.layer, exclude)
    return {"violations": [
        {
            "item_id": item.id,
            "item_type": item.item_type,
            "layer": item.layer,
            "distance": dist,
        }
        for item, dist in violations
    ]}


@router.post("/nearby", summary="Find items near a point")
async def find_nearby(req: NearbyQueryRequest):
    idx = get_spatial_index()
    items = idx.find_nearby(
        req.x, req.y, req.radius,
        layer=req.layer, item_type=req.item_type,
    )
    return {"items": [_item_to_dict(i) for i in items]}


@router.post("/region", summary="Find items in a rectangular region")
async def find_in_region(req: RegionQueryRequest):
    idx = get_spatial_index()
    bbox = BBox(req.bbox.x1, req.bbox.y1, req.bbox.x2, req.bbox.y2)
    items = idx.find_in_region(bbox, layer=req.layer)
    return {"items": [_item_to_dict(i) for i in items]}


@router.get("/net/{net_name}/adjacency", summary="Find nets adjacent to given net")
async def net_adjacency(net_name: str, radius: float = 2.0):
    idx = get_spatial_index()
    adj = idx.net_adjacency(net_name, radius)
    return {"net": net_name, "adjacent_nets": adj}


@router.get("/stats", summary="Get spatial index statistics")
async def get_stats():
    idx = get_spatial_index()
    return idx.stats()


@router.post("/reset", summary="Clear and reset the spatial index")
async def reset_index():
    reset_spatial_index()
    return {"status": "ok", "message": "Spatial index reset"}


@router.post("/batch", summary="Batch load PCB items into spatial index")
async def batch_load(items: List[Dict[str, Any]]):
    idx = get_spatial_index()
    loaded = 0
    errors = []
    for item_data in items:
        try:
            item_type = item_data.get("type", "component")
            if item_type == "component":
                idx.add_component(
                    ref=item_data["id"],
                    x=item_data["x"], y=item_data["y"],
                    width=item_data["width"], height=item_data["height"],
                    layer=item_data.get("layer", "F.Cu"),
                    rotation=item_data.get("rotation", 0),
                )
            elif item_type == "track":
                points = [tuple(p) for p in item_data.get("points", [])]
                idx.add_track(
                    track_id=item_data["id"],
                    points=points,
                    width=item_data.get("width", 0.25),
                    layer=item_data.get("layer", "F.Cu"),
                    net=item_data.get("net", ""),
                )
            elif item_type == "via":
                idx.add_via(
                    via_id=item_data["id"],
                    x=item_data["x"], y=item_data["y"],
                    drill=item_data.get("drill", 0.4),
                    pad=item_data.get("pad", 0.6),
                    net=item_data.get("net", ""),
                )
            elif item_type == "pad":
                idx.add_pad(
                    pad_id=item_data["id"],
                    x=item_data["x"], y=item_data["y"],
                    width=item_data["width"], height=item_data["height"],
                    layer=item_data.get("layer", "F.Cu"),
                    net=item_data.get("net", ""),
                )
            loaded += 1
        except Exception as e:
            errors.append({"id": item_data.get("id", "?"), "error": str(e)})

    return {"loaded": loaded, "errors": errors}


# ---- Helpers ----

def _item_to_dict(item) -> Dict[str, Any]:
    return {
        "id": item.id,
        "type": item.item_type,
        "layer": item.layer,
        "bbox": {
            "x1": item.bbox.x1, "y1": item.bbox.y1,
            "x2": item.bbox.x2, "y2": item.bbox.y2,
        },
        "data": item.data,
    }

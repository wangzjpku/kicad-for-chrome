"""
PCB Generation API Routes

Provides AI-powered PCB generation with:
- Component placement
- Trace routing
- Multi-layer support
- Integration with KiCad IPC API
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from placement.placement_engine import (
    PlacementEngine,
    Placement,
    Component,
    BoardConstraints,
    PlacementStrategy,
    PlacementResult
)
from routing.routing_engine import (
    RoutingEngine,
    Route,
    RouteSegment,
    Pad,
    Net,
    RoutingConstraints,
    RoutingResult,
    RouteLayer
)
from services.component_recommender import ComponentRecommender, ComponentRecommendation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pcb", tags=["PCB Generation"])


# ============== Request/Response Models ==============

class ComponentSpec(BaseModel):
    """Component specification for PCB generation"""
    ref: str
    symbol: str
    footprint: str
    width: float = 10.0  # mm
    height: float = 10.0  # mm
    thermal_load: float = 0.0
    is_high_speed: bool = False
    is_power: bool = False
    pins: List[Tuple[float, float]] = []


class NetSpec(BaseModel):
    """Net specification for routing"""
    name: str
    source_ref: str
    source_pin: int
    target_ref: str
    target_pin: int
    is_power: bool = False
    is_ground: bool = False
    is_high_speed: bool = False


class BoardSpec(BaseModel):
    """Board specification"""
    width: float = 100.0  # mm
    height: float = 80.0  # mm
    margin: float = 2.0  # mm
    layers: List[str] = ["F.Cu", "B.Cu"]
    trace_width: float = 0.25  # mm


class PlacementRequest(BaseModel):
    """Request for component placement"""
    board: BoardSpec
    components: List[ComponentSpec]
    strategy: str = "balanced"  # "grid", "thermal", "signal", "balanced"
    seed: Optional[int] = None


class RoutingRequest(BaseModel):
    """Request for trace routing"""
    board: BoardSpec
    nets: List[NetSpec]
    component_placements: List[Dict[str, Any]]  # From placement result
    use_multilayer: bool = True


class PCBGenerationRequest(BaseModel):
    """Complete PCB generation request"""
    requirements: str = ""
    board: BoardSpec
    components: List[ComponentSpec]
    nets: List[NetSpec]
    placement_strategy: str = "balanced"
    routing_strategy: str = "manhattan"
    use_multilayer: bool = True


class PlacementResponse(BaseModel):
    """Response for placement operation"""
    success: bool
    placements: List[Dict[str, Any]]
    unplaced: List[str] = []
    metrics: Dict[str, Any] = {}


class RoutingResponse(BaseModel):
    """Response for routing operation"""
    success: bool
    routes: List[Dict[str, Any]]
    unrouted: List[str] = []
    total_length: float = 0.0
    via_count: int = 0
    metrics: Dict[str, Any] = {}


class PCBGenerationResponse(BaseModel):
    """Response for complete PCB generation"""
    success: bool
    message: str
    placements: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    vias: List[Dict[str, Any]] = []
    board_outline: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}


# ============== Global Instances ==============

_placement_engine: Optional[PlacementEngine] = None
_routing_engine: Optional[RoutingEngine] = None
_component_recommender: Optional[ComponentRecommender] = None


def get_placement_engine() -> PlacementEngine:
    """Get or create placement engine instance"""
    global _placement_engine
    if _placement_engine is None:
        _placement_engine = PlacementEngine()
    return _placement_engine


def get_routing_engine() -> RoutingEngine:
    """Get or create routing engine instance"""
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine


def get_component_recommender() -> ComponentRecommender:
    """Get or create component recommender instance"""
    global _component_recommender
    if _component_recommender is None:
        _component_recommender = ComponentRecommender()
    return _component_recommender


# ============== API Endpoints ==============

@router.post("/placement", response_model=PlacementResponse)
async def place_components(request: PlacementRequest):
    """
    Place components on PCB board

    Uses AI-powered placement algorithms with collision avoidance
    and strategy-specific optimization (thermal, signal integrity, etc.)
    """
    try:
        engine = get_placement_engine()

        # Convert specs to components
        components = [
            Component(
                ref=spec.ref,
                width=spec.width,
                height=spec.height,
                thermal_load=spec.thermal_load,
                is_high_speed=spec.is_high_speed,
                is_power=spec.is_power
            )
            for spec in request.components
        ]

        # Select strategy
        strategy = PlacementStrategy.BALANCED
        if request.strategy == "grid":
            strategy = PlacementStrategy.GRID
        elif request.strategy == "thermal":
            strategy = PlacementStrategy.THERMAL_AWARE
        elif request.strategy == "signal":
            strategy = PlacementStrategy.SIGNAL_INTEGRITY

        # Place components
        result = engine.place(
            components=components,
            strategy=strategy,
            seed=request.seed
        )

        return PlacementResponse(
            success=True,
            placements=[p.to_dict() for p in result.placements],
            unplaced=result.unplaced,
            metrics=result.metrics
        )

    except Exception as e:
        logger.error(f"Placement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routing", response_model=RoutingResponse)
async def route_traces(request: RoutingRequest):
    """
    Route traces between components

    Uses Manhattan routing with optional multi-layer support
    and automatic via insertion.
    """
    try:
        engine = get_routing_engine()

        # Create component lookup
        placement_map = {
            p["ref"]: (p["x"], p["y"])
            for p in request.component_placements
        }

        # Convert nets to routing nets
        nets = []
        for net_spec in request.nets:
            source_pos = placement_map.get(net_spec.source_ref)
            target_pos = placement_map.get(net_spec.target_ref)

            if source_pos and target_pos:
                pad1 = Pad(
                    x=source_pos[0],
                    y=source_pos[1],
                    net=net_spec.name,
                    layer="top"
                )
                pad2 = Pad(
                    x=target_pos[0],
                    y=target_pos[1],
                    net=net_spec.name,
                    layer="top"
                )

                net = Net(
                    name=net_spec.name,
                    pads=[pad1, pad2],
                    is_power=net_spec.is_power,
                    is_ground=net_spec.is_ground,
                    is_high_speed=net_spec.is_high_speed,
                    trace_width=request.board.trace_width
                )
                nets.append(net)

        # Route nets
        if request.use_multilayer:
            result = engine.route_with_vias(nets)
        else:
            result = engine.route_nets(nets)

        # Convert routes to dict
        routes_data = []
        for route in result.routes:
            route_dict = {
                "net": route.net,
                "segments": [s.to_dict() for s in route.segments],
                "is_differential_pair": route.is_differential_pair
            }
            routes_data.append(route_dict)

        # Collect vias
        vias_data = []
        for route in result.routes:
            for via in route.vias:
                vias_data.append(via.to_dict())

        return RoutingResponse(
            success=True,
            routes=routes_data,
            unrouted=[p.net for p in result.unrouted_pads],
            total_length=result.total_length,
            via_count=result.via_count,
            metrics=result.metrics
        )

    except Exception as e:
        logger.error(f"Routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=PCBGenerationResponse)
async def generate_pcb(request: PCBGenerationRequest):
    """
    Generate complete PCB (placement + routing)

    This is the main entry point for AI PCB generation:
    1. Place components based on strategy
    2. Route traces between connected pads
    3. Return complete PCB data
    """
    try:
        # Get engines
        placement_engine = get_placement_engine()
        routing_engine = get_routing_engine()

        # Convert components
        components = [
            Component(
                ref=spec.ref,
                width=spec.width,
                height=spec.height,
                thermal_load=spec.thermal_load,
                is_high_speed=spec.is_high_speed,
                is_power=spec.is_power
            )
            for spec in request.components
        ]

        # Select placement strategy
        strategy = PlacementStrategy.BALANCED
        if request.placement_strategy == "grid":
            strategy = PlacementStrategy.GRID
        elif request.placement_strategy == "thermal":
            strategy = PlacementStrategy.THERMAL_AWARE
        elif request.placement_strategy == "signal":
            strategy = PlacementStrategy.SIGNAL_INTEGRITY

        # Step 1: Place components
        placement_result = placement_engine.place(
            components=components,
            strategy=strategy
        )

        placements_data = [p.to_dict() for p in placement_result.placements]

        # Step 2: Route traces
        placement_map = {
            p.ref: (p.x, p.y)
            for p in placement_result.placements
        }

        nets = []
        for net_spec in request.nets:
            source_pos = placement_map.get(net_spec.source_ref)
            target_pos = placement_map.get(net_spec.target_ref)

            if source_pos and target_pos:
                pad1 = Pad(
                    x=source_pos[0],
                    y=source_pos[1],
                    net=net_spec.name,
                    layer="top"
                )
                pad2 = Pad(
                    x=target_pos[0],
                    y=target_pos[1],
                    net=net_spec.name,
                    layer="top"
                )

                net = Net(
                    name=net_spec.name,
                    pads=[pad1, pad2],
                    is_power=net_spec.is_power,
                    is_ground=net_spec.is_ground,
                    is_high_speed=net_spec.is_high_speed,
                    trace_width=request.board.trace_width
                )
                nets.append(net)

        if request.use_multilayer:
            routing_result = routing_engine.route_with_vias(nets)
        else:
            routing_result = routing_engine.route_nets(nets)

        # Convert routes
        routes_data = []
        vias_data = []
        for route in routing_result.routes:
            routes_data.append({
                "net": route.net,
                "segments": [s.to_dict() for s in route.segments],
                "is_differential_pair": route.is_differential_pair
            })
            for via in route.vias:
                vias_data.append(via.to_dict())

        # Board outline
        board_outline = {
            "width": request.board.width,
            "height": request.board.height,
            "margin": request.board.margin
        }

        # Combined metrics
        metrics = {
            "placement": placement_result.metrics,
            "routing": routing_result.metrics,
            "total_vias": routing_result.via_count,
            "total_route_length": routing_result.total_length,
            "components_placed": len(placement_result.placements),
            "nets_routed": len(routing_result.routes)
        }

        return PCBGenerationResponse(
            success=True,
            message="PCB generated successfully",
            placements=placements_data,
            routes=routes_data,
            vias=vias_data,
            board_outline=board_outline,
            metrics=metrics
        )

    except Exception as e:
        logger.error(f"PCB generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend-components")
async def recommend_components(requirements: str = ""):
    """
    Recommend components based on requirements

    Uses AI to analyze requirements and recommend appropriate
    KiCad symbols and footprints.
    """
    try:
        recommender = get_component_recommender()

        recommendations = recommender.recommend_from_requirements(requirements)

        # Convert to dict format
        result = {}
        for category, recs in recommendations.items():
            result[category] = [r.to_dict() for r in recs]

        return {
            "success": True,
            "requirements": requirements,
            "recommendations": result
        }

    except Exception as e:
        logger.error(f"Component recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategies():
    """
    Get available placement and routing strategies

    Returns list of supported strategies with descriptions.
    """
    return {
        "placement_strategies": [
            {
                "name": "grid",
                "description": "Simple grid-based placement",
                "best_for": "General purpose, fast placement"
            },
            {
                "name": "thermal",
                "description": "Thermal-aware placement",
                "best_for": "Power electronics, high-heat designs"
            },
            {
                "name": "signal",
                "description": "Signal integrity optimized",
                "best_for": "High-speed digital designs"
            },
            {
                "name": "balanced",
                "description": "Balanced approach",
                "best_for": "Most designs, default choice"
            }
        ],
        "routing_strategies": [
            {
                "name": "manhattan",
                "description": "L-shaped horizontal/vertical routing",
                "best_for": "Standard PCB designs"
            },
            {
                "name": "multilayer",
                "description": "Multi-layer with automatic vias",
                "best_for": "Complex designs, dense boards"
            }
        ]
    }

"""
Pydantic Schemas
数据验证和序列化
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID


# ==================== 基础 Schema ====================


class BaseSchema(BaseModel):
    """基础 Schema"""

    class Config:
        from_attributes = True


# ==================== 项目 Schema ====================


class ProjectCreate(BaseModel):
    """创建项目"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    """更新项目"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectResponse(BaseSchema):
    """项目响应"""

    id: UUID
    name: str
    description: Optional[str]
    status: str
    project_file: Optional[str]
    schematic_file: Optional[str]
    pcb_file: Optional[str]
    created_at: datetime
    updated_at: datetime
    owner_id: UUID


class ProjectList(BaseModel):
    """项目列表"""

    total: int
    items: List[ProjectResponse]


# ==================== 原理图 Schema ====================


class SchematicComponentCreate(BaseModel):
    """创建原理图元件"""

    library_name: str
    symbol_name: str
    full_symbol_name: str
    reference: str
    value: str
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0
    mirror: bool = False
    unit: int = 1
    fields: Dict[str, str] = {}
    footprint: Optional[str] = None


class SchematicComponentUpdate(BaseModel):
    """更新原理图元件"""

    reference: Optional[str] = None
    value: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    rotation: Optional[float] = None
    mirror: Optional[bool] = None
    fields: Optional[Dict[str, str]] = None
    footprint: Optional[str] = None


class SchematicComponentResponse(BaseSchema):
    """原理图元件响应"""

    id: UUID
    sheet_id: UUID
    library_name: str
    symbol_name: str
    full_symbol_name: str
    reference: str
    value: str
    position_x: float
    position_y: float
    rotation: float
    mirror: bool
    unit: int
    fields: Dict[str, str]
    footprint: Optional[str]


class WireCreate(BaseModel):
    """创建导线"""

    start_x: float
    start_y: float
    end_x: float
    end_y: float


class WireResponse(BaseSchema):
    """导线响应"""

    id: UUID
    sheet_id: UUID
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    net_id: Optional[UUID]


# ==================== PCB Schema ====================


class Point2D(BaseModel):
    """2D 坐标点"""

    x: float
    y: float


class PCBFootprintCreate(BaseModel):
    """创建 PCB 封装"""

    library_name: str
    footprint_name: str
    full_footprint_name: str
    reference: str
    value: str
    position_x: float = 0.0
    position_y: float = 0.0
    rotation: float = 0.0
    layer: str = "F.Cu"


class PCBFootprintUpdate(BaseModel):
    """更新 PCB 封装"""

    reference: Optional[str] = None
    value: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    rotation: Optional[float] = None
    layer: Optional[str] = None


class PCBFootprintResponse(BaseSchema):
    """PCB 封装响应"""

    id: UUID
    pcb_id: UUID
    library_name: str
    footprint_name: str
    full_footprint_name: str
    reference: str
    value: str
    position_x: float
    position_y: float
    rotation: float
    layer: str


class TrackCreate(BaseModel):
    """创建走线"""

    layer: str
    width: float = 0.25
    points: List[Point2D]
    net_id: Optional[UUID] = None


class TrackResponse(BaseSchema):
    """走线响应"""

    id: UUID
    pcb_id: UUID
    layer: str
    width: float
    points: List[Point2D]
    net_id: Optional[UUID]


class ViaCreate(BaseModel):
    """创建过孔"""

    position_x: float
    position_y: float
    size: float = 0.8
    drill: float = 0.4
    start_layer: str
    end_layer: str
    via_type: str = "through"
    net_id: Optional[UUID] = None


class ViaResponse(BaseSchema):
    """过孔响应"""

    id: UUID
    pcb_id: UUID
    position_x: float
    position_y: float
    size: float
    drill: float
    start_layer: str
    end_layer: str
    via_type: str
    net_id: Optional[UUID]


class ZoneCreate(BaseModel):
    """创建铜皮"""

    layer: str
    priority: int = 0
    outline: List[Point2D]
    net_id: Optional[UUID] = None
    fill_style: str = "solid"


class ZoneResponse(BaseSchema):
    """铜皮响应"""

    id: UUID
    pcb_id: UUID
    layer: str
    priority: int
    outline: List[Point2D]
    net_id: Optional[UUID]
    fill_style: str


# ==================== 层管理 Schema ====================


class LayerCreate(BaseModel):
    """创建层"""

    name: str
    layer_type: str = "signal"
    color: str = "#FF0000"
    visible: bool = True
    layer_number: int
    thickness: float = 0.035


class LayerUpdate(BaseModel):
    """更新层"""

    color: Optional[str] = None
    visible: Optional[bool] = None
    active: Optional[bool] = None


class LayerResponse(BaseSchema):
    """层响应"""

    id: UUID
    pcb_id: UUID
    name: str
    layer_type: str
    color: str
    visible: bool
    active: bool
    layer_number: int
    thickness: float


# ==================== DRC Schema ====================


class DRCItem(BaseModel):
    """DRC 项目"""

    description: str
    type: str  # error, warning
    position: Optional[Point2D]
    object_ids: List[UUID]


class DRCReport(BaseModel):
    """DRC 报告"""

    error_count: int
    warning_count: int
    errors: List[DRCItem]
    warnings: List[DRCItem]
    timestamp: datetime


# ==================== 导出 Schema ====================


class ExportRequest(BaseModel):
    """导出请求"""

    format: str  # gerber, drill, bom, pos, step, pdf
    output_dir: str
    options: Dict[str, Any] = {}


class ExportResponse(BaseModel):
    """导出响应"""

    success: bool
    files: List[str]
    output_dir: str
    error: Optional[str] = None


# ==================== 库 Schema ====================


class SymbolInfo(BaseModel):
    """符号信息"""

    name: str
    library: str
    description: Optional[str]
    keywords: List[str]
    pin_count: int


class FootprintInfo(BaseModel):
    """封装信息"""

    name: str
    library: str
    description: Optional[str]
    keywords: List[str]
    pad_count: int
    has_3d_model: bool


# ==================== WebSocket Schema ====================


class WSCursorMove(BaseModel):
    """光标移动消息"""

    type: str = "cursor_move"
    x: float
    y: float
    editor: str  # schematic, pcb


class WSElementUpdate(BaseModel):
    """元素更新消息"""

    type: str = "element_update"
    element_type: str
    element_id: UUID
    changes: Dict[str, Any]


class WSProjectState(BaseModel):
    """项目状态消息"""

    type: str = "project_state"
    project_id: UUID
    last_modified: datetime
    active_users: List[UUID]

"""
数据库模型定义
SQLAlchemy ORM 模型
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum as PyEnum
import uuid

# Use SQLite-compatible types (String for UUID, JSON for arrays)
UUIDType = String(36)
ArrayType = JSON

Base = declarative_base()


class ProjectStatus(str, PyEnum):
    """项目状态"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class LayerType(str, PyEnum):
    """层类型"""

    SIGNAL = "signal"
    POWER = "power"
    DIELECTRIC = "dielectric"


class ViaType(str, PyEnum):
    """过孔类型"""

    THROUGH = "through"
    BLIND = "blind"
    BURIED = "buried"
    MICRO = "micro"


class Point2D:
    """2D 坐标点 (用于 JSON 存储)"""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Dict) -> "Point2D":
        return cls(data["x"], data["y"])


class User(Base):
    """用户"""

    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    projects = relationship("Project", back_populates="owner")


class Project(Base):
    """项目 - 顶级容器"""

    __tablename__ = "projects"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default=ProjectStatus.ACTIVE)

    # 文件路径
    project_file = Column(String(512))  # .kicad_pro
    schematic_file = Column(String(512))  # .kicad_sch
    pcb_file = Column(String(512))  # .kicad_pcb

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at = Column(DateTime)

    # 外键
    owner_id = Column(UUIDType, ForeignKey("users.id"))

    # 关系
    owner = relationship("User", back_populates="projects")
    schematic_sheets = relationship(
        "SchematicSheet", back_populates="project", cascade="all, delete-orphan"
    )
    pcb_design = relationship(
        "PCBDesign",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    nets = relationship("Net", back_populates="project", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("idx_project_owner", "owner_id"),
        Index("idx_project_status", "status"),
    )


class SchematicSheet(Base):
    """原理图页面 - 支持多页原理图"""

    __tablename__ = "schematic_sheets"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), default="Root")
    page_number = Column(Integer, default=1)
    file_path = Column(String(512))

    # 纸张设置
    paper_size = Column(String(50), default="A4")
    paper_orientation = Column(String(20), default="landscape")

    # 关系
    project = relationship("Project", back_populates="schematic_sheets")
    components = relationship(
        "SchematicComponent", back_populates="sheet", cascade="all, delete-orphan"
    )
    wires = relationship("Wire", back_populates="sheet", cascade="all, delete-orphan")
    labels = relationship("Label", back_populates="sheet", cascade="all, delete-orphan")
    power_symbols = relationship(
        "PowerSymbol", back_populates="sheet", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sheet_project", "project_id"),
        UniqueConstraint("project_id", "page_number", name="uq_sheet_page"),
    )


class SchematicComponent(Base):
    """原理图元件实例"""

    __tablename__ = "schematic_components"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    sheet_id = Column(
        UUIDType, ForeignKey("schematic_sheets.id"), nullable=False
    )

    # 符号信息
    library_name = Column(String(255))
    symbol_name = Column(String(255))
    full_symbol_name = Column(String(512))

    # 位号和值
    reference = Column(String(50), index=True)
    value = Column(String(255))

    # 位置和变换
    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    rotation = Column(Float, default=0.0)
    mirror = Column(Boolean, default=False)

    # 单位 (多部件器件)
    unit = Column(Integer, default=1)

    # 自定义字段
    fields = Column(JSON, default=dict)

    # 关联的封装
    footprint = Column(String(255))

    # 关系
    sheet = relationship("SchematicSheet", back_populates="components")
    pins = relationship(
        "PinConnection", back_populates="component", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_comp_sheet", "sheet_id"),
        Index("idx_comp_reference", "reference"),
    )


class Wire(Base):
    """原理图导线"""

    __tablename__ = "wires"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    sheet_id = Column(
        UUIDType, ForeignKey("schematic_sheets.id"), nullable=False
    )

    # 线段端点
    start_x = Column(Float, nullable=False)
    start_y = Column(Float, nullable=False)
    end_x = Column(Float, nullable=False)
    end_y = Column(Float, nullable=False)

    # 所属网络
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 关系
    sheet = relationship("SchematicSheet", back_populates="wires")
    net = relationship("Net", back_populates="wires")


class Label(Base):
    """原理图标签"""

    __tablename__ = "labels"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    sheet_id = Column(
        UUIDType, ForeignKey("schematic_sheets.id"), nullable=False
    )

    text = Column(String(255), nullable=False)
    label_type = Column(String(50), default="local")  # local, global, hierarchical

    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    rotation = Column(Float, default=0.0)

    # 所属网络
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 关系
    sheet = relationship("SchematicSheet", back_populates="labels")
    net = relationship("Net", back_populates="labels")


class PowerSymbol(Base):
    """电源符号"""

    __tablename__ = "power_symbols"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    sheet_id = Column(
        UUIDType, ForeignKey("schematic_sheets.id"), nullable=False
    )

    name = Column(String(100), nullable=False)  # VCC, GND, +3.3V

    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)

    # 所属网络
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 关系
    sheet = relationship("SchematicSheet", back_populates="power_symbols")
    net = relationship("Net", back_populates="power_symbols")


class PinConnection(Base):
    """引脚连接"""

    __tablename__ = "pin_connections"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    component_id = Column(UUIDType, ForeignKey("schematic_components.id"))

    pin_number = Column(String(50))
    pin_name = Column(String(100))

    # 连接的网络
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 关系
    component = relationship("SchematicComponent", back_populates="pins")
    net = relationship("Net", back_populates="pins")


class PCBDesign(Base):
    """PCB 设计"""

    __tablename__ = "pcb_designs"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUIDType, ForeignKey("projects.id"), unique=True, nullable=False
    )

    # 板框信息
    board_outline = Column(JSON)  # 板框坐标点集
    board_width = Column(Float)
    board_height = Column(Float)
    board_thickness = Column(Float, default=1.6)

    # 层叠结构
    layer_stack = Column(JSON, default=list)

    # 渲染设置
    render_config = Column(JSON, default=dict)

    # 关系
    project = relationship("Project", back_populates="pcb_design")
    layers = relationship("Layer", back_populates="pcb", cascade="all, delete-orphan")
    footprints = relationship(
        "PCBFootprint", back_populates="pcb", cascade="all, delete-orphan"
    )
    tracks = relationship("Track", back_populates="pcb", cascade="all, delete-orphan")
    vias = relationship("Via", back_populates="pcb", cascade="all, delete-orphan")
    zones = relationship("Zone", back_populates="pcb", cascade="all, delete-orphan")
    texts = relationship(
        "BoardText", back_populates="pcb", cascade="all, delete-orphan"
    )
    design_rules = relationship(
        "DesignRules", back_populates="pcb", uselist=False, cascade="all, delete-orphan"
    )


class Layer(Base):
    """PCB 层"""

    __tablename__ = "layers"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)

    name = Column(String(50), nullable=False)  # F.Cu, B.Cu, In1.Cu
    layer_type = Column(String(50), default="signal")  # signal, power, dielectric

    # 显示属性
    color = Column(String(7), default="#FF0000")  # HEX 颜色
    visible = Column(Boolean, default=True)
    active = Column(Boolean, default=False)

    # 层序号
    layer_number = Column(Integer)

    # 厚度 (mm)
    thickness = Column(Float, default=0.035)

    # 关系
    pcb = relationship("PCBDesign", back_populates="layers")

    __table_args__ = (UniqueConstraint("pcb_id", "name", name="uq_layer_name"),)


class PCBFootprint(Base):
    """PCB 封装实例"""

    __tablename__ = "pcb_footprints"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)

    # 封装信息
    library_name = Column(String(255))
    footprint_name = Column(String(255))
    full_footprint_name = Column(String(512))

    # 对应原理图元件
    schematic_component_id = Column(UUIDType)
    reference = Column(String(50), index=True)
    value = Column(String(255))

    # 位置和变换
    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    position_z = Column(Float, default=0.0)
    rotation = Column(Float, default=0.0)

    # 层
    layer = Column(String(50), default="F.Cu")

    # 属性
    attributes = Column(JSON, default=dict)

    # 3D 模型
    model_3d = Column(JSON)

    # 状态
    locked = Column(Boolean, default=False)

    # 关系
    pcb = relationship("PCBDesign", back_populates="footprints")
    pads = relationship("Pad", back_populates="footprint", cascade="all, delete-orphan")


class Pad(Base):
    """焊盘"""

    __tablename__ = "pads"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    footprint_id = Column(
        UUIDType, ForeignKey("pcb_footprints.id"), nullable=False
    )

    pad_number = Column(String(50))
    pad_type = Column(String(50), default="smd")  # smd, thru_hole, np_thru_hole
    shape = Column(String(50), default="rect")  # rect, circle, oval

    # 尺寸
    size_x = Column(Float, default=1.0)
    size_y = Column(Float, default=1.0)

    # 位置 (相对于封装)
    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)

    # 层
    layers = Column(ArrayType, default=list)

    # 网络
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 关系
    footprint = relationship("PCBFootprint", back_populates="pads")
    net = relationship("Net", back_populates="pads")


class Track(Base):
    """走线"""

    __tablename__ = "tracks"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 走线属性
    layer = Column(String(50), nullable=False)
    width = Column(Float, default=0.25)

    # 线段点集
    points = Column(JSON, nullable=False)  # [[x1,y1], [x2,y2], ...]

    # 类型
    track_type = Column(String(50), default="trace")  # trace, arc

    # 状态
    locked = Column(Boolean, default=False)

    # 关系
    pcb = relationship("PCBDesign", back_populates="tracks")
    net = relationship("Net", back_populates="tracks")


class Via(Base):
    """过孔"""

    __tablename__ = "vias"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 位置
    position_x = Column(Float)
    position_y = Column(Float)

    # 尺寸
    size = Column(Float, default=0.8)
    drill = Column(Float, default=0.4)

    # 层连接
    start_layer = Column(String(50))
    end_layer = Column(String(50))

    # 类型
    via_type = Column(String(50), default="through")

    # 状态
    locked = Column(Boolean, default=False)

    # 关系
    pcb = relationship("PCBDesign", back_populates="vias")
    net = relationship("Net", back_populates="vias")


class Zone(Base):
    """铜皮/区域"""

    __tablename__ = "zones"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)
    net_id = Column(UUIDType, ForeignKey("nets.id"))

    # 层
    layer = Column(String(50))

    # 优先级
    priority = Column(Integer, default=0)

    # 填充样式
    fill_style = Column(String(50), default="solid")
    hatch_style = Column(String(50))
    hatch_pitch = Column(Float)

    # 轮廓
    outline = Column(JSON)  # [[x1,y1], [x2,y2], ...]
    islands = Column(JSON, default=list)
    keepouts = Column(JSON, default=list)

    # 连接方式
    thermal_relief = Column(Boolean, default=True)
    thermal_width = Column(Float, default=0.5)
    thermal_gap = Column(Float, default=0.5)

    # 关系
    pcb = relationship("PCBDesign", back_populates="zones")
    net = relationship("Net", back_populates="zones")


class BoardText(Base):
    """PCB 文本"""

    __tablename__ = "board_texts"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)

    text = Column(Text, nullable=False)
    layer = Column(String(50), default="F.SilkS")

    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    rotation = Column(Float, default=0.0)

    font_size = Column(Float, default=1.0)
    font_width = Column(Float, default=0.15)

    # 关系
    pcb = relationship("PCBDesign", back_populates="texts")


class Net(Base):
    """网络 - 连接原理图和 PCB"""

    __tablename__ = "nets"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), nullable=False)
    netclass_id = Column(UUIDType, ForeignKey("netclasses.id"))

    # 默认属性
    default_width = Column(Float)
    default_via_size = Column(Float)
    default_via_drill = Column(Float)

    # 关系
    project = relationship("Project", back_populates="nets")
    netclass = relationship("NetClass", back_populates="nets")
    pins = relationship("PinConnection", back_populates="net")
    pads = relationship("Pad", back_populates="net")
    wires = relationship("Wire", back_populates="net")
    labels = relationship("Label", back_populates="net")
    power_symbols = relationship("PowerSymbol", back_populates="net")
    tracks = relationship("Track", back_populates="net")
    vias = relationship("Via", back_populates="net")
    zones = relationship("Zone", back_populates="net")

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_net_name"),)


class NetClass(Base):
    """网络类"""

    __tablename__ = "netclasses"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    name = Column(String(100), nullable=False)
    description = Column(Text)

    # 默认规则
    default_width = Column(Float, default=0.25)
    default_clearance = Column(Float, default=0.2)
    default_via_size = Column(Float, default=0.8)
    default_via_drill = Column(Float, default=0.4)

    # 关系
    nets = relationship("Net", back_populates="netclass")


class DesignRules(Base):
    """设计规则 - PCB 约束"""

    __tablename__ = "design_rules"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(
        UUIDType, ForeignKey("pcb_designs.id"), unique=True, nullable=False
    )

    # 基本规则
    min_track_width = Column(Float, default=0.2)
    min_via_size = Column(Float, default=0.6)
    min_via_drill = Column(Float, default=0.3)
    min_clearance = Column(Float, default=0.2)
    min_hole_clearance = Column(Float, default=0.25)

    # 高级规则 (JSON 存储复杂规则)
    layer_rules = Column(JSON, default=dict)
    netclass_rules = Column(JSON, default=dict)
    region_rules = Column(JSON, default=dict)

    # 关系
    pcb = relationship("PCBDesign", back_populates="design_rules")


class DRCError(Base):
    """DRC 错误记录"""

    __tablename__ = "drc_errors"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    pcb_id = Column(UUIDType, ForeignKey("pcb_designs.id"), nullable=False)

    error_type = Column(String(100), nullable=False)
    severity = Column(String(50), default="error")  # error, warning
    message = Column(Text, nullable=False)

    position_x = Column(Float)
    position_y = Column(Float)

    # 相关对象
    object_ids = Column(ArrayType, default=list)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)


class ProjectShare(Base):
    """项目分享/协作"""

    __tablename__ = "project_shares"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)

    permission = Column(String(50), default="read")  # read, write, admin
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_share"),
    )


class FileVersion(Base):
    """文件版本历史"""

    __tablename__ = "file_versions"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)

    file_type = Column(String(50))  # schematic, pcb
    file_path = Column(String(512))
    version_number = Column(Integer)

    # 变更信息
    change_summary = Column(Text)
    changed_by = Column(UUIDType, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

"""
项目 API 路由
提供项目的完整 CRUD 功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
import json
import os
from pathlib import Path
import logging
from collections import OrderedDict
import threading
import re

# 导入封装库函数
from footprint_library import (
    get_default_footprint,
    infer_component_type,
)

# 导入智能封装查找器
try:
    from smart_footprint_finder import find_footprint as smart_find_footprint
    HAS_SMART_FOOTPRINT_FINDER = True
except ImportError:
    HAS_SMART_FOOTPRINT_FINDER = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


# ========== 内存存储管理（带过期清理） ==========

MAX_PROJECTS = 500
PROJECT_EXPIRY_HOURS = 24


class ProjectCache:
    """
    项目缓存管理器 - 带 LRU 淘汰和过期清理
    """

    def __init__(self, max_size: int = MAX_PROJECTS, expiry_hours: int = PROJECT_EXPIRY_HOURS):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._timestamps: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._expiry = timedelta(hours=expiry_hours)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key in self._cache:
                # 更新访问顺序（LRU）
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
            self._cache.move_to_end(key)

            # 检查是否需要清理
            if len(self._cache) > self._max_size:
                self._evict_oldest()

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._timestamps.pop(key, None)
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def values(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._cache.values())

    def keys(self) -> List[str]:
        """获取所有缓存的键"""
        with self._lock:
            return list(self._cache.keys())

    def _evict_oldest(self) -> int:
        """清理最旧的项目"""
        evicted = 0
        now = datetime.now()

        # 首先清理过期的
        expired_keys = [
            k for k, t in self._timestamps.items()
            if now - t > self._expiry
        ]
        for key in expired_keys:
            del self._cache[key]
            del self._timestamps[key]
            evicted += 1

        # 如果还是太满，清理最旧的
        while len(self._cache) > self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._timestamps.pop(oldest_key, None)
            evicted += 1

        if evicted > 0:
            logger.info(f"Evicted {evicted} projects from cache")

        return evicted

    def cleanup_expired(self) -> int:
        """手动清理过期项目"""
        with self._lock:
            now = datetime.now()
            expired_keys = [
                k for k, t in self._timestamps.items()
                if now - t > self._expiry
            ]
            for key in expired_keys:
                del self._cache[key]
                del self._timestamps[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired projects")

            return len(expired_keys)


# 使用缓存管理器替代简单字典
_projects = ProjectCache()
_pcb_data = ProjectCache()
_schematic_data = ProjectCache()


# ========== 辅助函数 ==========


def _get_default_footprint_for_pcb(
    component_name: str, component_model: str = "", component_category: str = ""
) -> str:
    """
    根据元件名称、型号和类别获取PCB封装

    优先根据 component_category 确定封装类型，
    然后使用 smart_footprint_finder 从 KiCad 标准库中查找具体封装。
    如果 component_model 是标准型号，则使用该型号的封装。

    Args:
        component_name: 元件名称
        component_model: 元件型号
        component_category: 元件类别（如 resistor, capacitor, led, ic 等）

    Returns:
        封装名称字符串 (格式: 库名:封装名)
    """
    logger.debug(f"get_footprint: name={component_name}, model={component_model}, category={component_category}")

    # 1. 如果有 component_category，直接使用类别对应的默认封装
    # 这是最可靠的方案，避免像 "1K" 这样的值被库搜索误匹配
    if component_category:
        category_lower = component_category.lower()
        # 常见类别的默认封装
        category_footprints = {
            "led": ("LED_SMD", "LED_0603_1608Metric"),
            "capacitor": ("Capacitor_SMD", "C_0603_1608Metric"),
            "resistor": ("Resistor_SMD", "R_0603_1608Metric"),
            "inductor": ("Inductor_SMD", "L_0603_1608Metric"),
            "diode": ("Diode_SMD", "D_SOD-123"),
            "ic": ("Package_TO_SOT_SMD", "SOT-223"),  # 默认 IC 封装
            "transistor": ("Package_TO_SOT_SMD", "SOT-23"),
            "crystal": ("Crystal", "Crystal_HC49-4H_Vertical"),
        }

        if category_lower in category_footprints:
            lib_name, fp_name = category_footprints[category_lower]
            logger.info(f"Category default footprint: {component_category} -> {lib_name}:{fp_name}")
            return f"{lib_name}:{fp_name}"

    # 2. 只有当 component_model 是明确的型号（如 LM7805, ESP32 等）时才使用库搜索
    # 避免简单值（如 "Red", "1K", "10uF"）被库搜索误匹配
    if HAS_SMART_FOOTPRINT_FINDER and component_model:
        # 判断是否为标准型号（包含完整型号特征）
        is_standard_model = (
            len(component_model) >= 4 and  # 至少4个字符
            any(c.isdigit() for c in component_model) and  # 包含数字
            any(c.isalpha() for c in component_model)  # 包含字母
        )

        # 只有标准型号才进行库搜索
        if is_standard_model:
            try:
                lib_name, fp_name = smart_find_footprint(
                    model=component_model,
                    component_type=component_category,
                    package_hint=""
                )
                if lib_name and fp_name:
                    logger.info(f"Smart footprint found: {component_model} -> {lib_name}:{fp_name}")
                    return f"{lib_name}:{fp_name}"
            except Exception as e:
                logger.warning(f"Smart footprint lookup failed for {component_model}: {e}")

    # 3. 降级使用 footprint_library 的默认封装
    component_type = infer_component_type(component_name, component_model)
    footprint = get_default_footprint(component_type)
    logger.info(f"Using default footprint: {component_name} -> {footprint}")
    return footprint


def _generate_pads_for_footprint(
    footprint_name: str, pins: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    根据封装名称和引脚定义生成焊盘列表

    Args:
        footprint_name: 封装名称
        pins: 原理图引脚列表

    Returns:
        焊盘列表
    """
    pads = []

    # 如果有原理图引脚信息，生成对应的焊盘
    if pins:
        for i, pin in enumerate(pins):
            pad = {
                "id": f"P{i + 1}",
                "number": pin.get("number", str(i + 1)),
                "name": pin.get("name", f"Pin{i + 1}"),
                "type": "thru_hole"
                if "THT" in footprint_name or "DIP" in footprint_name
                else "smd",
                "shape": "rect" if i == 1 else "circle",  # 第一个焊盘通常是方形
                "position": {"x": 0, "y": i * 2.54},  # 简化的焊盘位置
                "size": {"x": 1.5, "y": 1.5},
                "drill": 0.8
                if "thru_hole" in ["thru_hole", "smd"]
                and ("THT" in footprint_name or "DIP" in footprint_name)
                else 0,
                "layer": "F.Cu",
                "net": None,
            }
            pads.append(pad)
    else:
        # 没有引脚信息时，根据封装类型生成默认焊盘
        # 检测封装类型
        if (
            "0603" in footprint_name
            or "0805" in footprint_name
            or "1206" in footprint_name
        ):
            # SMD 电阻/电容 - 两个焊盘
            pads = [
                {
                    "id": "P1",
                    "number": "1",
                    "name": "1",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": -0.75, "y": 0},
                    "size": {"x": 0.8, "y": 0.9},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
                {
                    "id": "P2",
                    "number": "2",
                    "name": "2",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": 0.75, "y": 0},
                    "size": {"x": 0.8, "y": 0.9},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
            ]
        elif "SOT-23" in footprint_name:
            # SOT-23 - 三个焊盘
            pads = [
                {
                    "id": "P1",
                    "number": "1",
                    "name": "1",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": -0.95, "y": 0.95},
                    "size": {"x": 0.6, "y": 1.1},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
                {
                    "id": "P2",
                    "number": "2",
                    "name": "2",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": -0.95, "y": -0.95},
                    "size": {"x": 0.6, "y": 1.1},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
                {
                    "id": "P3",
                    "number": "3",
                    "name": "3",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": 0.95, "y": 0},
                    "size": {"x": 0.6, "y": 1.1},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
            ]
        elif "SOIC" in footprint_name or "SOP" in footprint_name:
            # SOIC/SOP - 8个焊盘 (默认)
            for i in range(8):
                side = "left" if i < 4 else "right"
                idx = i if i < 4 else i - 4
                x = -3.9 if side == "left" else 3.9
                y = -2.54 + idx * 1.27
                pads.append(
                    {
                        "id": f"P{i + 1}",
                        "number": str(i + 1),
                        "name": str(i + 1),
                        "type": "smd",
                        "shape": "rect",
                        "position": {"x": x, "y": y},
                        "size": {"x": 1.0, "y": 0.5},
                        "drill": 0,
                        "layer": "F.Cu",
                        "net": None,
                    }
                )
        elif "DIP" in footprint_name:
            # DIP - 通孔封装
            for i in range(8):  # 默认8脚
                side = "left" if i < 4 else "right"
                idx = i if i < 4 else i - 4
                x = -3.81 if side == "left" else 3.81
                y = -3.81 + idx * 2.54
                pads.append(
                    {
                        "id": f"P{i + 1}",
                        "number": str(i + 1),
                        "name": str(i + 1),
                        "type": "thru_hole",
                        "shape": "oval" if i == 0 else "circle",
                        "position": {"x": x, "y": y},
                        "size": {"x": 1.5, "y": 1.5},
                        "drill": 0.8,
                        "layer": "F.Cu",
                        "net": None,
                    }
                )
        else:
            # 默认两个焊盘
            pads = [
                {
                    "id": "P1",
                    "number": "1",
                    "name": "1",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": -1, "y": 0},
                    "size": {"x": 1, "y": 1},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
                {
                    "id": "P2",
                    "number": "2",
                    "name": "2",
                    "type": "smd",
                    "shape": "rect",
                    "position": {"x": 1, "y": 0},
                    "size": {"x": 1, "y": 1},
                    "drill": 0,
                    "layer": "F.Cu",
                    "net": None,
                },
            ]

    return pads


# ========== Pydantic 模型 ==========


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schematicData: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    projectFile: Optional[str] = None
    schematicFile: Optional[str] = None
    pcbFile: Optional[str] = None
    createdAt: str
    updatedAt: str
    ownerId: str = "default"


class PCBDataUpdate(BaseModel):
    boardOutline: Optional[List[Dict[str, float]]] = None
    footprints: Optional[List[Dict[str, Any]]] = None
    tracks: Optional[List[Dict[str, Any]]] = None
    vias: Optional[List[Dict[str, Any]]] = None
    zones: Optional[List[Dict[str, Any]]] = None
    texts: Optional[List[Dict[str, Any]]] = None
    nets: Optional[List[Dict[str, Any]]] = None


# ========== 项目 CRUD ==========


@router.get("")
async def list_projects():
    """列出所有项目（去重）"""
    projects = _projects.values()
    # 根据项目名称去重，保留最新创建的项目
    seen = {}
    for project in projects:
        name = project.get('name', '')
        if name not in seen:
            seen[name] = project
        else:
            # 保留更新日期更新的
            if project.get('updatedAt', '') > seen[name].get('updatedAt', ''):
                seen[name] = project
    return list(seen.values())


@router.delete("/clear-all")
async def clear_all_projects():
    """清除所有项目（仅用于调试）"""
    global _projects, _pcb_data, _schematic_data
    _projects.clear()
    _pcb_data.clear()
    _schematic_data.clear()
    return {"success": True, "message": "All projects cleared"}


@router.post("", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """创建新项目"""
    project_id = str(uuid4())
    now = datetime.now().isoformat()

    new_project = {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "status": "active",
        "projectFile": None,
        "schematicFile": None,
        "pcbFile": None,
        "createdAt": now,
        "updatedAt": now,
        "ownerId": "default",
    }

    _projects.set(project_id, new_project)

    # 保存原理图数据
    if project.schematicData:
        _schematic_data.set(project_id, project.schematicData)
        # 同时更新项目信息
        new_project["schematicFile"] = f"/api/v1/projects/{project_id}/schematic"

    # 从原理图生成PCB数据
    pcb_footprints = []
    pcb_nets = []

    if project.schematicData and project.schematicData.get("components"):
        # ===== 修复1: 收集所有网络名称 =====
        schematic_nets = project.schematicData.get("nets", [])
        for net in schematic_nets:
            net_name = net.get("name", "")
            if net_name and net_name not in [n["name"] for n in pcb_nets]:
                pcb_nets.append({
                    "id": net.get("id", f"net-{net_name}"),
                    "name": net_name
                })

        # 确保VCC和GND网络存在
        net_names = [n["name"] for n in pcb_nets]
        if "GND" not in net_names:
            pcb_nets.append({"id": "net-gnd", "name": "GND"})
        if "VCC" not in net_names and "+5V" not in net_names:
            pcb_nets.append({"id": "net-vcc", "name": "VCC"})

        # ===== 修复2: 正确传递封装信息 =====
        for i, comp in enumerate(project.schematicData["components"]):
            # 获取封装 - 优先使用footprint字段，否则使用package字段
            footprint_name = comp.get("footprint") or comp.get("package", "")
            # 获取元件类别（用于封装推断），如果没有则从名称推断
            component_category = comp.get("category", "")
            if not component_category:
                # 从元件名称推断类别
                name_lower = comp.get("name", "").lower()
                if "led" in name_lower or "灯" in name_lower:
                    component_category = "led"
                elif "电容" in name_lower or "c" == name_lower or "cap" in name_lower:
                    component_category = "capacitor"
                elif "电阻" in name_lower or "r" == name_lower:
                    component_category = "resistor"
                elif "电感" in name_lower or "l" == name_lower:
                    component_category = "inductor"
                elif "二极管" in name_lower or "d" == name_lower or "diode" in name_lower:
                    component_category = "diode"
                elif "ams1117" in name_lower or "lm" in name_lower or "稳压" in name_lower:
                    component_category = "ic"
                else:
                    component_category = "passive"

            if not footprint_name:
                # 根据元件类型推断默认封装
                footprint_name = _get_default_footprint_for_pcb(
                    comp.get("name", ""), comp.get("model", ""), component_category
                )

            # 获取位号 - 使用schematic中的reference字段
            reference = comp.get("reference") or f"{comp.get('name', 'U')[0]}{i + 1}"

            footprint = {
                "id": f"FP{i + 1}",
                "reference": reference,
                "value": comp.get("model", ""),
                "footprint": footprint_name,
                "layer": "F.Cu",
                "position": {"x": 20 + (i % 4) * 15, "y": 20 + (i // 4) * 15},
                "rotation": 0,
                "locked": False,
                "attributes": [],
                "pad": _generate_pads_for_footprint(
                    footprint_name, comp.get("pins", [])
                ),
            }
            pcb_footprints.append(footprint)

    # ===== 修复3: 从原理图导线生成PCB走线 =====
    pcb_tracks = []
    if project.schematicData and project.schematicData.get("wires"):
        for i, wire in enumerate(project.schematicData["wires"]):
            net_name = wire.get("net", "")
            points = wire.get("points", [])
            if len(points) >= 2:
                # 将原理图导线转换为PCB走线
                track = {
                    "id": f"track-{i + 1}",
                    "net": net_name,
                    "layer": "F.Cu",
                    "width": 0.25,  # 默认线宽
                    "points": points  # 直接使用原理图导线的坐标点
                }
                pcb_tracks.append(track)

    # 创建 PCB 数据
    _pcb_data.set(project_id, {
        "id": f"pcb-{project_id}",
        "projectId": project_id,
        "boardOutline": [
            {"x": 10, "y": 10},
            {"x": 90, "y": 10},
            {"x": 90, "y": 70},
            {"x": 10, "y": 70},
        ],
        "boardWidth": 80,
        "boardHeight": 60,
        "boardThickness": 1.6,
        "layerStack": [
            {
                "id": "F.Cu",
                "name": "F.Cu",
                "type": "signal",
                "color": "#FF0000",
                "visible": True,
                "active": True,
                "layerNumber": 0,
                "thickness": 0.035,
            },
            {
                "id": "B.Cu",
                "name": "B.Cu",
                "type": "signal",
                "color": "#00FF00",
                "visible": True,
                "active": False,
                "layerNumber": 31,
                "thickness": 0.035,
            },
        ],
        "footprints": pcb_footprints,
        "tracks": pcb_tracks,
        "vias": [],
        "zones": [],
        "texts": [],
        "nets": pcb_nets if pcb_nets else [{"id": "net-gnd", "name": "GND"}, {"id": "net-vcc", "name": "VCC"}],
        "netclasses": [],
        "designRules": {
            "minTrackWidth": 0.1,
            "minViaSize": 0.4,
            "minViaDrill": 0.2,
            "minClearance": 0.1,
            "minHoleClearance": 0.2,
            "layerRules": {},
            "netclassRules": [],
        },
    }

    # 保存PCB数据并更新项目信息
    if pcb_footprints:
        new_project["pcbFile"] = f"/api/v1/projects/{project_id}/pcb/design"

    return new_project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """获取项目详情"""
    project = _projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectUpdate):
    """更新项目"""
    existing = _projects.get(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.name is not None:
        existing["name"] = project.name
    if project.description is not None:
        existing["description"] = project.description
    if project.status is not None:
        existing["status"] = project.status

    existing["updatedAt"] = datetime.now().isoformat()
    _projects.set(project_id, existing)  # 更新缓存

    return existing


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    _projects.delete(project_id)
    _pcb_data.delete(project_id)
    _schematic_data.delete(project_id)

    return {"message": "Project deleted"}


# ========== PCB 数据 ==========


@router.get("/{project_id}/pcb/design")
async def get_pcb_design(project_id: str):
    """获取 PCB 设计数据"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    pcb = _pcb_data.get(project_id)
    if pcb is None:
        raise HTTPException(status_code=404, detail="PCB data not found")

    return pcb


@router.get("/{project_id}/schematic")
async def get_schematic(project_id: str):
    """获取原理图数据"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    schematic = _schematic_data.get(project_id)
    if schematic is None:
        raise HTTPException(status_code=404, detail="Schematic data not found")

    return schematic


@router.post("/{project_id}/pcb/design")
async def save_pcb_design(project_id: str, pcb_data: PCBDataUpdate):
    """保存 PCB 设计数据"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    existing = _pcb_data.get(project_id) or {}

    # 更新非空字段
    if pcb_data.boardOutline is not None:
        existing["boardOutline"] = pcb_data.boardOutline
    if pcb_data.footprints is not None:
        existing["footprints"] = pcb_data.footprints
    if pcb_data.tracks is not None:
        existing["tracks"] = pcb_data.tracks
    if pcb_data.vias is not None:
        existing["vias"] = pcb_data.vias
    if pcb_data.zones is not None:
        existing["zones"] = pcb_data.zones
    if pcb_data.texts is not None:
        existing["texts"] = pcb_data.texts
    if pcb_data.nets is not None:
        existing["nets"] = pcb_data.nets

    _pcb_data.set(project_id, existing)

    # 更新项目修改时间
    project = _projects.get(project_id)
    if project:
        project["updatedAt"] = datetime.now().isoformat()
        _projects.set(project_id, project)

    return {"message": "PCB data saved"}


# ========== PCB 元素操作 ==========


@router.post("/{project_id}/pcb/items/footprint")
async def create_footprint(project_id: str, footprint: Dict[str, Any]):
    """创建封装"""
    pcb = _pcb_data.get(project_id)
    if pcb is None:
        raise HTTPException(status_code=404, detail="PCB data not found")

    footprint_id = footprint.get("id", f"fp-{uuid4()}")
    footprint["id"] = footprint_id

    pcb["footprints"].append(footprint)
    _pcb_data.set(project_id, pcb)

    return {"success": True, "id": footprint_id}


@router.post("/{project_id}/pcb/items/track")
async def create_track(project_id: str, track: Dict[str, Any]):
    """创建走线"""
    pcb = _pcb_data.get(project_id)
    if pcb is None:
        raise HTTPException(status_code=404, detail="PCB data not found")

    track_id = track.get("id", f"track-{uuid4()}")
    track["id"] = track_id

    pcb["tracks"].append(track)
    _pcb_data.set(project_id, pcb)

    return {"success": True, "id": track_id}


@router.post("/{project_id}/pcb/items/via")
async def create_via(project_id: str, via: Dict[str, Any]):
    """创建过孔"""
    pcb = _pcb_data.get(project_id)
    if pcb is None:
        raise HTTPException(status_code=404, detail="PCB data not found")

    via_id = via.get("id", f"via-{uuid4()}")
    via["id"] = via_id

    pcb["vias"].append(via)
    _pcb_data.set(project_id, pcb)

    return {"success": True, "id": via_id}


# ========== DRC ==========


@router.post("/{project_id}/drc/run")
async def run_drc(project_id: str):
    """运行 DRC 检查"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # 简化的 DRC 检查 - 实际应该调用 KiCad
    pcb = _pcb_data.get(project_id) or {}

    # 示例检查: 检查走线宽度
    errors = []
    warnings = []

    for track in pcb.get("tracks", []):
        width = track.get("width", 0)
        if width < 0.1:
            errors.append(
                {
                    "id": f"drc-{len(errors)}",
                    "type": "track_width",
                    "severity": "error",
                    "message": f"Track width {width}mm is below minimum 0.1mm",
                    "objectIds": [track.get("id", "unknown")],
                }
            )

    return {
        "success": True,
        "data": {
            "errorCount": len(errors),
            "warningCount": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        },
    }


@router.get("/{project_id}/drc/report")
async def get_drc_report(project_id: str):
    """获取 DRC 报告"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # 返回空的 DRC 报告
    return {
        "success": True,
        "data": {
            "errorCount": 0,
            "warningCount": 0,
            "errors": [],
            "warnings": [],
            "timestamp": datetime.now().isoformat(),
        },
    }


# ========== 导出 ==========


@router.post("/{project_id}/export/gerber")
async def export_gerber(project_id: str):
    """导出 Gerber 文件"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # 简化的导出响应 - 实际应该调用 KiCad
    return {
        "success": True,
        "data": {"files": [f"{project_id}-F_Cu.gbr", f"{project_id}-B_Cu.gbr"]},
    }


@router.post("/{project_id}/export/drill")
async def export_drill(project_id: str):
    """导出钻孔文件"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    return {"files": [f"{project_id}-drill.xln"]}


@router.post("/{project_id}/export/bom")
async def export_bom(project_id: str):
    """导出 BOM"""
    import csv
    import os
    from datetime import datetime

    # 验证 project_id 格式，防止路径遍历攻击
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # 获取PCB数据中的元件信息
    pcb_info = _pcb_data.get(project_id, {})
    footprints = pcb_info.get("footprints", [])
    components = []  # 初始化变量，避免未定义风险

    # 如果没有PCB数据，尝试从原理图数据中获取
    if not footprints:
        # 从_schematic_data获取原理图数据
        schematic = _schematic_data.get(project_id, {})
        components = schematic.get("components", [])
        # 从原理图组件生成BOM数据
        footprints = [
            {
                "reference": comp.get("id", f"U{i + 1}"),
                "value": comp.get("model", ""),
                "footprint": comp.get("package", ""),
                "layer": "F",
            }
            for i, comp in enumerate(components)
        ]

    logger.info(
        f"BOM export: project_id={project_id}, pcb_footprints={len(footprints)}, "
        f"schematic components={len(components)}"
    )

    # 使用环境变量配置的输出目录，支持跨平台
    output_dir = os.getenv("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))

    # 验证输出目录安全性
    safe_output_dir = Path(output_dir).resolve()
    cwd_path = Path.cwd().resolve()

    # 确保输出目录在当前工作目录下或其子目录中
    try:
        # 检查路径遍历
        if ".." in str(safe_output_dir):
            raise ValueError("Path traversal not allowed in output directory")

        # 允许在当前工作目录下或环境变量指定的安全目录
        if not (str(safe_output_dir).startswith(str(cwd_path)) or
                safe_output_dir.is_relative_to(cwd_path)):
            logger.warning(f"Output directory outside working directory: {safe_output_dir}")
            # 回退到安全目录
            safe_output_dir = cwd_path / "output"
    except Exception as e:
        logger.warning(f"Output directory validation failed: {e}, using default")
        safe_output_dir = cwd_path / "output"

    logger.info(f"Creating output directory: {safe_output_dir}")
    os.makedirs(safe_output_dir, exist_ok=True)
    output_path = safe_output_dir / f"{project_id}-bom.csv"
    logger.info(f"Writing BOM to: {output_path}")

    try:
        logger.debug(f"Footprints to write: {len(footprints)}")

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["reference", "value", "footprint", "layer", "quantity"]
            )
            writer.writeheader()

            # 按元件值分组统计数量
            component_groups = {}
            for fp in footprints:
                key = (fp.get("value", ""), fp.get("footprint", ""))
                if key not in component_groups:
                    component_groups[key] = {
                        "reference": fp.get("reference", "?"),
                        "value": fp.get("value", ""),
                        "footprint": fp.get("footprint", ""),
                        "layer": fp.get("layer", "F"),
                        "quantity": 0,
                    }
                component_groups[key]["quantity"] += 1

            for group in component_groups.values():
                writer.writerow(group)

        logger.info(f"BOM export completed for {project_id}")
        return {
            "success": True,
            "file": str(output_path),
            "components": len(footprints),
            "files": [f"{project_id}-bom.csv"],
        }
    except Exception as e:
        logger.error(f"BOM export failed: {e}", exc_info=True)
        return {"success": False, "error": "BOM export failed", "files": []}


@router.post("/{project_id}/export/step")
async def export_step(project_id: str):
    """导出 STEP 模型"""
    if not _projects.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    return {"files": [f"{project_id}.step"]}

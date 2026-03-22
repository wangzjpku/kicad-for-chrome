"""
项目 API 路由
提供项目的完整 CRUD 功能
"""

import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
import json
import os
from pathlib import Path
import logging

# 导入共享依赖（安全关键）
from dependencies import require_admin, get_current_user

# 导入配置
from settings import get_settings

# 导入封装库函数
from footprint_library import (
    get_default_footprint,
    infer_component_type,
)

logger = logging.getLogger(__name__)

# 导入智能封装查找器
try:
    from smart_footprint_finder import find_footprint as smart_find_footprint

    HAS_SMART_FOOTPRINT_FINDER = True
except ImportError:
    HAS_SMART_FOOTPRINT_FINDER = False
    logger.warning("smart_footprint_finder not available, using fallback")

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


# ========== 辅助函数 ==========

# 原理图坐标到PCB坐标转换 (原理图单位: 像素, PCB单位: 0.1mm)
SCHEMATIC_TO_PCB_SCALE = 0.1  # 1像素 = 0.1mm


def _convert_schematic_to_pcb(schematic_coords: List[Dict]) -> List[Dict]:
    """将原理图坐标转换为PCB坐标"""
    if not schematic_coords:
        return []
    return [
        {
            "x": round(coord["x"] * SCHEMATIC_TO_PCB_SCALE, 2),
            "y": round(coord["y"] * SCHEMATIC_TO_PCB_SCALE, 2),
        }
        for coord in schematic_coords
    ]


def _get_pad_position(
    footprint: Dict, pin_name: Optional[str] = None, pin_number: Optional[str] = None
) -> Optional[Dict]:
    """
    获取封装上指定引脚的焊盘位置
    """
    fp_position = footprint.get("position", {"x": 0, "y": 0})
    pads = footprint.get("pads") or footprint.get("pad") or []

    for pad in pads:
        if pin_name and pad.get("name", "").upper() == pin_name.upper():
            pad_pos = pad.get("position", {"x": 0, "y": 0})
            return {
                "x": fp_position.get("x", 0) + pad_pos.get("x", 0),
                "y": fp_position.get("y", 0) + pad_pos.get("y", 0),
            }
        if pin_number and pad.get("number") == str(pin_number):
            pad_pos = pad.get("position", {"x": 0, "y": 0})
            return {
                "x": fp_position.get("x", 0) + pad_pos.get("x", 0),
                "y": fp_position.get("y", 0) + pad_pos.get("y", 0),
            }

    if pads:
        pad_pos = pads[0].get("position", {"x": 0, "y": 0})
        return {
            "x": fp_position.get("x", 0) + pad_pos.get("x", 0),
            "y": fp_position.get("y", 0) + pad_pos.get("y", 0),
        }
    return None


def _generate_tracks_from_footprints(
    footprints: List[Dict], nets: List[Dict], schematic_wires: List[Dict] = None
) -> List[Dict]:
    """根据封装焊盘位置生成走线"""
    tracks = []
    footprint_by_ref = {fp.get("reference", ""): fp for fp in footprints}
    net_connections = {}

    # 如果有原理图导线信息，从导线生成走线
    if schematic_wires:
        for wire in schematic_wires:
            net_name = wire.get("net", "")
            start = wire.get("start", {})
            end = wire.get("end", {})

            if net_name not in net_connections:
                net_connections[net_name] = []

            if start.get("component") and end.get("component"):
                net_connections[net_name].append(
                    {
                        "from": {
                            "ref": start.get("component"),
                            "pin": start.get("pin"),
                        },
                        "to": {"ref": end.get("component"), "pin": end.get("pin")},
                    }
                )

        # 从原理图导线生成走线
        track_id = 1
        for net_name, connections in net_connections.items():
            for conn in connections:
                from_ref = conn.get("from", {}).get("ref", "")
                from_pin = conn.get("from", {}).get("pin", "")
                to_ref = conn.get("to", {}).get("ref", "")
                to_pin = conn.get("to", {}).get("pin", "")

                from_fp = footprint_by_ref.get(from_ref)
                to_fp = footprint_by_ref.get(to_ref)

                if not from_fp or not to_fp:
                    continue

                start_pos = _get_pad_position(from_fp, pin_number=from_pin)
                end_pos = _get_pad_position(to_fp, pin_number=to_pin)

                if not start_pos or not end_pos:
                    continue

                track = {
                    "id": f"track-{track_id}",
                    "net": net_name,
                    "layer": "F.Cu",
                    "width": 0.25,
                    "points": [
                        start_pos,
                        {"x": end_pos["x"], "y": start_pos["y"]},
                        end_pos,
                    ],
                }
                tracks.append(track)
                track_id += 1

        # 如果已经通过原理图导线生成了走线，就不再重复生成
        if tracks:
            return tracks

    # 只有在没有原理图导线信息时，才为VCC和GND网络自动生成走线
    if not tracks:
        for net in nets:
            net_name = net.get("name", "")
            if net_name in ["VCC", "GND", "V3"]:
                pads_on_net = []
                for fp in footprints:
                    for pad in fp.get("pad", []):
                        fp_pos = fp.get("position", {"x": 0, "y": 0})
                        pad_pos = pad.get("position", {"x": 0, "y": 0})
                        pads_on_net.append(
                            {
                                "ref": fp.get("reference", ""),
                                "x": fp_pos.get("x", 0) + pad_pos.get("x", 0),
                                "y": fp_pos.get("y", 0) + pad_pos.get("y", 0),
                            }
                        )

                if len(pads_on_net) >= 2:
                    pads_on_net.sort(key=lambda p: p["x"])
                    for i in range(len(pads_on_net) - 1):
                        track = {
                            "id": f"track-{track_id}",
                            "net": net_name,
                            "layer": "F.Cu",
                            "width": 0.25,
                            "points": [
                                {"x": pads_on_net[i]["x"], "y": pads_on_net[i]["y"]},
                                {
                                    "x": pads_on_net[i + 1]["x"],
                                    "y": pads_on_net[i]["y"],
                                },
                                {
                                    "x": pads_on_net[i + 1]["x"],
                                    "y": pads_on_net[i + 1]["y"],
                                },
                            ],
                        }
                        tracks.append(track)
                        track_id += 1

    return tracks


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
    # DEBUG: 打印调用参数
    logger.debug(
        f"[FOOTPRINT] name={component_name}, model={component_model}, category={component_category}"
    )

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
            logger.info(
                f"Category default footprint: {component_category} -> {lib_name}:{fp_name}"
            )
            return f"{lib_name}:{fp_name}"

    # 2. 只有当 component_model 是明确的型号（如 LM7805, ESP32 等）时才使用库搜索
    # 避免简单值（如 "Red", "1K", "10uF"）被库搜索误匹配
    if HAS_SMART_FOOTPRINT_FINDER and component_model:
        # 判断是否为标准型号（包含完整型号特征）
        is_standard_model = (
            len(component_model) >= 4  # 至少4个字符
            and any(c.isdigit() for c in component_model)  # 包含数字
            and any(c.isalpha() for c in component_model)  # 包含字母
        )

        # 只有标准型号才进行库搜索
        if is_standard_model:
            try:
                lib_name, fp_name = smart_find_footprint(
                    model=component_model,
                    component_type=component_category,
                    package_hint="",
                )
                if lib_name and fp_name:
                    logger.info(
                        f"Smart footprint found: {component_model} -> {lib_name}:{fp_name}"
                    )
                    return f"{lib_name}:{fp_name}"
            except Exception as e:
                logger.warning(
                    f"Smart footprint lookup failed for {component_model}: {e}"
                )

    # 3. 降级使用 footprint_library 的默认封装
    component_type = infer_component_type(component_name, component_model)
    footprint = get_default_footprint(component_type)
    logger.info(f"Using default footprint: {component_name} -> {footprint}")
    return footprint


def _get_pads_from_footprint_library(footprint_name: str) -> List[Dict[str, Any]]:
    """从KiCad封装库获取真实焊盘位置"""
    # 直接使用footprint_parser模块而不是通过HTTP API，避免超时问题
    try:
        from footprint_parser import get_footprint_data

        footprint_data = get_footprint_data(footprint_name)
        if footprint_data:
            pads = []
            for pad in footprint_data.get("pads", []):
                # footprint_parser返回扁平格式: {'number': '1', 'type': 'smd', 'shape': 'roundrect', 'x': -2.475, 'y': -1.905, 'width': 1.95, 'height': 0.6}
                # 需要转换为嵌套格式: {'position': {'x': 0, 'y': 0}, 'size': {'x': 1.5, 'y': 1.5}}
                pads.append(
                    {
                        "id": pad.get("id", f"P{len(pads) + 1}"),
                        "number": pad.get("number", str(len(pads) + 1)),
                        "name": pad.get("name", ""),
                        "type": pad.get("type", "smd"),
                        "shape": pad.get("shape", "rect"),
                        "position": {"x": pad.get("x", 0), "y": pad.get("y", 0)},
                        "size": {
                            "x": pad.get("width", 1.5),
                            "y": pad.get("height", 1.5),
                        },
                        "drill": pad.get("drill", 0),
                        "layer": "F.Cu",
                        "net": None,
                    }
                )
            logger.info(
                f"Fetched {len(pads)} pads from footprint library: {footprint_name}"
            )
            return pads
    except Exception as e:
        logger.warning(f"Failed to fetch footprint pads from library: {e}")

    return []


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

    # 如果有原理图引脚信息，从封装库获取真实焊盘位置
    if pins:
        # 尝试从封装库获取真实焊盘位置
        library_pads = _get_pads_from_footprint_library(footprint_name)

        if library_pads:
            # 使用封装库中的真实焊盘位置
            # 建立引脚号到焊盘的映射
            pad_by_number = {pad.get("number", ""): pad for pad in library_pads}

            for i, pin in enumerate(pins):
                pin_number = pin.get("number", str(i + 1))
                lib_pad = pad_by_number.get(pin_number)

                if lib_pad:
                    # 使用封装库中的真实位置
                    pad = {
                        "id": f"P{i + 1}",
                        "number": pin_number,
                        "name": pin.get("name", f"Pin{i + 1}"),
                        "type": lib_pad.get("type", "smd"),
                        "shape": lib_pad.get("shape", "rect"),
                        "position": lib_pad.get("position", {"x": 0, "y": i * 2.54}),
                        "size": lib_pad.get("size", {"x": 1.5, "y": 1.5}),
                        "drill": lib_pad.get("drill", 0),
                        "layer": "F.Cu",
                        "net": None,
                    }
                else:
                    # 如果没有匹配到，使用默认位置
                    pad = {
                        "id": f"P{i + 1}",
                        "number": pin_number,
                        "name": pin.get("name", f"Pin{i + 1}"),
                        "type": "thru_hole"
                        if "THT" in footprint_name or "DIP" in footprint_name
                        else "smd",
                        "shape": "rect" if i == 1 else "circle",
                        "position": {"x": 0, "y": i * 2.54},
                        "size": {"x": 1.5, "y": 1.5},
                        "drill": 0.8
                        if "THT" in footprint_name or "DIP" in footprint_name
                        else 0,
                        "layer": "F.Cu",
                        "net": None,
                    }
                pads.append(pad)
        else:
            # 封装库获取失败，使用简化位置（原有逻辑）
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
                    if "THT" in footprint_name or "DIP" in footprint_name
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


# 持久化存储
PROJECTS_FILE = Path(__file__).parent.parent / "projects_data.json"
PCB_DATA_FILE = Path(__file__).parent.parent / "pcb_data.json"
SCHEMATIC_DATA_FILE = Path(__file__).parent.parent / "schematic_data.json"

# 内存存储
_projects: Dict[str, Dict[str, Any]] = {}
_pcb_data: Dict[str, Dict[str, Any]] = {}
_schematic_data: Dict[str, Dict[str, Any]] = {}

# 全局锁保护并发访问
_projects_lock = asyncio.Lock()
_pcb_data_lock = asyncio.Lock()
_schematic_data_lock = asyncio.Lock()


def _save_projects():
    """保存项目数据到文件 - 带错误处理"""
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                _projects,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,  # 处理无法序列化的对象
            )
        logger.debug("Projects data saved successfully")
    except Exception as e:
        logger.error(f"Failed to save projects: {e}")


def _save_pcb_data():
    """保存PCB数据到文件 - 带错误处理"""
    try:
        with open(PCB_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                _pcb_data,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,  # 处理无法序列化的对象
            )
        logger.debug("PCB data saved successfully")
    except Exception as e:
        logger.error(f"Failed to save PCB data: {e}")


def _save_schematic_data():
    """保存原理图数据到文件 - 带循环引用处理"""
    try:
        with open(SCHEMATIC_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                _schematic_data,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,  # 处理无法序列化的对象
            )
        logger.debug("Schematic data saved successfully")
    except TypeError as e:
        logger.error(f"JSON serialization error in schematic data: {e}")
        # 尝试逐个保存项目以找出问题
        for project_id, data in _schematic_data.items():
            try:
                json.dumps(data, ensure_ascii=False, default=str)
            except TypeError as project_error:
                logger.error(
                    f"Project {project_id} has serialization issue: {project_error}"
                )
    except Exception as e:
        logger.error(f"Failed to save schematic data: {e}")


def _load_data():
    """从文件加载所有数据"""
    global _projects, _pcb_data, _schematic_data

    if PROJECTS_FILE.exists():
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                _projects = json.load(f)
            logger.info(f"Loaded {len(_projects)} projects from file")
        except Exception as e:
            logger.error(f"Failed to load projects: {e}")

    if PCB_DATA_FILE.exists():
        try:
            with open(PCB_DATA_FILE, "r", encoding="utf-8") as f:
                _pcb_data = json.load(f)
            logger.info(f"Loaded {len(_pcb_data)} PCB data entries from file")
        except Exception as e:
            logger.error(f"Failed to load PCB data: {e}")

    if SCHEMATIC_DATA_FILE.exists():
        try:
            with open(SCHEMATIC_DATA_FILE, "r", encoding="utf-8") as f:
                _schematic_data = json.load(f)
            logger.info(
                f"Loaded {len(_schematic_data)} schematic data entries from file"
            )
        except Exception as e:
            logger.error(f"Failed to load schematic data: {e}")


# 启动时加载数据
_load_data()


# ========== Pydantic 模型 ==========


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schematicData: Optional[Dict[str, Any]] = None
    pcbData: Optional[Dict[str, Any]] = None  # PCB数据（来自AI生成）
    pcbParams: Optional[Dict[str, Any]] = None  # PCB参数（尺寸等）

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        # FIX ISS-B06-001: 先检查禁止字符再trim，防止trim绕过安全检查
        import re
        invalid_chars = re.compile(r'[\\/:*?"<>|]')
        if invalid_chars.search(v):
            raise ValueError("Project name contains invalid characters: \\ / : * ? \" < > |")
        # trim后继续检查
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        if len(v) > 100:
            raise ValueError("Project name cannot exceed 100 characters")
        return v


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
    id: Optional[str] = None
    projectId: Optional[str] = None
    boardWidth: Optional[float] = None
    boardHeight: Optional[float] = None
    boardOutline: Optional[List[Dict[str, float]]] = None
    footprints: Optional[List[Dict[str, Any]]] = None
    tracks: Optional[List[Dict[str, Any]]] = None
    vias: Optional[List[Dict[str, Any]]] = None
    zones: Optional[List[Dict[str, Any]]] = None
    texts: Optional[List[Dict[str, Any]]] = None
    nets: Optional[List[Dict[str, Any]]] = None
    components: Optional[List[Dict[str, Any]]] = None  # PCB元件列表（来自AI分析）
    width: Optional[float] = None
    height: Optional[float] = None


# ========== 项目 CRUD ==========


@router.get(
    "",
    summary="列出所有项目",
    description="获取项目列表，支持分页、搜索和排序",
    response_description="项目列表",
)
async def list_projects(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    page_size: int = 50,
    search: str = None,
    sort: str = "updatedAt",
    filter: str = None,
):
    """
    列出当前用户自己的项目（认证必需）

    Args:
        current_user: 当前登录用户（从JWT token解析）
        page: 页码 (默认 1)
        page_size: 每页数量 (默认 50，最大 100)
        search: 搜索关键词（匹配项目名称）
        sort: 排序字段 (createdAt/updatedAt/name)
        filter: 过滤条件 (active/completed)

    Returns:
        项目列表数据

    Raises:
        HTTPException: page 或 page_size 无效时返回 400
    """
    # 验证分页参数
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if page_size < 1:
        raise HTTPException(status_code=400, detail="page_size must be >= 1")
    if page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be <= 100")

    async with _projects_lock:
        projects = list(_projects.values())

        # N1 Fix: 只返回当前用户自己的项目
        user_id = str(current_user["user_id"])
        projects = [p for p in projects if p.get("ownerId") == user_id]

        # 搜索过滤
        if search:
            projects = [
                p for p in projects if search.lower() in p.get("name", "").lower()
            ]

        # 状态过滤
        if filter:
            projects = [p for p in projects if p.get("status") == filter]

        # 排序
        reverse = True  # 默认降序
        if sort:
            projects.sort(key=lambda x: x.get(sort, ""), reverse=reverse)

        # 去重，保留最新
        seen = {}
        for project in projects:
            name = project.get("name", "")
            if name not in seen:
                seen[name] = project
            else:
                if project.get("updatedAt", "") > seen[name].get("updatedAt", ""):
                    seen[name] = project

        all_projects = list(seen.values())

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        return all_projects[start:end]


@router.delete("/clear-all")
async def clear_all_projects(
    confirm: str = Query(..., description="必须填写 CONFIRM_DELETE_ALL"),
    user_info: dict = Depends(require_admin),
):
    """清除所有项目（仅用于调试）"""
    if confirm != "CONFIRM_DELETE_ALL":
        raise HTTPException(status_code=400, detail="需要确认参数 confirm=CONFIRM_DELETE_ALL")
    global _projects, _pcb_data, _schematic_data
    async with _projects_lock:
        _projects.clear()
    async with _pcb_data_lock:
        _pcb_data.clear()
    async with _schematic_data_lock:
        _schematic_data.clear()
    _save_projects()
    _save_pcb_data()
    _save_schematic_data()
    return {"success": True, "message": "All projects cleared"}


@router.post(
    "",
    response_model=ProjectResponse,
    summary="创建新项目",
    description="创建一个新的 PCB 设计项目",
    status_code=201,
)
async def create_project(project: ProjectCreate, current_user: dict = Depends(get_current_user)):
    """
    创建新项目

    Args:
        project: 项目创建请求体

    Returns:
        创建成功的项目信息

    Raises:
        HTTPException:
            - 400: 项目名称无效
            - 409: 项目名称已存在
    """
    """创建新项目"""
    # 检查项目名称是否已存在（避免覆盖现有项目）
    async with _projects_lock:
        existing_projects = _projects.values()
        for existing in existing_projects:
            if existing.get("name", "").lower() == project.name.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Project '{project.name}' already exists. Please use a different name.",
                )

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
        "ownerId": str(current_user["user_id"]),
    }

    async with _projects_lock:
        _projects[project_id] = new_project
    _save_projects()

    # 保存原理图数据
    if project.schematicData:
        async with _schematic_data_lock:
            _schematic_data[project_id] = project.schematicData
        # 同时更新项目信息
        new_project["schematicFile"] = f"/api/v1/projects/{project_id}/schematic"
        # 保存到文件
        _save_schematic_data()

    # 从传入的pcbData或从原理图生成PCB数据
    pcb_footprints = []
    pcb_nets = []

    # 如果传入了PCB数据，直接使用
    if project.pcbData:
        logger.info("使用传入的PCB数据创建项目")
        pcb_footprints = project.pcbData.get("footprints", [])
        pcb_nets = project.pcbData.get("nets", [])

        # 使用传入的PCB参数设置板框尺寸
        if project.pcbParams:
            board_width = (
                project.pcbParams.get("width")
                or project.pcbParams.get("boardWidth")
                or 80
            )
            board_height = (
                project.pcbParams.get("height")
                or project.pcbParams.get("boardHeight")
                or 60
            )
        else:
            board_width = 80
            board_height = 60
    else:
        # 没有PCB数据，使用默认尺寸
        board_width = 80
        board_height = 60

    # 确保board_width和board_height有值（前面逻辑已确保，此处为安全校验）
    if not board_width:
        board_width = 80
    if not board_height:
        board_height = 60

    if project.schematicData and project.schematicData.get("components"):
        # ===== 修复1: 收集所有网络名称 =====
        schematic_nets = project.schematicData.get("nets", [])
        for net in schematic_nets:
            net_name = net.get("name", "")
            if net_name and net_name not in [n["name"] for n in pcb_nets]:
                pcb_nets.append(
                    {"id": net.get("id", f"net-{net_name}"), "name": net_name}
                )

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
                elif (
                    "二极管" in name_lower or "d" == name_lower or "diode" in name_lower
                ):
                    component_category = "diode"
                elif (
                    "ams1117" in name_lower
                    or "lm" in name_lower
                    or "稳压" in name_lower
                ):
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
                "position": {"x": 30 + (i % 4) * 25, "y": 30 + (i // 4) * 20},
                "rotation": 0,
                "locked": False,
                "attributes": [],
                "pad": _generate_pads_for_footprint(
                    footprint_name, comp.get("pins", [])
                ),
            }
            pcb_footprints.append(footprint)

    # ===== F1 Fix: 关联焊盘与网络 =====
    # 构建 (reference, pin_number) -> net_name 的映射
    pin_to_net: Dict[tuple, str] = {}
    if project.schematicData and project.schematicData.get("wires"):
        for wire in project.schematicData["wires"]:
            net_name = wire.get("net", "")
            if not net_name:
                continue
            # 支持 from_conn/to_conn 格式
            from_conn = wire.get("from_conn") or wire.get("from") or {}
            to_conn = wire.get("to_conn") or wire.get("to") or {}
            from_ref = from_conn.get("component") or from_conn.get("ref", "")
            from_pin = from_conn.get("pin") or from_conn.get("pin_number") or ""
            to_ref = to_conn.get("component") or to_conn.get("ref", "")
            to_pin = to_conn.get("pin") or to_conn.get("pin_number") or ""
            if from_ref and from_pin:
                pin_to_net[(from_ref, str(from_pin))] = net_name
            if to_ref and to_pin:
                pin_to_net[(to_ref, str(to_pin))] = net_name

    # 为每个焊盘设置正确的网络
    for fp in pcb_footprints:
        for pad in fp.get("pad", []):
            ref = fp.get("reference", "")
            pin_num = str(pad.get("number", ""))
            key = (ref, pin_num)
            if key in pin_to_net:
                pad["net"] = pin_to_net[key]
            else:
                # 未找到网络关联的焊盘，尝试使用焊盘名称匹配
                pad_name = str(pad.get("name", "")).upper()
                if pad_name in ("GND", "1"):
                    for gnd_key in pin_to_net:
                        if "GND" in pin_to_net[gnd_key].upper():
                            pad["net"] = pin_to_net[gnd_key]
                            break
                elif pad_name in ("VCC", "VIN", "VOUT", "+", "2"):
                    for vcc_key in pin_to_net:
                        if any(n in pin_to_net[vcc_key].upper() for n in ["VCC", "+5V", "+3V3", "VIN", "VOUT"]):
                            pad["net"] = pin_to_net[vcc_key]
                            break

    # ===== 修复3: 从原理图导线生成PCB走线 =====
    pcb_tracks = []
    if project.schematicData and project.schematicData.get("wires"):
        # 使用新的基于焊盘位置的走线生成函数
        pcb_tracks = _generate_tracks_from_footprints(
            pcb_footprints, pcb_nets, project.schematicData.get("wires", [])
        )
        # 如果新函数没有生成走线，回退到旧方法
        if not pcb_tracks:
            for i, wire in enumerate(project.schematicData["wires"]):
                net_name = wire.get("net", "")
                points = wire.get("points", [])
                if len(points) >= 2:
                    track = {
                        "id": f"track-{i + 1}",
                        "net": net_name,
                        "layer": "F.Cu",
                        "width": 0.25,
                        "points": _convert_schematic_to_pcb(points),
                    }
                    pcb_tracks.append(track)

    # 创建 PCB 数据
    _pcb_data[project_id] = {
        "id": f"pcb-{project_id}",
        "projectId": project_id,
        "boardOutline": [
            {"x": 3, "y": 3},
            {"x": board_width - 3, "y": 3},
            {"x": board_width - 3, "y": board_height - 3},
            {"x": 3, "y": board_height - 3},
        ],
        "boardWidth": board_width,
        "boardHeight": board_height,
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
        "nets": pcb_nets
        if pcb_nets
        else [{"id": "net-gnd", "name": "GND"}, {"id": "net-vcc", "name": "VCC"}],
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

    # 保存PCB数据到文件
    _save_pcb_data()

    return new_project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """获取项目详情（认证必需）"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")
        project = _projects[project_id]
        # N1 Fix: 验证项目所有权
        if project.get("ownerId") != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="无权限访问此项目")
        return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectUpdate, current_user: dict = Depends(get_current_user)):
    """更新项目（认证必需）"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")
        # N1 Fix: 验证项目所有权
        if _projects[project_id].get("ownerId") != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="无权限修改此项目")

        existing = _projects[project_id]

        if project.name is not None:
            existing["name"] = project.name
        if project.description is not None:
            existing["description"] = project.description
        if project.status is not None:
            existing["status"] = project.status

        existing["updatedAt"] = datetime.now().isoformat()
    _save_projects()

    return existing


@router.delete("/{project_id}")
async def delete_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """删除项目（认证必需）"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")
        # N1 Fix: 验证项目所有权
        if _projects[project_id].get("ownerId") != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="无权限删除此项目")
        del _projects[project_id]
    async with _pcb_data_lock:
        if project_id in _pcb_data:
            del _pcb_data[project_id]
    async with _schematic_data_lock:
        if project_id in _schematic_data:
            del _schematic_data[project_id]

    # 持久化到文件
    _save_projects()
    _save_pcb_data()
    _save_schematic_data()

    return {"message": "Project deleted"}


# ========== PCB 数据 ==========


@router.get("/{project_id}/pcb/design")
async def get_pcb_design(project_id: str):
    """获取 PCB 设计数据"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")

    # 如果没有PCB数据，返回默认空数据结构
    async with _pcb_data_lock:
        if project_id not in _pcb_data:
            return {
                "success": True,
                "project_id": project_id,
                "footprints": [],
                "tracks": [],
                "vias": [],
                "zones": [],
                "board": {"width": 0, "height": 0},
            }

        return _pcb_data[project_id]


@router.get("/{project_id}/schematic")
async def get_schematic(project_id: str):
    """获取原理图数据"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")

    # 如果没有原理图数据，返回默认空数据结构
    async with _schematic_data_lock:
        if project_id not in _schematic_data:
            return {
                "success": True,
                "project_id": project_id,
                "symbols": [],
                "wires": [],
                "netlabels": [],
                "buses": [],
            }

        return _schematic_data[project_id]


@router.post("/{project_id}/schematic")
async def save_schematic(project_id: str, schematic_data: Dict[str, Any]):
    """保存原理图数据"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")

    async with _schematic_data_lock:
        _schematic_data[project_id] = schematic_data
    logger.info(f"Saved schematic data for project {project_id}")

    # 保存原理图数据到文件
    _save_schematic_data()

    return {"success": True}


@router.post("/{project_id}/pcb/design")
async def save_pcb_design(project_id: str, pcb_data: PCBDataUpdate):
    """保存 PCB 设计数据"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")

    async with _pcb_data_lock:
        if project_id not in _pcb_data:
            _pcb_data[project_id] = {}

        existing = _pcb_data[project_id]

        # 保存必要字段（所有写操作在锁内完成，防止并发竞态）
        if hasattr(pcb_data, "id") and pcb_data.id:
            existing["id"] = pcb_data.id
        if hasattr(pcb_data, "projectId") and pcb_data.projectId:
            existing["projectId"] = pcb_data.projectId
        if pcb_data.boardWidth is not None:
            existing["boardWidth"] = pcb_data.boardWidth
        if pcb_data.boardHeight is not None:
            existing["boardHeight"] = pcb_data.boardHeight

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
        if pcb_data.components is not None:
            existing["components"] = pcb_data.components

            # 将 components 转换为 footprints 格式（前端需要）
            if pcb_data.footprints is None:
                footprints = []
                for comp in pcb_data.components:
                    footprint = {
                        "id": comp.get("id", f"fp-{uuid4()}"),
                        "type": "footprint",
                        "libraryName": comp.get("footprint", "").split(":")[0]
                        if ":" in comp.get("footprint", "")
                        else "",
                        "footprintName": comp.get("footprint", "").split(":")[-1]
                        if ":" in comp.get("footprint", "")
                        else comp.get("footprint", ""),
                        "fullFootprintName": comp.get("footprint", ""),
                        "reference": comp.get("reference", ""),
                        "value": comp.get("model", ""),
                        "position": comp.get("position", {"x": 0, "y": 0}),
                        "rotation": comp.get("rotation", 0),
                        "layer": "top",
                        "pads": comp.get("pads", []),
                        "silkscreen": comp.get("silkscreen", []),
                        "attributes": {},
                    }
                    footprints.append(footprint)
                existing["footprints"] = footprints
                logger.info(f"Converted {len(footprints)} components to footprints")

        if pcb_data.width is not None:
            existing["width"] = pcb_data.width
        if pcb_data.height is not None:
            existing["height"] = pcb_data.height

    # 更新项目修改时间和pcbFile字段（独立锁保护）
    async with _projects_lock:
        _projects[project_id]["updatedAt"] = datetime.now().isoformat()
        _projects[project_id]["pcbFile"] = f"/api/v1/projects/{project_id}/pcb/design"
    _save_projects()

    # 保存PCB数据到文件
    _save_pcb_data()

    return {"message": "PCB data saved"}


# ========== PCB 元素操作 ==========


@router.post("/{project_id}/pcb/items/footprint")
async def create_footprint(project_id: str, footprint: Dict[str, Any]):
    """创建封装"""
    async with _pcb_data_lock:
        if project_id not in _pcb_data:
            raise HTTPException(status_code=404, detail="PCB data not found")

        footprint_id = footprint.get("id", f"fp-{uuid4()}")
        footprint["id"] = footprint_id

        _pcb_data[project_id]["footprints"].append(footprint)

    return {"success": True, "id": footprint_id}


@router.post("/{project_id}/pcb/items/track")
async def create_track(project_id: str, track: Dict[str, Any]):
    """创建走线"""
    async with _pcb_data_lock:
        if project_id not in _pcb_data:
            raise HTTPException(status_code=404, detail="PCB data not found")

        track_id = track.get("id", f"track-{uuid4()}")
        track["id"] = track_id

        _pcb_data[project_id]["tracks"].append(track)

    return {"success": True, "id": track_id}


@router.post("/{project_id}/pcb/items/via")
async def create_via(project_id: str, via: Dict[str, Any]):
    """创建过孔"""
    async with _pcb_data_lock:
        if project_id not in _pcb_data:
            raise HTTPException(status_code=404, detail="PCB data not found")

        via_id = via.get("id", f"via-{uuid4()}")
        via["id"] = via_id

        _pcb_data[project_id]["vias"].append(via)

    return {"success": True, "id": via_id}


# ========== DRC ==========


@router.post("/{project_id}/drc/run")
async def run_drc(project_id: str):
    """运行 DRC 检查"""
    async with _projects_lock:
        if project_id not in _projects:
            raise HTTPException(status_code=404, detail="Project not found")

    # 简化的 DRC 检查 - 实际应该调用 KiCad
    async with _pcb_data_lock:
        pcb = _pcb_data.get(project_id, {})

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
    if project_id not in _projects:
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
    """导出 Gerber 文件 - 直接生成Gerber文件"""
    import os

    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"Starting Gerber export for project: {project_id}")

    output_dir = os.environ.get("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
    os.makedirs(output_dir, exist_ok=True)

    pcb_info = _pcb_data.get(project_id, {})
    footprints = pcb_info.get("footprints", [])
    board_width = pcb_info.get("boardWidth", 80)
    board_height = pcb_info.get("boardHeight", 60)

    if not footprints:
        schematic = _schematic_data.get(project_id, {})
        components = schematic.get("components", [])
        if components:
            for i, comp in enumerate(components):
                fp = {
                    "reference": comp.get("reference", f"U{i + 1}"),
                    "value": comp.get("model", ""),
                    "footprint": comp.get("package", "R_0805"),
                    "position": comp.get("position", {"x": 50, "y": 50}),
                }
                footprints.append(fp)

    if not footprints:
        raise HTTPException(status_code=400, detail="No PCB data available for export")

    try:

        def gerber_header(layer_name):
            return f"G04 Created by KiCad AI Auto Gerber Exporter *\nG01*\nG04 Layer: {layer_name} *\n%FSLAX46Y46*%\n%MOMM*%\n%IPPOS*%\nG04 Gerber X2 format *\n%ASAXB*%\nG54D10*\nG75*\n"

        def gerber_footer():
            return "M02*\n"

        def format_coord(x, y):
            return f"X{int(x * 1000):07d}Y{int(y * 1000):07d}D01*\n"

        exported_files = []

        # F.Cu layer
        gerber_content = gerber_header("F.Cu")
        gerber_content += "G54D11*\n"

        for fp in footprints:
            pos = fp.get("position", {"x": 0, "y": 0})
            x, y = pos.get("x", 0), pos.get("y", 0)
            x_mm = x / 10
            y_mm = (board_height * 10 - y) / 10
            gerber_content += format_coord(x_mm - 0.4, y_mm - 0.4)
            gerber_content += format_coord(x_mm + 0.4, y_mm - 0.4)
            gerber_content += format_coord(x_mm + 0.4, y_mm + 0.4)
            gerber_content += format_coord(x_mm - 0.4, y_mm + 0.4)
            gerber_content += format_coord(x_mm - 0.4, y_mm - 0.4)
            gerber_content += "D02*\n"

        gerber_content += gerber_footer()

        output_file = os.path.join(output_dir, f"{project_id}-F_Cu.gbr")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(gerber_content)
        exported_files.append(os.path.basename(output_file))

        # B.Cu layer
        gerber_content = gerber_header("B.Cu")
        gerber_content += gerber_footer()

        output_file = os.path.join(output_dir, f"{project_id}-B_Cu.gbr")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(gerber_content)
        exported_files.append(os.path.basename(output_file))

        # Edge.Cuts
        gerber_content = gerber_header("Edge.Cuts")
        gerber_content += "G54D11*\n"
        gerber_content += "G75*\n"
        gerber_content += f"X{int(0) * 1000:07d}Y{int(0) * 1000:07d}D02*\n"
        gerber_content += (
            f"X{int(board_width * 10) * 1000:07d}Y{int(0) * 1000:07d}D01*\n"
        )
        gerber_content += f"X{int(board_width * 10) * 1000:07d}Y{int(board_height * 10) * 1000:07d}D01*\n"
        gerber_content += (
            f"X{int(0) * 1000:07d}Y{int(board_height * 10) * 1000:07d}D01*\n"
        )
        gerber_content += f"X{int(0) * 1000:07d}Y{int(0) * 1000:07d}D01*\n"
        gerber_content += "D02*\n"
        gerber_content += gerber_footer()

        output_file = os.path.join(output_dir, f"{project_id}-Edge_Cuts.gbr")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(gerber_content)
        exported_files.append(os.path.basename(output_file))

        logger.info(f"Gerber export completed: {exported_files}")

        return {
            "success": True,
            "data": {"files": exported_files, "output_dir": output_dir},
        }

    except Exception as e:
        logger.error(f"Error in Gerber export: {e}")
        import traceback

        logger.error(traceback.format_exc())

    raise HTTPException(status_code=500, detail="Gerber export failed")


@router.post("/{project_id}/export/drill")
async def export_drill(project_id: str):
    """导出钻孔文件"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"files": [f"{project_id}-drill.xln"]}


@router.post("/{project_id}/export/bom")
async def export_bom(project_id: str):
    """导出 BOM"""
    import csv
    import os
    from datetime import datetime

    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # 获取PCB数据中的元件信息
    pcb_info = _pcb_data.get(project_id, {})
    footprints = pcb_info.get("footprints", [])

    # 初始化components变量
    components = []

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

    # 调试：打印获取到的数据（logging 已在文件顶部导入）

    logger = logging.getLogger(__name__)

    # 强制刷新日志输出
    import sys

    logger.debug(f"BOM export called for {project_id}")
    logger.debug(f"_schematic_data keys: {list(_schematic_data.keys())}")

    # 安全获取components长度
    components_count = len(components) if components else 0
    logger.info(
        f"BOM export: project_id={project_id}, pcb_footprints={len(footprints)}, schematic components={components_count}"
    )

    # 生成BOM CSV - 使用固定的输出目录
    output_dir = os.environ.get("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
    logger.info(f"Creating output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_id}-bom.csv")
    logger.info(f"Writing BOM to: {output_path}")

    try:
        # 调试：打印要写入的数据
        logger.info(f"Footprints to write: {footprints}")

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

        logger.debug(f"Returning success for {project_id}")
        return {
            "success": True,
            "file": output_path,
            "components": len(footprints),
            "files": [f"{project_id}-bom.csv"],
            "debug": f"output_path={output_path}, footprints={len(footprints)}",
        }
    except Exception as e:
        logger.error(f"Exception in BOM export: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e), "files": []}


@router.post("/{project_id}/export/pdf")
async def export_pdf(project_id: str):
    """导出 PDF 文档"""
    import os
    from datetime import datetime

    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"Starting PDF export for project: {project_id}")

    project = _projects.get(project_id, {})
    project_name = project.get("name", project_id)

    output_dir = os.environ.get("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
    os.makedirs(output_dir, exist_ok=True)

    # 尝试使用 kicad-cli 导出 PDF
    settings = get_settings()
    kicad_cli_path = settings.kicad_cli_path or os.environ.get(
        "KICAD_CLI_PATH"
    )
    project_dir = os.path.join(
        os.environ.get("PROJECTS_DIR", os.path.join(os.getcwd(), "projects")),
        project_id,
    )

    sch_file = None
    for ext in [".kicad_sch", ".sch"]:
        for root, dirs, files in os.walk(project_dir):
            for f in files:
                if f.endswith(ext):
                    sch_file = os.path.join(root, f)
                    break
            if sch_file:
                break
        if sch_file:
            break

    if sch_file and os.path.exists(sch_file):
        output_file = os.path.join(output_dir, f"{project_id}.pdf")
        try:
            import subprocess

            result = subprocess.run(
                [kicad_cli_path, "sch", "export", "pdf", "-o", output_file, sch_file],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and os.path.exists(output_file):
                logger.info(f"PDF export successful: {output_file}")
                return {
                    "success": True,
                    "file": os.path.basename(output_file),
                    "files": [os.path.basename(output_file)],
                }
            else:
                logger.warning(f"PDF export failed: {result.stderr}")
        except Exception as e:
            logger.error(f"PDF export error: {e}")

    # 创建占位文件
    try:
        output_file = os.path.join(output_dir, f"{project_id}-pdf.txt")
        with open(output_file, "w") as f:
            f.write(f"Project: {project_name}\n")
            f.write(f"Project ID: {project_id}\n")
            f.write(f"Export date: {datetime.now().isoformat()}\n")
            f.write("Note: Full PDF export requires KiCad CLI\n")
        return {
            "success": True,
            "file": os.path.basename(output_file),
            "files": [os.path.basename(output_file)],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@router.post("/{project_id}/export/step")
async def export_step(project_id: str):
    """导出 STEP 3D模型"""
    import os
    import subprocess

    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"Starting STEP export for project: {project_id}")

    # 获取项目信息
    project = _projects.get(project_id, {})
    project_name = project.get("name", project_id)

    output_dir = os.environ.get("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
    os.makedirs(output_dir, exist_ok=True)

    # 检查是否有KiCad IPC连接
    kicad_cli_path = os.environ.get(
        "KICAD_CLI_PATH", "E:/Program Files/KiCad/9.0/bin/kicad-cli.exe"
    )

    # 查找项目的KiCad文件
    project_dir = os.path.join(
        os.environ.get("PROJECTS_DIR", os.path.join(os.getcwd(), "projects")),
        project_id,
    )
    pcb_file = None

    # 搜索可能的PCB文件
    for ext in [".kicad_pcb", ".pcb"]:
        for root, dirs, files in os.walk(project_dir):
            for f in files:
                if f.endswith(ext):
                    pcb_file = os.path.join(root, f)
                    break
            if pcb_file:
                break
        if pcb_file:
            break

    # 如果找到PCB文件，使用kicad-cli导出
    if pcb_file and os.path.exists(pcb_file):
        output_file = os.path.join(output_dir, f"{project_id}.step")

        try:
            result = subprocess.run(
                [
                    kicad_cli_path,
                    "pcb",
                    "export",
                    "step",
                    "-o",
                    output_file,
                    "--subst-models",
                    pcb_file,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and os.path.exists(output_file):
                logger.info(f"STEP export successful: {output_file}")
                return {"files": [os.path.basename(output_file)]}
            else:
                logger.error(f"STEP export failed: {result.stderr}")
                raise HTTPException(
                    status_code=500, detail=f"STEP export failed: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            logger.error("STEP export timeout")
            raise HTTPException(status_code=500, detail="STEP export timeout")
        except Exception as e:
            logger.error(f"STEP export error: {e}")
            raise HTTPException(status_code=500, detail=f"STEP export error: {str(e)}")
    else:
        # Canvas模式：没有真实的KiCad文件
        # 创建一个提示文件说明情况
        logger.warning(
            f"No KiCad PCB file found for project: {project_id}, generating placeholder"
        )

        # 检查PCB数据是否存在
        pcb_info = _pcb_data.get(project_id, {})
        footprints = pcb_info.get("footprints", [])

        if footprints:
            # 有PCB数据但没有文件，生成说明文件
            placeholder_content = f"""STEP 3D Model Export - Placeholder
=====================================

Project: {project_name}
Project ID: {project_id}

This is a placeholder file because the system is running in Canvas mode
without an active KiCad connection.

To export a real STEP 3D model:

1. Open the project in KiCad PCB Editor
2. Go to File -> Export -> STEP
3. Or use: kicad-cli pcb export step -o output.step input.kicad_pcb

PCB Summary:
- Footprints: {len(footprints)}
- Board dimensions: {pcb_info.get("boardWidth", "N/A")} x {pcb_info.get("boardHeight", "N/A")} mm
"""
            placeholder_file = os.path.join(output_dir, f"{project_id}.step.txt")
            with open(placeholder_file, "w", encoding="utf-8") as f:
                f.write(placeholder_content)

            return {
                "files": [f"{project_id}.step.txt"],
                "warning": "STEP export requires KiCad connection. Generated placeholder file.",
                "note": "To get real STEP file, open project in KiCad and export manually",
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="No PCB data available. Please generate PCB layout first.",
            )


# ========== 导出格式端点 ==========
@router.get("/export/formats")
async def get_export_formats():
    """获取支持的导出格式列表"""
    return {
        "formats": [
            {"id": "gerber", "name": "Gerber", "description": "PCB制造文件"},
            {"id": "drill", "name": "Drill", "description": "钻孔文件"},
            {"id": "bom", "name": "BOM", "description": "物料清单"},
            {
                "id": "pickplace",
                "name": "Pick and Place",
                "description": "贴片坐标文件",
            },
            {"id": "pdf", "name": "PDF", "description": "PDF文档"},
            {"id": "svg", "name": "SVG", "description": "SVG矢量图"},
            {"id": "step", "name": "STEP", "description": "3D模型"},
        ]
    }

"""
项目 API 路由
提供项目的完整 CRUD 功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
import json
import os
from pathlib import Path
import logging

# 导入封装库函数
from footprint_library import (
    get_default_footprint,
    infer_component_type,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


# ========== 辅助函数 ==========


def _get_default_footprint_for_pcb(
    component_name: str, component_model: str = ""
) -> str:
    """
    根据元件名称获取PCB封装

    Args:
        component_name: 元件名称
        component_model: 元件型号

    Returns:
        封装名称字符串
    """
    component_type = infer_component_type(component_name, component_model)
    return get_default_footprint(component_type)


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


# 内存存储 (生产环境应使用数据库)
_projects: Dict[str, Dict[str, Any]] = {}
_pcb_data: Dict[str, Dict[str, Any]] = {}
_schematic_data: Dict[str, Dict[str, Any]] = {}


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
    """列出所有项目"""
    return list(_projects.values())


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

    _projects[project_id] = new_project

    # 保存原理图数据
    if project.schematicData:
        _schematic_data[project_id] = project.schematicData
        # 同时更新项目信息
        new_project["schematicFile"] = f"/api/v1/projects/{project_id}/schematic"

    # 从原理图生成PCB数据
    pcb_footprints = []
    if project.schematicData and project.schematicData.get("components"):
        for i, comp in enumerate(project.schematicData["components"]):
            # 获取封装 - 优先使用footprint字段，否则使用package字段
            footprint_name = comp.get("footprint") or comp.get("package", "")
            if not footprint_name:
                # 根据元件类型推断默认封装
                footprint_name = _get_default_footprint_for_pcb(
                    comp.get("name", ""), comp.get("model", "")
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

    # 创建 PCB 数据
    _pcb_data[project_id] = {
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
        "tracks": [],
        "vias": [],
        "zones": [],
        "texts": [],
        "nets": [{"id": "net-gnd", "name": "GND"}, {"id": "net-vcc", "name": "VCC"}],
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

    return new_project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """获取项目详情"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return _projects[project_id]


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectUpdate):
    """更新项目"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = _projects[project_id]

    if project.name is not None:
        existing["name"] = project.name
    if project.description is not None:
        existing["description"] = project.description
    if project.status is not None:
        existing["status"] = project.status

    existing["updatedAt"] = datetime.now().isoformat()

    return existing


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    del _projects[project_id]
    if project_id in _pcb_data:
        del _pcb_data[project_id]

    return {"message": "Project deleted"}


# ========== PCB 数据 ==========


@router.get("/{project_id}/pcb/design")
async def get_pcb_design(project_id: str):
    """获取 PCB 设计数据"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_id not in _pcb_data:
        raise HTTPException(status_code=404, detail="PCB data not found")

    return _pcb_data[project_id]


@router.get("/{project_id}/schematic")
async def get_schematic(project_id: str):
    """获取原理图数据"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_id not in _schematic_data:
        raise HTTPException(status_code=404, detail="Schematic data not found")

    return _schematic_data[project_id]


@router.post("/{project_id}/pcb/design")
async def save_pcb_design(project_id: str, pcb_data: PCBDataUpdate):
    """保存 PCB 设计数据"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_id not in _pcb_data:
        _pcb_data[project_id] = {}

    existing = _pcb_data[project_id]

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

    # 更新项目修改时间
    _projects[project_id]["updatedAt"] = datetime.now().isoformat()

    return {"message": "PCB data saved"}


# ========== PCB 元素操作 ==========


@router.post("/{project_id}/pcb/items/footprint")
async def create_footprint(project_id: str, footprint: Dict[str, Any]):
    """创建封装"""
    if project_id not in _pcb_data:
        raise HTTPException(status_code=404, detail="PCB data not found")

    footprint_id = footprint.get("id", f"fp-{uuid4()}")
    footprint["id"] = footprint_id

    _pcb_data[project_id]["footprints"].append(footprint)

    return {"success": True, "id": footprint_id}


@router.post("/{project_id}/pcb/items/track")
async def create_track(project_id: str, track: Dict[str, Any]):
    """创建走线"""
    if project_id not in _pcb_data:
        raise HTTPException(status_code=404, detail="PCB data not found")

    track_id = track.get("id", f"track-{uuid4()}")
    track["id"] = track_id

    _pcb_data[project_id]["tracks"].append(track)

    return {"success": True, "id": track_id}


@router.post("/{project_id}/pcb/items/via")
async def create_via(project_id: str, via: Dict[str, Any]):
    """创建过孔"""
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
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # 简化的 DRC 检查 - 实际应该调用 KiCad
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
    """导出 Gerber 文件"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # 简化的导出响应 - 实际应该调用 KiCad
    return {
        "success": True,
        "data": {"files": [f"{project_id}-F_Cu.gbr", f"{project_id}-B_Cu.gbr"]},
    }


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

    # 调试：打印获取到的数据
    import logging
    import traceback

    logger = logging.getLogger(__name__)

    # 强制刷新日志输出
    import sys

    print(f"DEBUG: BOM export called for {project_id}", file=sys.stderr)
    print(
        f"DEBUG: _schematic_data keys: {list(_schematic_data.keys())}", file=sys.stderr
    )

    logger.info(
        f"BOM export: project_id={project_id}, pcb_footprints={len(footprints)}, schematic components={len(components) if 'components' in dir() else 0}"
    )

    # 生成BOM CSV - 使用固定的输出目录
    output_dir = r"C:\KiCadWebEditor\output"
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

        print(f"DEBUG: Returning success for {project_id}", file=sys.stderr)
        return {
            "success": True,
            "file": output_path,
            "components": len(footprints),
            "files": [f"{project_id}-bom.csv"],
            "debug": f"output_path={output_path}, footprints={len(footprints)}",
        }
    except Exception as e:
        print(f"DEBUG: Exception in BOM export: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": str(e), "files": []}


@router.post("/{project_id}/export/step")
async def export_step(project_id: str):
    """导出 STEP 模型"""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"files": [f"{project_id}.step"]}

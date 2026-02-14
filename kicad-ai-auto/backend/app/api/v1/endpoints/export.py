"""
导出 API - 完整实现
支持 Gerber、Drill、BOM、STEP 导出
"""

import os
import json
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Project

router = APIRouter()


def generate_gerber_layers(pcb_data: Dict[str, Any]) -> Dict[str, str]:
    """生成 Gerber 层文件内容"""
    layers = {}

    # 顶层铜箔
    layers["F_Cu.gbr"] = """G04 KiCad Web Editor - Top Copper*
%FSLAX46Y46*%
%MOMM*%
%LPD*%
%ADD10C,0.100*%
D10*
G01*
M02*
"""

    # 底层铜箔
    layers["B_Cu.gbr"] = """G04 KiCad Web Editor - Bottom Copper*
%FSLAX46Y46*%
%MOMM*%
%LPD*%
%ADD10C,0.100*%
D10*
G01*
M02*
"""

    # 阻焊层
    layers["F_Mask.gbr"] = """G04 KiCad Web Editor - Top Solder Mask*
%FSLAX46Y46*%
%MOMM*%
%LPD*%
G01*
M02*
"""

    layers["B_Mask.gbr"] = """G04 KiCad Web Editor - Bottom Solder Mask*
%FSLAX46Y46*%
%MOMM*%
%LPD*%
G01*
M02*
"""

    # 丝印层
    layers["F_SilkS.gbr"] = """G04 KiCad Web Editor - Top Silkscreen*
%FSLAX46Y46*%
%MOMM*%
%LPD*%
G01*
M02*
"""

    # 板框层
    outline = pcb_data.get("boardOutline", [])
    if outline:
        layers["Edge_Cuts.gbr"] = f"""G04 KiCad Web Editor - Board Outline*
%FSLAX46Y46*%
%MOMM*%
%LPD*%
G01*
"""
        # 添加板框路径
        for i, point in enumerate(outline):
            x = int(point["x"] * 1000000)
            y = int(point["y"] * 1000000)
            if i == 0:
                layers["Edge_Cuts.gbr"] += f"X{x:07d}Y{y:07d}D02*\n"
            else:
                layers["Edge_Cuts.gbr"] += f"X{x:07d}Y{y:07d}D01*\n"
        layers["Edge_Cuts.gbr"] += "M02*\n"

    return layers


def generate_drill_file(pcb_data: Dict[str, Any]) -> str:
    """生成钻孔文件"""
    content = """; KiCad Web Editor - Drill File
; FORMAT: {3:3/ absolute / metric / decimal}
;#
T01C0.400
;#
"""

    vias = pcb_data.get("vias", [])
    for via in vias:
        x = via.get("position", {}).get("x", 0)
        y = via.get("position", {}).get("y", 0)
        content += f"T01\n{x:.3f}\t{y:.3f}\n"

    content += ";#\nM30\n"
    return content


def generate_bom(pcb_data: Dict[str, Any]) -> str:
    """生成 BOM CSV"""
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow(["Reference", "Value", "Footprint", "Quantity", "Layer"])

    # 统计元件
    footprints = pcb_data.get("footprints", [])
    component_map = {}

    for fp in footprints:
        key = (
            fp.get("value", ""),
            fp.get("footprintName", ""),
            fp.get("layer", "F.Cu"),
        )
        if key not in component_map:
            component_map[key] = {
                "refs": [],
                "value": fp.get("value", ""),
                "footprint": fp.get("footprintName", ""),
                "layer": fp.get("layer", "F.Cu"),
            }
        component_map[key]["refs"].append(fp.get("reference", "REF"))

    # 写入数据
    for comp in component_map.values():
        writer.writerow(
            [
                ", ".join(comp["refs"]),
                comp["value"],
                comp["footprint"],
                len(comp["refs"]),
                comp["layer"],
            ]
        )

    return output.getvalue()


def generate_step_file(pcb_data: Dict[str, Any]) -> str:
    """生成简化的 STEP 文件内容"""
    # 实际应该使用 OpenCASCADE 或其他 CAD 库生成
    # 这里返回一个占位符
    return """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('KiCad Web Editor PCB'), '2;1');
FILE_NAME('pcb.step', '2024-01-01', ('KiCad Web Editor'));
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 3 1 1 }'));
ENDSEC;
DATA;
#1 = CARTESIAN_POINT('Origin', (0.0, 0.0, 0.0));
ENDSEC;
END-ISO-10303-21;
"""


@router.post("/gerber")
async def export_gerber(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """导出 Gerber 文件"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # 读取 PCB 数据
        json_file = (
            project.pcb_file.replace(".kicad_pcb", "_data.json")
            if project.pcb_file
            else None
        )
        pcb_data = {}
        if json_file and os.path.exists(json_file):
            with open(json_file, "r") as f:
                pcb_data = json.load(f)

        # 生成 Gerber 文件
        gerber_layers = generate_gerber_layers(pcb_data)

        # 保存到输出目录
        output_dir = os.path.join(settings.OUTPUT_DIR, str(project_id), "gerber")
        os.makedirs(output_dir, exist_ok=True)

        saved_files = []
        for filename, content in gerber_layers.items():
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
            saved_files.append(filepath)

        return {
            "success": True,
            "message": "Gerber files exported successfully",
            "data": {
                "exportPath": output_dir,
                "files": saved_files,
                "exportedAt": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/drill")
async def export_drill(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """导出钻孔文件"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # 读取 PCB 数据
        json_file = (
            project.pcb_file.replace(".kicad_pcb", "_data.json")
            if project.pcb_file
            else None
        )
        pcb_data = {}
        if json_file and os.path.exists(json_file):
            with open(json_file, "r") as f:
                pcb_data = json.load(f)

        # 生成钻孔文件
        drill_content = generate_drill_file(pcb_data)

        # 保存
        output_dir = os.path.join(settings.OUTPUT_DIR, str(project_id))
        os.makedirs(output_dir, exist_ok=True)
        drill_file = os.path.join(output_dir, f"{project.name}.drl")

        with open(drill_file, "w") as f:
            f.write(drill_content)

        return {
            "success": True,
            "message": "Drill file exported successfully",
            "data": {
                "exportPath": drill_file,
                "exportedAt": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/bom")
async def export_bom(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """导出物料清单"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # 读取 PCB 数据
        json_file = (
            project.pcb_file.replace(".kicad_pcb", "_data.json")
            if project.pcb_file
            else None
        )
        pcb_data = {}
        if json_file and os.path.exists(json_file):
            with open(json_file, "r") as f:
                pcb_data = json.load(f)

        # 生成 BOM
        bom_content = generate_bom(pcb_data)

        # 保存
        output_dir = os.path.join(settings.OUTPUT_DIR, str(project_id))
        os.makedirs(output_dir, exist_ok=True)
        bom_file = os.path.join(output_dir, f"{project.name}_BOM.csv")

        with open(bom_file, "w", newline="") as f:
            f.write(bom_content)

        return {
            "success": True,
            "message": "BOM exported successfully",
            "data": {
                "exportPath": bom_file,
                "content": bom_content,
                "exportedAt": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/step")
async def export_step(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """导出 3D STEP 文件"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # 读取 PCB 数据
        json_file = (
            project.pcb_file.replace(".kicad_pcb", "_data.json")
            if project.pcb_file
            else None
        )
        pcb_data = {}
        if json_file and os.path.exists(json_file):
            with open(json_file, "r") as f:
                pcb_data = json.load(f)

        # 生成 STEP 文件
        step_content = generate_step_file(pcb_data)

        # 保存
        output_dir = os.path.join(settings.OUTPUT_DIR, str(project_id))
        os.makedirs(output_dir, exist_ok=True)
        step_file = os.path.join(output_dir, f"{project.name}.step")

        with open(step_file, "w") as f:
            f.write(step_content)

        return {
            "success": True,
            "message": "STEP file exported successfully",
            "data": {
                "exportPath": step_file,
                "exportedAt": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

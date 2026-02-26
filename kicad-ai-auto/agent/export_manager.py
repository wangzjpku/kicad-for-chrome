"""
Export Manager - Handle file exports with security validation
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 安全配置：允许的输出目录
DEFAULT_OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/output")
ALLOWED_OUTPUT_BASE = Path(DEFAULT_OUTPUT_DIR).resolve()


def _validate_output_path(output_dir: str) -> Path:
    """
    验证输出目录路径安全性

    Args:
        output_dir: 用户提供的输出目录

    Returns:
        验证后的安全路径

    Raises:
        ValueError: 如果路径不安全
    """
    # 规范化路径
    path = Path(output_dir).resolve()

    # 检查路径遍历
    if ".." in str(path):
        raise ValueError("Path traversal not allowed in output directory")

    # 确保路径在允许的基础目录内
    try:
        path.relative_to(ALLOWED_OUTPUT_BASE)
    except ValueError:
        raise ValueError(
            f"Output directory must be within {ALLOWED_OUTPUT_BASE}"
        )

    return path


class ExportManager:
    """导出管理器 - 带安全验证"""

    def __init__(self, kicad_controller):
        self.controller = kicad_controller
        self.export_jobs = {}

    async def export(
        self,
        format_type: str,
        output_dir: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        导出文件

        Args:
            format_type: 导出格式 (gerber, drill, bom, pickplace, pdf, svg, step)
            output_dir: 输出目录
            options: 导出选项

        Raises:
            ValueError: 如果输出目录路径不安全
        """
        options = options or {}

        # 验证输出目录路径
        try:
            safe_output_dir = _validate_output_path(output_dir)
        except ValueError as e:
            logger.error(f"Invalid output directory: {e}")
            return {"success": False, "error": str(e)}

        # 确保输出目录存在
        os.makedirs(safe_output_dir, exist_ok=True)

        if format_type == "gerber":
            return self.controller.export_gerber(str(safe_output_dir), options.get("layers"))
        elif format_type == "drill":
            return self.controller.export_drill(str(safe_output_dir))
        elif format_type == "bom":
            output_path = safe_output_dir / "bom.csv"
            return self.controller.export_bom(str(output_path))
        elif format_type == "pickplace":
            output_path = safe_output_dir / "pickplace.csv"
            return self.controller.export_pickplace(str(output_path))
        elif format_type == "pdf":
            output_path = safe_output_dir / "output.pdf"
            return self.controller.export_pdf(str(output_path))
        elif format_type == "svg":
            output_path = safe_output_dir / "output.svg"
            return self.controller.export_svg(str(output_path))
        elif format_type == "step":
            output_path = safe_output_dir / "board.step"
            return self.controller.export_step(str(output_path))
        else:
            return {"success": False, "error": f"Unknown export format: {format_type}"}

    async def export_all(self, output_dir: str) -> Dict[str, Any]:
        """导出所有生产文件"""
        # 验证输出目录路径
        try:
            safe_output_dir = _validate_output_path(output_dir)
        except ValueError as e:
            logger.error(f"Invalid output directory: {e}")
            return {"success": False, "error": str(e), "results": {}}

        results = {}

        formats = ["gerber", "drill", "bom", "pickplace"]

        for fmt in formats:
            try:
                result = await self.export(fmt, str(safe_output_dir))
                results[fmt] = result
            except Exception as e:
                logger.error(f"Failed to export {fmt}: {e}")
                results[fmt] = {"success": False, "error": str(e)}

        return {
            "success": all(r.get("success", False) for r in results.values()),
            "results": results,
        }

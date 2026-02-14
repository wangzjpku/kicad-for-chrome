"""
Export Manager - Handle file exports
"""

import os
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ExportManager:
    """导出管理器"""

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
        """
        options = options or {}

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        if format_type == "gerber":
            return self.controller.export_gerber(output_dir, options.get("layers"))
        elif format_type == "drill":
            return self.controller.export_drill(output_dir)
        elif format_type == "bom":
            output_path = os.path.join(output_dir, "bom.csv")
            return self.controller.export_bom(output_path)
        elif format_type == "pickplace":
            output_path = os.path.join(output_dir, "pickplace.csv")
            return self.controller.export_pickplace(output_path)
        elif format_type == "pdf":
            output_path = os.path.join(output_dir, "output.pdf")
            return self.controller.export_pdf(output_path)
        elif format_type == "svg":
            output_path = os.path.join(output_dir, "output.svg")
            return self.controller.export_svg(output_path)
        elif format_type == "step":
            output_path = os.path.join(output_dir, "board.step")
            return self.controller.export_step(output_path)
        else:
            return {"success": False, "error": f"Unknown export format: {format_type}"}

    async def export_all(self, output_dir: str) -> Dict[str, Any]:
        """导出所有生产文件"""
        results = {}

        formats = ["gerber", "drill", "bom", "pickplace"]

        for fmt in formats:
            try:
                result = await self.export(fmt, output_dir)
                results[fmt] = result
            except Exception as e:
                logger.error(f"Failed to export {fmt}: {e}")
                results[fmt] = {"success": False, "error": str(e)}

        return {
            "success": all(r.get("success", False) for r in results.values()),
            "results": results,
        }

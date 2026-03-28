"""
PCB 生成器 V1
封装现有的 kicad_pcb_generator.py
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from ..generators import PCBGeneratorBase, GenerationResult

logger = logging.getLogger(__name__)


class PCBGeneratorV1(PCBGeneratorBase):
    """
    PCB 生成器 V1

    使用现有的 kicad_pcb_generator.py
    """

    @property
    def version(self):
        from ..generators import GeneratorVersion

        return GeneratorVersion.V1

    def generate(self, schematic_path: str, output_path: str) -> GenerationResult:
        """
        从原理图生成 PCB

        Args:
            schematic_path: 原理图文件路径
            output_path: 输出文件路径

        Returns:
            GenerationResult: 生成结果
        """

        try:
            # 调用现有的 PCB 生成器
            from kicad_pcb_generator import create_pcb_from_json

            # 读取原理图 JSON
            # V1 需要先读取原理图 JSON
            json_path = schematic_path.replace(".kicad_sch", ".json")

            if not Path(json_path).exists():
                # 尝试其他可能的路径
                json_path = Path(schematic_path).parent / "schematic.json"

            if not Path(json_path).exists():
                return GenerationResult(
                    success=False,
                    output_path=output_path,
                    errors=[f"找不到原理图 JSON: {json_path}"],
                )

            success = create_pcb_from_json(str(json_path), output_path)

            if success:
                return GenerationResult(
                    success=True,
                    output_path=output_path,
                    metadata={"version": "v1", "source": "kicad_pcb_generator"},
                )
            else:
                return GenerationResult(
                    success=False, output_path=output_path, errors=["生成失败"]
                )

        except Exception as e:
            logger.error(f"V1 PCB 生成失败: {e}", exc_info=True)
            return GenerationResult(
                success=False, output_path=output_path, errors=[str(e)]
            )

    def validate(self, output_path: str) -> Dict[str, Any]:
        """
        验证生成结果

        V1 版本需要通过 KiCad CLI 进行 DRC 检查
        """
        return {"validated": False, "message": "V1 需要通过 KiCad CLI 进行 DRC 验证"}

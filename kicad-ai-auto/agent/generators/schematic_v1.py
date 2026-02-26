"""
原理图生成器 V1
封装现有的 kicad_schematic_generator.py
"""

import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generators import SchematicGeneratorBase, GenerationResult

logger = logging.getLogger(__name__)


class SchematicGeneratorV1(SchematicGeneratorBase):
    """
    原理图生成器 V1

    使用现有的 kicad_schematic_generator.py
    """

    @property
    def version(self):
        from generators import GeneratorVersion

        return GeneratorVersion.V1

    def generate(self, json_data: Dict[str, Any], output_path: str) -> GenerationResult:
        """
        生成 KiCad 原理图

        Args:
            json_data: 电路 JSON 数据
            output_path: 输出文件路径

        Returns:
            GenerationResult: 生成结果
        """

        try:
            # 1. 创建临时 JSON 文件
            # V1 生成器需要文件路径
            temp_json = Path(output_path).with_suffix(".json")

            with open(temp_json, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            # 2. 调用现有的生成器
            from kicad_schematic_generator import create_schematic_from_json

            success = create_schematic_from_json(str(temp_json), output_path)

            # 3. 清理临时文件
            temp_json.unlink(missing_ok=True)

            if success:
                return GenerationResult(
                    success=True,
                    output_path=output_path,
                    metadata={"version": "v1", "source": "kicad_schematic_generator"},
                )
            else:
                return GenerationResult(
                    success=False, output_path=output_path, errors=["生成失败"]
                )

        except Exception as e:
            logger.error(f"V1 生成失败: {e}", exc_info=True)
            return GenerationResult(
                success=False, output_path=output_path, errors=[str(e)]
            )

    def validate(self, output_path: str) -> Dict[str, Any]:
        """
        验证生成结果

        V1 版本不包含内置验证，需要通过 KiCad CLI
        """
        return {"validated": False, "message": "V1 需要通过 KiCad CLI 进行验证"}

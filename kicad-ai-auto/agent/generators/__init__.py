"""
生成器模块
提供原理图和PCB生成器的统一接口
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class GeneratorVersion(Enum):
    """生成器版本"""

    V1 = "v1"  # 现有版本
    V2 = "v2"  # kicad-sch-api 版本


@dataclass
class GenerationResult:
    """生成结果"""

    success: bool
    output_path: str
    errors: list = None
    warnings: list = None
    erc_result: dict = None
    metadata: dict = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class SchematicGeneratorBase:
    """原理图生成器基类"""

    @property
    def version(self) -> GeneratorVersion:
        """返回生成器版本"""
        raise NotImplementedError

    def generate(self, json_data: Dict[str, Any], output_path: str) -> GenerationResult:
        """生成原理图"""
        raise NotImplementedError

    def validate(self, output_path: str) -> Dict[str, Any]:
        """验证生成结果"""
        raise NotImplementedError


class PCBGeneratorBase:
    """PCB生成器基类"""

    @property
    def version(self) -> GeneratorVersion:
        """返回生成器版本"""
        raise NotImplementedError

    def generate(self, schematic_path: str, output_path: str) -> GenerationResult:
        """从原理图生成PCB"""
        raise NotImplementedError

    def validate(self, output_path: str) -> Dict[str, Any]:
        """验证生成结果"""
        raise NotImplementedError


# 导出
__all__ = [
    "GeneratorVersion",
    "GenerationResult",
    "SchematicGeneratorBase",
    "PCBGeneratorBase",
]

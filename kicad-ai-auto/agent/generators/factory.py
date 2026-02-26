"""
生成器工厂
根据版本获取合适的生成器
"""

import logging
import sys
import os
from typing import Optional

# 绝对导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generators import (
    GeneratorVersion,
    SchematicGeneratorBase,
    PCBGeneratorBase,
    GenerationResult,
)

logger = logging.getLogger(__name__)

# 缓存生成器实例
_schematic_generators = {}
_pcb_generators = {}


def get_schematic_generator(version: str = "v2", **kwargs) -> SchematicGeneratorBase:
    """
    获取原理图生成器

    Args:
        version: 版本 "v1" 或 "v2"
        **kwargs: 传递给生成器的额外参数

    Returns:
        SchematicGeneratorBase: 生成器实例
    """
    global _schematic_generators

    # 如果是 v2 但不可用，回退到 v1
    if version == "v2":
        try:
            from .schematic_v2 import SchematicGeneratorV2, is_v2_available

            if not is_v2_available():
                logger.warning("V2 不可用，回退到 V1")
                version = "v1"
        except ImportError:
            logger.warning("V2 导入失败，回退到 V1")
            version = "v1"

    # 返回缓存的实例或创建新实例
    if version not in _schematic_generators:
        if version == "v1":
            from .schematic_v1 import SchematicGeneratorV1

            _schematic_generators[version] = SchematicGeneratorV1()
        elif version == "v2":
            from .schematic_v2 import SchematicGeneratorV2

            _schematic_generators[version] = SchematicGeneratorV2(**kwargs)
        else:
            raise ValueError(f"未知版本: {version}")

    return _schematic_generators[version]


def get_pcb_generator(version: str = "v1", **kwargs) -> PCBGeneratorBase:
    """
    获取 PCB 生成器

    Args:
        version: 版本
        **kwargs: 传递给生成器的额外参数

    Returns:
        PCBGeneratorBase: 生成器实例
    """
    global _pcb_generators

    if version not in _pcb_generators:
        if version == "v1":
            from .pcb_v1 import PCBGeneratorV1

            _pcb_generators[version] = PCBGeneratorV1()
        else:
            raise ValueError(f"未知版本: {version}")

    return _pcb_generators[version]


def generate_schematic(
    json_data: dict, output_path: str, version: str = "v2", validate: bool = False
) -> GenerationResult:
    """
    生成原理图的便捷函数

    Args:
        json_data: 电路 JSON 数据
        output_path: 输出文件路径
        version: 生成器版本
        validate: 是否在生成后进行验证

    Returns:
        GenerationResult: 生成结果
    """
    generator = get_schematic_generator(version)
    result = generator.generate(json_data, output_path)

    # 可选的验证
    if validate and result.success:
        result.erc_result = generator.validate(output_path)

    return result


def clear_generator_cache():
    """清除生成器缓存"""
    global _schematic_generators, _pcb_generators
    _schematic_generators.clear()
    _pcb_generators.clear()
    logger.info("生成器缓存已清除")


# 导出
__all__ = [
    "get_schematic_generator",
    "get_pcb_generator",
    "generate_schematic",
    "clear_generator_cache",
]

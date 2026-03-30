"""
PCB Module - 多层板支持

Phase 4: 提供层叠管理、阻抗计算、串扰分析等功能
"""

from .layer_stackup import (
    StackupManager,
    LayerStackup,
    CopperLayer,
    DielectricLayer,
    DielectricMaterial,
    LayerType,
    PlaneType,
    ImpedanceProfile,
    create_2layer_stackup,
    create_4layer_stackup,
    create_6layer_stackup,
    get_recommended_stackup,
    calculate_crosstalk,
)

__all__ = [
    "StackupManager",
    "LayerStackup",
    "CopperLayer",
    "DielectricLayer",
    "DielectricMaterial",
    "LayerType",
    "PlaneType",
    "ImpedanceProfile",
    "create_2layer_stackup",
    "create_4layer_stackup",
    "create_6layer_stackup",
    "get_recommended_stackup",
    "calculate_crosstalk",
]

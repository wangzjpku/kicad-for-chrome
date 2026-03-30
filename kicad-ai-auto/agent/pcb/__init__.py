"""
PCB Module - 多层板支持

Phase 4: 提供层叠管理、阻抗计算、串扰分析、网络分类、电流计算等功能
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

# Phase 4: 网络分类和电流计算
from .net_classifier import (
    NetClassifier,
    NetInfo,
    NetClass,
    classify_nets,
)
from .current_calculator import (
    CurrentCalculator,
    calculate_trace_width,
    IPC2221_CALCULATOR,
)

__all__ = [
    # 层叠管理
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
    # Phase 4: 网络分类和电流计算
    "NetClassifier",
    "NetInfo",
    "NetClass",
    "classify_nets",
    "CurrentCalculator",
    "calculate_trace_width",
    "IPC2221_CALCULATOR",
]

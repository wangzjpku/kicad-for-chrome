"""
Phase 14: 高级分析集成

提供热仿真、EMC分析、信号完整性分析等功能
"""

from .thermal_simulator import (
    ThermalSimulator,
    ThermalHotspot,
    ThermalVia,
    ThermalSimulationResult,
    ComponentPower,
    CoolingMethod,
    create_thermal_simulator,
)

from .emc_analyzer import (
    EMCAnalyzer,
    EMCStandard,
    EMISeverity,
    EMIHotspot,
    CurrentLoop,
    FilterSuggestion,
    EMCAnalysisReport,
    create_emc_analyzer,
)

__all__ = [
    # 热仿真
    "ThermalSimulator",
    "ThermalHotspot",
    "ThermalVia",
    "ThermalSimulationResult",
    "ComponentPower",
    "CoolingMethod",
    "create_thermal_simulator",
    # EMC分析
    "EMCAnalyzer",
    "EMCStandard",
    "EMISeverity",
    "EMIHotspot",
    "CurrentLoop",
    "FilterSuggestion",
    "EMCAnalysisReport",
    "create_emc_analyzer",
]

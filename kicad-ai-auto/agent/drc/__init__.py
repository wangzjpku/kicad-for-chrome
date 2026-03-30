"""
Advanced DRC (Design Rule Check) Module

Phase 3: Extended DRC rules with 30+ checks
- Net class support
- Manufacturing constraints
- High-speed signal checks
- Differential pair validation
"""

from .advanced_drc import (
    AdvancedDRCEngine,
    DRCRule,
    NetClass,
    DRCViolation,
    DRCResult,
    RuleType,
    RuleSeverity,
    PCBComponent,
    PCBTrack,
    PCBVia,
    PCBPad,
    create_jlcpcb_drc,
    create_pcbway_drc,
)

__all__ = [
    "AdvancedDRCEngine",
    "DRCRule",
    "NetClass",
    "DRCViolation",
    "DRCResult",
    "RuleType",
    "RuleSeverity",
    "PCBComponent",
    "PCBTrack",
    "PCBVia",
    "PCBPad",
    "create_jlcpcb_drc",
    "create_pcbway_drc",
]

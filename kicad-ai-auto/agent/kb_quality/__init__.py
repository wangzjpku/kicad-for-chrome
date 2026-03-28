# -*- coding: utf-8 -*-
"""
知识库质量保障体系 (Knowledge Base Quality Assurance)

提供端到端的质量保障，保证从元件选型→原理图→网表→PCB的全链路正确性。

核心模块:
    models      - 数据模型定义
    validators  - 三层校验器
    cross_checker - KiCad库交叉验证
    quality_runner - CI质量门控
    reports     - 报告生成
    ad_parser   - Altium Designer原理图解析器
    jlc_parser  - 嘉立创EDA项目解析器
    lcsc_fetcher - LCSC API元件数据获取
    pcb_rules   - PCB制程规则
    circuit_rules - 电路连接规则知识库

使用示例:
    from kb_quality import run_quality_gate, validate_component

    # 运行全量质量检查
    report = run_quality_gate()
    print(report.summary())

    # 校验单个元件
    result = validate_component("STM32F103C8T6")
    print(result.severity)
"""

__version__ = "0.9.12"

from .models import (
    QualityMeta,
    PinEntry,
    ComponentValidationResult,
    QualityReport,
    Severity,
    ValidationType,
)
from .validators import ComponentValidator
from .cross_checker import CrossChecker
from .quality_runner import run_quality_gate, validate_component, run_quality_gate_cli
from .reports import QualityReporter, ReportFormat
from .circuit_rules import (
    ConnectionRuleEngine,
    ConnectionType,
    TopologyType,
    PinConnectionRule,
    CircuitPattern,
    get_connection_rule_engine,
    check_pin_compatibility,
    suggest_connections,
    POWER_CONNECTION_RULES,
    SIGNAL_CONNECTION_RULES,
    CIRCUIT_PATTERNS,
)

__all__ = [
    # models
    "QualityMeta",
    "PinEntry",
    "ComponentValidationResult",
    "QualityReport",
    "Severity",
    "ValidationType",
    # validators
    "ComponentValidator",
    # cross_checker
    "CrossChecker",
    # runner
    "run_quality_gate",
    "validate_component",
    "run_quality_gate_cli",
    # reporter
    "QualityReporter",
    "ReportFormat",
    # circuit_rules
    "ConnectionRuleEngine",
    "ConnectionType",
    "TopologyType",
    "PinConnectionRule",
    "CircuitPattern",
    "get_connection_rule_engine",
    "check_pin_compatibility",
    "suggest_connections",
    "POWER_CONNECTION_RULES",
    "SIGNAL_CONNECTION_RULES",
    "CIRCUIT_PATTERNS",
]

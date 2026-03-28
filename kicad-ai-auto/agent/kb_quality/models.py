# -*- coding: utf-8 -*-
"""
数据模型定义

定义知识库质量保障体系中用到的所有数据结构和枚举类型。
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class Severity(str, Enum):
    """问题严重等级"""

    P0 = "P0"  # 致命错误 - 阻止发布
    P1 = "P1"  # 严重错误 - 必须修复
    P2 = "P2"  # 一般错误 - 建议修复
    P3 = "P3"  # 提示信息 - 可选优化

    def __lt__(self, other):
        order = [Severity.P0, Severity.P1, Severity.P2, Severity.P3]
        return order.index(self) < order.index(other)


class ValidationType(str, Enum):
    """校验类型"""

    FORMAT = "format"                # Tier 1: 格式校验
    PIN_TYPE = "pin_type"           # Tier 2: 引脚类型校验
    CROSS_REF = "cross_ref"         # Tier 3: KiCad库交叉验证
    DATASHEET = "datasheet"         # datasheet URL 可访问性
    CONSISTENCY = "consistency"     # 数据一致性校验


class Source(str, Enum):
    """数据来源"""

    DATASHEET = "datasheet"
    LCSC = "lcsc"
    GITHUB = "github"
    KICAD_OFFICIAL = "kicad_official"
    INFERRED = "inferred"
    GERBERGPT = "gerbergpt"
    USER = "user"


class TrustLevel(int, Enum):
    """信任等级"""

    UNTRUSTED = 0   # 未验证
    LOW = 1         # 低信任
    MEDIUM = 2      # 中信任
    HIGH = 3         # 高信任（已人工核实）


@dataclass
class QualityMeta:
    """质量元数据"""

    source: str = Source.INFERRED.value
    source_url: str = ""
    verified: bool = False
    verified_by: str = ""
    verified_at: str = ""
    trust_level: int = TrustLevel.UNTRUSTED.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityMeta":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PinEntry:
    """元件引脚条目"""

    number: str
    name: str
    type: str  # power_in | output | input | bidirectional | passive | no_connect | unspecified
    description: str = ""
    datasheet_confirmed: bool = False

    # 交叉验证信息
    kicad_pin_number: Optional[str] = None
    kicad_pin_type: Optional[str] = None
    mismatch: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PinEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ValidationIssue:
    """单个校验问题"""

    severity: str
    validation_type: str
    code: str          # 唯一问题代码，如 "P0-MISSING-SYMBOL-LIB"
    message: str
    field: str = ""
    expected: str = ""
    actual: str = ""
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComponentValidationResult:
    """元件校验结果"""

    component_name: str
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)

    # 校验元数据
    validation_time: str = field(default_factory=lambda: datetime.now().isoformat())

    # KiCad 交叉验证详情
    symbol_exists: Optional[bool] = None
    footprint_exists: Optional[bool] = None
    pin_count_match: Optional[bool] = None
    pin_count_kb: Optional[int] = None
    pin_count_kicad: Optional[int] = None

    # datasheet 验证
    datasheet_url_accessible: Optional[bool] = None
    datasheet_url: str = ""

    def add_issue(self, severity: str, validation_type: str, code: str,
                  message: str, field: str = "", expected: str = "", actual: str = "",
                  suggestion: str = "") -> None:
        issue = ValidationIssue(
            severity=severity,
            validation_type=validation_type,
            code=code,
            message=message,
            field=field,
            expected=expected,
            actual=actual,
            suggestion=suggestion,
        )
        if severity == Severity.P0.value or severity == Severity.P1.value:
            self.issues.append(issue)
        elif severity == Severity.P2.value:
            self.warnings.append(issue)
        else:
            self.info.append(issue)

    @property
    def has_p0_errors(self) -> bool:
        return any(i.severity == Severity.P0.value for i in self.issues)

    @property
    def has_p1_errors(self) -> bool:
        return any(i.severity == Severity.P1.value for i in self.issues)

    @property
    def has_errors(self) -> bool:
        return len(self.issues) > 0

    @property
    def worst_severity(self) -> Optional[str]:
        if self.has_p0_errors:
            return Severity.P0.value
        if self.has_p1_errors:
            return Severity.P1.value
        if self.warnings:
            return Severity.P2.value
        if self.info:
            return Severity.P3.value
        return None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["has_p0_errors"] = self.has_p0_errors
        d["has_p1_errors"] = self.has_p1_errors
        d["has_errors"] = self.has_errors
        d["worst_severity"] = self.worst_severity
        return d


@dataclass
class QualityReport:
    """全量质量报告"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors_p0: int = 0
    errors_p1: int = 0
    warnings_p2: int = 0
    info_p3: int = 0

    component_results: List[Dict[str, Any]] = field(default_factory=list)
    summary_by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    summary_by_validation_type: Dict[str, Dict[str, int]] = field(default_factory=dict)

    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "0.9.12"

    def summary(self) -> str:
        return (
            f"Quality Report: {self.total} total, "
            f"{self.passed} passed, {self.failed} failed | "
            f"P0={self.errors_p0}, P1={self.errors_p1}, "
            f"P2={self.warnings_p2}, P3={self.info_p3}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

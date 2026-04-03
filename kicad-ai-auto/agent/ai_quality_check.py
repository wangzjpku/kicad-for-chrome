"""
AI生成质量检查工作流 - 集成所有质量检查功能

功能:
1. AI生成电路后自动进行质量检查
2. 检查芯片是否在知识库中
3. 检查必要电路是否完整
4. 检查Datasheet可用性
5. 检查供应链状态
6. 生成质量报告和改进建议
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class QualityStatus(Enum):
    """质量状态"""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass
class QualityCheckResult:
    """质量检查结果"""

    status: QualityStatus
    chip_name: str

    # 检查项
    in_knowledge_base: bool = False
    has_datasheet: bool = False
    has_footprint: bool = False
    has_required_circuits: bool = False
    has_alternatives: bool = False
    supply_available: bool = False

    # 元数据
    manufacturer: Optional[str] = None
    footprint: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

    # 建议
    suggestions: List[str] = field(default_factory=list)

    # 替代方案
    alternatives: List[str] = field(default_factory=list)


@dataclass
class DesignQualityReport:
    """设计质量报告"""

    overall_status: QualityStatus

    # 统计
    total_chips: int = 0
    chips_passed: int = 0
    chips_with_warnings: int = 0
    chips_failed: int = 0

    # 详细结果
    results: List[QualityCheckResult] = field(default_factory=list)

    # 汇总问题
    missing_knowledgebase: List[str] = field(default_factory=list)
    missing_datasheet: List[str] = field(default_factory=list)
    missing_footprint: List[str] = field(default_factory=list)
    missing_circuits: List[str] = field(default_factory=list)
    supply_issues: List[str] = field(default_factory=list)

    # 建议
    recommendations: List[str] = field(default_factory=list)


class AIGenerationQualityChecker:
    """AI生成质量检查器"""

    def __init__(self):
        """初始化检查器"""
        self.chip_validator = None
        self.supply_chain = None

    def _get_validator(self):
        """获取芯片验证器"""
        if self.chip_validator is None:
            from chip_quality_validator import get_validator

            self.chip_validator = get_validator()
        return self.chip_validator

    def _get_supply_chain(self):
        """获取供应链API"""
        if self.supply_chain is None:
            from supply_chain_api import get_supply_chain

            self.supply_chain = get_supply_chain()
        return self.supply_chain

    def check_chip(
        self, chip_name: str, used_circuits: Optional[List[str]] = None
    ) -> QualityCheckResult:
        """检查单个芯片"""
        if used_circuits is None:
            used_circuits = []

        validator = self._get_validator()

        # 获取芯片信息
        chip_info = validator.get_chip_info(chip_name)

        result = QualityCheckResult(status=QualityStatus.UNKNOWN, chip_name=chip_name)

        if chip_info:
            # 芯片在知识库中
            result.in_knowledge_base = True
            result.manufacturer = chip_info.get("manufacturer")
            result.footprint = chip_info.get("footprint")
            result.category = chip_info.get("category")
            result.description = chip_info.get("description")

            # 检查Datasheet
            if chip_info.get("datasheet_url"):
                result.has_datasheet = True
            else:
                result.suggestions.append(f"建议为 {chip_name} 添加Datasheet链接")

            # 检查封装
            if chip_info.get("footprint"):
                result.has_footprint = True
            else:
                result.suggestions.append(f"警告: {chip_name} 缺少封装定义")

            # 检查替代芯片
            if chip_info.get("alternative_chips"):
                result.has_alternatives = True
                result.alternatives = chip_info["alternative_chips"]

            # 检查必要电路
            category = chip_info.get("category")
            if category:
                rules = validator.quality_rules.get(category, {})
                required = rules.get("required_circuits", [])
                missing = [c for c in required if c not in used_circuits]
                if missing:
                    result.suggestions.append(
                        f"警告: {chip_name} 缺少必要电路: {', '.join(missing)}"
                    )
                else:
                    result.has_required_circuits = True
        else:
            # 芯片不在知识库中
            result.suggestions.append(f"错误: {chip_name} 不在知识库中")
            result.suggestions.append(f"建议: 从知识库选择已知芯片或添加新的芯片定义")

            # 尝试搜索相似芯片
            search_results = validator.search_chips(chip_name)
            if search_results:
                similar = [r["name"] for r in search_results[:3]]
                result.suggestions.append(f"可能您想找的是: {', '.join(similar)}")
                result.alternatives = similar

        # 检查供应链
        try:
            supply = self._get_supply_chain().check_availability(chip_name)
            result.supply_available = supply.get("available", False)
            if supply.get("warnings"):
                result.suggestions.extend(supply["warnings"])
        except Exception as e:
            logger.warning(f"供应链检查失败: {e}")

        # 确定状态
        if not result.in_knowledge_base:
            result.status = QualityStatus.FAIL
        elif not result.has_footprint:
            result.status = QualityStatus.FAIL
        elif not result.has_required_circuits:
            result.status = QualityStatus.WARNING
        elif not result.supply_available:
            result.status = QualityStatus.WARNING
        else:
            result.status = QualityStatus.PASS

        return result

    def check_design(self, components: List[Dict[str, Any]]) -> DesignQualityReport:
        """
        检查整个设计

        Args:
            components: 组件列表,每个包含 name, type, footprint, circuits 等

        Returns:
            设计质量报告
        """
        report = DesignQualityReport(overall_status=QualityStatus.PASS)

        for comp in components:
            chip_type = comp.get("type", comp.get("name", ""))
            if not chip_type:
                continue

            # 获取使用的电路
            circuits = comp.get("circuits", [])

            # 检查芯片
            result = self.check_chip(chip_type, circuits)
            report.results.append(result)

            # 统计
            report.total_chips += 1
            if result.status == QualityStatus.PASS:
                report.chips_passed += 1
            elif result.status == QualityStatus.WARNING:
                report.chips_with_warnings += 1
                report.overall_status = QualityStatus.WARNING
            elif result.status == QualityStatus.FAIL:
                report.chips_failed += 1
                report.overall_status = QualityStatus.FAIL

            # 收集问题
            if not result.in_knowledge_base:
                report.missing_knowledgebase.append(chip_type)
            if not result.has_datasheet:
                report.missing_datasheet.append(chip_type)
            if not result.has_footprint:
                report.missing_footprint.append(chip_type)
            if not result.has_required_circuits:
                report.missing_circuits.append(chip_type)
            if not result.supply_available:
                report.supply_issues.append(chip_type)

        # 生成建议
        if report.missing_knowledgebase:
            report.recommendations.append(
                f"有 {len(report.missing_knowledgebase)} 个芯片不在知识库中,需要添加"
            )
        if report.missing_footprint:
            report.recommendations.append(
                f"有 {len(report.missing_footprint)} 个芯片缺少封装定义"
            )
        if report.missing_circuits:
            report.recommendations.append(
                f"有 {len(report.missing_circuits)} 个芯片缺少必要电路"
            )
        if report.supply_issues:
            report.recommendations.append(
                f"有 {len(report.supply_issues)} 个芯片可能存在供货问题"
            )

        if report.overall_status == QualityStatus.PASS:
            report.recommendations.append("✅ 设计质量检查通过!")

        return report

    def validate_and_suggest(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证并提供改进建议

        Returns:
            验证结果和改进建议
        """
        report = self.check_design(components)

        # 格式化输出
        output = {
            "status": report.overall_status.value,
            "summary": {
                "total_chips": report.total_chips,
                "passed": report.chips_passed,
                "warnings": report.chips_with_warnings,
                "failed": report.chips_failed,
            },
            "issues": {
                "missing_knowledgebase": report.missing_knowledgebase,
                "missing_datasheet": report.missing_datasheet,
                "missing_footprint": report.missing_footprint,
                "missing_circuits": report.missing_circuits,
                "supply_issues": report.supply_issues,
            },
            "recommendations": report.recommendations,
            "detailed_results": [],
        }

        # 添加详细结果
        for result in report.results:
            output["detailed_results"].append(
                {
                    "chip": result.chip_name,
                    "status": result.status.value,
                    "manufacturer": result.manufacturer,
                    "footprint": result.footprint,
                    "category": result.category,
                    "in_knowledge_base": result.in_knowledge_base,
                    "has_datasheet": result.has_datasheet,
                    "has_footprint": result.has_footprint,
                    "has_required_circuits": result.has_required_circuits,
                    "supply_available": result.supply_available,
                    "alternatives": result.alternatives,
                    "suggestions": result.suggestions,
                }
            )

        return output


# 全局检查器
_checker: Optional[AIGenerationQualityChecker] = None


def get_quality_checker() -> AIGenerationQualityChecker:
    """获取质量检查器"""
    global _checker
    if _checker is None:
        _checker = AIGenerationQualityChecker()
    return _checker


def validate_ai_generation(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """验证AI生成的设计"""
    return get_quality_checker().validate_and_suggest(components)

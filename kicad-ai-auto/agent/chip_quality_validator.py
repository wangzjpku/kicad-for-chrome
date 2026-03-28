"""
芯片质量验证器 - 验证AI生成的电路是否符合质量标准

功能:
1. 验证芯片引脚完整性
2. 检查必要电路是否存在
3. 验证电源引脚
4. 检查封装可用性
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """质量等级"""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    INFO = "info"


@dataclass
class QualityIssue:
    """质量问题"""

    level: QualityLevel
    category: str
    message: str
    chip_name: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ChipQualityReport:
    """芯片质量报告"""

    chip_name: str
    overall_status: QualityLevel
    issues: List[QualityIssue] = field(default_factory=list)
    warnings: List[QualityIssue] = field(default_factory=list)
    info: List[QualityIssue] = field(default_factory=list)

    # 检查结果
    has_required_circuits: bool = False
    has_power_pins: bool = False
    has_valid_footprint: bool = False
    has_datasheet: bool = False
    has_alternatives: bool = False

    # 元数据
    manufacturer: Optional[str] = None
    footprint: Optional[str] = None
    category: Optional[str] = None

    def add_issue(self, issue: QualityIssue):
        """添加问题"""
        if issue.level == QualityLevel.FAIL:
            self.issues.append(issue)
        elif issue.level == QualityLevel.WARNING:
            self.warnings.append(issue)
        elif issue.level == QualityLevel.INFO:
            self.info.append(issue)

        # 更新总体状态
        if (
            issue.level == QualityLevel.FAIL
            and self.overall_status == QualityLevel.PASS
        ):
            self.overall_status = QualityLevel.WARNING


class ChipQualityValidator:
    """芯片质量验证器"""

    def __init__(self, db_path: Optional[Path] = None):
        """初始化验证器"""
        if db_path is None:
            db_path = (
                Path(__file__).parent / "component_knowledge" / "component_db.json"
            )

        self.db_path = db_path
        self.component_db: Dict[str, Any] = {}
        self.quality_rules: Dict[str, Any] = {}
        self.templates: Dict[str, Any] = {}
        self.categories: Dict[str, str] = {}
        self._load_database()

    def _load_database(self):
        """加载数据库"""
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.component_db = data.get("components", {})
                self.quality_rules = data.get("quality_check_rules", {})
                self.templates = data.get("templates", {})
                self.categories = data.get("categories", {})
                logger.info(f"已加载 {len(self.component_db)} 个芯片知识库")
        except Exception as e:
            logger.error(f"加载芯片数据库失败: {e}")
            self.component_db = {}

    def validate_chip(
        self, chip_name: str, used_circuits: Optional[List[str]] = None
    ) -> ChipQualityReport:
        """
        验证单个芯片的质量

        Args:
            chip_name: 芯片名称
            used_circuits: 已使用的电路模板列表

        Returns:
            质量报告
        """
        if used_circuits is None:
            used_circuits = []

        report = ChipQualityReport(
            chip_name=chip_name, overall_status=QualityLevel.PASS
        )

        # 检查芯片是否在知识库中
        if chip_name not in self.component_db:
            report.overall_status = QualityLevel.FAIL
            report.add_issue(
                QualityIssue(
                    level=QualityLevel.FAIL,
                    category="database",
                    message=f"芯片 '{chip_name}' 不在知识库中",
                    suggestion="请从知识库选择已知芯片，或添加新的芯片定义",
                )
            )
            return report

        chip_data = self.component_db[chip_name]

        # 1. 检查元数据
        report.manufacturer = chip_data.get("manufacturer")
        report.footprint = chip_data.get("footprint")
        report.category = chip_data.get("category")

        # 2. 检查Datasheet
        if chip_data.get("datasheet_url"):
            report.has_datasheet = True
        else:
            report.add_issue(
                QualityIssue(
                    level=QualityLevel.WARNING,
                    category="documentation",
                    message=f"芯片 '{chip_name}' 缺少Datasheet链接",
                    suggestion="建议添加官方datasheet链接以便查阅",
                )
            )

        # 3. 检查替代芯片
        if chip_data.get("alternative_chips"):
            report.has_alternatives = True
        else:
            report.add_issue(
                QualityIssue(
                    level=QualityLevel.INFO,
                    category="alternatives",
                    message=f"芯片 '{chip_name}' 缺少替代方案推荐",
                    suggestion="建议添加替代芯片以防供货问题",
                )
            )

        # 4. 检查电源引脚
        power_pins = chip_data.get("power_pins", [])
        if len(power_pins) >= 2:  # 至少需要VCC和GND
            report.has_power_pins = True
        else:
            report.overall_status = QualityLevel.FAIL
            report.add_issue(
                QualityIssue(
                    level=QualityLevel.FAIL,
                    category="power",
                    message=f"芯片 '{chip_name}' 电源引脚定义不完整",
                    suggestion="必须定义VCC和GND电源引脚",
                )
            )

        # 5. 检查封装
        if chip_data.get("footprint"):
            report.has_valid_footprint = True
        else:
            report.overall_status = QualityLevel.FAIL
            report.add_issue(
                QualityIssue(
                    level=QualityLevel.FAIL,
                    category="footprint",
                    message=f"芯片 '{chip_name}' 缺少封装定义",
                    suggestion="必须为芯片指定KiCad封装",
                )
            )

        # 6. 检查引脚定义
        pins = chip_data.get("pins", [])
        if not pins:
            report.add_issue(
                QualityIssue(
                    level=QualityLevel.WARNING,
                    category="pins",
                    message=f"芯片 '{chip_name}' 缺少引脚定义",
                    suggestion="建议添加完整引脚定义以便检查连接",
                )
            )

        # 7. 检查必要电路
        category = chip_data.get("category")
        if category and category in self.quality_rules:
            rules = self.quality_rules[category]
            required_circuits = rules.get("required_circuits", [])

            # 检查是否包含所有必要电路
            missing_circuits = [c for c in required_circuits if c not in used_circuits]

            if missing_circuits:
                report.overall_status = QualityLevel.FAIL
                for circ in missing_circuits:
                    report.add_issue(
                        QualityIssue(
                            level=QualityLevel.FAIL,
                            category="circuit",
                            message=f"芯片 '{chip_name}' 缺少必要电路: {circ}",
                            suggestion=f"需要添加 {circ} 电路模板",
                        )
                    )
            else:
                report.has_required_circuits = True

        return report

    def validate_design(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证整个设计

        Args:
            components: 组件列表, 每个包含 name, type, footprint 等

        Returns:
            验证结果汇总
        """
        results = {
            "overall_pass": True,
            "total_chips": 0,
            "chips_with_issues": 0,
            "chip_reports": [],
            "summary": {
                "missing_knowledgebase": [],
                "missing_datasheet": [],
                "missing_footprint": [],
                "missing_required_circuits": [],
                "recommendations": [],
            },
        }

        # 构建电路模板使用映射
        circuit_usage: Dict[str, List[str]] = {}  # chip_name -> [circuits]

        for comp in components:
            chip_type = comp.get("type", comp.get("name", ""))

            # 检查是否有关联的电路模板
            if "circuits" in comp:
                circuit_usage[chip_type] = comp.get("circuits", [])

        # 验证每个芯片
        for comp in components:
            chip_type = comp.get("type", comp.get("name", ""))
            if not chip_type:
                continue

            results["total_chips"] += 1

            # 获取该芯片使用的电路
            used_circuits = circuit_usage.get(chip_type, [])

            # 检查是否指定了需要的电路
            if chip_type in self.component_db:
                chip_data = self.component_db[chip_type]
                category = chip_data.get("category")
                if category in self.quality_rules:
                    required = self.quality_rules[category].get("required_circuits", [])
                    # 从模板名称推断电路
                    for template_name, template_data in self.templates.items():
                        if template_name in str(comp):
                            used_circuits.append(template_name)

            report = self.validate_chip(chip_type, used_circuits)
            results["chip_reports"].append(
                {
                    "chip": chip_type,
                    "status": report.overall_status.value,
                    "issues": [
                        {
                            "level": i.level.value,
                            "message": i.message,
                            "suggestion": i.suggestion,
                        }
                        for i in report.issues + report.warnings
                    ],
                }
            )

            # 收集问题
            if report.overall_status != QualityLevel.PASS:
                results["chips_with_issues"] += 1
                results["overall_pass"] = False

                # 分类汇总
                for issue in report.issues + report.warnings:
                    if issue.category == "database":
                        results["summary"]["missing_knowledgebase"].append(chip_type)
                    elif issue.category == "documentation":
                        results["summary"]["missing_datasheet"].append(chip_type)
                    elif issue.category == "footprint":
                        results["summary"]["missing_footprint"].append(chip_type)
                    elif issue.category == "circuit":
                        results["summary"]["missing_required_circuits"].append(
                            f"{chip_type}: {issue.message}"
                        )

        # 生成建议
        if results["summary"]["missing_knowledgebase"]:
            results["summary"]["recommendations"].append(
                f"有 {len(results['summary']['missing_knowledgebase'])} 个芯片不在知识库中, 建议添加"
            )
        if results["summary"]["missing_required_circuits"]:
            results["summary"]["recommendations"].append(
                f"有 {len(results['summary']['missing_required_circuits'])} 个芯片缺少必要电路, 可能导致工作异常"
            )

        return results

    def get_chip_info(self, chip_name: str) -> Optional[Dict[str, Any]]:
        """获取芯片信息"""
        return self.component_db.get(chip_name)

    def search_chips(
        self, keyword: str, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索芯片"""
        results = []
        keyword_lower = keyword.lower()

        for name, data in self.component_db.items():
            # 分类过滤
            if category and data.get("category") != category:
                continue

            # 关键词匹配
            if (
                keyword_lower in name.lower()
                or keyword_lower in data.get("description", "").lower()
                or keyword_lower in data.get("manufacturer", "").lower()
            ):
                results.append(
                    {
                        "name": name,
                        "description": data.get("description", ""),
                        "manufacturer": data.get("manufacturer", ""),
                        "category": data.get("category", ""),
                        "status": data.get("status", "unknown"),
                        "footprint": data.get("footprint", ""),
                        "datasheet_url": data.get("datasheet_url", ""),
                    }
                )

        return results

    def get_categories(self) -> Dict[str, str]:
        """获取所有分类"""
        return self.categories

    def get_all_chips(self, category: Optional[str] = None) -> List[str]:
        """获取所有芯片名称"""
        if category:
            return [
                name
                for name, data in self.component_db.items()
                if data.get("category") == category
            ]
        return list(self.component_db.keys())


# 全局验证器实例
_validator: Optional[ChipQualityValidator] = None


def get_validator() -> ChipQualityValidator:
    """获取验证器单例"""
    global _validator
    if _validator is None:
        _validator = ChipQualityValidator()
    return _validator


def validate_chip(
    chip_name: str, used_circuits: Optional[List[str]] = None
) -> ChipQualityReport:
    """验证单个芯片"""
    return get_validator().validate_chip(chip_name, used_circuits)


def validate_design(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """验证整个设计"""
    return get_validator().validate_design(components)


def get_chip_info(chip_name: str) -> Optional[Dict[str, Any]]:
    """获取芯片信息"""
    return get_validator().get_chip_info(chip_name)


def search_chips(keyword: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """搜索芯片"""
    return get_validator().search_chips(keyword, category)

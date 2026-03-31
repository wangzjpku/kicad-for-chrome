"""
Templates Package - 模板系统包

Phase 6: 项目模板系统
"""

from .template_data import (
    ProjectTemplate,
    TemplateCategory,
    TemplateSchematic,
    TemplatePCB,
    PREDEFINED_TEMPLATES,
    get_template_by_id,
    get_templates_by_category,
    search_templates,
)

from .template_manager import (
    TemplateManager,
    CustomTemplate,
    get_template_manager,
)

from .template_matcher import (
    TemplateMatcher,
    TemplateMatch,
    MatchResult,
)

from .template_validator import (
    TemplateValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
)

__all__ = [
    "ProjectTemplate",
    "TemplateCategory",
    "TemplateSchematic",
    "TemplatePCB",
    "PREDEFINED_TEMPLATES",
    "get_template_by_id",
    "get_templates_by_category",
    "search_templates",
    "TemplateManager",
    "CustomTemplate",
    "get_template_manager",
    "TemplateMatcher",
    "TemplateMatch",
    "MatchResult",
    "TemplateValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
]

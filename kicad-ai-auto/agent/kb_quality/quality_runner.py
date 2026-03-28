# -*- coding: utf-8 -*-
"""
CI 质量门控 - 质量检查执行器

用法:
    # Python API
    from kb_quality import run_quality_gate, validate_component
    report = run_quality_gate()
    print(report.summary())

    # CLI
    python -m kb_quality.quality_runner
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .models import (
    ComponentValidationResult,
    QualityReport,
    Severity,
)
from .validators import ComponentValidator
from .cross_checker import CrossChecker
from .reports import QualityReporter

logger = logging.getLogger(__name__)

# 知识库路径
KB_DIR = Path(__file__).parent.parent / "component_knowledge"
COMPONENT_DB_PATH = KB_DIR / "component_db.json"
QUALITY_REPORT_PATH = KB_DIR / "kb_quality_report.json"


def load_component_db() -> Dict[str, Any]:
    """加载元件数据库"""
    if not COMPONENT_DB_PATH.exists():
        raise FileNotFoundError(f"Component DB not found: {COMPONENT_DB_PATH}")

    with open(COMPONENT_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_component(
    name: str,
    *,
    check_datasheet: bool = False,
    cross_check: bool = True,
) -> ComponentValidationResult:
    """
    校验单个元件。

    Args:
        name: 元件名称
        check_datasheet: 是否检查 datasheet URL 可访问性
        cross_check: 是否进行 KiCad 库交叉验证

    Returns:
        ComponentValidationResult
    """
    db = load_component_db()
    components = db.get("components", {})
    comp = components.get(name)

    if comp is None:
        result = ComponentValidationResult(component_name=name)
        result.add_issue(
            Severity.P0, "format",
            code="P0-COMPONENT-NOT-FOUND",
            message=f"Component '{name}' not found in component_db.json",
            suggestion="Add the component or check the spelling",
        )
        return result

    validator = ComponentValidator()

    symbol_parser = None
    footprint_parser = None

    if cross_check:
        try:
            from symbol_lib_parser import get_symbol_parser
            symbol_parser = get_symbol_parser()
        except ImportError:
            logger.warning("symbol_lib_parser not available")

        try:
            from footprint_parser import get_footprint_parser
            footprint_parser = get_footprint_parser()
        except ImportError:
            logger.warning("footprint_parser not available")

    result = validator.validate(
        comp=comp,
        name=name,
        symbol_parser=symbol_parser,
        footprint_parser=footprint_parser,
        check_datasheet=check_datasheet,
        datasheet_timeout=5.0,
    )

    return result


def run_quality_gate(
    *,
    check_datasheet: bool = False,
    cross_check: bool = True,
    build_cache: bool = True,
    save_report: bool = True,
    component_filter: Optional[str] = None,
) -> QualityReport:
    """
    运行全量质量门控检查。

    Args:
        check_datasheet: 是否检查 datasheet URL 可访问性（较慢）
        cross_check: 是否进行 KiCad 库交叉验证
        build_cache: 是否构建符号/封装缓存
        save_report: 是否保存报告到磁盘
        component_filter: 可选，仅检查匹配此名称前缀的元件

    Returns:
        QualityReport
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting knowledge base quality gate...")

    # 加载数据库
    db = load_component_db()
    components = db.get("components", {})
    logger.info(f"Loaded {len(components)} components from component_db.json")

    # 构建交叉验证器
    cross_checker = CrossChecker()
    if build_cache and cross_check:
        logger.info("Building KiCad symbol/footprint caches...")
        try:
            cross_checker.build_symbol_cache()
            cross_checker.build_footprint_cache()
        except Exception as e:
            logger.warning(f"Failed to build caches: {e}")

    # 获取 parsers
    symbol_parser = None
    footprint_parser = None
    try:
        from symbol_lib_parser import get_symbol_parser
        symbol_parser = get_symbol_parser()
    except ImportError:
        pass

    try:
        from footprint_parser import get_footprint_parser
        footprint_parser = get_footprint_parser()
    except ImportError:
        pass

    validator = ComponentValidator()

    # 全量校验
    component_results: list = []
    category_stats: Dict[str, Dict[str, int]] = {}
    validation_stats: Dict[str, Dict[str, int]] = {}

    total = 0
    passed = 0
    failed = 0
    errors_p0 = 0
    errors_p1 = 0
    warnings_p2 = 0
    info_p3 = 0

    for name, comp in components.items():
        # 名称过滤
        if component_filter and not name.startswith(component_filter):
            continue

        total += 1
        result = validator.validate(
            comp=comp,
            name=name,
            symbol_parser=symbol_parser,
            footprint_parser=footprint_parser,
            check_datasheet=check_datasheet,
        )

        component_results.append(result.to_dict())

        # 统计
        cat = comp.get("category", "unknown")
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0, "errors": 0}

        category_stats[cat]["total"] += 1

        if result.has_errors:
            failed += 1
            category_stats[cat]["errors"] += 1
            errors_p0 += sum(1 for i in result.issues if i.severity == Severity.P0.value)
            errors_p1 += sum(1 for i in result.issues if i.severity == Severity.P1.value)
        else:
            passed += 1
            category_stats[cat]["passed"] += 1

        warnings_p2 += len(result.warnings)
        info_p3 += len(result.info)

        # 按验证类型统计
        for issue in result.issues:
            vtype = issue.validation_type
            if vtype not in validation_stats:
                validation_stats[vtype] = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
            if issue.severity in validation_stats[vtype]:
                validation_stats[vtype][issue.severity] += 1

    # 构建报告
    report = QualityReport(
        total=total,
        passed=passed,
        failed=failed,
        errors_p0=errors_p0,
        errors_p1=errors_p1,
        warnings_p2=warnings_p2,
        info_p3=info_p3,
        component_results=component_results,
        summary_by_category=category_stats,
        summary_by_validation_type=validation_stats,
    )

    logger.info(report.summary())

    # 保存报告
    if save_report:
        report_path = QUALITY_REPORT_PATH
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Quality report saved to {report_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    return report


def run_quality_gate_cli() -> None:
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="Knowledge Base Quality Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full quality gate (fast, no datasheet check)
  python -m kb_quality.quality_runner

  # Include datasheet URL checks (slower)
  python -m kb_quality.quality_runner --check-datasheet

  # Validate specific component
  python -m kb_quality.quality_runner --component STM32

  # Rebuild KiCad caches
  python -m kb_quality.quality_runner --rebuild-cache

  # Print detailed JSON report
  python -m kb_quality.quality_runner --json
        """,
    )
    parser.add_argument("--check-datasheet", action="store_true",
                        help="Check datasheet URL accessibility (slow)")
    parser.add_argument("--no-cross-check", action="store_true",
                        help="Skip KiCad library cross-validation")
    parser.add_argument("--rebuild-cache", action="store_true",
                        help="Force rebuild of symbol/footprint caches")
    parser.add_argument("--component", type=str,
                        help="Validate only components matching this name prefix")
    parser.add_argument("--json", action="store_true",
                        help="Output full JSON report")
    parser.add_argument("--save", action="store_true", default=True,
                        help="Save report to disk (default: True)")
    parser.add_argument("--no-save", dest="save", action="store_false",
                        help="Do not save report to disk")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 单个元件快速检查
    if args.component:
        result = validate_component(
            args.component,
            check_datasheet=args.check_datasheet,
            cross_check=not args.no_cross_check,
        )
        print(f"\n=== Validation Result for '{args.component}' ===")
        print(f"Worst Severity: {result.worst_severity or 'NONE'}")
        print(f"Issues: {len(result.issues)}")
        print(f"Warnings: {len(result.warnings)}")
        print(f"Info: {len(result.info)}")
        for issue in result.issues:
            print(f"  [{issue.severity}] {issue.code}: {issue.message}")
            if issue.suggestion:
                print(f"    → {issue.suggestion}")
        sys.exit(1 if result.has_errors else 0)

    # 全量质量门控
    report = run_quality_gate(
        check_datasheet=args.check_datasheet,
        cross_check=not args.no_cross_check,
        build_cache=args.rebuild_cache,
        save_report=args.save,
        component_filter=args.component,
    )

    # 控制台报告
    reporter = QualityReporter()
    reporter.print_summary(report)

    if args.json:
        reporter.print_full_report(report)

    # P0 错误 → 非零退出码
    sys.exit(1 if report.errors_p0 > 0 else 0)


if __name__ == "__main__":
    run_quality_gate_cli()

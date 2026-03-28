# -*- coding: utf-8 -*-
"""
质量报告生成器

支持多种输出格式：控制台、JSON、HTML、Markdown
"""

import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional

from .models import QualityReport, Severity


class ReportFormat(str, Enum):
    """报告格式"""

    CONSOLE = "console"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


class QualityReporter:
    """
    质量报告生成器。

    用法:
        reporter = QualityReporter()
        reporter.print_summary(report)
        reporter.save_html_report(report, "quality_report.html")
        reporter.save_markdown_report(report, "quality_report.md")
    """

    # ANSI 颜色码
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def print_summary(self, report: QualityReport) -> None:
        """打印简洁的质量摘要到控制台"""
        r = report
        total_w = 50

        print()
        print(self.BOLD + "═" * total_w + self.RESET)
        print(self.BOLD + f"{'知识库质量报告':^{total_w}}".center(total_w) + self.RESET)
        print(self.BOLD + "═" * total_w + self.RESET)
        print(f"  Total:  {r.total:<8}  Passed: {r.passed:<8}  Failed: {r.failed}")
        print()
        print(f"  {self.RED}P0 Errors:  {r.errors_p0:<6}{self.RESET}", end="")
        print(f"  {self.RED}P1 Errors:  {r.errors_p1:<6}{self.RESET}")
        print(f"  {self.YELLOW}P2 Warnings:{r.warnings_p2:<6}{self.RESET}", end="")
        print(f"  {self.BLUE}P3 Info:    {r.info_p3:<6}{self.RESET}")
        print()

        # 按类别统计
        if r.summary_by_category:
            print(f"  {self.BOLD}By Category:{self.RESET}")
            for cat, stats in sorted(r.summary_by_category.items()):
                err_rate = stats["errors"] / stats["total"] * 100 if stats["total"] > 0 else 0
                color = self.RED if err_rate > 50 else self.YELLOW if err_rate > 0 else self.GREEN
                status = f"{err_rate:5.1f}% errors"
                print(f"    {cat:<15} {stats['total']:>3} total, {stats['passed']:>3} ok  {color}{status}{self.RESET}")
            print()

        # 按验证类型统计
        if r.summary_by_validation_type:
            print(f"  {self.BOLD}By Validation Type:{self.RESET}")
            for vtype, stats in sorted(r.summary_by_validation_type.items()):
                p0 = stats.get("P0", 0)
                p1 = stats.get("P1", 0)
                p2 = stats.get("P2", 0)
                color = self.RED if p0 > 0 else self.YELLOW if p1 > 0 else self.GREEN
                print(f"    {vtype:<20} P0={p0} P1={p1} P2={p2}  {color}●{self.RESET}")
            print()

        # 门控结果
        gate_passed = r.errors_p0 == 0
        if gate_passed:
            print(f"  {self.GREEN}{self.BOLD}[PASS] Quality gate passed - No P0 errors{self.RESET}")
        else:
            print(f"  {self.RED}{self.BOLD}[FAIL] Quality gate failed - {r.errors_p0} P0 errors block release{self.RESET}")

        print(f"  Generated: {r.generated_at}")
        print("═" * total_w)

    def print_full_report(self, report: QualityReport) -> None:
        """打印完整 JSON 报告"""
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))

    def print_component_detail(self, result: Dict[str, Any]) -> None:
        """打印单个元件的详细问题"""
        name = result.get("component_name", "?")
        worst = result.get("worst_severity", "NONE")
        issues = result.get("issues", [])
        warnings = result.get("warnings", [])
        info = result.get("info", [])

        color = self._severity_color(worst)
        print(f"\n{self.BOLD}{color}  {name} [{worst}]{self.RESET}")

        for issue in issues:
            print(f"    {self.RED}✗ {issue['code']}: {issue['message']}{self.RESET}")
            if issue.get("suggestion"):
                print(f"      → {issue['suggestion']}")

        for w in warnings:
            print(f"    {self.YELLOW}⚠ {w['code']}: {w['message']}{self.RESET}")

        for i in info:
            print(f"    {self.BLUE}ℹ {i['code']}: {i['message']}{self.RESET}")

    def save_json_report(self, report: QualityReport, path: str) -> None:
        """保存 JSON 格式报告"""
        path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"JSON report saved: {path}")

    def save_markdown_report(self, report: QualityReport, path: str) -> None:
        """保存 Markdown 格式报告"""
        r = report
        lines = [
            "# 知识库质量报告",
            "",
            f"**生成时间**: {r.generated_at}",
            f"**版本**: {r.version}",
            "",
            "## 摘要",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总元件数 | {r.total} |",
            f"| 通过 | {r.passed} |",
            f"| 失败 | {r.failed} |",
            f"| P0 错误 | {r.errors_p0} |",
            f"| P1 错误 | {r.errors_p1} |",
            f"| P2 警告 | {r.warnings_p2} |",
            f"| P3 提示 | {r.info_p3} |",
            "",
            "## 按类别统计",
            "",
        ]

        if r.summary_by_category:
            lines.append("| 类别 | 总数 | 通过 | 错误 | 错误率 |")
            lines.append("|------|------|------|------|--------|")
            for cat, stats in sorted(r.summary_by_category.items()):
                err_rate = stats["errors"] / stats["total"] * 100 if stats["total"] > 0 else 0
                lines.append(
                    f"| {cat} | {stats['total']} | {stats['passed']} | {stats['errors']} | {err_rate:.1f}% |"
                )

        lines += [
            "",
            "## 按验证类型统计",
            "",
        ]

        if r.summary_by_validation_type:
            lines.append("| 验证类型 | P0 | P1 | P2 | P3 |")
            lines.append("|----------|----|----|----|----|")
            for vtype, stats in sorted(r.summary_by_validation_type.items()):
                lines.append(
                    f"| {vtype} | {stats.get('P0', 0)} | {stats.get('P1', 0)} | "
                    f"{stats.get('P2', 0)} | {stats.get('P3', 0)} |"
                )

        lines += [
            "",
            "## 门控结果",
            "",
            f"- **P0 错误数**: {r.errors_p0}  {'✅ 无 P0 错误，通过门控' if r.errors_p0 == 0 else '❌ 存在 P0 错误，阻止发布'}",
            "",
            "## 详细问题列表",
            "",
        ]

        for comp_result in r.component_results:
            if comp_result.get("has_errors"):
                lines.append(f"### {comp_result['component_name']} ({comp_result['worst_severity']})")
                lines.append("")
                for issue in comp_result.get("issues", []):
                    lines.append(
                        f"- **[{issue['severity']}] {issue['code']}**: {issue['message']}"
                    )
                    if issue.get("suggestion"):
                        lines.append(f"  - → {issue['suggestion']}")
                lines.append("")

        path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Markdown report saved: {path}")

    def save_html_report(self, report: QualityReport, path: str) -> None:
        """保存 HTML 格式报告"""
        r = report
        status_color = "#22c55e" if r.errors_p0 == 0 else "#ef4444"
        status_text = "PASS" if r.errors_p0 == 0 else "FAIL"

        cat_rows = ""
        if r.summary_by_category:
            for cat, stats in sorted(r.summary_by_category.items()):
                err_rate = stats["errors"] / stats["total"] * 100 if stats["total"] > 0 else 0
                color = "#ef4444" if err_rate > 50 else "#f59e0b" if err_rate > 0 else "#22c55e"
                cat_rows += f"<tr><td>{cat}</td><td>{stats['total']}</td>"
                cat_rows += f"<td>{stats['passed']}</td><td>{stats['errors']}</td>"
                cat_rows += f"<td style='color:{color}'>{err_rate:.1f}%</td></tr>"

        vtype_rows = ""
        if r.summary_by_validation_type:
            for vtype, stats in sorted(r.summary_by_validation_type.items()):
                p0 = stats.get("P0", 0)
                p1 = stats.get("P1", 0)
                color = "#ef4444" if p0 > 0 else "#f59e0b" if p1 > 0 else "#22c55e"
                vtype_rows += f"<tr><td>{vtype}</td>"
                vtype_rows += f"<td style='color:{"#ef4444" if p0>0 else ""}'>{p0}</td>"
                vtype_rows += f"<td style='color:{"#f59e0b" if p1>0 else ""}'>{p1}</td>"
                vtype_rows += f"<td>{stats.get("P2", 0)}</td>"
                vtype_rows += f"<td>{stats.get("P3", 0)}</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>知识库质量报告</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 40px; background: #f9fafb; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
  .badge {{ padding: 8px 24px; border-radius: 8px; color: white; font-weight: bold; font-size: 18px; background: {status_color}; }}
  .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .card-label {{ font-size: 14px; color: #6b7280; }}
  .card-value {{ font-size: 28px; font-weight: bold; }}
  .card.p0 .card-value {{ color: #ef4444; }}
  .card.p1 .card-value {{ color: #f97316; }}
  .card.p2 .card-value {{ color: #f59e0b; }}
  .card-value.ok {{ color: #22c55e; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }}
  th {{ background: #f3f4f6; padding: 12px 16px; text-align: left; font-weight: 600; }}
  td {{ padding: 10px 16px; border-top: 1px solid #f3f4f6; }}
  tr:hover {{ background: #f9fafb; }}
  .error-row {{ background: #fef2f2 !important; }}
  h2 {{ margin: 32px 0 16px; font-size: 18px; color: #374151; }}
  .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 40px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🧪 知识库质量报告</h1>
    <span class="badge">{status_text}</span>
  </div>

  <div class="summary">
    <div class="card">
      <div class="card-label">Total</div>
      <div class="card-value">{r.total}</div>
    </div>
    <div class="card">
      <div class="card-label">Passed</div>
      <div class="card-value ok">{r.passed}</div>
    </div>
    <div class="card">
      <div class="card-label">Failed</div>
      <div class="card-value" style="color:{'#ef4444' if r.failed>0 else '#22c55e'}">{r.failed}</div>
    </div>
    <div class="card">
      <div class="card-label">Pass Rate</div>
      <div class="card-value ok">{r.passed/r.total*100:.1f}%</div>
    </div>
  </div>

  <div class="summary">
    <div class="card p0">
      <div class="card-label">P0 Errors</div>
      <div class="card-value">{r.errors_p0}</div>
    </div>
    <div class="card p1">
      <div class="card-label">P1 Errors</div>
      <div class="card-value">{r.errors_p1}</div>
    </div>
    <div class="card p2">
      <div class="card-label">Warnings</div>
      <div class="card-value">{r.warnings_p2}</div>
    </div>
    <div class="card">
      <div class="card-label">Info</div>
      <div class="card-value">{r.info_p3}</div>
    </div>
  </div>

  <h2>📊 By Category</h2>
  <table>
    <thead><tr><th>Category</th><th>Total</th><th>Passed</th><th>Errors</th><th>Error Rate</th></tr></thead>
    <tbody>{cat_rows}</tbody>
  </table>

  <h2>🔍 By Validation Type</h2>
  <table>
    <thead><tr><th>Validation</th><th>P0</th><th>P1</th><th>P2</th><th>P3</th></tr></thead>
    <tbody>{vtype_rows}</tbody>
  </table>

  <div class="footer">
    Generated: {r.generated_at} | kb_quality v{r.version}
  </div>
</div>
</body>
</html>"""

        path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML report saved: {path}")

    def _severity_color(self, severity: Optional[str]) -> str:
        if severity == Severity.P0.value:
            return self.RED
        elif severity == Severity.P1.value:
            return self.RED
        elif severity == Severity.P2.value:
            return self.YELLOW
        elif severity == Severity.P3.value:
            return self.BLUE
        return self.GREEN

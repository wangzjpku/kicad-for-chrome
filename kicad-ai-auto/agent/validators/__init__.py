"""
验证器模块
提供 ERC/DRC 验证功能
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _validate_file_path(file_path: str) -> Path:
    """
    验证文件路径安全性

    Args:
        file_path: 要验证的文件路径

    Returns:
        验证后的 Path 对象

    Raises:
        ValueError: 如果路径不安全或文件不存在
    """
    path = Path(file_path).resolve()

    # 检查路径遍历
    if ".." in str(path):
        raise ValueError("Path traversal not allowed in file path")

    # 检查文件是否存在
    if not path.exists():
        raise ValueError(f"File not found: {path}")

    # 检查是否为文件（非目录）
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # 检查路径中的字符是否安全（防止命令注入）
    # 允许字母、数字、下划线、连字符、点、斜杠、反斜杠、冒号（Windows盘符）、空格
    if not re.match(r'^[a-zA-Z0-9_\-./\\:\s]+$', str(path)):
        raise ValueError("File path contains invalid characters")

    return path


class ERCValidator:
    """
    ERC (Electrical Rules Check) 验证器

    支持两种验证方式:
    1. kicad-sch-api 内置验证 (推荐)
    2. KiCad CLI 验证
    """

    def __init__(self, kicad_cli_path: Optional[str] = None):
        """
        初始化 ERC 验证器

        Args:
            kicad_cli_path: KiCad CLI 路径
        """
        self.kicad_cli_path = kicad_cli_path or self._find_kicad_cli()

        # 检查 kicad-sch-api 是否可用
        self._sch_api_available = False
        try:
            import kicad_sch_api as ksa
            from kicad_sch_api.validation import ElectricalRulesChecker

            self._sch_api_available = True
            self._ksa = ksa
            self._ERC = ElectricalRulesChecker
        except ImportError:
            logger.warning("kicad-sch-api 未安装，将使用 CLI 验证")

    def _find_kicad_cli(self) -> Optional[str]:
        """查找 KiCad CLI"""
        import os

        # 常见路径
        possible_paths = [
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            r"E:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            r"E:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            "kicad-cli",  # PATH 中的
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        return None

    def validate(self, schematic_path: str) -> Dict[str, Any]:
        """
        验证原理图

        Args:
            schematic_path: 原理图文件路径

        Returns:
            验证结果字典
        """
        # 优先使用 kicad-sch-api
        if self._sch_api_available:
            return self._validate_with_sch_api(schematic_path)
        else:
            return self._validate_with_cli(schematic_path)

    def _validate_with_sch_api(self, schematic_path: str) -> Dict[str, Any]:
        """使用 kicad-sch-api 验证"""
        try:
            sch = self._ksa.load_schematic(schematic_path)
            erc = self._ERC(sch)
            result = erc.run_all_checks()

            return {
                "method": "kicad-sch-api",
                "has_errors": result.has_errors(),
                "has_warnings": result.has_warnings(),
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "errors": [
                    {"type": e.error_type, "message": e.message, "severity": "error"}
                    for e in result.errors
                ],
                "warnings": [
                    {"type": w.error_type, "message": w.message, "severity": "warning"}
                    for w in result.warnings
                ],
                "summary": result.summary() if result.has_errors() else "Pass",
            }

        except Exception as e:
            logger.error(f"kicad-sch-api 验证失败: {e}")
            # 回退到 CLI
            return self._validate_with_cli(schematic_path)

    def _validate_with_cli(self, schematic_path: str) -> Dict[str, Any]:
        """使用 KiCad CLI 验证"""
        if not self.kicad_cli_path:
            return {"error": "KiCad CLI 未找到", "method": "none"}

        try:
            # 验证输入路径安全性
            try:
                safe_path = _validate_file_path(schematic_path)
            except ValueError as e:
                return {"error": f"Invalid schematic path: {e}", "method": "cli"}

            # 生成 ERC JSON 报告
            output_json = safe_path.with_suffix("-erc.json")

            result = subprocess.run(
                [
                    self.kicad_cli_path,
                    "sch",
                    "export",
                    "erc-json",
                    str(safe_path),
                    "-o",
                    str(output_json),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": result.stderr, "method": "cli"}

            # 读取 ERC 结果
            if output_json.exists():
                with open(output_json, "r", encoding="utf-8") as f:
                    erc_data = json.load(f)

                # 解析 violations
                violations = []
                for sheet in erc_data.get("sheets", []):
                    for v in sheet.get("violations", []):
                        violations.append(
                            {
                                "type": v.get("type", ""),
                                "message": v.get("description", ""),
                                "severity": v.get("severity", "error"),
                            }
                        )

                errors = [v for v in violations if v["severity"] == "error"]
                warnings = [v for v in violations if v["severity"] == "warning"]

                return {
                    "method": "cli",
                    "has_errors": len(errors) > 0,
                    "has_warnings": len(warnings) > 0,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "errors": errors,
                    "warnings": warnings,
                    "summary": f"{len(errors)} errors, {len(warnings)} warnings"
                    if errors
                    else "Pass",
                }
            else:
                return {"error": "ERC 报告未生成", "method": "cli"}

        except subprocess.TimeoutExpired:
            return {"error": "ERC 验证超时", "method": "cli"}
        except Exception as e:
            return {"error": str(e), "method": "cli"}


class DRCValidator:
    """
    DRC (Design Rules Check) 验证器

    使用 KiCad CLI 进行验证
    """

    def __init__(self, kicad_cli_path: Optional[str] = None):
        """初始化 DRC 验证器"""
        self.kicad_cli_path = kicad_cli_path or self._find_kicad_cli()

    def _find_kicad_cli(self) -> Optional[str]:
        """查找 KiCad CLI"""
        possible_paths = [
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            r"E:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            r"E:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
            "kicad-cli",
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        return None

    def validate(self, pcb_path: str) -> Dict[str, Any]:
        """
        验证 PCB

        Args:
            pcb_path: PCB 文件路径

        Returns:
            验证结果字典
        """
        if not self.kicad_cli_path:
            return {"error": "KiCad CLI 未找到", "method": "none"}

        try:
            # 验证输入路径安全性
            try:
                safe_path = _validate_file_path(pcb_path)
            except ValueError as e:
                return {"error": f"Invalid PCB path: {e}", "method": "cli"}

            # 生成 DRC JSON 报告
            output_json = safe_path.with_suffix("-drc.json")

            result = subprocess.run(
                [
                    self.kicad_cli_path,
                    "pcb",
                    "drc",
                    str(safe_path),
                    "--json",
                    "-o",
                    str(output_json),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {"error": result.stderr, "method": "cli"}

            # 读取 DRC 结果
            if output_json.exists():
                with open(output_json, "r", encoding="utf-8") as f:
                    drc_data = json.load(f)

                return {
                    "method": "cli",
                    "has_errors": drc_data.get("error_count", 0) > 0,
                    "has_warnings": drc_data.get("warning_count", 0) > 0,
                    "error_count": drc_data.get("error_count", 0),
                    "warning_count": drc_data.get("warning_count", 0),
                    "summary": drc_data.get("summary", ""),
                }
            else:
                return {"error": "DRC 报告未生成", "method": "cli"}

        except subprocess.TimeoutExpired:
            return {"error": "DRC 验证超时", "method": "cli"}
        except Exception as e:
            return {"error": str(e), "method": "cli"}


# 便捷函数
def validate_schematic(schematic_path: str, **kwargs) -> Dict[str, Any]:
    """验证原理图的便捷函数"""
    validator = ERCValidator(**kwargs)
    return validator.validate(schematic_path)


def validate_pcb(pcb_path: str, **kwargs) -> Dict[str, Any]:
    """验证 PCB 的便捷函数"""
    validator = DRCValidator(**kwargs)
    return validator.validate(pcb_path)


__all__ = [
    "ERCValidator",
    "DRCValidator",
    "validate_schematic",
    "validate_pcb",
]

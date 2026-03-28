# -*- coding: utf-8 -*-
"""
三层校验器

Tier 1 - 格式校验 (validate_format):
    - JSON Schema 结构检查
    - 必填字段存在性
    - 引脚数合理性 (1-500)
    - footprint 格式标准化
    - symbol_library 格式检查

Tier 2 - 引脚类型校验 (validate_pin_types):
    - VCC/VDD/VIN → power_in
    - GND/VSS/VSSA → power_in
    - RX/TX/D+/D- → bidirectional
    - NC → no_connect
    - 未标记类型警告

Tier 3 - KiCad 库交叉验证 (validate_cross_ref):
    - symbol_library 在 KiCad 库中存在
    - footprint 在 KiCad 封装库中存在
    - symbol 引脚数 == component_db 引脚数
    - 引脚类型一致性
"""

import re
import logging
import requests
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urlparse

from .models import (
    ComponentValidationResult,
    Severity,
    ValidationType,
)

logger = logging.getLogger(__name__)

# 预编译正则表达式以提高性能
_SYMBOL_LIB_PATTERN = re.compile(r"^[A-Za-z0-9_:\-]+$")

# KiCad 合法引脚类型
VALID_PIN_TYPES: Set[str] = {
    "input", "output", "bidirectional", "passive",
    "power_in", "power_out", "no_connect", "unspecified",
    "tri_state", "open_collector", "open_emitter",
    "free", "NC", "connector", "pushed", "mechanical",
}

# 引脚类型推断规则: name 模式 → type
PIN_TYPE_INFERENCE_RULES: List[tuple] = [
    # Power pins
    (r"^(VCC|VDD|VIN|VIO|VDDA|VCC_|_P)$", "power_in"),
    (r"^(GND|VSS|VSSA|VEE|VSS_|_N)$", "power_in"),
    (r"^(VBAT|VBAT_)$", "power_in"),
    (r"^(AVDD|AVCC)$", "power_in"),
    # USB differential
    (r"^(D\+|DP|USB_DP)$", "bidirectional"),
    (r"^(D\-|DM|USB_DM)$", "bidirectional"),
    # UART
    (r"^(RX|RXD|RX0|RX1|TX|TXD|TX0|TX1)$", "bidirectional"),
    # Communication
    (r"^(SDA|SDL|SCL|MOSI|MISO|SCK|NSS|CS|SCLK)$", "bidirectional"),
    # No connect
    (r"^NC$", "no_connect"),
    # Output
    (r"^(PWM|OUT|LED|Buzz|BUZZ)$", "output"),
    # Input
    (r"^(KEY|BTN|SW|RST|NRST|EN|boot|boot0)$", "input"),
]

# footprint 标准化映射
FOOTPRINT_ALIASES: Dict[str, str] = {
    "QFN": "QFN",
    "TSSOP": "TSSOP",
    "SOP": "SOIC",
    "DIP": "DIP",
    "SOT-23": "SOT-23",
    "SOT23": "SOT-23",
    "0805": "0805",
    "0603": "0603",
    "0402": "0402",
    "1206": "1206",
    "BGA": "BGA",
}


class ComponentValidator:
    """三层校验器"""

    def __init__(self):
        self._kicad_libs: Optional[Set[str]] = None
        self._kicad_footprints: Optional[Set[str]] = None
        self._kicad_symbol_pins: Optional[Dict[str, Dict[str, int]]] = None  # lib.symbol -> pin_count

    # ─── Tier 1: 格式校验 ───────────────────────────────────────

    def validate_format(self, comp: Dict[str, Any], name: str) -> ComponentValidationResult:
        """Tier 1: 格式校验"""
        result = ComponentValidationResult(component_name=name)

        # 必填字段检查
        required_fields = ["category", "symbol_library"]
        for field in required_fields:
            if field not in comp or not comp[field]:
                result.add_issue(
                    Severity.P0, ValidationType.FORMAT,
                    code=f"P0-MISSING-{field.upper()}",
                    message=f"Missing required field: {field}",
                    field=field,
                    suggestion=f"Add {field} to component {name}",
                )

        # 名称合理性
        if not name or not name.strip():
            result.add_issue(Severity.P0, ValidationType.FORMAT,
                             code="P0-INVALID-NAME", message="Component name is empty")

        # 引脚数合理性
        pins = comp.get("pins", [])
        if pins is None:
            result.add_issue(Severity.P0, ValidationType.FORMAT,
                             code="P0-NULL-PINS", message="pins field is null",
                             field="pins")
        elif not isinstance(pins, list):
            result.add_issue(Severity.P0, ValidationType.FORMAT,
                             code="P0-PINS-NOT-LIST", message="pins must be a list",
                             field="pins", actual=type(pins).__name__)
        elif len(pins) == 0:
            result.add_issue(Severity.P1, ValidationType.FORMAT,
                             code="P1-ZERO-PINS", message="Component has 0 pins",
                             field="pins", suggestion="Add pin definitions from datasheet")
        elif len(pins) > 500:
            result.add_issue(Severity.P1, ValidationType.FORMAT,
                             code="P1-TOO-MANY-PINS", message=f"Pin count {len(pins)} exceeds maximum (500)",
                             field="pins", actual=str(len(pins)))

        # symbol_library 格式检查
        symbol_lib = comp.get("symbol_library", "")
        if symbol_lib:
            if not _SYMBOL_LIB_PATTERN.match(symbol_lib):
                result.add_issue(
                    Severity.P2, ValidationType.FORMAT,
                    code="P2-INVALID-SYMBOL-LIB",
                    message=f"Invalid symbol_library format: {symbol_lib}",
                    field="symbol_library", actual=symbol_lib,
                    suggestion="Use format 'Library:Symbol' (e.g., MCU_ST:STM32F103)",
                )

        # footprint 格式检查
        footprint = comp.get("footprint", "")
        if footprint:
            # KiCad 标准格式: Package_Type:Footprint_Name
            if ":" not in footprint and not footprint.startswith("Package_"):
                result.add_issue(
                    Severity.P2, ValidationType.FORMAT,
                    code="P2-NON-STANDARD-FOOTPRINT",
                    message=f"Footprint may not be in KiCad standard format: {footprint}",
                    field="footprint", actual=footprint,
                    suggestion="Use KiCad format 'Library:Footprint' (e.g., Package_QFP:LQFP-48)",
                )

        # 引脚编号连续性检查
        pin_numbers = []
        for pin in pins:
            if isinstance(pin, dict) and "number" in pin:
                pin_numbers.append(str(pin["number"]))

        if pin_numbers:
            # 检查是否有重复引脚编号
            seen: Set[str] = set()
            for pn in pin_numbers:
                if pn in seen:
                    result.add_issue(
                        Severity.P1, ValidationType.FORMAT,
                        code="P1-DUPLICATE-PIN-NUMBER",
                        message=f"Duplicate pin number: {pn}",
                        field="pins", actual=pn,
                    )
                seen.add(pn)

        return result

    # ─── Tier 2: 引脚类型校验 ───────────────────────────────────

    def validate_pin_types(self, comp: Dict[str, Any], name: str) -> ComponentValidationResult:
        """Tier 2: 引脚类型校验"""
        result = ComponentValidationResult(component_name=name)
        pins = comp.get("pins", [])

        if not isinstance(pins, list):
            return result

        for pin in pins:
            if not isinstance(pin, dict):
                result.add_issue(
                    Severity.P1, ValidationType.PIN_TYPE,
                    code="P1-INVALID-PIN-STRUCT",
                    message="Pin entry is not a dict",
                    field="pins",
                )
                continue

            pin_name = pin.get("name", "")
            pin_type = pin.get("type", "")
            pin_num = pin.get("number", "?")

            if not pin_type:
                # 尝试推断类型
                inferred = self._infer_pin_type(pin_name)
                if inferred:
                    result.add_issue(
                        Severity.P3, ValidationType.PIN_TYPE,
                        code="P3-MISSING-PIN-TYPE",
                        message=f"Pin {pin_num} ({pin_name}): type missing, inferred as '{inferred}'",
                        field=f"pins[{pin_num}].type",
                        suggestion=f"Confirm pin {pin_num} type from datasheet",
                    )
                else:
                    result.add_issue(
                        Severity.P2, ValidationType.PIN_TYPE,
                        code="P2-UNKNOWN-PIN-TYPE",
                        message=f"Pin {pin_num} ({pin_name}): unknown type for '{pin_name}'",
                        field=f"pins[{pin_num}].type",
                        suggestion="Verify pin function from datasheet",
                    )
                continue

            # 验证类型是否合法
            if pin_type.lower() not in VALID_PIN_TYPES and pin_type not in VALID_PIN_TYPES:
                result.add_issue(
                    Severity.P2, ValidationType.PIN_TYPE,
                    code="P2-INVALID-PIN-TYPE",
                    message=f"Pin {pin_num} ({pin_name}): type '{pin_type}' is not a standard KiCad type",
                    field=f"pins[{pin_num}].type", actual=pin_type,
                    suggestion=f"Use standard type: {', '.join(sorted(VALID_PIN_TYPES))[:80]}",
                )

            # 类型一致性检查（基于名称推断 vs 声明）
            inferred = self._infer_pin_type(pin_name)
            if inferred and pin_type and inferred != pin_type:
                # 仅警告明显不匹配的情况
                mismatch_pairs = [
                    ("power_in", "unspecified"),
                    ("no_connect", "unspecified"),
                ]
                if (inferred, pin_type) not in mismatch_pairs and (pin_type, inferred) not in mismatch_pairs:
                    result.add_issue(
                        Severity.P3, ValidationType.PIN_TYPE,
                        code="P3-PIN-TYPE-MISMATCH",
                        message=f"Pin {pin_num} ({pin_name}): declared as '{pin_type}', inferred as '{inferred}'",
                        field=f"pins[{pin_num}].type",
                        expected=inferred, actual=pin_type,
                    )

        return result

    def _infer_pin_type(self, pin_name: str) -> Optional[str]:
        """根据引脚名称推断引脚类型"""
        if not pin_name:
            return None
        for pattern, ptype in PIN_TYPE_INFERENCE_RULES:
            if re.match(pattern, pin_name, re.IGNORECASE):
                return ptype
        return None

    # ─── Tier 3: KiCad 库交叉验证 ───────────────────────────────

    def validate_cross_ref(
        self,
        comp: Dict[str, Any],
        name: str,
        symbol_parser=None,
        footprint_parser=None,
    ) -> ComponentValidationResult:
        """Tier 3: KiCad 库交叉验证"""
        result = ComponentValidationResult(component_name=name)

        symbol_lib = comp.get("symbol_library", "")
        footprint = comp.get("footprint", "")
        pins = comp.get("pins", [])
        symbol_name = comp.get("symbol_name", name)

        # 检查 symbol_library 是否存在
        if symbol_lib == "custom":
            # 自定义/外部模块，跳过 KiCad 库交叉验证
            result.symbol_exists = False
            result.footprint_exists = False
            result.add_issue(
                Severity.P3, ValidationType.CROSS_REF,
                code="P3-CUSTOM-COMPONENT",
                message=f"Component '{name}' is a custom/external module (symbol_library=custom)",
                field="symbol_library",
                suggestion="This module is not in KiCad official library. Create custom symbol manually if needed.",
            )
            return result

        if symbol_lib:
            exists = self._symbol_library_exists(symbol_lib, symbol_parser)
            result.symbol_exists = exists
            if not exists:
                result.add_issue(
                    Severity.P1, ValidationType.CROSS_REF,
                    code="P1-SYMBOL-LIB-NOT-FOUND",
                    message=f"Symbol library not found in KiCad: {symbol_lib}",
                    field="symbol_library", actual=symbol_lib,
                    suggestion=f"Verify '{symbol_lib}' exists in kicad-symbols directory",
                )
            else:
                # 检查引脚数一致性
                pin_count = len(pins) if isinstance(pins, list) else 0
                kicad_pin_count = self._get_kicad_pin_count(symbol_lib, symbol_name, symbol_parser)
                result.pin_count_kb = pin_count
                result.pin_count_kicad = kicad_pin_count
                result.pin_count_match = kicad_pin_count == pin_count if kicad_pin_count else None

                if kicad_pin_count is not None and kicad_pin_count > 0:
                    # 注意: KiCad 解析器对复杂 MCU 符号可能只返回 0（power symbol pins 未被解析）
                    # 因此仅在 KiCad 返回有效非零引脚数时进行比较
                    if kicad_pin_count != pin_count:
                        result.add_issue(
                            Severity.P1, ValidationType.CROSS_REF,
                            code="P1-PIN-COUNT-MISMATCH",
                            message=f"Pin count mismatch: KB={pin_count}, KiCad={kicad_pin_count}",
                            field="pins",
                            expected=str(kicad_pin_count), actual=str(pin_count),
                            suggestion=f"Align pins count with {symbol_lib}:{symbol_name}",
                        )

        # 检查 footprint 是否存在
        if footprint:
            exists = self._footprint_exists(footprint, footprint_parser)
            result.footprint_exists = exists
            if not exists:
                result.add_issue(
                    Severity.P1, ValidationType.CROSS_REF,
                    code="P1-FOOTPRINT-NOT-FOUND",
                    message=f"Footprint not found in KiCad library: {footprint}",
                    field="footprint", actual=footprint,
                    suggestion="Use KiCad footprint library format 'Package_Library:Footprint_Name'",
                )

        return result

    def _symbol_library_exists(self, symbol_lib: str, parser) -> bool:
        """检查 KiCad 符号库是否存在"""
        if not parser:
            return None  # 未知
        try:
            if ":" in symbol_lib:
                lib, sym = symbol_lib.split(":", 1)
                sym_data = parser.get_symbol(lib, sym)
                return sym_data is not None
            else:
                # symbol_lib 是库名，检查库是否存在
                return symbol_lib in parser.list_available_libraries()
        except Exception as e:
            logger.warning(f"Error checking symbol {symbol_lib}: {e}")
            return None

    def _get_kicad_pin_count(self, symbol_lib: str, symbol_name: str, parser) -> Optional[int]:
        """获取 KiCad 符号的引脚数"""
        if not parser:
            return None
        try:
            if ":" in symbol_lib:
                lib, sym = symbol_lib.split(":", 1)
                sym_data = parser.get_symbol(lib, sym)
            else:
                # symbol_lib 是库名，symbol_name 是符号名
                # 尝试直接查找，避免 find_symbol_for_component 返回错误的默认符号
                if symbol_name:
                    sym_data = parser.get_symbol(symbol_lib, symbol_name)
                else:
                    # 无符号名，降级到搜索
                    sym_data = parser.find_symbol_for_component(symbol_lib)

            if sym_data and hasattr(sym_data, "pins"):
                return len(sym_data.pins)
            return None
        except Exception as e:
            logger.warning(f"Error getting pin count for {symbol_lib}:{symbol_name}: {e}")
            return None

    def _footprint_exists(self, footprint: str, parser) -> bool:
        """检查 KiCad 封装是否存在"""
        try:
            from footprint_parser import get_footprint_data
            fp_data = get_footprint_data(footprint)
            return fp_data is not None
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"Error checking footprint {footprint}: {e}")
            return None

    # ─── datasheet URL 校验 ────────────────────────────────────

    def validate_datasheet_url(
        self,
        comp: Dict[str, Any],
        name: str,
        timeout: float = 5.0,
    ) -> ComponentValidationResult:
        """验证 datasheet URL 可访问性"""
        result = ComponentValidationResult(component_name=name)
        url = comp.get("datasheet_url", "")

        result.datasheet_url = url

        if not url:
            result.add_issue(
                Severity.P1, ValidationType.DATASHEET,
                code="P1-MISSING-DATASHEET-URL",
                message="No datasheet_url provided",
                field="datasheet_url",
                suggestion=f"Add datasheet URL from manufacturer (ST, TI, etc.)",
            )
            result.datasheet_url_accessible = False
            return result

        # URL 格式检查
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                result.add_issue(
                    Severity.P2, ValidationType.DATASHEET,
                    code="P2-INVALID-DATASHEET-URL",
                    message=f"Invalid URL format: {url}",
                    field="datasheet_url", actual=url,
                    suggestion="Use full URL starting with http:// or https://",
                )
                result.datasheet_url_accessible = False
                return result
        except Exception:
            result.add_issue(
                Severity.P2, ValidationType.DATASHEET,
                code="P2-MALFORMED-URL",
                message=f"Cannot parse URL: {url}",
                field="datasheet_url",
            )
            result.datasheet_url_accessible = False
            return result

        # 可访问性检查（HEAD 请求，轻量）
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                result.add_issue(
                    Severity.P1, ValidationType.DATASHEET,
                    code="P1-DATASHEET-URL-DEAD",
                    message=f"Datasheet URL returns HTTP {resp.status_code}: {url}",
                    field="datasheet_url",
                    suggestion="Update to a working datasheet URL",
                )
                result.datasheet_url_accessible = False
            else:
                result.datasheet_url_accessible = True
        except requests.exceptions.Timeout:
            result.add_issue(
                Severity.P2, ValidationType.DATASHEET,
                code="P2-DATASHEET-URL-TIMEOUT",
                message=f"Datasheet URL timed out ({timeout}s): {url}",
                field="datasheet_url",
            )
            result.datasheet_url_accessible = False
        except requests.exceptions.RequestException as e:
            result.add_issue(
                Severity.P2, ValidationType.DATASHEET,
                code="P2-DATASHEET-URL-ERROR",
                message=f"Datasheet URL check failed: {e}",
                field="datasheet_url",
            )
            result.datasheet_url_accessible = False

        return result

    # ─── 完整校验流程 ─────────────────────────────────────────

    def validate(
        self,
        comp: Dict[str, Any],
        name: str,
        symbol_parser=None,
        footprint_parser=None,
        check_datasheet: bool = False,
        datasheet_timeout: float = 5.0,
    ) -> ComponentValidationResult:
        """运行全部三层校验"""
        result = ComponentValidationResult(component_name=name)

        # Tier 1: 格式校验
        r1 = self.validate_format(comp, name)
        self._merge_results(result, r1)

        # Tier 2: 引脚类型校验
        r2 = self.validate_pin_types(comp, name)
        self._merge_results(result, r2)

        # Tier 3: KiCad 库交叉验证
        r3 = self.validate_cross_ref(comp, name, symbol_parser, footprint_parser)
        self._merge_results(result, r3)

        # datasheet URL 校验
        if check_datasheet:
            r4 = self.validate_datasheet_url(comp, name, datasheet_timeout)
            self._merge_results(result, r4)

        return result

    def _merge_results(self, target: ComponentValidationResult, source: ComponentValidationResult) -> None:
        """合并两个校验结果"""
        target.issues.extend(source.issues)
        target.warnings.extend(source.warnings)
        target.info.extend(source.info)
        # 复制 KiCad 验证详情
        for attr in ["symbol_exists", "footprint_exists", "pin_count_match",
                     "pin_count_kb", "pin_count_kicad", "datasheet_url_accessible", "datasheet_url"]:
            val = getattr(source, attr, None)
            if val is not None and getattr(target, attr, None) is None:
                setattr(target, attr, val)

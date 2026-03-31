"""
Template Validator - 模板质量验证器

Phase 7D: 验证模板质量

检查项:
- 电源引脚已连接
- 无悬空引脚
- IC 旁有去耦电容
- 信号路径完整
- 封装已分配
- 网络已分类

Author: Claude Code
Date: 2026-03-31
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from .template_data import (
    ProjectTemplate,
    TemplateSchematic,
    TemplatePCB,
)

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证严重级别"""
    ERROR = "error"        # 必须修复
    WARNING = "warning"    # 建议修复
    INFO = "info"          # 信息提示


@dataclass
class ValidationIssue:
    """验证问题"""
    rule_id: str
    severity: ValidationSeverity
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    score: float = 0.0        # 0-100 质量评分
    issues: List[ValidationIssue] = field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def pass_rate(self) -> float:
        if self.checks_total == 0:
            return 0.0
        return self.checks_passed / self.checks_total


# ============== IC 关键词 ==============

_IC_PATTERNS = [
    "esp32", "esp8266", "stm32", "atmega", "arduino",
    "ams1117", "lm78", "tp4056", "ch340", "cp2102",
    "max485", "lm386", "l298n", "pn532", "nrf24",
    "pam8403", "ws2812", "al8805", "dw01",
]

_POWER_NET_NAMES = {"vcc", "3v3", "5v", "vin", "vout", "gnd", "3.3v", "5.0v", "vbus"}

_GROUND_NET_NAMES = {"gnd", "ground", "dgnd", "agnd", "pgnd", "sgnd"}

_DECOUPLING_CAP_PATTERNS = ["100nf", "0.1uf", "10uf", "1uf", "100n", "0.1u"]


class TemplateValidator:
    """
    模板质量验证器

    验证模板数据的完整性和正确性:
    - 电源引脚连接
    - 悬空引脚检测
    - 去耦电容存在性
    - 信号路径完整性
    - 封装分配
    - 网络分类
    """

    def validate(self, template: ProjectTemplate) -> ValidationResult:
        """
        验证模板

        Args:
            template: 项目模板

        Returns:
            ValidationResult 包含所有检查结果
        """
        issues: List[ValidationIssue] = []
        passed = 0
        total = 0

        checks = [
            self._check_power_pins_connected,
            self._check_no_floating_pins,
            self._check_decoupling_caps,
            self._check_signal_paths_complete,
            self._check_footprints_assigned,
            self._check_nets_classified,
            self._check_schematic_components,
            self._check_pcb_outline,
        ]

        for check_fn in checks:
            total += 1
            try:
                check_issues = check_fn(template)
                if not any(i.severity == ValidationSeverity.ERROR for i in check_issues):
                    passed += 1
                issues.extend(check_issues)
            except Exception as e:
                logger.warning(f"Check {check_fn.__name__} failed: {e}")
                issues.append(ValidationIssue(
                    rule_id="INTERNAL",
                    severity=ValidationSeverity.WARNING,
                    message=f"检查 {check_fn.__name__} 执行失败: {e}",
                ))

        # 计算评分
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        score = max(0.0, 100.0 - error_count * 20 - warning_count * 5)

        return ValidationResult(
            valid=error_count == 0,
            score=score,
            issues=issues,
            checks_passed=passed,
            checks_total=total,
        )

    # ============== 检查方法 ==============

    def _check_power_pins_connected(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查所有电源引脚已连接"""
        issues = []
        nets = template.schematic.nets

        # 收集所有已连接的网络名
        connected_net_names = set()
        for net in nets:
            connected_net_names.add(net.get("name", "").lower())

        # 检查是否有电源网络
        has_power = any(n in connected_net_names for n in _POWER_NET_NAMES if n != "gnd")
        has_ground = any(n in connected_net_names for n in _GROUND_NET_NAMES)

        if not has_power:
            issues.append(ValidationIssue(
                rule_id="POWER_001",
                severity=ValidationSeverity.ERROR,
                message="缺少电源网络 (VCC/3V3/5V)",
                details={"available_nets": list(connected_net_names)},
            ))

        if not has_ground:
            issues.append(ValidationIssue(
                rule_id="POWER_002",
                severity=ValidationSeverity.ERROR,
                message="缺少地线网络 (GND)",
                details={"available_nets": list(connected_net_names)},
            ))

        # 检查 IC 的电源引脚是否在某个网络中
        for comp in template.schematic.components:
            ref = comp.get("reference", "").upper()
            symbol = comp.get("symbol", "").lower()
            if any(ic in symbol for ic in _IC_PATTERNS):
                # IC 应该出现在至少一个电源网络和一个地线网络中
                found_in_power = False
                found_in_gnd = False
                for net in nets:
                    nodes = net.get("nodes", [])
                    net_name = net.get("name", "").lower()
                    for node in nodes:
                        if node.split(".")[0].upper() == ref:
                            if net_name in _POWER_NET_NAMES and net_name not in _GROUND_NET_NAMES:
                                found_in_power = True
                            if net_name in _GROUND_NET_NAMES:
                                found_in_gnd = True

                if not found_in_power:
                    issues.append(ValidationIssue(
                        rule_id="POWER_003",
                        severity=ValidationSeverity.WARNING,
                        message=f"IC {ref} 未连接到电源网络",
                        details={"component": ref, "symbol": symbol},
                    ))

                if not found_in_gnd:
                    issues.append(ValidationIssue(
                        rule_id="POWER_004",
                        severity=ValidationSeverity.WARNING,
                        message=f"IC {ref} 未连接到地线网络",
                        details={"component": ref, "symbol": symbol},
                    ))

        return issues

    def _check_no_floating_pins(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查无悬空引脚"""
        issues = []
        components = template.schematic.components
        nets = template.schematic.nets

        # 收集所有已连接的 引脚
        connected_pins = set()
        for net in nets:
            for node in net.get("nodes", []):
                connected_pins.add(node.upper())

        # 检查 IC 的引脚连接率
        for comp in components:
            ref = comp.get("reference", "")
            symbol = comp.get("symbol", "").lower()

            if any(ic in symbol for ic in _IC_PATTERNS):
                # IC 应该有多个引脚连接到网络
                ic_connections = 0
                for net in nets:
                    for node in net.get("nodes", []):
                        if node.split(".")[0].upper() == ref.upper():
                            ic_connections += 1

                if ic_connections < 2:
                    issues.append(ValidationIssue(
                        rule_id="FLOAT_001",
                        severity=ValidationSeverity.WARNING,
                        message=f"IC {ref} 连接引脚过少 ({ic_connections})，可能有悬空引脚",
                        details={"component": ref, "connections": ic_connections},
                    ))

        return issues

    def _check_decoupling_caps(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查 IC 旁有去耦电容"""
        issues = []
        components = template.schematic.components

        # 找到所有 IC
        ics = []
        for comp in components:
            symbol = comp.get("symbol", "").lower()
            if any(ic in symbol for ic in _IC_PATTERNS):
                ics.append(comp)

        # 找到所有电容
        caps = []
        for comp in components:
            symbol = comp.get("symbol", "").lower()
            if symbol in ("c", "cp", "cap", "ceramic_cap", "electrolytic_cap"):
                value = comp.get("properties", {}).get("Value", "").lower()
                caps.append((comp, value))

        # 检查每个 IC 是否有附近的去耦电容
        for ic in ics:
            ic_x = ic.get("x", 0)
            ic_y = ic.get("y", 0)
            has_decoupling = False

            for cap, value in caps:
                cap_x = cap.get("x", 0)
                cap_y = cap.get("y", 0)
                distance = ((ic_x - cap_x) ** 2 + (ic_y - cap_y) ** 2) ** 0.5

                # 去耦电容应该在 IC 附近 (坐标距离 < 30)
                if distance < 30:
                    has_decoupling = True
                    break

            # 如果没有距离上的去耦电容，检查网络上的
            if not has_decoupling:
                ic_ref = ic.get("reference", "").upper()
                ic_power_nets = set()
                for net in template.schematic.nets:
                    for node in net.get("nodes", []):
                        if node.split(".")[0].upper() == ic_ref:
                            net_name = net.get("name", "").lower()
                            if net_name in _POWER_NET_NAMES:
                                ic_power_nets.add(net.get("name", ""))

                # 检查是否有电容也在同一个电源网络中
                for cap, value in caps:
                    cap_ref = cap.get("reference", "").upper()
                    for net_name in ic_power_nets:
                        for net in template.schematic.nets:
                            if net.get("name", "") == net_name:
                                nodes = net.get("nodes", [])
                                if any(n.split(".")[0].upper() == cap_ref for n in nodes):
                                    has_decoupling = True
                                    break

            if not has_decoupling and len(ics) > 0:
                issues.append(ValidationIssue(
                    rule_id="DECOUP_001",
                    severity=ValidationSeverity.WARNING,
                    message=f"IC {ic.get('reference', '?')} 旁未检测到去耦电容",
                    details={"component": ic.get("reference", "?")},
                ))

        return issues

    def _check_signal_paths_complete(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查信号路径完整性"""
        issues = []
        components = template.schematic.components
        nets = template.schematic.nets

        # 每个网络应该连接至少 2 个节点
        for net in nets:
            nodes = net.get("nodes", [])
            net_name = net.get("name", "unnamed")

            if len(nodes) == 0:
                issues.append(ValidationIssue(
                    rule_id="SIG_001",
                    severity=ValidationSeverity.ERROR,
                    message=f"网络 '{net_name}' 没有连接任何节点",
                ))
            elif len(nodes) == 1:
                issues.append(ValidationIssue(
                    rule_id="SIG_002",
                    severity=ValidationSeverity.WARNING,
                    message=f"网络 '{net_name}' 只连接了 1 个节点，可能有悬空连接",
                    details={"nodes": nodes},
                ))

        return issues

    def _check_footprints_assigned(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查 PCB 封装是否已分配"""
        issues = []

        for comp in template.pcb.components:
            if not comp.get("footprint"):
                ref = comp.get("reference", "?")
                issues.append(ValidationIssue(
                    rule_id="FOOT_001",
                    severity=ValidationSeverity.WARNING,
                    message=f"PCB 元件 {ref} 未分配封装",
                    details={"component": ref},
                ))

        return issues

    def _check_nets_classified(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查网络是否已分类"""
        issues = []
        nets = template.schematic.nets

        unclassified = []
        for net in nets:
            name = net.get("name", "").lower()
            # 检查是否能识别网络类型
            is_power = name in _POWER_NET_NAMES or name in _GROUND_NET_NAMES
            is_signal = not is_power and len(net.get("nodes", [])) >= 2

            if not is_power and not is_signal:
                unclassified.append(net.get("name", "unnamed"))

        if unclassified:
            issues.append(ValidationIssue(
                rule_id="NET_001",
                severity=ValidationSeverity.INFO,
                message=f"{len(unclassified)} 个网络未分类: {', '.join(unclassified[:5])}",
                details={"unclassified": unclassified},
            ))

        return issues

    def _check_schematic_components(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查原理图组件基本完整性"""
        issues = []
        components = template.schematic.components

        if not components:
            issues.append(ValidationIssue(
                rule_id="SCH_001",
                severity=ValidationSeverity.ERROR,
                message="原理图没有任何组件",
            ))
            return issues

        # 检查每个组件有 reference 和 symbol
        refs_seen = set()
        for comp in components:
            ref = comp.get("reference", "")
            symbol = comp.get("symbol", "")

            if not ref:
                issues.append(ValidationIssue(
                    rule_id="SCH_002",
                    severity=ValidationSeverity.ERROR,
                    message=f"组件缺少 reference: {comp}",
                ))

            if not symbol:
                issues.append(ValidationIssue(
                    rule_id="SCH_003",
                    severity=ValidationSeverity.WARNING,
                    message=f"组件 {ref} 缺少 symbol 定义",
                    details={"component": ref},
                ))

            if ref in refs_seen:
                issues.append(ValidationIssue(
                    rule_id="SCH_004",
                    severity=ValidationSeverity.ERROR,
                    message=f"重复的 reference: {ref}",
                ))
            refs_seen.add(ref)

        return issues

    def _check_pcb_outline(
        self, template: ProjectTemplate
    ) -> List[ValidationIssue]:
        """检查 PCB 板框定义"""
        issues = []
        outline = template.pcb.board_outline

        if not outline:
            issues.append(ValidationIssue(
                rule_id="PCB_001",
                severity=ValidationSeverity.WARNING,
                message="PCB 缺少板框定义",
            ))
        elif len(outline) < 3:
            issues.append(ValidationIssue(
                rule_id="PCB_002",
                severity=ValidationSeverity.ERROR,
                message="PCB 板框至少需要 3 个点",
                details={"points": len(outline)},
            ))

        # 检查层数合理性
        layers = template.pcb.layers
        if layers not in (1, 2, 4, 6, 8):
            issues.append(ValidationIssue(
                rule_id="PCB_003",
                severity=ValidationSeverity.WARNING,
                message=f"PCB 层数 {layers} 不常见 (常见: 1, 2, 4, 6)",
                details={"layers": layers},
            ))

        return issues

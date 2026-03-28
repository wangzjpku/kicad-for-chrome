#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KiCad 网表验证器 v1.0

功能：
1. 验证原理图和PCB之间的网络一致性
2. 检查未连接的引脚
3. 检查电源网络
4. 生成验证报告

作者：AI Assistant
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """问题严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class NetIssue:
    """网表问题"""
    severity: IssueSeverity
    category: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NetValidationResult:
    """网表验证结果"""
    is_valid: bool
    issues: List[NetIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def add_issue(self, severity: IssueSeverity, category: str, message: str, details: Dict = None):
        """添加问题"""
        issue = NetIssue(severity, category, message, details or {})
        self.issues.append(issue)

        # 更新摘要
        key = severity.value
        self.summary[key] = self.summary.get(key, 0) + 1

        if severity == IssueSeverity.ERROR:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "summary": self.summary,
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "details": i.details
                } for i in self.issues
            ]
        }


class NetlistValidator:
    """网表验证器"""

    # 电源网络名称
    POWER_NETS = {"VCC", "VDD", "VEE", "VSS", "GND", "VREF", "AVDD", "AVSS", "VBAT"}

    def __init__(self):
        self.schematic_nets: Dict[str, Set[str]] = {}  # {net_name: {pin_ref: pin}}
        self.pcb_nets: Dict[str, Set[str]] = {}
        self.schematic_components: Dict[str, Dict] = {}
        self.pcb_components: Dict[str, Dict] = {}

    def load_schematic_nets(self, schematic_data: Dict[str, Any]):
        """
        加载原理图网络

        Args:
            schematic_data: 原理图数据字典
        """
        self.schematic_nets = {}

        for net in schematic_data.get("nets", []):
            net_name = net.get("name", "")
            connections = net.get("connections", [])

            if net_name:
                self.schematic_nets[net_name] = set()
                for conn in connections:
                    ref = conn.get("reference", conn.get("ref", ""))
                    pin = conn.get("pin", "")
                    if ref and pin:
                        self.schematic_nets[net_name].add(f"{ref}:{pin}")

        # 加载元件信息
        self.schematic_components = {}
        for comp in schematic_data.get("components", []):
            ref = comp.get("reference", "")
            if ref:
                self.schematic_components[ref] = comp

        logger.info(f"已加载 {len(self.schematic_nets)} 个原理图网络")

    def load_pcb_nets(self, pcb_data: Dict[str, Any]):
        """
        加载PCB网络

        Args:
            pcb_data: PCB数据字典
        """
        self.pcb_nets = {}

        for net in pcb_data.get("nets", []):
            net_name = net.get("name", "")
            connections = net.get("connections", [])
            pads = net.get("pads", [])

            if net_name:
                self.pcb_nets[net_name] = set()

                # 从connections获取
                for conn in connections:
                    ref = conn.get("reference", conn.get("ref", ""))
                    pad = conn.get("pad", conn.get("pin", ""))
                    if ref and pad:
                        self.pcb_nets[net_name].add(f"{ref}:{pad}")

                # 从pads获取
                for pad_info in pads:
                    ref = pad_info.get("reference", "")
                    pad_num = pad_info.get("pad_number", pad_info.get("pad", ""))
                    if ref and pad_num:
                        self.pcb_nets[net_name].add(f"{ref}:{pad_num}")

        # 加载PCB元件信息
        self.pcb_components = {}
        for comp in pcb_data.get("footprints", []):
            ref = comp.get("reference", "")
            if ref:
                self.pcb_components[ref] = comp

        logger.info(f"已加载 {len(self.pcb_nets)} 个PCB网络")

    def validate(self) -> NetValidationResult:
        """
        执行验证

        Returns:
            NetValidationResult: 验证结果
        """
        result = NetValidationResult(is_valid=True)

        # 1. 检查网络存在性
        self._check_network_existence(result)

        # 2. 检查网络连接一致性
        self._check_network_consistency(result)

        # 3. 检查未连接的引脚
        self._check_unconnected_pins(result)

        # 4. 检查电源网络
        self._check_power_nets(result)

        # 5. 检查元件封装匹配
        self._check_footprint_match(result)

        return result

    def _check_network_existence(self, result: NetValidationResult):
        """检查网络存在性"""
        schematic_net_names = set(self.schematic_nets.keys())
        pcb_net_names = set(self.pcb_nets.keys())

        # 原理图中没有但PCB中有的网络
        extra_in_pcb = pcb_net_names - schematic_net_names
        if extra_in_pcb:
            for net_name in extra_in_pcb:
                # 跳过电源网络
                if net_name.upper() not in self.POWER_NETS:
                    result.add_issue(
                        IssueSeverity.WARNING,
                        "network_existence",
                        f"PCB中有但原理图中没有的网络: {net_name}",
                        {"net": net_name, "connections": len(self.pcb_nets.get(net_name, set()))}
                    )

        # 原理图中有但PCB中没有的网络
        missing_in_pcb = schematic_net_names - pcb_net_names
        if missing_in_pcb:
            for net_name in missing_in_pcb:
                result.add_issue(
                    IssueSeverity.ERROR,
                    "network_existence",
                    f"原理图中有但PCB中缺失的网络: {net_name}",
                    {"net": net_name, "connections": len(self.schematic_nets.get(net_name, set()))}
                )

    def _check_network_consistency(self, result: NetValidationResult):
        """检查网络连接一致性"""
        common_nets = set(self.schematic_nets.keys()) & set(self.pcb_nets.keys())

        for net_name in common_nets:
            schematic_pins = self.schematic_nets.get(net_name, set())
            pcb_pins = self.pcb_nets.get(net_name, set())

            # PCB中有但原理图中没有的引脚
            extra_in_pcb = pcb_pins - schematic_pins
            if extra_in_pcb:
                result.add_issue(
                    IssueSeverity.WARNING,
                    "network_consistency",
                    f"网络 '{net_name}' 中有未在原理图中声明的连接",
                    {"net": net_name, "extra_pins": list(extra_in_pcb)}
                )

            # 原理图中有但PCB中没有的引脚
            missing_in_pcb = schematic_pins - pcb_pins
            if missing_in_pcb:
                result.add_issue(
                    IssueSeverity.ERROR,
                    "network_consistency",
                    f"网络 '{net_name}' 有未连接到PCB的引脚",
                    {"net": net_name, "missing_pins": list(missing_in_pcb)}
                )

    def _check_unconnected_pins(self, result: NetValidationResult):
        """检查未连接的引脚"""
        # 统计所有在原理图中定义的引脚
        all_schematic_pins: Set[str] = set()
        for pins in self.schematic_nets.values():
            all_schematic_pins.update(pins)

        # 统计所有在PCB中连接的引脚
        all_pcb_pins: Set[str] = set()
        for pins in self.pcb_nets.values():
            all_pcb_pins.update(pins)

        # 找出未连接的引脚
        unconnected = all_schematic_pins - all_pcb_pins

        if unconnected:
            # 按元件分组
            unconnected_by_component: Dict[str, List[str]] = {}
            for pin in unconnected:
                if ":" in pin:
                    ref, pad = pin.split(":", 1)
                    if ref not in unconnected_by_component:
                        unconnected_by_component[ref] = []
                    unconnected_by_component[ref].append(pad)

            for ref, pads in unconnected_by_component.items():
                result.add_issue(
                    IssueSeverity.WARNING,
                    "unconnected_pins",
                    f"元件 {ref} 有 {len(pads)} 个未连接的引脚",
                    {"reference": ref, "pins": pads}
                )

    def _check_power_nets(self, result: NetValidationResult):
        """检查电源网络"""
        # 检查重要的电源网络是否存在
        required_power_nets = {"VCC", "GND"}

        schematic_power_nets = {net.upper() for net in self.schematic_nets.keys()}
        pcb_power_nets = {net.upper() for net in self.pcb_nets.keys()}

        for power_net in required_power_nets:
            # 检查原理图
            if power_net not in schematic_power_nets:
                # 检查可能的变体
                has_variant = any(power_net in net.upper() for net in self.schematic_nets.keys())
                if not has_variant:
                    result.add_issue(
                        IssueSeverity.WARNING,
                        "power_net",
                        f"原理图中缺少电源网络: {power_net}",
                        {}
                    )

            # 检查PCB
            if power_net not in pcb_power_nets:
                has_variant = any(power_net in net.upper() for net in self.pcb_nets.keys())
                if not has_variant:
                    result.add_issue(
                        IssueSeverity.WARNING,
                        "power_net",
                        f"PCB中缺少电源网络: {power_net}",
                        {}
                    )

    def _check_footprint_match(self, result: NetValidationResult):
        """检查元件封装匹配"""
        for ref, comp in self.schematic_components.items():
            schematic_fp = comp.get("footprint", "")

            if ref in self.pcb_components:
                pcb_comp = self.pcb_components[ref]
                pcb_fp = pcb_comp.get("footprint", pcb_comp.get("module", ""))

                if schematic_fp and pcb_fp and schematic_fp != pcb_fp:
                    result.add_issue(
                        IssueSeverity.ERROR,
                        "footprint_mismatch",
                        f"元件 {ref} 封装不匹配",
                        {
                            "reference": ref,
                            "schematic_footprint": schematic_fp,
                            "pcb_footprint": pcb_fp
                        }
                    )


def validate_netlists(schematic_data: Dict[str, Any], pcb_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证原理图和PCB网表一致性的便捷函数

    Args:
        schematic_data: 原理图数据
        pcb_data: PCB数据

    Returns:
        Dict: 验证结果
    """
    validator = NetlistValidator()
    validator.load_schematic_nets(schematic_data)
    validator.load_pcb_nets(pcb_data)

    result = validator.validate()
    return result.to_dict()


# 测试代码
if __name__ == "__main__":
    # 测试数据
    test_schematic = {
        "components": [
            {"reference": "U1", "value": "STM32F103", "footprint": "LQFP-48"},
            {"reference": "U2", "value": "CH340G", "footprint": "SOIC-16"},
            {"reference": "R1", "value": "10K", "footprint": "0603"},
            {"reference": "C1", "value": "10uF", "footprint": "0603"},
            {"reference": "C2", "value": "22pF", "footprint": "0603"},
            {"reference": "Y1", "value": "8MHz", "footprint": "HC-49"},
        ],
        "nets": [
            {"name": "VCC", "connections": [
                {"reference": "U1", "pin": "VDD"},
                {"reference": "U2", "pin": "VCC"},
                {"reference": "R1", "pin": "1"},
                {"reference": "C1", "pin": "1"},
            ]},
            {"name": "GND", "connections": [
                {"reference": "U1", "pin": "VSS"},
                {"reference": "U2", "pin": "GND"},
                {"reference": "C1", "pin": "2"},
                {"reference": "C2", "pin": "2"},
                {"reference": "Y1", "pin": "2"},
            ]},
            {"name": "NET1", "connections": [
                {"reference": "U1", "pin": "PA9"},
                {"reference": "U2", "pin": "TXD"},
            ]},
            {"name": "NET2", "connections": [
                {"reference": "U1", "pin": "PA10"},
                {"reference": "U2", "pin": "RXD"},
            ]},
            {"name": "OSC_NET", "connections": [
                {"reference": "U1", "pin": "OSC_IN"},
                {"reference": "Y1", "pin": "1"},
                {"reference": "C2", "pin": "1"},
            ]},
            # 未连接的引脚测试
            {"name": "UNCONNECTED", "connections": [
                {"reference": "U1", "pin": "PB0"},  # 未连接到PCB
            ]},
        ]
    }

    test_pcb = {
        "footprints": [
            {"reference": "U1", "module": "LQFP-48"},
            {"reference": "U2", "module": "SOIC-16"},
            {"reference": "R1", "module": "0603"},
            {"reference": "C1", "module": "0603"},
            {"reference": "C2", "module": "0603"},
            {"reference": "Y1", "module": "HC-49"},
        ],
        "nets": [
            {"name": "VCC", "connections": [
                {"reference": "U1", "pin": "VDD"},
                {"reference": "U2", "pin": "VCC"},
                {"reference": "R1", "pin": "1"},
                {"reference": "C1", "pin": "1"},
            ]},
            {"name": "GND", "connections": [
                {"reference": "U1", "pin": "VSS"},
                {"reference": "U2", "pin": "GND"},
                {"reference": "C1", "pin": "2"},
                {"reference": "C2", "pin": "2"},
                {"reference": "Y1", "pin": "2"},
            ]},
            {"name": "NET1", "connections": [
                {"reference": "U1", "pin": "PA9"},
                {"reference": "U2", "pin": "TXD"},
            ]},
            {"name": "NET2", "connections": [
                {"reference": "U1", "pin": "PA10"},
                {"reference": "U2", "pin": "RXD"},
            ]},
            {"name": "OSC_NET", "connections": [
                {"reference": "U1", "pin": "OSC_IN"},
                {"reference": "Y1", "pin": "1"},
                {"reference": "C2", "pin": "1"},
            ]},
            # PCB中多出的网络
            {"name": "EXTRA_NET", "connections": [
                {"reference": "U1", "pin": "PB1"},
            ]},
        ]
    }

    print("=== 网表验证测试 ===\n")

    result = validate_netlists(test_schematic, test_pcb)

    print(f"验证结果: {'通过' if result['is_valid'] else '失败'}")
    print(f"\n摘要:")
    for severity, count in result['summary'].items():
        print(f"  {severity}: {count}")

    print(f"\n问题列表:")
    for issue in result['issues']:
        print(f"  [{issue['severity'].upper()}] {issue['category']}: {issue['message']}")
        if issue['details']:
            print(f"    详情: {issue['details']}")

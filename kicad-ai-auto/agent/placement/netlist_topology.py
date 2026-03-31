"""
网表拓扑分析器 - Netlist Topology Analyzer

从网表数据中分析电路拓扑，识别功能分区和功率流向。
模仿工业级PCB设计中的"输入→EMI→整流→DC-DC→协议→输出"式功能分区布局。

功能:
1. 功能分区识别 - POWER_INPUT, POWER_CONVERT, POWER_OUTPUT, CONTROL, PROTECTION, PASSIVE
2. 功率流向追踪 - VIN → VCC5V → VCC3V3 → VOUT
3. 安规隔离需求检测 - 初级/次级隔离
4. 分组亲和度计算 - 哪些分区应靠近

Author: Claude Code
Date: 2026-03-31
Phase: 7B
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class FunctionalGroup(Enum):
    """功能分区枚举"""
    POWER_INPUT = "power_input"       # AC输入、整流桥、保险丝、共模电感
    POWER_CONVERT = "power_convert"   # 变压器、DC-DC IC、开关管、功率电感
    POWER_OUTPUT = "power_output"     # 输出滤波、USB连接器、充电协议IC
    CONTROL = "control"               # MCU、反馈电路、光耦、基准电压
    PROTECTION = "protection"         # ESD保护、TVS、过压/过流检测
    PASSIVE = "passive"               # 去耦电容、上拉电阻 → 附属于最近的IC
    INTERFACE = "interface"           # 连接器、通信接口
    CRYSTAL = "crystal"               # 晶振、谐振器


@dataclass
class IsolationRequirement:
    """安规隔离需求"""
    group1: FunctionalGroup
    group2: FunctionalGroup
    min_distance_mm: float           # 最小隔离距离 (mm)
    isolation_type: str              # "slot" (物理开槽) / "clearance" (无铜带)
    voltage_range: str               # 电压范围描述 (e.g. "220V AC")
    standard: str                    # 标准 (e.g. "IEC 60950-1")


@dataclass
class TopologyResult:
    """拓扑分析结果"""
    functional_groups: Dict[FunctionalGroup, List[str]]  # 分区 → 元件列表
    group_affinity: Dict[Tuple[FunctionalGroup, FunctionalGroup], float]  # 亲和度 0-1
    isolation_requirements: List[IsolationRequirement]
    power_flow: List[FunctionalGroup]   # 功率流向序列
    component_group_map: Dict[str, FunctionalGroup]  # 元件ref → 分区


# ========== 分区识别关键词 ==========

GROUP_KEYWORDS: Dict[FunctionalGroup, Dict] = {
    FunctionalGroup.POWER_INPUT: {
        "refs": ["BD", "BR", "D1", "D2", "D3", "D4"],   # 整流桥
        "values": [
            "bridge", "rectifier", "fuse", "varistor", "mov",
            "nmos", "pmos", "mosfet", "igbt",
            "保险丝", "整流桥", "压敏电阻", "共模", "电感",
        ],
        "footprints": ["bridge", "rectifier", "to-220", "to-247", "d-pack"],
        "nets": ["AC", "L_LINE", "N_LINE", "LIVE", "NEUTRAL", "VIN_RAW", "HV"],
    },
    FunctionalGroup.POWER_CONVERT: {
        "refs": ["T1", "T2"],  # 变压器
        "values": [
            "transformer", "dcdc", "buck", "boost", "flyback", "forward",
            "switch", "converter", "regulator", "inductor", "choke",
            "变压器", "开关管", "功率电感", "dc-dc", "转换器",
            "mp1584", "lm2596", "xl4015", "sy8120", "sy8009",
            "tps54331", "tps562201", "ncp1529", "mt3608",
            "ob2538", "ob2576", "cr6842", "cr6850",
        ],
        "footprints": ["transformer", "inductor", "sot-23-6", "sot-89", "soic-8"],
        "nets": ["VCC12V", "VCC5V", "VCC3V3", "VOUT", "SW", "BOOST", "BUCK"],
    },
    FunctionalGroup.POWER_OUTPUT: {
        "refs": ["USB", "J"],
        "values": [
            "usb", "pd", "type-c", "charger", "charging",
            "充电", "输出", "协议", "usb-c", "usb-a",
            "fusb", "ch224k", "ip2721", "cypd", "stpusb",
            "fp6601", "fp6606", "sx1308",
        ],
        "footprints": ["usb", "connector", "type-c", "usb-a", "usb-c"],
        "nets": ["VBUS", "CC1", "CC2", "DP", "DM", "D+", "D-", "VOUT"],
    },
    FunctionalGroup.CONTROL: {
        "refs": ["U1", "U2", "U3"],
        "values": [
            "mcu", "microcontroller", "opto", "optocoupler", "reference",
            "op-amp", "comparator", "feedback", "isolator",
            "stm32", "esp32", "atmega", "gd32", "ch32",
            "光耦", "反馈", "运放", "比较器", "控制器",
        ],
        "footprints": ["qfn", "qfp", "bga", "tssop", "msop", "soic", "ssop"],
        "nets": ["FB", "COMP", "VREF", "SENSE"],
    },
    FunctionalGroup.PROTECTION: {
        "refs": ["SC", "TVS"],
        "values": [
            "esd", "tvs", "clamp", "surge", "overvoltage", "overcurrent",
            "protection", "suppressor", "gdt", "polyfuse",
            "保护", "防静电", "过压", "过流", "浪涌",
        ],
        "footprints": ["sod", "sot-23", "dfn"],
        "nets": ["ESD", "PROT", "OVP"],
    },
    FunctionalGroup.INTERFACE: {
        "refs": [],
        "values": [
            "uart", "rs485", "rs232", "can", "i2c", "spi",
            "ethernet", "wifi", "bluetooth",
            "接口", "通信", "串口",
            "ch340", "cp2102", "ft232", "max485", "sp3485",
        ],
        "footprints": ["connector", "rj45", "sma", "u.fl"],
        "nets": ["TX", "RX", "SDA", "SCL", "MOSI", "MISO", "SCK"],
    },
    FunctionalGroup.CRYSTAL: {
        "refs": ["Y"],
        "values": ["crystal", "oscillator", "resonator", "晶振", "谐振"],
        "footprints": ["crystal", "oscillator"],
        "nets": ["XTAL", "OSC"],
    },
}

# 被动元件关键词 (附属于最近的IC)
PASSIVE_REF_PREFIXES = {"R", "C", "L", "D", "FB", "RN", "TP"}
PASSIVE_VALUE_KEYWORDS = {"bypass", "decoupling", "filter", "pullup", "pulldown", "bootstrap"}


class NetlistTopologyAnalyzer:
    """
    网表拓扑分析器

    从网表数据中分析电路拓扑，识别功能分区。
    模仿工业级PCB设计的功能分区策略。

    使用方法:
        analyzer = NetlistTopologyAnalyzer()
        result = analyzer.analyze(components, nets)
    """

    def __init__(self):
        self._component_cache: Dict[str, FunctionalGroup] = {}

    def analyze(self, components: List[Dict], nets: List[Dict]) -> TopologyResult:
        """
        分析网表拓扑

        Args:
            components: 元件列表 [{"reference", "value", "footprint", "pins", ...}]
            nets: 网络列表 [{"name", "nodes": [{"ref", "pin"}], ...}]

        Returns:
            TopologyResult: 拓扑分析结果
        """
        logger.info(f"开始拓扑分析: {len(components)} 元件, {len(nets)} 网络")

        # Step 1: 识别功能分区
        functional_groups, component_group_map = self._identify_groups(components, nets)

        # Step 2: 计算分区亲和度
        group_affinity = self._calculate_affinity(functional_groups, nets)

        # Step 3: 检测功率流向
        power_flow = self._detect_power_flow(functional_groups, nets)

        # Step 4: 检测安规隔离需求
        isolation_reqs = self._detect_isolation_needs(functional_groups, nets)

        result = TopologyResult(
            functional_groups=functional_groups,
            group_affinity=group_affinity,
            isolation_requirements=isolation_reqs,
            power_flow=power_flow,
            component_group_map=component_group_map,
        )

        group_summary = {g.value: len(comps) for g, comps in functional_groups.items()}
        logger.info(f"拓扑分析完成: {group_summary}")
        return result

    def _identify_groups(
        self, components: List[Dict], nets: List[Dict]
    ) -> Tuple[Dict[FunctionalGroup, List[str]], Dict[str, FunctionalGroup]]:
        """
        将元件分组到功能分区

        策略:
        1. 非被动元件 → 关键词匹配到分区
        2. 被动元件 → 附属于连接到同一网络的最近IC
        """
        functional_groups: Dict[FunctionalGroup, List[str]] = {
            g: [] for g in FunctionalGroup
        }
        component_group_map: Dict[str, FunctionalGroup] = {}

        # 构建网络连接映射: ref → [net_name]
        ref_nets: Dict[str, List[str]] = {}
        for net in nets:
            net_name = net.get("name", "")
            for node in net.get("nodes", net.get("connections", [])):
                ref = node.get("ref", "")
                if ref:
                    ref_nets.setdefault(ref, []).append(net_name)

        # 第一遍: 分类非被动元件
        ic_refs: List[str] = []  # IC类元件 (用于被动元件附着)

        for comp in components:
            ref = comp.get("reference", "")
            if not ref:
                continue

            group = self._classify_component(comp, ref_nets.get(ref, []))

            if group != FunctionalGroup.PASSIVE:
                functional_groups[group].append(ref)
                component_group_map[ref] = group
                # 记录IC类元件
                if group in (FunctionalGroup.CONTROL, FunctionalGroup.POWER_CONVERT,
                             FunctionalGroup.INTERFACE, FunctionalGroup.POWER_OUTPUT):
                    ic_refs.append(ref)
            else:
                # 被动元件暂存，第二遍处理
                pass

        # 第二遍: 被动元件附着到最近的IC
        for comp in components:
            ref = comp.get("reference", "")
            if not ref or ref in component_group_map:
                continue

            ref_prefix = re.match(r'^([A-Z]+)', ref)
            if not ref_prefix:
                continue

            prefix = ref_prefix.group(1)
            if prefix not in PASSIVE_REF_PREFIXES:
                functional_groups[FunctionalGroup.PASSIVE].append(ref)
                component_group_map[ref] = FunctionalGroup.PASSIVE
                continue

            # 找到被动元件连接的IC
            parent_group = self._find_parent_group(ref, ref_nets.get(ref, []),
                                                    component_group_map, ic_refs)
            functional_groups[parent_group].append(ref)
            component_group_map[ref] = parent_group

        # 清除空分组
        functional_groups = {g: comps for g, comps in functional_groups.items() if comps}

        return functional_groups, component_group_map

    def _classify_component(self, comp: Dict, connected_nets: List[str]) -> FunctionalGroup:
        """分类单个元件到功能分区"""
        ref = comp.get("reference", "").upper()
        value = (comp.get("value", "") or "").lower()
        footprint = (comp.get("footprint", "") or "").lower()

        # 检查是否为被动元件
        ref_prefix = re.match(r'^([A-Z]+)', ref)
        if ref_prefix:
            prefix = ref_prefix.group(1)
            if prefix in PASSIVE_REF_PREFIXES and not any(
                kw in value for kw in PASSIVE_VALUE_KEYWORDS
            ):
                # 只有特殊的被动元件 (如大功率电感) 才单独分类
                if prefix == "L" and any(
                    kw in value for kw in ["power", "choke", "功率", "共模", "filter"]
                ):
                    return FunctionalGroup.POWER_CONVERT
                return FunctionalGroup.PASSIVE

        # 按优先级匹配各分区关键词
        for group, keywords in GROUP_KEYWORDS.items():
            # 检查参考编号
            for ref_kw in keywords.get("refs", []):
                if ref_kw.upper() in ref:
                    return group

            # 检查值
            for val_kw in keywords.get("values", []):
                if val_kw.lower() in value:
                    return group

            # 检查封装
            for fp_kw in keywords.get("footprints", []):
                if fp_kw.lower() in footprint:
                    return group

        # 检查连接的网络
        all_nets_upper = " ".join(n.upper() for n in connected_nets)
        for group, keywords in GROUP_KEYWORDS.items():
            for net_kw in keywords.get("nets", []):
                if net_kw.upper() in all_nets_upper:
                    return group

        # 默认: 控制类 (IC类元件)
        if ref.startswith("U") or ref.startswith("IC"):
            return FunctionalGroup.CONTROL

        return FunctionalGroup.PASSIVE

    def _find_parent_group(
        self,
        passive_ref: str,
        connected_nets: List[str],
        component_group_map: Dict[str, FunctionalGroup],
        ic_refs: List[str],
    ) -> FunctionalGroup:
        """找到被动元件应附属的功能分区"""
        # 查找被动元件通过共同网络连接到的IC
        for ic_ref in ic_refs:
            if ic_ref in component_group_map:
                return component_group_map[ic_ref]

        # 如果没有找到IC，根据连接的网络推断
        all_nets_upper = " ".join(n.upper() for n in connected_nets)

        if any(kw in all_nets_upper for kw in ["GND", "VCC", "VDD", "3V3", "5V"]):
            return FunctionalGroup.POWER_CONVERT

        return FunctionalGroup.CONTROL

    def _calculate_affinity(
        self,
        functional_groups: Dict[FunctionalGroup, List[str]],
        nets: List[Dict],
    ) -> Dict[Tuple[FunctionalGroup, FunctionalGroup], float]:
        """
        计算分区之间的亲和度 (0-1)

        亲和度越高，两个分区在布局时应越近。
        基于分区之间的网络连接数量计算。
        """
        affinity: Dict[Tuple[FunctionalGroup, FunctionalGroup], float] = {}

        groups = list(functional_groups.keys())
        if len(groups) < 2:
            return affinity

        # 构建每个分区的网络集合
        group_nets: Dict[FunctionalGroup, Set[str]] = {}
        for group, refs in functional_groups.items():
            nets_set = set()
            for net in nets:
                for node in net.get("nodes", net.get("connections", [])):
                    if node.get("ref", "") in refs:
                        nets_set.add(net.get("name", ""))
            group_nets[group] = nets_set

        # 计算两两亲和度 (Jaccard系数)
        for i, g1 in enumerate(groups):
            for g2 in groups[i + 1:]:
                n1 = group_nets.get(g1, set())
                n2 = group_nets.get(g2, set())
                shared = len(n1 & n2)
                union = len(n1 | n2)
                score = shared / union if union > 0 else 0.0

                # 功率流向连续性加分
                flow_bonus = self._flow_affinity_bonus(g1, g2)
                score = min(1.0, score + flow_bonus)

                if score > 0:
                    affinity[(g1, g2)] = score
                    affinity[(g2, g1)] = score

        return affinity

    def _flow_affinity_bonus(self, g1: FunctionalGroup, g2: FunctionalGroup) -> float:
        """功率流向连续性加分"""
        flow_pairs = [
            (FunctionalGroup.POWER_INPUT, FunctionalGroup.POWER_CONVERT),
            (FunctionalGroup.POWER_CONVERT, FunctionalGroup.POWER_OUTPUT),
            (FunctionalGroup.POWER_OUTPUT, FunctionalGroup.INTERFACE),
            (FunctionalGroup.CONTROL, FunctionalGroup.POWER_CONVERT),
            (FunctionalGroup.CRYSTAL, FunctionalGroup.CONTROL),
        ]
        for fg1, fg2 in flow_pairs:
            if (g1 == fg1 and g2 == fg2) or (g1 == fg2 and g2 == fg1):
                return 0.3
        return 0.0

    def _detect_power_flow(
        self,
        functional_groups: Dict[FunctionalGroup, List[str]],
        nets: List[Dict],
    ) -> List[FunctionalGroup]:
        """
        追踪功率流向

        典型流向: POWER_INPUT → POWER_CONVERT → POWER_OUTPUT
        """
        flow = []

        if FunctionalGroup.POWER_INPUT in functional_groups:
            flow.append(FunctionalGroup.POWER_INPUT)
        if FunctionalGroup.POWER_CONVERT in functional_groups:
            flow.append(FunctionalGroup.POWER_CONVERT)
        if FunctionalGroup.POWER_OUTPUT in functional_groups:
            flow.append(FunctionalGroup.POWER_OUTPUT)
        if FunctionalGroup.INTERFACE in functional_groups:
            flow.append(FunctionalGroup.INTERFACE)

        # 如果没有功率分区，返回默认流向
        if not flow:
            flow = list(functional_groups.keys())

        return flow

    def _detect_isolation_needs(
        self,
        functional_groups: Dict[FunctionalGroup, List[str]],
        nets: List[Dict],
    ) -> List[IsolationRequirement]:
        """
        检测安规隔离需求

        规则:
        - AC输入 vs USB输出 → 6mm隔离 (IEC 60950)
        - 高压初级 vs 低压次级 → 物理开槽
        """
        requirements = []

        has_power_input = FunctionalGroup.POWER_INPUT in functional_groups
        has_power_output = FunctionalGroup.POWER_OUTPUT in functional_groups
        has_interface = FunctionalGroup.INTERFACE in functional_groups

        # 检查是否有AC相关网络 (表示高压初级侧)
        ac_nets = {"AC", "L_LINE", "N_LINE", "LIVE", "NEUTRAL", "VIN_RAW", "HV"}
        has_ac = any(
            any(net.get("name", "").upper() in ac_nets for net in nets)
            for _ in [None] if has_power_input
        )

        if has_ac and (has_power_output or has_interface):
            requirements.append(IsolationRequirement(
                group1=FunctionalGroup.POWER_INPUT,
                group2=FunctionalGroup.POWER_OUTPUT,
                min_distance_mm=6.0,
                isolation_type="slot",
                voltage_range="220V AC",
                standard="IEC 60950-1",
            ))
            requirements.append(IsolationRequirement(
                group1=FunctionalGroup.POWER_INPUT,
                group2=FunctionalGroup.INTERFACE,
                min_distance_mm=6.0,
                isolation_type="clearance",
                voltage_range="220V AC",
                standard="IEC 60950-1",
            ))

        # 低压电源之间也需要隔离 (如5V和3.3V)
        if has_power_output and has_interface:
            requirements.append(IsolationRequirement(
                group1=FunctionalGroup.POWER_OUTPUT,
                group2=FunctionalGroup.INTERFACE,
                min_distance_mm=1.0,
                isolation_type="clearance",
                voltage_range="5V DC",
                standard="IPC-2221",
            ))

        return requirements

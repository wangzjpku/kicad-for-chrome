"""
网络分类器 - Network Classifier

功能:
1. 关键词匹配 - 根据网络名识别电源/地/高速信号
2. 元器件推断 - 根据连接的元器件类型推断网络类型
3. 用户标注 - 支持用户手动标注覆盖

Author: Claude Code
Date: 2026-03-30
Phase: Phase 4
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NetClass(Enum):
    """网络分类枚举"""
    POWER = "power"           # 电源网络
    GROUND = "ground"        # 地网络
    SIGNAL = "signal"        # 信号网络
    HIGH_SPEED = "high_speed"  # 高速信号
    DIFF_PAIR = "diff_pair"  # 差分对
    MIXED = "mixed"          # 混合信号
    UNKNOWN = "unknown"      # 未知


@dataclass
class NetInfo:
    """网络信息"""
    name: str                    # 网络名称
    net_class: NetClass = NetClass.UNKNOWN  # 分类结果
    trace_width: float = 0.2   # 建议走线宽度 (mm)
    is_pour: bool = False       # 是否需要铺铜
    connected_components: List[str] = field(default_factory=list)  # 连接的元件
    current_ma: float = 0.0     # 电流 (mA)
    priority: int = 10           # 布线优先级 (1=最高)
    is_diff_pair_pos: bool = False  # 差分对正端
    is_diff_pair_neg: bool = False  # 差分对负端
    diff_pair_partner: Optional[str] = None  # 差分对伙伴网络

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "class": self.net_class.value,
            "trace_width": self.trace_width,
            "is_pour": self.is_pour,
            "connected_components": self.connected_components,
            "current_ma": self.current_ma,
            "priority": self.priority,
        }


# ========== 关键词匹配规则 ==========

POWER_KEYWORDS: Set[str] = {
    "VCC", "VDD", "VCC3V3", "VCC5V", "VCC12V", "VCC24V",
    "5V", "3V3", "12V", "24V", "VIN", "VOUT", "VBUS",
    "PWR", "POWER", "BAT", "VBAT", "AVCC", "DVDD",
}

GROUND_KEYWORDS: Set[str] = {
    "GND", "AGND", "DGND", "SGND", "EARTH", "GROUND",
    "VSS", "AVSS", "DVSS",
}

HIGH_SPEED_KEYWORDS: Set[str] = {
    "USB", "PCIe", "DDR", "HDMI", "DP", "ETH", "MIPI",
    "PCIE", "SATA", "QSPI", "SDIO", "CAMERA", "CSI",
    "DSI", "I2S", "SPI", "UART",  # 高速接口（排除普通UART）
}

# 差分对关键词
DIFF_PAIR_PATTERNS = [
    ("USB_D+", "USB_D-"),
    ("USB_DP", "USB_DM"),
    ("ETH_TX+", "ETH_TX-"),
    ("ETH_RX+", "ETH_RX-"),
    ("DP+", "DP-"),
    ("DM+", "DM-"),
]

# 电源芯片关键词（连接后推断为电源网络）
POWER_IC_KEYWORDS = {
    "LDO", "DCDC", "PMIC", "MP1584", "AMS1117", "TPS", "LM",
    "7805", "7805", "1117", "buck", "boost", "regulator",
    "CHARGER", "BATTERY", "IC",
}


class NetClassifier:
    """
    网络分类器

    分类流程:
    1. 关键词匹配 → 初步分类
    2. 元器件推断 → 修正分类
    3. 用户标注 → 最终结果（覆盖）
    """

    def __init__(self):
        self.classified_nets: Dict[str, NetInfo] = {}

    def classify(
        self,
        schematic_data: Dict,
        user_annotations: Optional[Dict] = None,
    ) -> Dict[str, NetInfo]:
        """
        对原理图中的所有网络进行分类

        Args:
            schematic_data: 原理图数据 {"components": [...], "nets": [...]}
            user_annotations: 用户标注 {"NET_NAME": {"class": "power", "current_ma": 1000}}

        Returns:
            Dict[str, NetInfo]: 网络名称 → 网络信息
        """
        self.classified_nets = {}

        # Step 1: 收集网络和组件信息
        nets_data = schematic_data.get("nets", [])
        components = schematic_data.get("components", [])

        # 构建元件类型映射
        component_types = self._build_component_type_map(components)

        # Step 2: 关键词匹配 - 初步分类
        for net in nets_data:
            net_name = net.get("name", "")
            if not net_name:
                continue

            # 收集连接到这个网络的元件
            connections = net.get("nodes", net.get("connections", []))
            connected_refs = [c.get("ref", "") for c in connections]

            net_info = NetInfo(
                name=net_name,
                connected_components=connected_refs,
            )

            # 关键词匹配
            self._classify_by_keywords(net_name, net_info)

            # 元器件推断
            self._classify_by_components(connected_refs, component_types, net_info)

            # 差分对检测
            self._detect_diff_pair(net_name, net_info)

            self.classified_nets[net_name] = net_info

        # Step 3: 用户标注覆盖
        if user_annotations:
            self._apply_user_annotations(user_annotations)

        # Step 4: 第二次元器件推断（考虑差分对）
        self._refine_diff_pairs()

        logger.info(f"网络分类完成: {len(self.classified_nets)} 个网络")
        return self.classified_nets

    def _build_component_type_map(self, components: List[Dict]) -> Dict[str, str]:
        """构建元件参考编号 → 元件类型的映射"""
        type_map = {}
        for comp in components:
            ref = comp.get("reference", "")
            value = comp.get("value", "")
            footprint = comp.get("footprint", "")
            # 简单规则：根据参考编号前缀判断
            if ref.startswith("U"):
                type_map[ref] = "IC"
            elif ref.startswith("C"):
                type_map[ref] = "CAP"
            elif ref.startswith("R"):
                type_map[ref] = "RES"
            elif ref.startswith("L"):
                type_map[ref] = "IND"
            elif ref.startswith("D"):
                type_map[ref] = "DIODE"
            elif ref.startswith("J"):
                type_map[ref] = "CONNECTOR"
            elif ref.startswith("Y"):
                type_map[ref] = "CRYSTAL"
            else:
                type_map[ref] = value if value else "UNKNOWN"
        return type_map

    def _classify_by_keywords(self, net_name: str, net_info: NetInfo):
        """根据网络名关键词进行分类"""
        name_upper = net_name.upper()
        name_clean = name_upper.lstrip("/")  # 去掉开头的 /

        # 地网络
        if any(gnd in name_clean for gnd in [g.upper() for g in GROUND_KEYWORDS]):
            net_info.net_class = NetClass.GROUND
            net_info.is_pour = True  # 地网络默认铺铜
            net_info.priority = 1
            net_info.trace_width = 0.5
            return

        # 电源网络
        if any(pwr in name_clean for pwr in [p.upper() for p in POWER_KEYWORDS]):
            net_info.net_class = NetClass.POWER
            net_info.priority = 2
            net_info.trace_width = 0.5
            return

        # 高速信号
        if any(hs in name_clean for hs in [h.upper() for h in HIGH_SPEED_KEYWORDS]):
            net_info.net_class = NetClass.HIGH_SPEED
            net_info.priority = 3
            net_info.trace_width = 0.2
            return

        # 未知
        net_info.net_class = NetClass.UNKNOWN
        net_info.priority = 10
        net_info.trace_width = 0.15

    def _classify_by_components(
        self,
        connected_refs: List[str],
        component_types: Dict[str, str],
        net_info: NetInfo,
    ):
        """根据连接的元器件类型修正分类"""
        # 如果已经分类为电源或地，不再修改
        if net_info.net_class in (NetClass.POWER, NetClass.GROUND):
            return

        # 检查是否连接到电源芯片
        has_power_ic = False
        has_mcu = False
        has_connector = False

        for ref in connected_refs:
            comp_type = component_types.get(ref, "UNKNOWN")

            # 电源芯片
            if "LDO" in ref or "DCDC" in ref or "REG" in ref or "POWER" in ref.upper():
                has_power_ic = True

            # MCU/处理器
            if any(mcu in ref.upper() for mcu in ["STM", "ESP", "ATMEGA", "PIC", "MCU", "CPU"]):
                has_mcu = True

            # 连接器
            if "USB" in ref.upper() or "CONN" in ref.upper() or "J" in ref:
                has_connector = True

        # 如果连接到电源芯片且未被分类为电源
        if has_power_ic and net_info.net_class == NetClass.UNKNOWN:
            net_info.net_class = NetClass.POWER
            net_info.priority = 4
            net_info.trace_width = 0.4

        # 如果是 MCU 电源域
        if has_mcu and has_connector and net_info.net_class == NetClass.UNKNOWN:
            # 可能是高速信号
            net_info.net_class = NetClass.SIGNAL
            net_info.priority = 5
            net_info.trace_width = 0.2

    def _detect_diff_pair(self, net_name: str, net_info: NetInfo):
        """检测差分对"""
        name_upper = net_name.upper()

        for pos_pattern, neg_pattern in DIFF_PAIR_PATTERNS:
            if pos_pattern.upper() in name_upper:
                net_info.is_diff_pair_pos = True
                net_info.diff_pair_partner = net_name.replace(pos_pattern, neg_pattern)
                net_info.net_class = NetClass.DIFF_PAIR
                net_info.priority = 3
                net_info.trace_width = 0.2
                return
            if neg_pattern.upper() in name_upper:
                net_info.is_diff_pair_neg = True
                net_info.diff_pair_partner = net_name.replace(neg_pattern, pos_pattern)
                net_info.net_class = NetClass.DIFF_PAIR
                net_info.priority = 3
                net_info.trace_width = 0.2
                return

    def _refine_diff_pairs(self):
        """第二次处理：完善差分对信息"""
        for net_name, net_info in self.classified_nets.items():
            if net_info.is_diff_pair_pos or net_info.is_diff_pair_neg:
                partner_name = net_info.diff_pair_partner
                if partner_name and partner_name in self.classified_nets:
                    partner = self.classified_nets[partner_name]
                    # 确保伙伴网络也被标记为差分对
                    if not partner.is_diff_pair_pos and not partner.is_diff_pair_neg:
                        partner.is_diff_pair_pos = net_info.is_diff_pair_neg
                        partner.is_diff_pair_neg = net_info.is_diff_pair_pos
                        partner.diff_pair_partner = net_name

    def _apply_user_annotations(self, annotations: Dict):
        """应用用户标注覆盖"""
        for net_name, annotation in annotations.items():
            if net_name not in self.classified_nets:
                # 如果网络不存在，创建新的
                self.classified_nets[net_name] = NetInfo(name=net_name)

            net_info = self.classified_nets[net_name]

            # 覆盖分类
            if "class" in annotation:
                class_map = {
                    "power": NetClass.POWER,
                    "ground": NetClass.GROUND,
                    "signal": NetClass.SIGNAL,
                    "high_speed": NetClass.HIGH_SPEED,
                    "diff_pair": NetClass.DIFF_PAIR,
                }
                if annotation["class"] in class_map:
                    net_info.net_class = class_map[annotation["class"]]

            # 覆盖电流
            if "current_ma" in annotation:
                net_info.current_ma = float(annotation["current_ma"])

            # 覆盖铺铜
            if "is_pour" in annotation:
                net_info.is_pour = annotation["is_pour"]

            # 覆盖走线宽度
            if "trace_width" in annotation:
                net_info.trace_width = float(annotation["trace_width"])

    def get_net_info(self, net_name: str) -> Optional[NetInfo]:
        """获取指定网络的信息"""
        return self.classified_nets.get(net_name)

    def get_power_nets(self) -> List[NetInfo]:
        """获取所有电源网络"""
        return [n for n in self.classified_nets.values() if n.net_class == NetClass.POWER]

    def get_ground_nets(self) -> List[NetInfo]:
        """获取所有地网络"""
        return [n for n in self.classified_nets.values() if n.net_class == NetClass.GROUND]

    def get_high_speed_nets(self) -> List[NetInfo]:
        """获取所有高速信号网络"""
        return [n for n in self.classified_nets.values() if n.net_class == NetClass.HIGH_SPEED]

    def get_diff_pair_nets(self) -> List[NetInfo]:
        """获取所有差分对网络"""
        return [n for n in self.classified_nets.values() if n.net_class == NetClass.DIFF_PAIR]

    def get_pour_nets(self) -> List[NetInfo]:
        """获取所有需要铺铜的网络"""
        return [n for n in self.classified_nets.values() if n.is_pour]


def classify_nets(
    schematic_data: Dict,
    user_annotations: Optional[Dict] = None,
) -> Dict[str, NetInfo]:
    """
    便捷函数：对原理图中的所有网络进行分类

    Args:
        schematic_data: 原理图数据 {"components": [...], "nets": [...]}
        user_annotations: 用户标注

    Returns:
        Dict[str, NetInfo]: 网络名称 → 网络信息
    """
    classifier = NetClassifier()
    return classifier.classify(schematic_data, user_annotations)

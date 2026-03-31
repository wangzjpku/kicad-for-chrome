# -*- coding: utf-8 -*-
"""
Net Classifier - Identify diff pairs, power nets, high-speed nets, etc.

Automatically classifies nets by name patterns and component connections
for proper routing strategy selection.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class NetType(Enum):
    """Network classification"""
    DIFF_PAIR = "diff_pair"
    POWER = "power"
    GROUND = "ground"
    HIGH_SPEED = "high_speed"
    RF = "rf"
    ANALOG = "analog"
    CLOCK = "clock"
    RESET = "reset"
    GENERAL = "general"


@dataclass
class DiffPair:
    """Identified differential pair"""
    name: str
    pos_net: str
    neg_net: str
    target_impedance: float = 90.0  # ohms, default USB
    max_length_mismatch: float = 0.1  # mm
    interface_type: str = "usb"  # usb/hdmi/pcie/ethernet/custom

    @property
    def gap(self) -> float:
        """Default gap based on interface type"""
        gaps = {"usb": 0.15, "hdmi": 0.10, "pcie": 0.12, "ethernet": 0.15, "custom": 0.15}
        return gaps.get(self.interface_type, 0.15)

    @property
    def trace_width(self) -> float:
        """Default trace width based on interface type"""
        widths = {"usb": 0.20, "hdmi": 0.15, "pcie": 0.15, "ethernet": 0.20, "custom": 0.20}
        return widths.get(self.interface_type, 0.20)


@dataclass
class NetClassification:
    """Classification result for a net"""
    net_name: str
    net_type: NetType
    priority: int = 50  # routing priority (lower = route first)
    trace_width: float = 0.25  # mm
    clearance: float = 0.2  # mm
    max_length: Optional[float] = None
    diff_pair: Optional[DiffPair] = None


# ── Pattern definitions ──────────────────────────────────────

# Diff pair suffix patterns (positive, negative)
DIFF_PAIR_PATTERNS = [
    (r"(.+)[_\-](D[P\+]|TX[P\+]|DP|DATA[P\+]|SDA|VIN)", r"\1_\2"),
    (r"(.+)[_\-](DN|D[N\-]|TX[N\-]|DN|DATA[N\-]|SCL|VIP)", r"\1_\2"),
]

# Common diff pair base names
DIFF_PAIR_NAMES = {
    # USB
    "USB_DP": "USB_DN", "USB_D_P": "USB_D_N", "USB_TX_P": "USB_TX_N", "USB_RX_P": "USB_RX_N",
    # HDMI
    "TMDS_DATA0_P": "TMDS_DATA0_N", "TMDS_DATA1_P": "TMDS_DATA1_N",
    "TMDS_DATA2_P": "TMDS_DATA2_N", "TMDS_CLK_P": "TMDS_CLK_N",
    "HDMI_D2_P": "HDMI_D2_N", "HDMI_D1_P": "HDMI_D1_N", "HDMI_D0_P": "HDMI_D0_N",
    # PCIe
    "PCIe_TX_P": "PCIe_TX_N", "PCIe_RX_P": "PCIe_RX_N",
    "PCIE_TX_P": "PCIE_TX_N", "PCIE_RX_P": "PCIE_RX_N",
    "PET_P": "PET_N", "PER_P": "PER_N",
    # Ethernet
    "ETH_TX_P": "ETH_TX_N", "ETH_RX_P": "ETH_RX_N",
    "MDI0_P": "MDI0_N", "MDI1_P": "MDI1_N",
    # Generic
    "DIFF_P": "DIFF_N", "DATA_P": "DATA_N", "SIGNAL_P": "SIGNAL_N",
}

# Impedance by interface
INTERFACE_IMPEDANCE = {
    "usb": 90.0, "usb3": 85.0,
    "hdmi": 100.0, "displayport": 100.0,
    "pcie": 85.0,
    "ethernet": 100.0,
    "sata": 100.0,
    "custom": 90.0,
}

# Power net patterns
POWER_PATTERNS = [
    r"^(VCC|VDD|VIN|3V3|5V|3\.3V|5\.0V|1V8|1\.8V|2V5|2\.5V|12V|24V|VSYS|VBAT|VBUS)$",
    r"^(VCC[A-Z0-9_]*|VDD[A-Z0-9_]*|VIN[A-Z0-9_]*)$",
    r"^P(OWER|WR)[_\-]",
]

# Ground net patterns
GROUND_PATTERNS = [
    r"^(GND|DGND|AGND|PGND|SGND|EGND|CHASSIS|EARTH|GNDD|GNDA)$",
    r"^GND[_\-]",
    r"^GROUND",
]

# High-speed patterns
HIGH_SPEED_PATTERNS = [
    r"(SDIO|SDRAM|DDR|SPI|QSPI|UART|I2C|CAN|JTAG|SWD)",
    r"(CLK|CLOCK|MCLK|SCLK|PCLK|HCLK|FCLK)",
    r"(SDA|SCL|MOSI|MISO|SCK|CS|TXD?|RXD?)",
]

# RF patterns
RF_PATTERNS = [
    r"^(RF|ANT|ANTENNA|RF_[A-Z])",
    r"(RF_IN|RF_OUT|RFIO|ANT_IN|ANT_OUT)",
]


class NetClassifier:
    """Classify nets for routing strategy selection."""

    def __init__(self):
        self.classifications: Dict[str, NetClassification] = {}
        self.diff_pairs: List[DiffPair] = []

    def classify_all(self, net_names: List[str]) -> Dict[str, NetClassification]:
        """Classify all nets and identify diff pairs."""
        # Step 1: Classify individual nets
        for name in net_names:
            self.classifications[name] = self._classify_single(name)

        # Step 2: Find diff pairs
        self._find_diff_pairs(net_names)

        # Step 3: Update classifications for diff pair nets
        for dp in self.diff_pairs:
            if dp.pos_net in self.classifications:
                c = self.classifications[dp.pos_net]
                c.net_type = NetType.DIFF_PAIR
                c.diff_pair = dp
                c.priority = 10  # High priority
                c.trace_width = dp.trace_width
            if dp.neg_net in self.classifications:
                c = self.classifications[dp.neg_net]
                c.net_type = NetType.DIFF_PAIR
                c.diff_pair = dp
                c.priority = 10
                c.trace_width = dp.trace_width

        return self.classifications

    def _classify_single(self, name: str) -> NetClassification:
        """Classify a single net."""
        upper = name.upper()

        # Check power
        for pattern in POWER_PATTERNS:
            if re.match(pattern, upper):
                return NetClassification(
                    net_name=name, net_type=NetType.POWER,
                    priority=5, trace_width=0.5, clearance=0.2,
                )

        # Check ground
        for pattern in GROUND_PATTERNS:
            if re.match(pattern, upper):
                return NetClassification(
                    net_name=name, net_type=NetType.GROUND,
                    priority=3, trace_width=0.5, clearance=0.2,
                )

        # Check RF
        for pattern in RF_PATTERNS:
            if re.search(pattern, upper):
                return NetClassification(
                    net_name=name, net_type=NetType.RF,
                    priority=15, trace_width=0.25, clearance=0.3,
                )

        # Check clock
        if re.search(r"(CLK|CLOCK|MCLK|SCLK|PCLK)", upper):
            return NetClassification(
                net_name=name, net_type=NetType.CLOCK,
                priority=20, trace_width=0.2, clearance=0.2,
            )

        # Check high-speed
        for pattern in HIGH_SPEED_PATTERNS:
            if re.search(pattern, upper):
                return NetClassification(
                    net_name=name, net_type=NetType.HIGH_SPEED,
                    priority=25, trace_width=0.2, clearance=0.2,
                )

        # Check analog
        if re.search(r"(ADC|DAC|ANALOG|AUDIO|MIC|SPK|AIN|AOUT)", upper):
            return NetClassification(
                net_name=name, net_type=NetType.ANALOG,
                priority=40, trace_width=0.25, clearance=0.25,
            )

        # Check reset
        if re.search(r"(RESET|RST|NRST)", upper):
            return NetClassification(
                net_name=name, net_type=NetType.RESET,
                priority=60, trace_width=0.2, clearance=0.2,
            )

        # Default: general signal
        return NetClassification(
            net_name=name, net_type=NetType.GENERAL,
            priority=50, trace_width=0.25, clearance=0.2,
        )

    def _find_diff_pairs(self, net_names: List[str]):
        """Identify differential pairs from net names."""
        name_set = set(n.upper() for n in net_names)
        used = set()

        # Method 1: Known pair names
        for pos_name, neg_name in DIFF_PAIR_NAMES.items():
            if pos_name.upper() in name_set and neg_name.upper() in name_set:
                interface = self._detect_interface(pos_name)
                impedance = INTERFACE_IMPEDANCE.get(interface, 90.0)
                dp = DiffPair(
                    name=pos_name.replace("_P", "").replace("_DP", ""),
                    pos_net=self._find_original(pos_name, net_names),
                    neg_net=self._find_original(neg_name, net_names),
                    target_impedance=impedance,
                    interface_type=interface,
                )
                self.diff_pairs.append(dp)
                used.add(pos_name.upper())
                used.add(neg_name.upper())

        # Method 2: Pattern matching (_P/_N, _+/-, _DP/_DN)
        patterns = [
            (r"(.+)[_](P|[+])$", r"\1_[N\-]"),
            (r"(.+)[_](DP|TX_P|VIN_P)$", None),
            (r"(.+)[_](N|[\-])$", None),
        ]

        for net in net_names:
            upper = net.upper()
            if upper in used:
                continue

            # Try _P / _N pattern
            for suffix_pos, suffix_neg in [("_P", "_N"), ("_DP", "_DN"), ("_TX_P", "_TX_N"),
                                            ("_RX_P", "_RX_N"), ("_+", "_-")]:
                if upper.endswith(suffix_pos):
                    base = upper[:-len(suffix_pos)]
                    neg_candidate = base + suffix_neg
                    if neg_neg := self._find_original(neg_candidate, net_names):
                        interface = self._detect_interface(upper)
                        dp = DiffPair(
                            name=base,
                            pos_net=net,
                            neg_net=neg_neg,
                            target_impedance=INTERFACE_IMPEDANCE.get(interface, 90.0),
                            interface_type=interface,
                        )
                        self.diff_pairs.append(dp)
                        used.add(upper)
                        used.add(neg_candidate)
                        break

    def _detect_interface(self, name: str) -> str:
        """Detect interface type from net name."""
        upper = name.upper()
        if "USB" in upper:
            return "usb3" if "3" in upper else "usb"
        if any(x in upper for x in ["HDMI", "TMDS"]):
            return "hdmi"
        if any(x in upper for x in ["PCIE", "PCI"]):
            return "pcie"
        if any(x in upper for x in ["ETH", "MDIO", "MDI"]):
            return "ethernet"
        if "SATA" in upper:
            return "sata"
        if "DP" in upper and "HDMI" not in upper:
            return "displayport"
        return "custom"

    def _find_original(self, target_upper: str, net_names: List[str]) -> Optional[str]:
        """Find original case net name matching uppercase target."""
        for name in net_names:
            if name.upper() == target_upper:
                return name
        return None

    def get_routing_order(self) -> List[str]:
        """Get nets sorted by routing priority."""
        return sorted(
            self.classifications.keys(),
            key=lambda n: self.classifications[n].priority,
        )

    def get_diff_pair_nets(self) -> List[str]:
        """Get all nets that belong to diff pairs."""
        nets = []
        for dp in self.diff_pairs:
            nets.append(dp.pos_net)
            nets.append(dp.neg_net)
        return nets

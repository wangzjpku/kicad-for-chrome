# -*- coding: utf-8 -*-
"""
DSN Exporter - Convert PCB data to Specctra DSN format for FreeRouter input.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class DSNComponent:
    ref: str
    footprint: str
    x: float
    y: float
    rotation: float = 0.0
    side: str = "front"
    pins: List[Tuple[str, float, float]] = field(default_factory=list)


@dataclass
class DSNNet:
    name: str
    pins: List[Tuple[str, str]] = field(default_factory=list)
    class_name: str = "Default"


@dataclass
class DSNSegment:
    start_x: float
    start_y: float
    end_x: float
    end_y: float


class DSNExporter:
    """PCB data to Specctra DSN format converter."""

    def __init__(self, unit="mm", resolution=10):
        self.unit = unit
        self.resolution = resolution
        self.components: List[DSNComponent] = []
        self.nets: List[DSNNet] = []
        self.board_outline: List[DSNSegment] = []
        self.trace_widths: Dict[str, float] = {"Default": 0.25}
        self.clearances: Dict[str, float] = {"Default": 0.2}
        self.layers = ["F.Cu", "B.Cu"]

    def add_component(self, comp: DSNComponent):
        self.components.append(comp)

    def add_net(self, net: DSNNet):
        self.nets.append(net)

    def set_board_outline(self, points: List[Tuple[float, float]]):
        if len(points) < 3:
            return
        self.board_outline = []
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            self.board_outline.append(DSNSegment(p1[0], p1[1], p2[0], p2[1]))

    def add_net_class(self, name: str, trace_width: float, clearance: float):
        self.trace_widths[name] = trace_width
        self.clearances[name] = clearance

    def export(self) -> str:
        """Export full DSN file content."""
        L = []  # output lines

        L.append("(pcb \"\\\\generated_board.dsn\"")
        L.append("  (parser")
        L.append("    (string_quote \\")
        L.append("    (space_in_quoted_tokens on)")
        L.append("    (host_cad \"KiCad AI\")")
        L.append("    (host_version \"0.9.13\")")
        L.append("  )")
        L.append(f"  (resolution {self.unit} {10 ** self.resolution})")
        L.append("")

        # Structure
        L.append("  (structure")
        for idx, layer in enumerate(self.layers):
            dsn_layer = self._layer_name(layer)
            L.append(f"    (layer {dsn_layer}")
            L.append("      (type signal)")
            L.append("      (property")
            L.append(f"        (index {idx})")
            L.append("      )")
            L.append("    )")

        if self.board_outline:
            L.append("    (boundary")
            L.append("      (path pcb 0")
            for seg in self.board_outline:
                L.append(f"        {self._f(seg.start_x)} {self._f(seg.start_y)}")
            # close polygon
            first = self.board_outline[0]
            L.append(f"        {self._f(first.start_x)} {self._f(first.start_y)}")
            L.append("      )")
            L.append("    )")

        L.append("    (rule")
        default_cl = self.clearances.get("Default", 0.2)
        L.append(f"      (clearance {self._f(default_cl)}")
        L.append("        (type default)")
        L.append("        (layer all)")
        L.append("      )")
        L.append("    )")
        L.append("  )  # end structure")
        L.append("")

        # Placement
        L.append("  (placement")
        for comp in self.components:
            side = "front" if comp.side == "front" else "back"
            L.append(f"    (component \"{comp.footprint}\"")
            L.append(f"      (place \"{comp.ref}\" {self._f(comp.x)} {self._f(comp.y)}")
            L.append(f"        (side {side})")
            L.append(f"        (rotation {self._f(comp.rotation)})")
            L.append(f"        (PN \"{comp.ref}\")")
            for pin_name, px, py in comp.pins:
                L.append(f"        (pin \"{pin_name}\" {self._f(px)} {self._f(py)})")
            L.append("      )")
            L.append("    )")
        L.append("  )  # end placement")
        L.append("")

        # Network
        L.append("  (network")
        L.append("    (nets")
        for net in self.nets:
            L.append(f"      (net \"{net.name}\"")
            if net.pins:
                L.append("        (pins")
                for ref, pin in net.pins:
                    L.append(f"          \"{ref}-{pin}\"")
                L.append("        )")
            L.append("      )")
        L.append("    )")

        # Net class
        L.append("    (class \"Default\"")
        for net in self.nets:
            L.append(f"      \"{net.name}\"")
        default_w = self.trace_widths.get("Default", 0.25)
        default_c = self.clearances.get("Default", 0.2)
        L.append("      (rule")
        L.append(f"        (width {self._f(default_w)})")
        L.append(f"        (clearance {self._f(default_c)})")
        L.append("      )")
        L.append("    )")
        L.append("  )  # end network")
        L.append("")

        # Wiring (empty - filled by router)
        L.append("  (wiring")
        L.append("  )")

        L.append(")  # end pcb")
        return "\n".join(L)

    def export_to_file(self, filepath: str):
        content = self.export()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"DSN exported to {filepath}")

    def _layer_name(self, layer: str) -> str:
        mapping = {"F.Cu": "Front", "B.Cu": "Bottom", "In1.Cu": "Inner1", "In2.Cu": "Inner2"}
        return mapping.get(layer, layer)

    def _f(self, value: float) -> str:
        return f"{value:.{self.resolution}f}"


def export_pcb_to_dsn(pcb_data: Dict, filepath: Optional[str] = None) -> str:
    """Convenience function: export PCB data dict to DSN format."""
    exporter = DSNExporter()

    outline = pcb_data.get("board_outline", [])
    if outline and len(outline) >= 3:
        points = [(p.get("x", 0), p.get("y", 0)) for p in outline]
        exporter.set_board_outline(points)

    for fp in pcb_data.get("footprints", []):
        comp = DSNComponent(
            ref=fp.get("reference", "U?"),
            footprint=fp.get("footprint_name", "unknown"),
            x=fp.get("x", 0), y=fp.get("y", 0),
            rotation=fp.get("rotation", 0),
            side="front" if fp.get("layer", "F.Cu") == "F.Cu" else "back",
        )
        for pad in fp.get("pads", []):
            comp.pins.append((pad.get("name", ""), pad.get("x", 0) + comp.x, pad.get("y", 0) + comp.y))
        exporter.add_component(comp)

    for net_info in pcb_data.get("nets", []):
        net = DSNNet(name=net_info.get("name", ""))
        for pin in net_info.get("pins", []):
            net.pins.append((pin.get("ref", ""), pin.get("pin", "")))
        if net_info.get("class"):
            net.class_name = net_info["class"]
        exporter.add_net(net)

    content = exporter.export()
    if filepath:
        exporter.export_to_file(filepath)
    return content

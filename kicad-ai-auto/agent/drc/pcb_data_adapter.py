"""
PCB Data Adapter for DRC Engine

Phase 7A: Converts between KiCad IPC/project data formats and AdvancedDRCEngine.check() format.

This file is part of the bridge layer that PCB data can come from multiple sources:
    IPC data from kicad_ipc_manager.get_full_pcb_data()
    Project data from projects_data.json / pcb_data.json
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PCBDataAdapter:
    """Converts between various PCB data sources and AdvancedDRCEngine.check() format."""

    @staticmethod
    def from_ipc(ipc_manager) -> Optional[Dict[str, Any]]:
        """Adapt KiCad IPC Manager data -> AdvancedDRCEngine.check() format.

        Args:
            ipc_manager: KiCadIPCManager instance with active connection

        Returns:
            Dict with keys: components, tracks, vias, pads, board, nets
            or None if adaptation fails
        """
        try:
            ipc_data = ipc_manager.get_full_pcb_data()
            if not ipc_data:
                return None

            board = ipc_data.get("board", {})
            if not board:
                board_edges = ipc_data.get("board_edges", [])
                if board_edges:
                    xs = [p.get("x", 0) for p in board_edges]
                    ys = [p.get("y", 0) for p in board_edges]
                    board = {
                        "width": max(xs) - min(xs) if xs else 100,
                        "height": max(ys) - min(ys) if ys else 80,
                    }
                else:
                    board = {"width": 100, "height": 80}

            # Adapt components/footprints
            components = []
            for fp in ipc_data.get("footprints", []):
                if not isinstance(fp, dict):
                    continue
                pos = fp.get("position", {})
                if not isinstance(pos, dict):
                    pos = {}
                components.append({
                    "reference": fp.get("reference", ""),
                    "footprint": fp.get("footprint", ""),
                    "x": pos.get("x", 0),
                    "y": pos.get("y", 0),
                    "width": fp.get("width", 5.0),
                    "height": fp.get("height", 5.0),
                    "layer": fp.get("layer", "F.Cu"),
                    "rotation": fp.get("rotation", 0),
                    "pins": fp.get("pins", []),
                })

            # Adapt tracks - merge start/end into points list
            tracks_list = []
            for track in ipc_data.get("tracks", []):
                if not isinstance(track, dict):
                    continue
                points = []
                start = track.get("start", {})
                end = track.get("end", {})
                if start and end:
                    points.append({"x": start.get("x", 0), "y": start.get("y", 0)})
                    points.append({"x": end.get("x", 0), "y": end.get("y", 0)})
                else:
                    # Already in points format
                    points = track.get("points", [])
                tracks_list.append({
                    "net": track.get("net", ""),
                    "layer": track.get("layer", "F.Cu"),
                    "width": track.get("width", 0.25),
                    "points": points,
                })

            # Adapt vias
            vias = []
            for via in ipc_data.get("vias", []):
                if isinstance(via, dict):
                    vias.append({
                        "x": via.get("x", 0),
                        "y": via.get("y", 0),
                        "net": via.get("net", ""),
                        "outer_diameter": via.get("size", via.get("outer_diameter", 0.6)),
                        "drill_diameter": via.get("drill", via.get("drill_diameter", 0.4)),
                    })

            # Extract pads from component pins
            pads = []
            for comp in components:
                for pin in comp.get("pins", []):
                    if not isinstance(pin, dict):
                        continue
                    pin_pos = pin.get("position", {})
                    if not isinstance(pin_pos, dict):
                        pin_pos = {"x": comp["x"], "y": comp["y"]}
                    pads.append({
                        "component": comp["reference"],
                        "pin": pin.get("number", ""),
                        "x": pin_pos.get("x", comp["x"]),
                        "y": pin_pos.get("y", comp["y"]),
                        "net": pin.get("net"),
                        "width": pin.get("width", 1.0),
                        "height": pin.get("height", 1.0),
                        "layer": pin.get("layer", "F.Cu"),
                    })

            # Classify nets
            classified_nets = _classify_nets(components, tracks_list)

            return {
                "components": components,
                "tracks": tracks_list,
                "vias": vias,
                "pads": pads,
                "board": board,
                "nets": classified_nets,
            }
        except Exception as e:
            logger.error(f"Failed to adapt IPC data: {e}")
            return None

    @staticmethod
    def from_project(project_data: dict) -> Optional[Dict[str, Any]]:
        """Adapt project JSON data -> AdvancedDRCEngine.check() format.

        Handles both flat project data and nested pcb_data format.

        Args:
            project_data: Project dict from projects_data.json or pcb_data.json

        Returns:
            Dict with keys: components, tracks, vias, pads, board, nets
            or None if adaptation fails
        """
        if not project_data:
            return None

        project = project_data.get("pcb", project_data)
        board = project_data.get("board", {})
        if not board or not isinstance(board, dict):
            board = {"width": 100, "height": 80}

        # Adapt components
        components = []
        for comp in project.get("footprints", project_data.get("components", [])):
            if not isinstance(comp, dict):
                continue
            pos = comp.get("position", {})
            if not isinstance(pos, dict):
                pos = {}
            components.append({
                "reference": comp.get("reference", ""),
                "footprint": comp.get("footprint", ""),
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "width": comp.get("width", 5.0),
                "height": comp.get("height", 5.0),
                "layer": comp.get("layer", "F.Cu"),
                "rotation": comp.get("rotation", 0),
                "pins": comp.get("pins", []),
            })

        # Adapt tracks - merge start/end into points
        tracks_list = []
        for track in project.get("tracks", []):
            if not isinstance(track, dict):
                continue
            points = []
            start = track.get("start", {})
            end = track.get("end", {})
            if start and end:
                points.append({"x": start.get("x", 0), "y": start.get("y", 0)})
                points.append({"x": end.get("x", 0), "y": end.get("y", 0)})
            else:
                points = track.get("points", [])
            tracks_list.append({
                "net": track.get("net", ""),
                "layer": track.get("layer", ""),
                "width": track.get("width", 0.25),
                "points": points,
            })

        # Adapt vias
        vias = []
        for via in project.get("vias", []):
            if isinstance(via, dict):
                vias.append({
                    "x": via.get("x", 0),
                    "y": via.get("y", 0),
                    "net": via.get("net", ""),
                    "outer_diameter": via.get("size", via.get("outer_diameter", 0.6)),
                    "drill_diameter": via.get("drill", via.get("drill_diameter", 0.4)),
                })

        # Classify nets
        classified_nets = _classify_nets(components, tracks_list)

        return {
            "components": components,
            "tracks": tracks_list,
            "vias": vias,
            "pads": [],
            "board": board,
            "nets": classified_nets,
        }


def _classify_nets(
    components: list, tracks: list
) -> List[Dict[str, Any]]:
    """Classify nets using NetClassifier for DRC rule selection."""
    net_names: Set[str] = set()
    for comp in components:
        for pin in comp.get("pins", []):
            if isinstance(pin, dict) and pin.get("net"):
                net_names.add(pin["net"])
    for track in tracks:
        if track.get("net"):
            net_names.add(track["net"])

    classified = []
    for name in sorted(net_names):
        try:
            from pcb.net_classifier import NetClassifier as NC
            nc = NC.classify_net_name(name)
            classified.append({
                "name": name,
                "class": nc.value,
                "trace_width": _get_trace_width(nc),
            })
        except Exception:
            classified.append({"name": name, "class": "unknown", "trace_width": 0.2})

    return classified


def _get_trace_width(net_class) -> float:
    """Get recommended trace width based on net class."""
    widths = {
        "power": 0.5,
        "ground": 0.5,
        "high_speed": 0.15,
        "diff_pair": 0.1,
        "signal": 0.2,
    }
    return widths.get(nc_value, 0.2)

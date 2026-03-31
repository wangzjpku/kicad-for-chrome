# -*- coding: utf-8 -*-
"""
SES Importer - Parse Specctra SES format from FreeRouter output.

SES (Session) format contains routing results:
  (session ...) -> (routes ...) -> (network_out ...) -> (net ...) -> (wire ...)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class SESTrack:
    """A single track segment from SES"""
    net_name: str
    layer: str
    width: float
    points: List[Tuple[float, float]]  # [(x1,y1), (x2,y2), ...]
    route_type: str = "track"  # track/via


@dataclass
class SESSVia:
    """A via from SES"""
    net_name: str
    x: float
    y: float
    via_type: str = "via"


@dataclass
class SESImportResult:
    """Result of SES import"""
    success: bool
    tracks: List[SESTrack] = field(default_factory=list)
    vias: List[SESSVia] = field(default_factory=list)
    net_count: int = 0
    track_count: int = 0
    via_count: int = 0
    errors: List[str] = field(default_factory=list)
    message: str = ""


class SESImporter:
    """Parse Specctra SES routing results."""

    def __init__(self):
        self.tracks: List[SESTrack] = []
        self.vias: List[SESSVia] = []

    def parse(self, ses_content: str) -> SESImportResult:
        """Parse SES file content string."""
        try:
            tokens = self._tokenize(ses_content)
        except Exception as e:
            return SESImportResult(
                success=False, errors=[str(e)],
                message=f"Tokenization failed: {e}"
            )

        try:
            self._parse_session(tokens)
        except Exception as e:
            logger.warning(f"SES parse error: {e}")
            # Return partial results
            pass

        net_names = set(t.net_name for t in self.tracks)
        return SESImportResult(
            success=len(self.tracks) > 0,
            tracks=self.tracks,
            vias=self.vias,
            net_count=len(net_names),
            track_count=len(self.tracks),
            via_count=len(self.vias),
            message=f"Imported {len(self.tracks)} tracks, {len(self.vias)} vias across {len(net_names)} nets",
        )

    def parse_file(self, filepath: str) -> SESImportResult:
        """Parse SES from file path."""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse(content)

    def to_kicad_tracks(self) -> List[Dict]:
        """Convert imported tracks to KiCad track format."""
        kicad_tracks = []
        for track in self.tracks:
            layer = self._ses_to_kicad_layer(track.layer)
            for i in range(len(track.points) - 1):
                kicad_tracks.append({
                    "type": "track",
                    "start": {"x": track.points[i][0], "y": track.points[i][1]},
                    "end": {"x": track.points[i + 1][0], "y": track.points[i + 1][1]},
                    "width": track.width,
                    "layer": layer,
                    "net": track.net_name,
                })
        return kicad_tracks

    def to_kicad_vias(self) -> List[Dict]:
        """Convert imported vias to KiCad via format."""
        return [
            {
                "type": "via",
                "x": via.x,
                "y": via.y,
                "size": 0.8,
                "drill": 0.4,
                "net": via.net_name,
            }
            for via in self.vias
        ]

    # ── Tokenizer ─────────────────────────────────────────────

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize S-expression text into a list of tokens."""
        tokens = []
        i = 0
        while i < len(text):
            c = text[i]
            if c in " \t\n\r":
                i += 1
            elif c == "(":
                tokens.append("(")
                i += 1
            elif c == ")":
                tokens.append(")")
                i += 1
            elif c == '"':
                # Quoted string
                j = i + 1
                while j < len(text) and text[j] != '"':
                    if text[j] == "\\":
                        j += 1
                    j += 1
                tokens.append(text[i + 1:j])
                i = j + 1
            elif c == ";":
                # Comment - skip to end of line
                while i < len(text) and text[i] != "\n":
                    i += 1
            else:
                # Unquoted token
                j = i
                while j < len(text) and text[j] not in " \t\n\r()\";":
                    j += 1
                tokens.append(text[i:j])
                i = j
        return tokens

    # ── Parser ────────────────────────────────────────────────

    def _parse_session(self, tokens: List[str]):
        """Parse session and extract routes."""
        pos = 0
        while pos < len(tokens):
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                if tokens[pos + 1] == "session":
                    self._parse_block(tokens, pos + 2, ["routes"])
                elif tokens[pos + 1] == "routes":
                    self._parse_routes(tokens, pos + 2)
            pos += 1

    def _parse_routes(self, tokens: List[str], start: int):
        """Parse routes section."""
        pos = start
        while pos < len(tokens):
            if tokens[pos] == ")":
                break
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                if tokens[pos + 1] == "network_out":
                    self._parse_network_out(tokens, pos + 2)
                elif tokens[pos + 1] == "library_out":
                    # Skip library
                    pos = self._skip_block(tokens, pos + 2)
                    continue
            pos += 1

    def _parse_network_out(self, tokens: List[str], start: int):
        """Parse network_out section containing routed nets."""
        pos = start
        current_net = ""
        while pos < len(tokens):
            if tokens[pos] == ")":
                break
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                if tokens[pos + 1] == "net":
                    # Find net name
                    if pos + 2 < len(tokens) and tokens[pos + 2] != "(":
                        current_net = tokens[pos + 2].strip('"')
                        pos = self._parse_net_routes(tokens, pos + 3, current_net)
                        continue
                else:
                    pos = self._skip_block(tokens, pos + 2)
                    continue
            pos += 1

    def _parse_net_routes(self, tokens: List[str], start: int, net_name: str) -> int:
        """Parse routes for a specific net."""
        pos = start
        while pos < len(tokens):
            if tokens[pos] == ")":
                return pos + 1
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                if tokens[pos + 1] == "route":
                    pos = self._parse_route_wires(tokens, pos + 2, net_name)
                    continue
                else:
                    pos = self._skip_block(tokens, pos + 2)
                    continue
            pos += 1
        return pos

    def _parse_route_wires(self, tokens: List[str], start: int, net_name: str) -> int:
        """Parse wire segments within a route."""
        pos = start
        while pos < len(tokens):
            if tokens[pos] == ")":
                return pos + 1
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                if tokens[pos + 1] == "wire":
                    pos = self._parse_wire(tokens, pos + 2, net_name)
                    continue
                elif tokens[pos + 1] == "via":
                    pos = self._parse_via_token(tokens, pos + 2, net_name)
                    continue
                else:
                    pos = self._skip_block(tokens, pos + 2)
                    continue
            pos += 1
        return pos

    def _parse_wire(self, tokens: List[str], start: int, net_name: str) -> int:
        """Parse a single wire segment."""
        pos = start
        layer = "Front"
        width = 0.25
        points = []
        route_type = "track"

        while pos < len(tokens):
            if tokens[pos] == ")":
                break
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                key = tokens[pos + 1]
                if key == "layer" and pos + 2 < len(tokens):
                    layer = tokens[pos + 2].strip('"')
                    pos += 3
                elif key == "width" and pos + 2 < len(tokens):
                    try:
                        width = float(tokens[pos + 2])
                    except ValueError:
                        pass
                    pos += 3
                elif key == "type" and pos + 2 < len(tokens):
                    route_type = tokens[pos + 2].strip('"')
                    pos += 3
                elif key == "path":
                    # path follows: layer width x1 y1 x2 y2 ...
                    if pos + 3 < len(tokens):
                        # tokens[pos+2] = layer, tokens[pos+3] = width
                        pos += 2  # skip "path" and (
                        # Collect numeric tokens
                        while pos < len(tokens) and tokens[pos] != ")":
                            try:
                                val = float(tokens[pos])
                                points.append(val)
                            except ValueError:
                                pass
                            pos += 1
                    else:
                        pos = self._skip_block(tokens, pos + 2)
                else:
                    pos = self._skip_block(tokens, pos + 2)
                    continue
            else:
                # Standalone value (coordinate)
                try:
                    val = float(tokens[pos])
                    points.append(val)
                except ValueError:
                    pass
                pos += 1

        # Convert flat coordinate list to (x,y) pairs
        point_pairs = []
        for i in range(0, len(points) - 1, 2):
            point_pairs.append((points[i], points[i + 1]))

        if point_pairs:
            self.tracks.append(SESTrack(
                net_name=net_name,
                layer=layer,
                width=width,
                points=point_pairs,
                route_type=route_type,
            ))

        return pos + 1

    def _parse_via_token(self, tokens: List[str], start: int, net_name: str) -> int:
        """Parse a via placement."""
        pos = start
        x, y = 0.0, 0.0

        while pos < len(tokens):
            if tokens[pos] == ")":
                break
            try:
                val = float(tokens[pos])
                if x == 0.0:
                    x = val
                elif y == 0.0:
                    y = val
            except ValueError:
                pass
            pos += 1

        self.vias.append(SESSVia(net_name=net_name, x=x, y=y))
        return pos + 1

    def _parse_block(self, tokens: List[str], start: int, targets: List[str]) -> int:
        """Find and parse target blocks at the current level."""
        pos = start
        while pos < len(tokens):
            if tokens[pos] == ")":
                return pos + 1
            if tokens[pos] == "(" and pos + 1 < len(tokens):
                if tokens[pos + 1] in targets:
                    if tokens[pos + 1] == "routes":
                        self._parse_routes(tokens, pos + 2)
                    pos = self._skip_block(tokens, pos + 2)
                    continue
                else:
                    pos = self._skip_block(tokens, pos + 2)
                    continue
            pos += 1
        return pos

    def _skip_block(self, tokens: List[str], start: int) -> int:
        """Skip a balanced block and return position after it."""
        depth = 1
        pos = start
        while pos < len(tokens) and depth > 0:
            if tokens[pos] == "(":
                depth += 1
            elif tokens[pos] == ")":
                depth -= 1
            pos += 1
        return pos

    def _ses_to_kicad_layer(self, ses_layer: str) -> str:
        mapping = {"Front": "F.Cu", "Bottom": "B.Cu", "Inner1": "In1.Cu", "Inner2": "In2.Cu"}
        return mapping.get(ses_layer, ses_layer)

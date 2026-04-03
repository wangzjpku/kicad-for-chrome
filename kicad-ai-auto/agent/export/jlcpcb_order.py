"""
JLCPCB Order Package Generator - Phase 11B-1

Generates complete JLCPCB-compatible manufacturing package:
- Gerber files (ZIP)
- BOM CSV (JLCPCB format)
- CPL/Pick-and-Place file (JLCPCB format)
"""

import csv
import io
import json
import logging
import os
import zipfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class JLCPCBBOMItem:
    """JLCPCB BOM item format"""
    reference: str          # "U1,U2,U3"
    value: str              # "STM32F103C8T6"
    footprint: str          # "LQFP-48"
    lcsc_part: str = ""     # "C8304"

    def to_csv_row(self) -> List[str]:
        return [self.reference, self.value, self.footprint, self.lcsc_part]


@dataclass
class JLCPCBCPLItem:
    """JLCPCB CPL (pick-and-place) item format"""
    designator: str         # "U1"
    x: float                # mm
    y: float                # mm
    side: str               # "T" (top) or "B" (bottom)
    rotation: float         # degrees
    lcsc_part: str = ""     # "C8304"

    def to_csv_row(self) -> List[str]:
        return [
            self.designator,
            f"{self.x:.3f}",
            f"{self.y:.3f}",
            self.side,
            f"{self.rotation:.1f}",
            self.lcsc_part,
        ]


@dataclass
class JLCPCBOrderPackage:
    """Complete JLCPCB order package"""
    gerber_zip_path: Optional[str] = None
    bom_csv: str = ""
    cpl_csv: str = ""
    bom_items: List[JLCPCBBOMItem] = field(default_factory=list)
    cpl_items: List[JLCPCBCPLItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bom_csv": self.bom_csv,
            "cpl_csv": self.cpl_csv,
            "bom_item_count": len(self.bom_items),
            "cpl_item_count": len(self.cpl_items),
            "warnings": self.warnings,
        }


class JLCPCBOrderGenerator:
    """Generates JLCPCB-compatible manufacturing order packages."""

    # JLCPCB BOM CSV header
    BOM_HEADER = ["Comment", "Designator", "Footprint", "LCSC Part #"]

    # JLCPCB CPL CSV header
    CPL_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation", "LCSC Part #"]

    def generate_order(
        self,
        pcb_data: Dict[str, Any],
        gerber_dir: Optional[str] = None,
        output_dir: str = ".",
    ) -> JLCPCBOrderPackage:
        """
        Generate complete JLCPCB order package.

        Args:
            pcb_data: PCB data dict with footprints, board outline, etc.
            gerber_dir: Directory containing pre-generated Gerber files
            output_dir: Output directory for generated files
        """
        result = JLCPCBOrderPackage()

        # 1. Generate BOM CSV
        result.bom_items = self._generate_bom(pcb_data)
        result.bom_csv = self._bom_to_csv(result.bom_items)

        # 2. Generate CPL (pick-and-place) CSV
        result.cpl_items = self._generate_cpl(pcb_data)
        result.cpl_csv = self._cpl_to_csv(result.cpl_items)

        # 3. Package Gerber files into ZIP
        if gerber_dir and os.path.isdir(gerber_dir):
            zip_path = os.path.join(output_dir, "jlcpcb_gerber.zip")
            self._zip_gerbers(gerber_dir, zip_path)
            result.gerber_zip_path = zip_path

        # 4. Generate warnings for missing data
        self._validate_order(pcb_data, result)

        logger.info(
            f"[JLCPCB] Order package generated: "
            f"{len(result.bom_items)} BOM items, {len(result.cpl_items)} CPL items"
        )
        return result

    def _generate_bom(self, pcb_data: Dict[str, Any]) -> List[JLCPCBBOMItem]:
        """Generate BOM items from PCB data."""
        # Group components by value+footprint
        groups: Dict[str, Dict[str, Any]] = {}

        for fp in pcb_data.get("footprints", []):
            value = fp.get("value", "")
            footprint = fp.get("footprint", fp.get("library", ""))
            key = f"{value}|{footprint}"

            if key not in groups:
                groups[key] = {
                    "value": value,
                    "footprint": footprint,
                    "references": [],
                    "lcsc_part": fp.get("lcsc_part", ""),
                }
            groups[key]["references"].append(fp.get("reference", fp.get("id", "")))

        items = []
        for group in groups.values():
            # Use first non-empty LCSC part
            lcsc = group["lcsc_part"]
            items.append(JLCPCBBOMItem(
                reference=",".join(group["references"]),
                value=group["value"],
                footprint=group["footprint"],
                lcsc_part=lcsc,
            ))

        return items

    def _generate_cpl(self, pcb_data: Dict[str, Any]) -> List[JLCPCBCPLItem]:
        """Generate CPL (pick-and-place) items from PCB data."""
        items = []

        for fp in pcb_data.get("footprints", []):
            pos = fp.get("position", {})
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            rotation = fp.get("rotation", 0)

            # Determine side (T=top, B=bottom)
            side = "T"
            if isinstance(pos, dict) and pos.get("side", "").lower() in ("bottom", "b", "back"):
                side = "B"

            items.append(JLCPCBCPLItem(
                designator=fp.get("reference", fp.get("id", "")),
                x=float(x),
                y=float(y),
                side=side,
                rotation=float(rotation),
                lcsc_part=fp.get("lcsc_part", ""),
            ))

        return items

    def _bom_to_csv(self, items: List[JLCPCBBOMItem]) -> str:
        """Convert BOM items to JLCPCB CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.BOM_HEADER)
        for item in items:
            # JLCPCB format: Comment, Designator, Footprint, LCSC Part
            writer.writerow([item.value, item.reference, item.footprint, item.lcsc_part])
        return output.getvalue()

    def _cpl_to_csv(self, items: List[JLCPCBCPLItem]) -> str:
        """Convert CPL items to JLCPCB CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.CPL_HEADER)
        for item in items:
            writer.writerow(item.to_csv_row())
        return output.getvalue()

    @staticmethod
    def _zip_gerbers(gerber_dir: str, zip_path: str) -> None:
        """Package Gerber files into a ZIP."""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(gerber_dir):
                if any(filename.endswith(ext) for ext in ('.gbr', '.gtl', '.gbl', '.gts', '.gbs', '.gbo', '.gto', '.gko', '.drl')):
                    filepath = os.path.join(gerber_dir, filename)
                    zf.write(filepath, filename)

    @staticmethod
    def _validate_order(pcb_data: Dict[str, Any], result: JLCPCBOrderPackage) -> None:
        """Validate order package and add warnings."""
        footprints = pcb_data.get("footprints", [])

        # Check for missing LCSC parts
        missing_lcsc = [fp.get("reference", "") for fp in footprints if not fp.get("lcsc_part")]
        if missing_lcsc:
            result.warnings.append(
                f"{len(missing_lcsc)} components missing LCSC part numbers: {', '.join(missing_lcsc[:5])}"
            )

        # Check for missing values
        missing_value = [fp.get("reference", "") for fp in footprints if not fp.get("value")]
        if missing_value:
            result.warnings.append(
                f"{len(missing_value)} components missing values: {', '.join(missing_value[:5])}"
            )


# --- Singleton ---

_generator: Optional[JLCPCBOrderGenerator] = None


def get_jlcpcb_generator() -> JLCPCBOrderGenerator:
    global _generator
    if _generator is None:
        _generator = JLCPCBOrderGenerator()
    return _generator

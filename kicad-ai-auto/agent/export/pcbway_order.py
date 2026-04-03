"""
PCBWay Order Package Generator - Phase 11B-2

Generates complete PCBWay-compatible manufacturing package:
- Gerber files (ZIP)
- BOM CSV (PCBWay format)
- Pick-and-Place file (PCBWay format)
"""

import csv
import io
import logging
import os
import zipfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PCBWayBOMItem:
    """PCBWay BOM item format"""
    designator: str         # "U1"
    value: str              # "10K"
    footprint: str          # "0402"
    manufacturer: str = ""
    mfr_part: str = ""
    quantity: int = 1
    lcsc_part: str = ""

    def to_csv_row(self) -> List[str]:
        return [
            self.designator, self.value, self.footprint,
            self.manufacturer, self.mfr_part, str(self.quantity),
        ]


@dataclass
class PCBWayPnPItem:
    """PCBWay pick-and-place item format"""
    designator: str         # "U1"
    x: float                # mm
    y: float                # mm
    side: str               # "Top" or "Bottom"
    rotation: float         # degrees
    value: str = ""
    footprint: str = ""

    def to_csv_row(self) -> List[str]:
        return [
            self.designator,
            f"{self.x:.2f}",
            f"{self.y:.2f}",
            self.side,
            f"{self.rotation:.1f}",
            self.value,
            self.footprint,
        ]


@dataclass
class PCBWayOrderPackage:
    """Complete PCBWay order package"""
    gerber_zip_path: Optional[str] = None
    bom_csv: str = ""
    pnp_csv: str = ""
    bom_items: List[PCBWayBOMItem] = field(default_factory=list)
    pnp_items: List[PCBWayPnPItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bom_csv": self.bom_csv,
            "pnp_csv": self.pnp_csv,
            "bom_item_count": len(self.bom_items),
            "pnp_item_count": len(self.pnp_items),
            "warnings": self.warnings,
        }


class PCBWayOrderGenerator:
    """Generates PCBWay-compatible manufacturing order packages."""

    # PCBWay BOM CSV header
    BOM_HEADER = ["Designator", "Value", "Footprint", "Manufacturer", "Mfr Part", "Qty"]

    # PCBWay PnP CSV header
    PNP_HEADER = ["Designator", "X (mm)", "Y (mm)", "Side", "Rotation", "Value", "Footprint"]

    def generate_order(
        self,
        pcb_data: Dict[str, Any],
        gerber_dir: Optional[str] = None,
        output_dir: str = ".",
    ) -> PCBWayOrderPackage:
        """
        Generate complete PCBWay order package.

        Args:
            pcb_data: PCB data dict with footprints, board outline, etc.
            gerber_dir: Directory containing pre-generated Gerber files
            output_dir: Output directory for generated files
        """
        result = PCBWayOrderPackage()

        # 1. Generate BOM
        result.bom_items = self._generate_bom(pcb_data)
        result.bom_csv = self._bom_to_csv(result.bom_items)

        # 2. Generate PnP
        result.pnp_items = self._generate_pnp(pcb_data)
        result.pnp_csv = self._pnp_to_csv(result.pnp_items)

        # 3. Package Gerbers
        if gerber_dir and os.path.isdir(gerber_dir):
            zip_path = os.path.join(output_dir, "pcbway_gerber.zip")
            self._zip_gerbers(gerber_dir, zip_path)
            result.gerber_zip_path = zip_path

        # 4. Validate
        self._validate(pcb_data, result)

        logger.info(
            f"[PCBWay] Order package generated: "
            f"{len(result.bom_items)} BOM items, {len(result.pnp_items)} PnP items"
        )
        return result

    def _generate_bom(self, pcb_data: Dict[str, Any]) -> List[PCBWayBOMItem]:
        """Generate BOM from PCB data (per-component, not grouped)."""
        items = []
        for fp in pcb_data.get("footprints", []):
            items.append(PCBWayBOMItem(
                designator=fp.get("reference", fp.get("id", "")),
                value=fp.get("value", ""),
                footprint=fp.get("footprint", fp.get("library", "")),
                manufacturer=fp.get("manufacturer", ""),
                mfr_part=fp.get("mfr_part", fp.get("value", "")),
                quantity=1,
                lcsc_part=fp.get("lcsc_part", ""),
            ))
        return items

    def _generate_pnp(self, pcb_data: Dict[str, Any]) -> List[PCBWayPnPItem]:
        """Generate pick-and-place data."""
        items = []
        for fp in pcb_data.get("footprints", []):
            pos = fp.get("position", {})
            side = "Top"
            if isinstance(pos, dict) and pos.get("side", "").lower() in ("bottom", "b", "back"):
                side = "Bottom"

            items.append(PCBWayPnPItem(
                designator=fp.get("reference", fp.get("id", "")),
                x=float(pos.get("x", 0)) if isinstance(pos, dict) else float(pos.get("x", 0)),
                y=float(pos.get("y", 0)) if isinstance(pos, dict) else float(pos.get("y", 0)),
                side=side,
                rotation=float(fp.get("rotation", 0)),
                value=fp.get("value", ""),
                footprint=fp.get("footprint", fp.get("library", "")),
            ))
        return items

    def _bom_to_csv(self, items: List[PCBWayBOMItem]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.BOM_HEADER)
        for item in items:
            writer.writerow(item.to_csv_row())
        return output.getvalue()

    def _pnp_to_csv(self, items: List[PCBWayPnPItem]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.PNP_HEADER)
        for item in items:
            writer.writerow(item.to_csv_row())
        return output.getvalue()

    @staticmethod
    def _zip_gerbers(gerber_dir: str, zip_path: str) -> None:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(gerber_dir):
                if any(filename.endswith(ext) for ext in ('.gbr', '.gtl', '.gbl', '.gts', '.gbs', '.gbo', '.gto', '.gko', '.drl')):
                    filepath = os.path.join(gerber_dir, filename)
                    zf.write(filepath, filename)

    @staticmethod
    def _validate(pcb_data: Dict[str, Any], result: PCBWayOrderPackage) -> None:
        footprints = pcb_data.get("footprints", [])

        missing_value = [fp.get("reference", "") for fp in footprints if not fp.get("value")]
        if missing_value:
            result.warnings.append(
                f"{len(missing_value)} components without values"
            )

        no_position = [
            fp.get("reference", "")
            for fp in footprints
            if not fp.get("position") or not fp.get("position", {}).get("x")
        ]
        if no_position:
            result.warnings.append(
                f"{len(no_position)} components without positions: {', '.join(no_position[:5])}"
            )


# --- Singleton ---

_generator: Optional[PCBWayOrderGenerator] = None


def get_pcbway_generator() -> PCBWayOrderGenerator:
    global _generator
    if _generator is None:
        _generator = PCBWayOrderGenerator()
    return _generator

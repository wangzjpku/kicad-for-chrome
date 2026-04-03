"""
Component Alternative Recommender - Phase 11A-2

Finds pin-compatible and spec-compatible replacement components.
Considers availability, cost, and performance trade-offs.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AlternativeComponent:
    """An alternative component recommendation"""
    original_part: str
    alternative_part: str
    lcsc_part: str = ""
    manufacturer: str = ""
    compatibility: str = "spec"  # "pin", "spec", "functional"
    compatibility_score: float = 0.0  # 0-1
    stock: int = 0
    unit_price: float = 0.0
    savings_pct: float = 0.0  # negative means more expensive
    package: str = ""
    key_diffs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_part": self.original_part,
            "alternative_part": self.alternative_part,
            "lcsc_part": self.lcsc_part,
            "manufacturer": self.manufacturer,
            "compatibility": self.compatibility,
            "compatibility_score": self.compatibility_score,
            "stock": self.stock,
            "unit_price": self.unit_price,
            "savings_pct": self.savings_pct,
            "package": self.package,
            "key_diffs": self.key_diffs,
            "warnings": self.warnings,
        }


# --- Compatibility database ---
# Maps component to known alternatives with compatibility info
_ALTERNATIVES_DB: Dict[str, List[Dict[str, Any]]] = {
    "STM32F103C8T6": [
        {
            "part": "GD32F103C8T6", "mfr": "GigaDevice", "lcsc": "C128732",
            "compat": "pin", "score": 0.95, "pkg": "LQFP-48",
            "diffs": ["GD32 runs at 108MHz vs 72MHz", "Flash 64KB same", "Pin-compatible"],
            "warnings": ["Different silicon vendor — verify firmware compatibility"],
        },
        {
            "part": "APM32F103C8T6", "mfr": "Zhixin", "lcsc": "C518631",
            "compat": "pin", "score": 0.92, "pkg": "LQFP-48",
            "diffs": ["APM32 runs at 96MHz", "Pin-compatible", "Lower power"],
            "warnings": ["Different silicon vendor"],
        },
        {
            "part": "CH32F103C8T6", "mfr": "WCH", "lcsc": "C829512",
            "compat": "pin", "score": 0.88, "pkg": "LQFP-48",
            "diffs": ["RISC-V core option", "Pin-compatible", "Lower cost"],
            "warnings": ["Different architecture option"],
        },
    ],
    "ESP32-WROOM-32D": [
        {
            "part": "ESP32-WROOM-32E", "mfr": "Espressif", "lcsc": "C703664",
            "compat": "pin", "score": 0.99, "pkg": "Module",
            "diffs": ["Same module, newer revision", "Same pinout"],
        },
        {
            "part": "ESP32-WROVER-E", "mfr": "Espressif", "lcsc": "C5335805",
            "compat": "pin", "score": 0.90, "pkg": "Module",
            "diffs": ["Additional 8MB PSRAM", "Same pinout", "Slightly larger"],
            "warnings": ["Physically larger — check board space"],
        },
        {
            "part": "ESP32-C3-MINI-1", "mfr": "Espressif", "lcsc": "C2913418",
            "compat": "functional", "score": 0.70, "pkg": "Module",
            "diffs": ["RISC-V core", "WiFi 6", "Lower power", "Fewer GPIOs"],
            "warnings": ["Different pinout — requires PCB change", "Fewer GPIO (22 vs 36)"],
        },
    ],
    "AMS1117-3.3": [
        {
            "part": "RT9193-33GB", "mfr": "Richtek", "lcsc": "C11783",
            "compat": "pin", "score": 0.90, "pkg": "SOT-23-5",
            "diffs": ["Lower dropout (250mV vs 1.1V)", "SOT-23-5 vs SOT-223"],
            "warnings": ["Different package — requires PCB change"],
        },
        {
            "part": "ME6211A33M3G", "mfr": "Microne", "lcsc": "C82941",
            "compat": "spec", "score": 0.85, "pkg": "SOT-23-3",
            "diffs": ["LDO 3.3V 500mA", "Much smaller package"],
            "warnings": ["Lower current (500mA vs 1A)", "Different package"],
        },
        {
            "part": "XC6206P332MR", "mfr": "Torex", "lcsc": "C5446",
            "compat": "spec", "score": 0.80, "pkg": "SOT-23-3",
            "diffs": ["LDO 3.3V 200mA", "Very low IQ", "Ultra-small"],
            "warnings": ["Much lower current (200mA vs 1A)"],
        },
    ],
    "CH340G": [
        {
            "part": "CH340C", "mfr": "WCH", "lcsc": "C84681",
            "compat": "pin", "score": 0.85, "pkg": "SOP-16",
            "diffs": ["No external crystal needed", "Same pinout"],
        },
        {
            "part": "CP2102-GMR", "mfr": "Silicon Labs", "lcsc": "C6568",
            "compat": "functional", "score": 0.70, "pkg": "QFN-28",
            "diffs": ["USB 2.0 Full Speed", "QFN package"],
            "warnings": ["Different package — requires PCB change"],
        },
    ],
    "LM2596S-5.0": [
        {
            "part": "XL2596S-5.0E1", "mfr": "XLSEMI", "lcsc": "C618029",
            "compat": "pin", "score": 0.92, "pkg": "TO-263-5",
            "diffs": ["Pin-compatible", "Same specs", "Lower cost"],
        },
        {
            "part": "MP1584EN-LF-Z", "mfr": "MPS", "lcsc": "C177597",
            "compat": "spec", "score": 0.75, "pkg": "SOIC-8",
            "diffs": ["Higher freq (1.5MHz)", "Smaller inductor", "Higher efficiency"],
            "warnings": ["Different pinout — requires PCB change"],
        },
    ],
}


class ComponentAlternativeRecommender:
    """Recommends alternative components based on specs, availability, and cost."""

    def __init__(self):
        self._db = _ALTERNATIVES_DB

    def find_alternatives(
        self,
        part_number: str,
        max_results: int = 5,
        min_score: float = 0.5,
    ) -> List[AlternativeComponent]:
        """
        Find alternative components for a given part number.

        Args:
            part_number: Original component part number
            max_results: Maximum alternatives to return
            min_score: Minimum compatibility score (0-1)

        Returns:
            List of alternative recommendations sorted by compatibility score
        """
        results = []

        # Direct lookup in alternatives database
        for key, alts in self._db.items():
            if key.upper() == part_number.upper():
                for alt in alts:
                    if alt.get("score", 0) >= min_score:
                        # Get pricing from LCSC if available
                        unit_price = 0.0
                        stock = 0
                        try:
                            from .lcsc_api import get_lcsc_client
                            client = get_lcsc_client()
                            if alt.get("lcsc"):
                                comp = client.get_component(alt["lcsc"])
                                if comp:
                                    unit_price = comp.unit_price
                                    stock = comp.stock
                        except Exception as e:
                            logger.warning(f"Alternative component lookup failed: {e}")

                        results.append(AlternativeComponent(
                            original_part=part_number,
                            alternative_part=alt["part"],
                            lcsc_part=alt.get("lcsc", ""),
                            manufacturer=alt.get("mfr", ""),
                            compatibility=alt.get("compat", "spec"),
                            compatibility_score=alt.get("score", 0),
                            stock=stock,
                            unit_price=unit_price,
                            package=alt.get("pkg", ""),
                            key_diffs=alt.get("diffs", []),
                            warnings=alt.get("warnings", []),
                        ))
                break

        # Fuzzy match — try searching LCSC for similar parts
        if len(results) < max_results:
            results.extend(
                self._search_similar(part_number, max_results - len(results), min_score, results)
            )

        # Sort by compatibility score descending
        results.sort(key=lambda x: x.compatibility_score, reverse=True)
        return results[:max_results]

    def _search_similar(
        self,
        part_number: str,
        limit: int,
        min_score: float,
        existing: List[AlternativeComponent],
    ) -> List[AlternativeComponent]:
        """Search LCSC for similar components (fuzzy match)."""
        results = []
        existing_parts = {a.alternative_part for a in existing}

        try:
            from .lcsc_api import get_lcsc_client
            client = get_lcsc_client()

            # Extract base part family (e.g. "STM32F103" from "STM32F103C8T6")
            family = self._extract_family(part_number)
            if family:
                search_result = client.search(family, limit=limit + len(existing_parts))
                for comp in search_result.components:
                    if comp.mfr_part in existing_parts:
                        continue
                    if comp.mfr_part.upper() == part_number.upper():
                        continue

                    # Compute rough compatibility score based on part similarity
                    score = self._compute_similarity(part_number, comp.mfr_part)
                    if score >= min_score:
                        results.append(AlternativeComponent(
                            original_part=part_number,
                            alternative_part=comp.mfr_part,
                            lcsc_part=comp.lcsc_part,
                            manufacturer=comp.manufacturer,
                            compatibility="spec",
                            compatibility_score=score,
                            stock=comp.stock,
                            unit_price=comp.unit_price,
                            package=comp.package,
                            key_diffs=["Found via similarity search"],
                            warnings=["Verify pin compatibility manually"],
                        ))
                        existing_parts.add(comp.mfr_part)
                        if len(results) >= limit:
                            break
        except Exception as e:
            logger.warning(f"[AlternativeRecommender] Similar search failed: {e}")

        return results

    @staticmethod
    def _extract_family(part_number: str) -> str:
        """Extract base part family for search."""
        # Common patterns: STM32F103C8T6 -> STM32F103, ESP32-WROOM-32D -> ESP32-WROOM
        import re
        # Remove trailing speed/variant codes
        match = re.match(r'^([A-Z]+\d+[A-Z]*\d*)', part_number, re.IGNORECASE)
        if match:
            return match.group(1)
        return part_number[:8]  # fallback: first 8 chars

    @staticmethod
    def _compute_similarity(original: str, candidate: str) -> float:
        """Compute rough similarity score between two part numbers."""
        o, c = original.upper(), candidate.upper()

        # Exact match (shouldn't happen, but safety)
        if o == c:
            return 1.0

        # Common prefix length
        common = 0
        for a, b in zip(o, c):
            if a == b:
                common += 1
            else:
                break

        # Score based on prefix ratio
        max_len = max(len(o), len(c))
        if max_len == 0:
            return 0.0

        prefix_score = common / max_len
        return min(prefix_score * 1.2, 0.9)  # Cap at 0.9 for fuzzy matches


# --- Singleton ---

_recommender: Optional[ComponentAlternativeRecommender] = None


def get_alternative_recommender() -> ComponentAlternativeRecommender:
    """Get the global recommender instance."""
    global _recommender
    if _recommender is None:
        _recommender = ComponentAlternativeRecommender()
    return _recommender

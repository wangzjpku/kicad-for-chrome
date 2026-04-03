"""
BOM Optimizer - Phase 11A-3

Optimizes BOM for cost, availability, and lifecycle.
Includes NRFND (Not Recommended For New Design) lifecycle checking.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BOMLineItem:
    """Single BOM line item"""
    reference: str              # e.g. "U1"
    part_number: str            # e.g. "STM32F103C8T6"
    footprint: str              # e.g. "LQFP-48"
    quantity: int = 1
    lcsc_part: str = ""
    unit_price: float = 0.0
    total_price: float = 0.0
    stock: int = 0
    lifecycle: str = "active"   # "active", "nrnd", "eol", "obsolete"
    category: str = ""
    warnings: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.quantity <= 0:
            self.quantity = 1
        if self.total_price == 0 and self.unit_price > 0:
            self.total_price = self.unit_price * self.quantity


@dataclass
class BOMOptimizationReport:
    """Full BOM optimization report"""
    items: List[BOMLineItem]
    total_cost: float = 0.0
    total_savings: float = 0.0
    savings_pct: float = 0.0
    availability_score: float = 0.0  # 0-100
    lifecycle_score: float = 0.0     # 0-100
    overall_score: float = 0.0       # 0-100
    warnings: List[str] = field(default_factory=list)
    optimized_items: List[BOMLineItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost": self.total_cost,
            "total_savings": self.total_savings,
            "savings_pct": round(self.savings_pct, 1),
            "availability_score": round(self.availability_score, 1),
            "lifecycle_score": round(self.lifecycle_score, 1),
            "overall_score": round(self.overall_score, 1),
            "warnings": self.warnings,
            "item_count": len(self.items),
            "items": [self._item_to_dict(i) for i in self.items],
            "optimized_items": [self._item_to_dict(i) for i in self.optimized_items],
        }

    @staticmethod
    def _item_to_dict(item: BOMLineItem) -> Dict[str, Any]:
        return {
            "reference": item.reference,
            "part_number": item.part_number,
            "footprint": item.footprint,
            "quantity": item.quantity,
            "lcsc_part": item.lcsc_part,
            "unit_price": item.unit_price,
            "total_price": item.total_price,
            "stock": item.stock,
            "lifecycle": item.lifecycle,
            "category": item.category,
            "warnings": item.warnings,
            "alternatives": item.alternatives[:3],
        }


# --- NRFND / Lifecycle database ---
# Common parts with known lifecycle status
_LIFECYCLE_DB: Dict[str, Dict[str, str]] = {
    # Obsolete / EOL parts
    "STM32F103C8T6": {"status": "active", "note": "Still active, widely available"},
    "STM32F103CBT6": {"status": "nrnd", "note": "NRND — consider STM32F4 or G4 series"},
    "ATMEGA328P-AU": {"status": "active", "note": "Still in production"},
    "ATMEGA2560-16AU": {"status": "nrnd", "note": "NRND — consider ATSAME series"},
    "ESP8266EX": {"status": "nrnd", "note": "NRND — ESP32-C3 recommended replacement"},
    "NRF51822": {"status": "obsolete", "note": "Obsolete — use NRF52832 or NRF52840"},
    "NRF52832": {"status": "active", "note": "Active"},
    "LM7805": {"status": "nrnd", "note": "NRND — switching regulators recommended"},
    "LM317": {"status": "active", "note": "Still active but consider modern LDOs"},
    "NE555": {"status": "active", "note": "Classic timer, still produced"},
    "CD4051BE": {"status": "nrnd", "note": "NRND — consider modern mux alternatives"},
    "FT232RL": {"status": "nrnd", "note": "NRND — FT232H or CH340 recommended"},
    "CP2102": {"status": "active", "note": "Active"},
    "CH340G": {"status": "active", "note": "Active, very popular"},
    "AMS1117-3.3": {"status": "active", "note": "Active but consider lower dropout parts"},
    "MP1584EN": {"status": "active", "note": "Active"},
    "TL431": {"status": "active", "note": "Active"},
}


class BOMOptimizer:
    """Optimizes BOM for cost, availability, and lifecycle."""

    def __init__(self):
        self._lifecycle_db = _LIFECYCLE_DB

    def optimize_bom(
        self,
        bom_items: List[Dict[str, Any]],
        target_qty: int = 100,
        optimize_for: str = "cost",  # "cost", "availability", "lifecycle"
    ) -> BOMOptimizationReport:
        """
        Optimize a BOM for cost and availability.

        Args:
            bom_items: List of BOM items with reference, part_number, footprint, quantity
            target_qty: Target production quantity for pricing tiers
            optimize_for: Optimization priority
        """
        items: List[BOMLineItem] = []
        optimized_items: List[BOMLineItem] = []
        total_cost = 0.0
        total_optimized_cost = 0.0
        all_warnings: List[str] = []

        for raw_item in bom_items:
            item = self._enrich_item(raw_item, target_qty)
            items.append(item)
            total_cost += item.total_price

            # Try to find cheaper alternative
            opt_item = self._optimize_item(item, target_qty, optimize_for)
            optimized_items.append(opt_item)
            total_optimized_cost += opt_item.total_price

            if item.warnings:
                all_warnings.extend(item.warnings)

        # Calculate savings
        savings = total_cost - total_optimized_cost
        savings_pct = (savings / total_cost * 100) if total_cost > 0 else 0

        # Calculate scores
        avail_score = self._compute_availability_score(items)
        lifecycle_score = self._compute_lifecycle_score(items)
        overall = (avail_score * 0.4 + lifecycle_score * 0.3 + (100 - min(savings_pct, 100)) * 0.3)

        return BOMOptimizationReport(
            items=items,
            total_cost=round(total_cost, 2),
            total_savings=round(max(savings, 0), 2),
            savings_pct=round(savings_pct, 1),
            availability_score=avail_score,
            lifecycle_score=lifecycle_score,
            overall_score=round(overall, 1),
            warnings=all_warnings,
            optimized_items=optimized_items,
        )

    def check_lifecycle(self, part_number: str) -> Dict[str, str]:
        """Check lifecycle status for a part."""
        upper = part_number.upper()
        if upper in self._lifecycle_db:
            return self._lifecycle_db[upper]

        # Try partial match
        for key, val in self._lifecycle_db.items():
            if key in upper or upper in key:
                return val

        return {"status": "unknown", "note": "Not in lifecycle database"}

    def _enrich_item(self, raw: Dict[str, Any], target_qty: int) -> BOMLineItem:
        """Enrich a BOM item with pricing and lifecycle data."""
        part_number = raw.get("part_number", "")
        quantity = raw.get("quantity", 1)
        warnings: List[str] = []

        # Check lifecycle
        lifecycle_info = self.check_lifecycle(part_number)
        lifecycle = lifecycle_info.get("status", "unknown")
        if lifecycle in ("nrnd", "eol", "obsolete"):
            warnings.append(f"{part_number}: {lifecycle_info.get('note', lifecycle)}")

        # Try to get LCSC pricing
        unit_price = 0.0
        lcsc_part = ""
        stock = 0
        category = ""

        try:
            from .lcsc_api import get_lcsc_client
            client = get_lcsc_client()
            search_result = client.search(part_number, limit=1)
            if search_result.components:
                comp = search_result.components[0]
                unit_price = comp.price_at_qty if target_qty >= 100 else comp.unit_price
                lcsc_part = comp.lcsc_part
                stock = comp.stock
                category = comp.category
        except Exception as e:
            logger.warning(f"BOM optimization failed: {e}")

        return BOMLineItem(
            reference=raw.get("reference", ""),
            part_number=part_number,
            footprint=raw.get("footprint", ""),
            quantity=quantity,
            lcsc_part=lcsc_part,
            unit_price=unit_price,
            stock=stock,
            lifecycle=lifecycle,
            category=category,
            warnings=warnings,
        )

    def _optimize_item(
        self,
        item: BOMLineItem,
        target_qty: int,
        optimize_for: str,
    ) -> BOMLineItem:
        """Try to find a better alternative for a single item."""
        # Skip passives (resistors, capacitors) — usually already cheapest
        if item.category in ("Resistor", "MLCC", "Capacitor"):
            return item

        # Try to find alternatives
        alternatives_data = []
        try:
            from .component_alternative import get_alternative_recommender
            recommender = get_alternative_recommender()
            alts = recommender.find_alternatives(item.part_number, max_results=3)

            for alt in alts:
                alternatives_data.append(alt.to_dict())

                # If optimizing for cost and alternative is cheaper
                if optimize_for == "cost" and alt.unit_price > 0 and alt.unit_price < item.unit_price:
                    return BOMLineItem(
                        reference=item.reference,
                        part_number=alt.alternative_part,
                        footprint=alt.package,
                        quantity=item.quantity,
                        lcsc_part=alt.lcsc_part,
                        unit_price=alt.unit_price,
                        stock=alt.stock,
                        lifecycle="active",  # alternatives assumed active
                        category=item.category,
                        warnings=alt.warnings,
                        alternatives=[],
                    )

                # If optimizing for availability and alternative has more stock
                if optimize_for == "availability" and alt.stock > item.stock:
                    return BOMLineItem(
                        reference=item.reference,
                        part_number=alt.alternative_part,
                        footprint=alt.package,
                        quantity=item.quantity,
                        lcsc_part=alt.lcsc_part,
                        unit_price=alt.unit_price or item.unit_price,
                        stock=alt.stock,
                        lifecycle="active",
                        category=item.category,
                        warnings=alt.warnings,
                        alternatives=[],
                    )

        except Exception as e:
            logger.warning(f"[BOMOptimizer] Alternative search failed for {item.part_number}: {e}")

        # No better alternative found — return original with alternatives listed
        result = BOMLineItem(
            reference=item.reference,
            part_number=item.part_number,
            footprint=item.footprint,
            quantity=item.quantity,
            lcsc_part=item.lcsc_part,
            unit_price=item.unit_price,
            stock=item.stock,
            lifecycle=item.lifecycle,
            category=item.category,
            warnings=item.warnings,
            alternatives=alternatives_data,
        )
        return result

    @staticmethod
    def _compute_availability_score(items: List[BOMLineItem]) -> float:
        """Compute overall availability score (0-100)."""
        if not items:
            return 100.0

        scores = []
        for item in items:
            if item.stock >= 10000:
                scores.append(100)
            elif item.stock >= 1000:
                scores.append(80)
            elif item.stock >= 100:
                scores.append(50)
            elif item.stock > 0:
                scores.append(20)
            else:
                scores.append(0)

        return sum(scores) / len(scores)

    @staticmethod
    def _compute_lifecycle_score(items: List[BOMLineItem]) -> float:
        """Compute lifecycle health score (0-100)."""
        if not items:
            return 100.0

        scores = []
        for item in items:
            status_scores = {
                "active": 100,
                "unknown": 70,
                "nrnd": 40,
                "eol": 15,
                "obsolete": 0,
            }
            scores.append(status_scores.get(item.lifecycle, 50))

        return sum(scores) / len(scores)


# --- Singleton ---

_optimizer: Optional[BOMOptimizer] = None


def get_bom_optimizer() -> BOMOptimizer:
    """Get the global BOM optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = BOMOptimizer()
    return _optimizer

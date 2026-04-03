"""
LCSC (立创商城) API Service - Phase 11A-1

Real-time component inventory query from LCSC.
Provides search, pricing, stock, and lifecycle data.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LCSCComponent:
    """LCSC component data"""
    lcsc_part: str              # e.g. "C8304"
    mfr_part: str               # e.g. "STM32F103C8T6"
    manufacturer: str           # e.g. "STMicroelectronics"
    description: str
    package: str                # e.g. "LQFP-48"
    category: str               # e.g. "MCU"
    stock: int
    price_tiers: Dict[int, float] = field(default_factory=dict)  # qty -> unit price (CNY)

    lifecycle: str = "active"   # "active", "nrnd", "eol", "obsolete"
    rohs: bool = True
    url: str = ""

    @property
    def unit_price(self) -> float:
        """Lowest tier unit price"""
        if not self.price_tiers:
            return 0.0
        return min(self.price_tiers.values())

    @property
    def price_at_qty(self) -> float:
        """Best price for typical order quantity (100+)"""
        if not self.price_tiers:
            return 0.0
        # Find the best price for qty >= 100, or lowest available
        best = float('inf')
        for qty, price in self.price_tiers.items():
            if qty >= 100 and price < best:
                best = price
        return best if best != float('inf') else min(self.price_tiers.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lcsc_part": self.lcsc_part,
            "mfr_part": self.mfr_part,
            "manufacturer": self.manufacturer,
            "description": self.description,
            "package": self.package,
            "category": self.category,
            "stock": self.stock,
            "price_tiers": self.price_tiers,
            "unit_price": self.unit_price,
            "price_at_qty": self.price_at_qty,
            "lifecycle": self.lifecycle,
            "rohs": self.rohs,
            "url": self.url,
        }


@dataclass
class LCSCSearchResult:
    """Search result from LCSC"""
    query: str
    total: int
    components: List[LCSCComponent]
    search_time_ms: float = 0.0


class LCSCAPIClient:
    """
    LCSC API client for component search and inventory.

    Uses LCSC's public search API. Falls back to local database
    when API is unavailable.
    """

    BASE_URL = "https://wmsc.lcsc.com/ftps/wm"

    # Expanded local component database for offline fallback
    LOCAL_DB: List[Dict[str, Any]] = [
        # MCU
        {"mfr_part": "STM32F103C8T6", "lcsc": "C8304", "mfr": "STMicroelectronics",
         "desc": "STM32F103C8T6 Mainstream MCU ARM Cortex-M3", "pkg": "LQFP-48",
         "cat": "MCU", "stock": 12500, "prices": {1: 14.2, 10: 12.8, 100: 10.5, 1000: 8.2}},
        {"mfr_part": "STM32F407VET6", "lcsc": "C45979", "mfr": "STMicroelectronics",
         "desc": "STM32F407VET6 High-performance MCU", "pkg": "LQFP-100",
         "cat": "MCU", "stock": 5200, "prices": {1: 28.5, 10: 25.2, 100: 22.0, 1000: 18.5}},
        {"mfr_part": "ESP32-WROOM-32D", "lcsc": "C473012", "mfr": "Espressif",
         "desc": "ESP32-WROOM-32D WiFi+BLE Module", "pkg": "Module",
         "cat": "WiFi Module", "stock": 8300, "prices": {1: 15.8, 10: 14.2, 100: 12.5, 1000: 10.8}},
        {"mfr_part": "ESP32-C3-MINI-1", "lcsc": "C2913418", "mfr": "Espressif",
         "desc": "ESP32-C3-MINI-1 RISC-V WiFi+BLE", "pkg": "Module",
         "cat": "WiFi Module", "stock": 6100, "prices": {1: 8.5, 10: 7.8, 100: 6.5, 1000: 5.2}},
        {"mfr_part": "CH32V003F4P6", "lcsc": "C5370347", "mfr": "WCH",
         "desc": "CH32V003F4P6 RISC-V MCU 16KB Flash", "pkg": "TSSOP-20",
         "cat": "MCU", "stock": 35000, "prices": {1: 1.2, 10: 0.9, 100: 0.6, 1000: 0.4}},
        # Power
        {"mfr_part": "AMS1117-3.3", "lcsc": "C6186", "mfr": "Advanced Monolithic Systems",
         "desc": "AMS1117-3.3 LDO 3.3V 1A SOT-223", "pkg": "SOT-223",
         "cat": "LDO", "stock": 50000, "prices": {1: 0.85, 10: 0.55, 100: 0.35, 1000: 0.22}},
        {"mfr_part": "LM2596S-5.0", "lcsc": "C347222", "mfr": "Texas Instruments",
         "desc": "LM2596S-5.0 Step-Down 5V 3A TO-263", "pkg": "TO-263-5",
         "cat": "DC-DC", "stock": 18000, "prices": {1: 3.8, 10: 3.2, 100: 2.5, 1000: 1.8}},
        {"mfr_part": "TPS54331DR", "lcsc": "C98637", "mfr": "Texas Instruments",
         "desc": "TPS54331 3A Step-Down Converter SOIC-8", "pkg": "SOIC-8",
         "cat": "DC-DC", "stock": 9200, "prices": {1: 5.2, 10: 4.5, 100: 3.8, 1000: 2.9}},
        # USB
        {"mfr_part": "CH340G", "lcsc": "C14267", "mfr": "WCH",
         "desc": "CH340G USB to UART SOIC-16", "pkg": "SOIC-16",
         "cat": "USB Interface", "stock": 45000, "prices": {1: 2.5, 10: 1.8, 100: 1.2, 1000: 0.8}},
        {"mfr_part": "CP2102-GMR", "lcsc": "C6568", "mfr": "Silicon Labs",
         "desc": "CP2102 USB to UART QFN-28", "pkg": "QFN-28",
         "cat": "USB Interface", "stock": 28000, "prices": {1: 8.5, 10: 7.2, 100: 5.8, 1000: 4.5}},
        # Storage
        {"mfr_part": "W25Q32JVSSIQ", "lcsc": "C179161", "mfr": "Winbond",
         "desc": "W25Q32JVSSIQ 32Mbit Flash SOIC-8", "pkg": "SOIC-8",
         "cat": "Flash", "stock": 32000, "prices": {1: 2.8, 10: 2.2, 100: 1.5, 1000: 1.1}},
        {"mfr_part": "W25Q128JVSIQ", "lcsc": "C2843388", "mfr": "Winbond",
         "desc": "W25Q128JVSIQ 128Mbit Flash SOIC-8", "pkg": "SOIC-8",
         "cat": "Flash", "stock": 15000, "prices": {1: 5.5, 10: 4.8, 100: 3.5, 1000: 2.8}},
        # Passives (sample)
        {"mfr_part": "CL10B104KB8NNNC", "lcsc": "C1591", "mfr": "Samsung",
         "desc": "100nF 50V X7R 0402 Capacitor", "pkg": "0402",
         "cat": "MLCC", "stock": 980000, "prices": {1: 0.02, 100: 0.012, 1000: 0.008, 10000: 0.005}},
        {"mfr_part": "RC0402JR-07100KL", "lcsc": "C25744", "mfr": "YAGEO",
         "desc": "100KΩ 5% 0402 Resistor", "pkg": "0402",
         "cat": "Resistor", "stock": 1200000, "prices": {1: 0.01, 100: 0.005, 1000: 0.003, 10000: 0.002}},
        # Connectors
        {"mfr_part": "TYPE-C-31-M-12", "lcsc": "C165948", "mfr": "Korean Hroparts",
         "desc": "USB Type-C 16-pin Female SMD", "pkg": "SMD",
         "cat": "USB Connector", "stock": 42000, "prices": {1: 0.85, 10: 0.65, 100: 0.45, 1000: 0.32}},
        # Sensors
        {"mfr_part": "BME280", "lcsc": "C78410", "mfr": "Bosch",
         "desc": "BME280 Temp/Humidity/Pressure LGA-8", "pkg": "LGA-8",
         "cat": "Sensor", "stock": 7500, "prices": {1: 18.5, 10: 15.8, 100: 12.5, 1000: 9.8}},
    ]

    def __init__(self):
        self._cache: Dict[str, LCSCSearchResult] = {}
        self._cache_ttl = 3600  # 1 hour

    def search(
        self,
        keyword: str,
        category: Optional[str] = None,
        in_stock_only: bool = False,
        limit: int = 20,
    ) -> LCSCSearchResult:
        """
        Search LCSC components by keyword.

        Args:
            keyword: Search term (part number, description, etc.)
            category: Optional category filter
            in_stock_only: Only return components with stock > 0
            limit: Maximum results to return
        """
        start = time.time()
        cache_key = f"{keyword}:{category}:{in_stock_only}:{limit}"

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.search_time_ms / 1000 < self._cache_ttl:
                logger.info(f"[LCSC] Cache hit for '{keyword}'")
                return cached

        # Try real API first
        components = self._search_api(keyword, category, in_stock_only, limit)

        # Fallback to local DB
        if not components:
            components = self._search_local(keyword, category, in_stock_only, limit)

        elapsed_ms = (time.time() - start) * 1000
        result = LCSCSearchResult(
            query=keyword,
            total=len(components),
            components=components,
            search_time_ms=elapsed_ms,
        )

        self._cache[cache_key] = result
        logger.info(f"[LCSC] Search '{keyword}' found {len(components)} results in {elapsed_ms:.0f}ms")
        return result

    def get_component(self, lcsc_part: str) -> Optional[LCSCComponent]:
        """Get a single component by LCSC part number."""
        for item in self.LOCAL_DB:
            if item["lcsc"] == lcsc_part:
                return self._dict_to_component(item)

        # Try API
        results = self._search_api(lcsc_part, limit=1)
        return results[0] if results else None

    def get_pricing(self, lcsc_part: str, quantity: int) -> Optional[float]:
        """Get price for a specific quantity."""
        comp = self.get_component(lcsc_part)
        if not comp:
            return None

        if not comp.price_tiers:
            return 0.0

        # Find applicable tier (largest qty <= requested)
        applicable_price = max(comp.price_tiers.values())
        for tier_qty, tier_price in comp.price_tiers.items():
            if tier_qty <= quantity and tier_price < applicable_price:
                applicable_price = tier_price
        return applicable_price

    def _search_api(
        self,
        keyword: str,
        category: Optional[str] = None,
        in_stock_only: bool = False,
        limit: int = 20,
    ) -> List[LCSCComponent]:
        """Search using LCSC web API."""
        try:
            import requests

            params = {
                "keyword": keyword,
                "limit": limit,
                "page": 1,
            }
            if in_stock_only:
                params["in_stock"] = True

            resp = requests.get(
                f"{self.BASE_URL}/product/search",
                params=params,
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                components = []
                for item in data.get("result", {}).get("tipProductList", [])[:limit]:
                    prices = {}
                    for tier in item.get("productPriceList", []):
                        prices[tier.get("ladder", 1)] = float(tier.get("productPrice", 0))

                    comp = LCSCComponent(
                        lcsc_part=item.get("productCode", ""),
                        mfr_part=item.get("productModel", ""),
                        manufacturer=item.get("brandNameEn", ""),
                        description=item.get("productIntroEn", ""),
                        package=item.get("encapStandard", ""),
                        category=item.get("parentCatalogName", ""),
                        stock=int(item.get("stockNumber", 0)),
                        price_tiers=prices,
                        url=f"https://www.lcsc.com/product-detail/{item.get('productCode', '')}.html",
                    )
                    components.append(comp)
                return components

        except ImportError:
            logger.debug("[LCSC] requests not available")
        except Exception as e:
            logger.warning(f"[LCSC] API search failed: {e}")

        return []

    def _search_local(
        self,
        keyword: str,
        category: Optional[str] = None,
        in_stock_only: bool = False,
        limit: int = 20,
    ) -> List[LCSCComponent]:
        """Search using local component database."""
        keyword_lower = keyword.lower()
        results = []

        for item in self.LOCAL_DB:
            # Match keyword against part number, description, category
            searchable = (
                f"{item['mfr_part']} {item['desc']} {item['cat']} {item['pkg']}"
            ).lower()

            if keyword_lower not in searchable:
                continue

            if category and category.lower() != item["cat"].lower():
                continue

            if in_stock_only and item["stock"] <= 0:
                continue

            results.append(self._dict_to_component(item))

            if len(results) >= limit:
                break

        return results

    def _dict_to_component(self, item: Dict[str, Any]) -> LCSCComponent:
        """Convert local DB dict to LCSCComponent."""
        return LCSCComponent(
            lcsc_part=item["lcsc"],
            mfr_part=item["mfr_part"],
            manufacturer=item["mfr"],
            description=item["desc"],
            package=item["pkg"],
            category=item["cat"],
            stock=item["stock"],
            price_tiers=item.get("prices", {}),
        )


# --- Singleton ---

_client: Optional[LCSCAPIClient] = None


def get_lcsc_client() -> LCSCAPIClient:
    """Get the global LCSC API client instance."""
    global _client
    if _client is None:
        _client = LCSCAPIClient()
    return _client

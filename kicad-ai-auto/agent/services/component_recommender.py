"""
Component Recommendation Engine

Provides AI-powered component recommendation based on:
- Functional requirements
- Parameter specifications
- Price and availability
- JLCPCB/LCSC component database
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json
import re
from pathlib import Path


@dataclass
class ComponentRecommendation:
    """A recommended component with metadata"""
    symbol: str              # KiCad symbol (e.g., "Device:R")
    footprint: str           # KiCad footprint (e.g., "Resistor_SMD:R_0805")
    description: str         # Human-readable description
    parameters: Dict         # Component parameters (value, tolerance, voltage, etc.)
    score: float             # Recommendation confidence (0-1)
    source: str              # Data source ("jlcpcb", "lcsc", "local")
    part_number: Optional[str] = None  # Manufacturer part number
    price: Optional[float] = None      # Unit price in USD
    stock: Optional[int] = None        # Stock quantity
    lcsc_part: Optional[str] = None    # LCSC part number
    jlcpcb_part: Optional[str] = None  # JLCPCB part number

    def to_dict(self) -> Dict:
        result = {
            "symbol": self.symbol,
            "footprint": self.footprint,
            "description": self.description,
            "parameters": self.parameters,
            "score": self.score,
            "source": self.source
        }
        if self.part_number:
            result["part_number"] = self.part_number
        if self.price is not None:
            result["price"] = self.price
        if self.stock is not None:
            result["stock"] = self.stock
        if self.lcsc_part:
            result["lcsc_part"] = self.lcsc_part
        if self.jlcpcb_part:
            result["jlcpcb_part"] = self.jlcpcb_part
        return result


class ComponentRecommender:
    """
    AI-powered component recommendation engine

    Recommends components based on:
    - Natural language functional requirements
    - Parameter specifications
    - JLCPCB/LCSC component database
    """

    # Common component mappings
    COMPONENT_PATTERNS = {
        # Connectors
        r"usb.*type.?c|type.?c.*usb|usb.?c\s": {
            "symbols": ["Connector:USB_C_Receptacle"],
            "footprints": ["Connector_USB:USB_C_Receptacle"]
        },
        r"usb.*type.?a|type.?a.*usb": {
            "symbols": ["Connector:USB_A"],
            "footprints": ["Connector_USB:USB_A"]
        },
        r"hdmi": {
            "symbols": ["Connector:HDR-1x20P"],
            "footprints": ["Connector_PinHeader_2.54mm:PinHeader_1x20_P2.54mm_Vertical"]
        },
        r"jst.*connector|jst": {
            "symbols": ["Connector_JST:JST_PH_B2B-PH-K"],
            "footprints": ["JST_PH:B2B-PH-K"]
        },

        # Power
        r"5v.*regulator|regulator.*5v|lm7805|ldo.*5v|5v.*稳压|稳压.*5v": {
            "symbols": ["Regulator_Linear:LM7805"],
            "footprints": ["Package_TO_SOT_THT:TO-220-3_Horizontal"]
        },
        r"3\.3v.*regulator|regulator.*3\.3v|ams1117.*3\.3|3\.3v.*稳压|稳压.*3\.3v|稳压器.*3\.3|3\.3.*稳压": {
            "symbols": ["Regulator_Linear:AMS1117-3.3"],
            "footprints": ["Package_TO_SOT_THT:SOT-223-3_TabPin2"]
        },
        r"barrel.*jack|power.*jack|dc.*jack": {
            "symbols": ["Connector:BarrelJack"],
            "footprints": ["Connector_BarrelJack:BarrelJack_Switch"]
        },

        # Passives
        r"resistor|r\s*$|电阻": {
            "symbols": ["Device:R"],
            "footprints": ["Resistor_SMD:R_0805"]
        },
        r"capacitor|c\s*$|电容": {
            "symbols": ["Device:C"],
            "footprints": ["Capacitor_SMD:C_0805"]
        },
        r"electrolytic.*capacitor|cap.*electrolytic|电解电容|滤波电容": {
            "symbols": ["Device:C"],
            "footprints": ["Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"]
        },
        r"inductor|l\s*$|电感": {
            "symbols": ["Device:L"],
            "footprints": ["Inductor_SMD:L_0805"]
        },

        # Semiconductors
        r"led|发光二极管": {
            "symbols": ["Device:LED"],
            "footprints": ["LED_SMD:LED_0805"]
        },
        r"diode|1n4148|1n4007|二极管": {
            "symbols": ["Device:D"],
            "footprints": ["Diode_SMD:D_0805"]
        },
        r"zener|稳压管": {
            "symbols": ["Device:D_Zener"],
            "footprints": ["Diode_SMD:D_0805"]
        },

        # ICs
        r"mcu|microship|atmega|attiny|单片机": {
            "symbols": ["MCU_Microchip_ATmega:ATmega328P"],
            "footprints": ["Package_QFP:TQFP-32_7x7mm_P0.8mm"]
        },
        r"esp32": {
            "symbols": ["MCU_Espressif:ESP32-WROOM"],
            "footprints": ["Module:ESP32-WROOM-32"]
        },
        r"stm32": {
            "symbols": ["MCU_ST_STM32:STM32F103C8Tx"],
            "footprints": ["Package_QFP:LQFP-48_7x7mm_P0.5mm"]
        },
        r"ch340|usb.*to.*uart|uart.*bridge|串口芯片|串口转接": {
            "symbols": ["Interface_USB:WCH_CH340C"],
            "footprints": ["Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"]
        },
        r"cp2102|usb.*to.*uart|uart.*bridge": {
            "symbols": ["Interface_USB:Silicon_Labs_CP2102"],
            "footprints": ["Package_QFN:QFPN-28_5x5mm_P0.5mm"]
        },
        r"ne555|timer|定时器|555": {
            "symbols": ["Timer:NE555"],
            "footprints": ["Package_DIP:DIP-8_W7.62mm_Socket"]
        },
        r"lm358|op-amp|operational.*amplifier|运放|运算放大器": {
            "symbols": ["Amplifier_Audio:LM358"],
            "footprints": ["Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"]
        },
        r"lm317|adjustable.*regulator|可调稳压": {
            "symbols": ["Regulator_Linear:LM317"],
            "footprints": ["Package_TO_SOT_THT:TO-220-3_Horizontal"]
        },

        # Crystals and Oscillators
        r"crystal|oscillator|quartz|晶振": {
            "symbols": ["Device:Xtal"],
            "footprints": ["Crystal:Crystal_HC49-4H_Vertical"]
        },

        # Switches and Buttons
        r"switch|tact.*button|button|按键|开关": {
            "symbols": ["Device:SW_Push"],
            "footprints": ["Button_Switch_SMD:SW_SPST_B3U-1000P"]
        },
        r"rotary.*encoder|encoder|旋转编码器": {
            "symbols": ["Device:SW_Rotary_Encoder"],
            "footprints": ["Mechanical:Rotary_Encoder_Alps_EC11E"]
        },
    }

    # JLCPCB basic parts (commonly available)
    JLC_BASIC_PARTS = [
        {
            "symbol": "Device:R",
            "footprint": "Resistor_SMD:R_0805",
            "description": "0805 SMD Resistor",
            "jlcpcb_part": "C21190",
            "price": 0.001
        },
        {
            "symbol": "Device:C",
            "footprint": "Capacitor_SMD:C_0805",
            "description": "0805 SMD Capacitor",
            "jlcpcb_part": "C45783",
            "price": 0.001
        },
        {
            "symbol": "Device:LED",
            "footprint": "LED_SMD:LED_0805",
            "description": "0805 SMD LED",
            "jlcpcb_part": "C2293",
            "price": 0.01
        },
    ]

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the recommender

        Args:
            db_path: Path to component database JSON file
        """
        self.db_path = db_path
        self._db_cache: Dict = {}

        # Load database if exists
        if db_path and Path(db_path).exists():
            self._load_db()
        else:
            self._db_cache = {"components": []}

    def _load_db(self):
        """Load component database from file"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                self._db_cache = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load component DB: {e}")
            self._db_cache = {"components": []}

    def recommend_by_function(
        self,
        description: str,
        limit: int = 5
    ) -> List[ComponentRecommendation]:
        """
        Recommend components based on functional description

        Args:
            description: Natural language description of needed component
            limit: Maximum number of recommendations

        Returns:
            List of ComponentRecommendation objects
        """
        description = description.lower()
        recommendations = []

        # Match against known patterns
        for pattern, template in self.COMPONENT_PATTERNS.items():
            if re.search(pattern, description, re.IGNORECASE):
                for symbol, footprint in zip(template["symbols"], template["footprints"]):
                    rec = ComponentRecommendation(
                        symbol=symbol,
                        footprint=footprint,
                        description=f"Matched: {description}",
                        parameters={},
                        score=0.9,
                        source="pattern_match"
                    )
                    recommendations.append(rec)

                if len(recommendations) >= limit:
                    break

        # Extract parameters from description
        params = self._extract_parameters(description)

        # Add default passives if needed
        if "resistor" in description or "r " in description.lower():
            recommendations.append(self._get_default_resistor(params))
        if "capacitor" in description or " c " in description.lower():
            recommendations.append(self._get_default_capacitor(params))

        # Sort by score
        recommendations.sort(key=lambda r: r.score, reverse=True)

        return recommendations[:limit]

    def _extract_parameters(self, description: str) -> Dict[str, Any]:
        """Extract component parameters from description"""
        params = {}

        # Extract resistance (e.g., "10k resistor", "4.7kΩ", "10kohm")
        res_match = re.search(r'(\d+(?:\.\d+)?)\s*[kKΩ]*(?:ohm)?', description)
        if res_match:
            params['resistance'] = res_match.group(1) + 'k'  # Add k multiplier if not present

        # Extract capacitance (e.g., "100nF capacitor", "10µF", "100n")
        cap_match = re.search(r'(\d+(?:\.\d+)?)\s*[nµuU]*F?', description)
        if cap_match:
            params['capacitance'] = cap_match.group(1) + 'n'  # Add n multiplier

        # Extract voltage (e.g., "5V", "12V")
        volt_match = re.search(r'(\d+)\s*V', description)
        if volt_match:
            params['voltage'] = volt_match.group(1)

        # Extract current (e.g., "3A", "500mA")
        curr_match = re.search(r'(\d+(?:\.\d+)?)\s*[mM]?A', description)
        if curr_match:
            params['current'] = curr_match.group(1)

        return params

    def _get_default_resistor(self, params: Dict) -> ComponentRecommendation:
        """Get default resistor recommendation"""
        value = params.get('resistance', '10k')
        return ComponentRecommendation(
            symbol="Device:R",
            footprint="Resistor_SMD:R_0805",
            description=f"SMD Resistor {value}Ω",
            parameters={"resistance": value, "tolerance": "5%", "power": "0.125W"},
            score=0.7,
            source="default"
        )

    def _get_default_capacitor(self, params: Dict) -> ComponentRecommendation:
        """Get default capacitor recommendation"""
        value = params.get('capacitance', '100n')
        voltage = params.get('voltage', '16V')
        return ComponentRecommendation(
            symbol="Device:C",
            footprint="Capacitor_SMD:C_0805",
            description=f"SMD Capacitor {value}F {voltage}",
            parameters={"capacitance": value, "voltage": voltage, "type": "MLCC"},
            score=0.7,
            source="default"
        )

    def recommend_by_parameters(
        self,
        category: str,
        parameters: Dict,
        limit: int = 5
    ) -> List[ComponentRecommendation]:
        """
        Recommend components based on specific parameters

        Args:
            category: Component category (resistor, capacitor, ic, etc.)
            parameters: Specific parameters (resistance, capacitance, voltage, etc.)
            limit: Maximum number of recommendations

        Returns:
            List of ComponentRecommendation objects
        """
        recommendations = []

        if category == "resistor":
            resistance = parameters.get("resistance", "10k")
            tolerance = parameters.get("tolerance", "5%")
            power = parameters.get("power", "0.125W")

            recommendations.append(ComponentRecommendation(
                symbol="Device:R",
                footprint=self._select_resistor_footprint(power),
                description=f"Resistor {resistance}Ω {tolerance} {power}",
                parameters={
                    "resistance": resistance,
                    "tolerance": tolerance,
                    "power": power
                },
                score=0.95,
                source="parameter_match"
            ))

        elif category == "capacitor":
            capacitance = parameters.get("capacitance", "100n")
            voltage = parameters.get("voltage", "16V")
            cap_type = parameters.get("type", "MLCC")

            recommendations.append(ComponentRecommendation(
                symbol="Device:C",
                footprint=self._select_capacitor_footprint(voltage, cap_type),
                description=f"Capacitor {capacitance}F {voltage}",
                parameters={
                    "capacitance": capacitance,
                    "voltage": voltage,
                    "type": cap_type
                },
                score=0.95,
                source="parameter_match"
            ))

        return recommendations[:limit]

    def _select_resistor_footprint(self, power: str) -> str:
        """Select appropriate resistor footprint based on power rating"""
        power_w = float(re.sub(r'[Ww]', '', power))

        if power_w <= 0.1:
            return "Resistor_SMD:R_0603"
        elif power_w <= 0.125:
            return "Resistor_SMD:R_0805"
        elif power_w <= 0.25:
            return "Resistor_SMD:R_1206"
        else:
            return "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"

    def _select_capacitor_footprint(self, voltage: str, cap_type: str) -> str:
        """Select appropriate capacitor footprint based on voltage and type"""
        voltage_v = int(re.sub(r'[Vv]', '', voltage))

        if cap_type == "electrolytic" or voltage_v >= 50:
            return "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"
        else:
            return "Capacitor_SMD:C_0805"

    def search_lcsc(
        self,
        keywords: str,
        limit: int = 10
    ) -> List[ComponentRecommendation]:
        """
        Search LCSC component database

        Args:
            keywords: Search keywords
            limit: Maximum results

        Returns:
            List of ComponentRecommendation from LCSC
        """
        try:
            from kb_quality.lcsc_fetcher import LcscFetcher

            fetcher = LcscFetcher()
            results = fetcher.search_components(keywords, limit)

            recommendations = []
            for chip in results:
                # 转换为 ComponentRecommendation 格式
                rec = ComponentRecommendation(
                    symbol=chip.symbol or "Device:C",
                    footprint=chip.footprint or "Package_SOIC:SOP-8",
                    description=chip.description or f"LCSC {chip.part_number}",
                    parameters={
                        "part_number": chip.part_number,
                        "manufacturer": chip.manufacturer,
                        "stock": chip.stock,
                    },
                    score=0.8,  # LCSC 数据有较高可信度
                    source="lcsc",
                    part_number=chip.part_number,
                    price=chip.price,
                    stock=chip.stock,
                    lcsc_part=chip.part_number,
                )
                recommendations.append(rec)

            return recommendations
        except Exception as e:
            logger.warning(f"LCSC search failed: {e}")
            return []

    def recommend_from_requirements(
        self,
        requirements: str,
        existing_components: Optional[List[str]] = None
    ) -> Dict[str, List[ComponentRecommendation]]:
        """
        Analyze requirements and recommend all needed components

        Args:
            requirements: Natural language requirements text
            existing_components: Optional list of already included components

        Returns:
            Dictionary mapping component categories to recommendations
        """
        requirements_lower = requirements.lower()
        result = {}

        existing = set(existing_components or [])

        # USB connector
        if "usb" in requirements_lower and "usb_c" not in existing:
            result["usb_connector"] = self.recommend_by_function("USB type-c connector", limit=2)

        # Voltage regulator
        if any(x in requirements_lower for x in ["5v", "3.3v", "regulator", "power"]):
            if "regulator" not in existing:
                result["regulator"] = self.recommend_by_function("voltage regulator", limit=2)

        # Resistors (always needed for pull-ups/down)
        if "resistor" in requirements_lower or "r " in requirements_lower:
            result["resistors"] = self.recommend_by_function("resistor", limit=3)

        # Capacitors (for decoupling)
        if "capacitor" in requirements_lower or "c " in requirements_lower:
            result["capacitors"] = self.recommend_by_function("capacitor", limit=5)

        # USB to UART bridge (common need)
        if any(x in requirements_lower for x in ["serial", "uart", "programming", "debug"]):
            if "usb_bridge" not in existing:
                result["usb_bridge"] = self.recommend_by_function("USB to UART bridge CH340", limit=1)

        # Crystal (for MCU)
        if "crystal" in requirements_lower or "oscillator" in requirements_lower:
            result["crystal"] = self.recommend_by_function("crystal oscillator 8MHz", limit=1)

        # LED indicator
        if "led" in requirements_lower or "indicator" in requirements_lower:
            result["led"] = self.recommend_by_function("LED", limit=2)

        return result

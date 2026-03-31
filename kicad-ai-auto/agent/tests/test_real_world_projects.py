"""
Real-World PCB Project Integration Tests

Uses 4 authentic PCB design scenarios to validate the complete design pipeline:
  ComponentRecommender → LayerCalculator → SchematicGenerator

Test Projects:
  1. STM32F103 Minimum System Board (ARM Cortex-M3 MCU)
  2. ESP32-WROOM IoT Development Board (WiFi/BLE + USB-Serial)
  3. NE555 Timer Circuit (Classic analog timer)
  4. USB-C PD Charger (Power delivery with LDO regulation)

These test the full integration flow, not just individual modules.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.component_recommender import ComponentRecommender, ComponentRecommendation
from services.layer_calculator import LayerCalculator, CircuitAnalysis, CircuitComplexity
from schematic_generator import (
    SchematicGenerator,
    SchematicComponent,
    ComponentCategory,
    PinType,
)


# ============================================================================
# Real-World Project Definitions
# ============================================================================

STM32_MIN_SYSTEM = {
    "name": "STM32F103C8T6 Minimum System Board",
    "description": "Blue Pill style development board with STM32F103C8T6 MCU",
    "bom": [
        {"name": "STM32F103C8T6", "model": "STM32F103C8T6", "category": "MCU", "quantity": 1},
        {"name": "8MHz Crystal", "model": "Crystal 8MHz", "category": "Crystal", "quantity": 1},
        {"name": "20pF Capacitor", "model": "C 20pF", "category": "Passive", "quantity": 2},
        {"name": "100nF Capacitor", "model": "C 100nF", "category": "Passive", "quantity": 4},
        {"name": "10uF Capacitor", "model": "C 10uF", "category": "Passive", "quantity": 1},
        {"name": "10K Resistor", "model": "R 10K", "category": "Passive", "quantity": 2},
        {"name": "1K Resistor", "model": "R 1K", "category": "Passive", "quantity": 2},
        {"name": "LED", "model": "LED Blue", "category": "LED", "quantity": 1},
        {"name": "USB Type-B Connector", "model": "USB_B", "category": "Connector", "quantity": 1},
        {"name": "Reset Button", "model": "SW_Push", "category": "Switch", "quantity": 1},
        {"name": "AMS1117-3.3", "model": "AMS1117-3.3", "category": "Power", "quantity": 1},
        {"name": "Boot Jumper", "model": "Header_2x2", "category": "Connector", "quantity": 2},
    ],
    "requirements": "STM32 minimum system with USB, 8MHz crystal, 3.3V LDO, reset button",
    "nets": [
        {"name": "VCC_3V3"},
        {"name": "VCC_5V"},
        {"name": "GND"},
        {"name": "NRST"},
        {"name": "BOOT0"},
        {"name": "BOOT1"},
        {"name": "USB_DM"},
        {"name": "USB_DP"},
        {"name": "OSC_IN"},
        {"name": "OSC_OUT"},
    ],
    "expected_layers": 4,  # USB + MCU
}

ESP32_IOT_BOARD = {
    "name": "ESP32-WROOM IoT Development Board",
    "description": "WiFi/BLE IoT board with USB-Serial bridge and voltage regulation",
    "bom": [
        {"name": "ESP32-WROOM-32", "model": "ESP32-WROOM-32", "category": "MCU", "quantity": 1},
        {"name": "CH340C", "model": "CH340C", "category": "Interface", "quantity": 1},
        {"name": "AMS1117-3.3", "model": "AMS1117-3.3", "category": "Power", "quantity": 1},
        {"name": "100nF Capacitor", "model": "C 100nF", "category": "Passive", "quantity": 6},
        {"name": "10uF Capacitor", "model": "C 10uF", "category": "Passive", "quantity": 2},
        {"name": "22uF Capacitor", "model": "C 22uF", "category": "Passive", "quantity": 1},
        {"name": "10K Resistor", "model": "R 10K", "category": "Passive", "quantity": 3},
        {"name": "1K Resistor", "model": "R 1K", "category": "Passive", "quantity": 2},
        {"name": "LED", "model": "LED Blue", "category": "LED", "quantity": 2},
        {"name": "USB Type-C Connector", "model": "USB_C", "category": "Connector", "quantity": 1},
        {"name": "Reset Button", "model": "SW_Push", "category": "Switch", "quantity": 2},
        {"name": "40pin Header", "model": "PinHeader_1x20", "category": "Connector", "quantity": 2},
    ],
    "requirements": "ESP32 IoT board with USB-C, CH340C UART bridge, 3.3V LDO, WiFi/BLE",
    "nets": [
        {"name": "VCC_3V3"},
        {"name": "VCC_5V_USB"},
        {"name": "GND"},
        {"name": "UART_TX"},
        {"name": "UART_RX"},
        {"name": "IO0"},
        {"name": "EN"},
        {"name": "USB_DM"},
        {"name": "USB_DP"},
    ],
    "expected_layers": 4,  # USB + WiFi RF
}

NE555_TIMER_CIRCUIT = {
    "name": "NE555 Timer Circuit",
    "description": "Classic NE555 astable multivibrator with LED output",
    "bom": [
        {"name": "NE555", "model": "NE555", "category": "IC", "quantity": 1},
        {"name": "10K Resistor", "model": "R 10K", "category": "Passive", "quantity": 2},
        {"name": "1K Resistor", "model": "R 1K", "category": "Passive", "quantity": 1},
        {"name": "10uF Capacitor", "model": "C 10uF", "category": "Passive", "quantity": 1},
        {"name": "100nF Capacitor", "model": "C 100nF", "category": "Passive", "quantity": 1},
        {"name": "LED", "model": "LED Red", "category": "LED", "quantity": 1},
        {"name": "9V Battery Connector", "model": "Conn_01x02", "category": "Connector", "quantity": 1},
    ],
    "requirements": "NE555 astable timer circuit with LED blink output, battery powered",
    "nets": [
        {"name": "VCC_9V"},
        {"name": "GND"},
        {"name": "TRIGGER"},
        {"name": "THRESHOLD"},
        {"name": "OUTPUT"},
        {"name": "DISCHARGE"},
        {"name": "CONTROL"},
    ],
    "expected_layers": 2,  # Simple analog circuit
}

USB_C_CHARGER = {
    "name": "USB-C PD Charger with LDO",
    "description": "USB-C powered charger with 5V and 3.3V outputs",
    "bom": [
        {"name": "USB Type-C Connector", "model": "USB_C_16P", "category": "Connector", "quantity": 1},
        {"name": "AMS1117-3.3", "model": "AMS1117-3.3", "category": "Power", "quantity": 1},
        {"name": "LM7805", "model": "LM7805", "category": "Power", "quantity": 1},
        {"name": "100uF Electrolytic", "model": "C_Polarized 100uF", "category": "Passive", "quantity": 2},
        {"name": "100nF Capacitor", "model": "C 100nF", "category": "Passive", "quantity": 4},
        {"name": "10uF Capacitor", "model": "C 10uF", "category": "Passive", "quantity": 2},
        {"name": "1K Resistor", "model": "R 1K", "category": "Passive", "quantity": 2},
        {"name": "5.1K Resistor", "model": "R 5.1K", "category": "Passive", "quantity": 2},  # USB-C CC pull-down
        {"name": "LED Power", "model": "LED Green", "category": "LED", "quantity": 1},
        {"name": "LED 3V3", "model": "LED Red", "category": "LED", "quantity": 1},
        {"name": "Schottky Diode", "model": "1N5819", "category": "Active", "quantity": 1},
        {"name": "Output Header", "model": "PinHeader_1x04", "category": "Connector", "quantity": 1},
    ],
    "requirements": "USB-C powered dual output 5V/3.3V charger with reverse polarity protection",
    "nets": [
        {"name": "VBUS_5V"},
        {"name": "VCC_5V"},
        {"name": "VCC_3V3"},
        {"name": "GND"},
        {"name": "CC1"},
        {"name": "CC2"},
    ],
    "expected_layers": 4,  # USB-C + power integrity
}

ALL_PROJECTS = [STM32_MIN_SYSTEM, ESP32_IOT_BOARD, NE555_TIMER_CIRCUIT, USB_C_CHARGER]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def recommender():
    return ComponentRecommender()


@pytest.fixture
def layer_calculator():
    return LayerCalculator()


@pytest.fixture
def schematic_generator():
    return SchematicGenerator()


# ============================================================================
# Test: Component Recommender with Real BOMs
# ============================================================================

class TestRealWorldComponentRecommendation:
    """Validate component recommendation for real PCB projects."""

    def test_stm32_mcu_recommendation(self, recommender):
        """STM32 project should recommend STM32 symbol."""
        results = recommender.recommend_by_function("STM32 microcontroller")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("STM32" in s or "MCU" in s for s in symbols), \
            f"Expected STM32 symbol, got: {symbols}"

    def test_esp32_mcu_recommendation(self, recommender):
        """ESP32 project should recommend ESP32 symbol."""
        results = recommender.recommend_by_function("ESP32 WiFi module")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("ESP32" in s for s in symbols), f"Expected ESP32, got: {symbols}"

    def test_ne555_timer_recommendation(self, recommender):
        """NE555 project should recommend timer IC symbol."""
        results = recommender.recommend_by_function("NE555 timer")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("NE555" in s or "Timer" in s for s in symbols), \
            f"Expected NE555/Timer, got: {symbols}"

    def test_usb_c_connector_recommendation(self, recommender):
        """USB-C charger should recommend USB-C connector."""
        results = recommender.recommend_by_function("USB type-c connector")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("USB" in s and "C" in s for s in symbols), \
            f"Expected USB-C connector, got: {symbols}"

    def test_ams1117_regulator_recommendation(self, recommender):
        """Projects with LDO should recommend AMS1117."""
        results = recommender.recommend_by_function("3.3V regulator AMS1117")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("AMS1117" in s or "Regulator" in s for s in symbols), \
            f"Expected AMS1117, got: {symbols}"

    def test_ch340_uart_bridge_recommendation(self, recommender):
        """ESP32 board should recommend CH340 USB-Serial bridge."""
        results = recommender.recommend_by_function("USB to UART bridge CH340")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("CH340" in s or "USB" in s for s in symbols), \
            f"Expected CH340, got: {symbols}"

    def test_crystal_recommendation(self, recommender):
        """STM32 project should recommend crystal oscillator."""
        results = recommender.recommend_by_function("8MHz crystal oscillator")
        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("Crystal" in s or "Xtal" in s for s in symbols), \
            f"Expected crystal, got: {symbols}"

    def test_full_bom_recommendation_stm32(self, recommender):
        """STM32 BOM: recommend_from_requirements should detect MCU, USB, crystal needs."""
        result = recommender.recommend_from_requirements(
            "STM32 microcontroller with USB, 8MHz crystal, 3.3V regulator and LED"
        )
        assert isinstance(result, dict)
        assert len(result) >= 2, f"Expected >= 2 categories, got: {list(result.keys())}"

    def test_full_bom_recommendation_esp32(self, recommender):
        """ESP32 BOM: should detect WiFi, USB, UART bridge needs."""
        result = recommender.recommend_from_requirements(
            "ESP32 WiFi board with USB-C serial CH340, 3.3V LDO, LED indicators"
        )
        assert isinstance(result, dict)
        assert len(result) >= 2, f"Expected >= 2 categories, got: {list(result.keys())}"

    def test_resistor_power_footprint_mapping(self, recommender):
        """Resistor footprints should scale with power rating (real-world constraint)."""
        low_power = recommender.recommend_by_parameters(
            "resistor", {"resistance": "10k", "tolerance": "1%", "power": "0.1W"}
        )
        assert len(low_power) > 0
        assert "0603" in low_power[0].footprint

        std_power = recommender.recommend_by_parameters(
            "resistor", {"resistance": "10k", "tolerance": "5%", "power": "0.125W"}
        )
        assert len(std_power) > 0
        assert "0805" in std_power[0].footprint

        high_power = recommender.recommend_by_parameters(
            "resistor", {"resistance": "100", "tolerance": "1%", "power": "0.25W"}
        )
        assert len(high_power) > 0
        assert "1206" in high_power[0].footprint

    def test_capacitor_voltage_footprint_mapping(self, recommender):
        """Capacitor footprints should change for high-voltage / electrolytic."""
        mlcc = recommender.recommend_by_parameters(
            "capacitor", {"capacitance": "100n", "voltage": "16V", "type": "MLCC"}
        )
        assert len(mlcc) > 0
        assert "SMD" in mlcc[0].footprint or "0805" in mlcc[0].footprint

        elec = recommender.recommend_by_parameters(
            "capacitor", {"capacitance": "100u", "voltage": "50V", "type": "electrolytic"}
        )
        assert len(elec) > 0
        assert "THT" in elec[0].footprint or "Radial" in elec[0].footprint


# ============================================================================
# Test: Layer Calculator with Real Projects
# ============================================================================

class TestRealWorldLayerCalculation:
    """Validate PCB layer count recommendations for real projects."""

    def test_stm32_layers(self, layer_calculator):
        """STM32 with USB should need 4 layers (high-speed USB interface)."""
        result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in STM32_MIN_SYSTEM["bom"]],
            "requirements": STM32_MIN_SYSTEM["requirements"],
            "nets": STM32_MIN_SYSTEM["nets"],
        })
        assert result.layer_count >= STM32_MIN_SYSTEM["expected_layers"], \
            f"STM32: expected >= {STM32_MIN_SYSTEM['expected_layers']} layers, got {result.layer_count}"
        assert result.analysis.high_speed_io_count >= 4, \
            "STM32 USB should detect high-speed IO"

    def test_esp32_layers(self, layer_calculator):
        """ESP32 with WiFi + USB should need 4 layers (RF + high-speed)."""
        result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in ESP32_IOT_BOARD["bom"]],
            "requirements": ESP32_IOT_BOARD["requirements"],
            "nets": ESP32_IOT_BOARD["nets"],
        })
        assert result.layer_count >= ESP32_IOT_BOARD["expected_layers"], \
            f"ESP32: expected >= {ESP32_IOT_BOARD['expected_layers']} layers, got {result.layer_count}"
        assert result.analysis.has_rf, "ESP32 should detect RF requirement"

    def test_ne555_layers(self, layer_calculator):
        """NE555 simple timer should only need 2 layers."""
        result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in NE555_TIMER_CIRCUIT["bom"]],
            "requirements": NE555_TIMER_CIRCUIT["requirements"],
            "nets": NE555_TIMER_CIRCUIT["nets"],
        })
        assert result.layer_count <= NE555_TIMER_CIRCUIT["expected_layers"], \
            f"NE555: expected <= {NE555_TIMER_CIRCUIT['expected_layers']} layers, got {result.layer_count}"

    def test_usb_c_charger_layers(self, layer_calculator):
        """USB-C charger with dual LDO should need 4 layers."""
        result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in USB_C_CHARGER["bom"]],
            "requirements": USB_C_CHARGER["requirements"],
            "nets": USB_C_CHARGER["nets"],
        })
        assert result.layer_count >= USB_C_CHARGER["expected_layers"], \
            f"USB-C charger: expected >= {USB_C_CHARGER['expected_layers']} layers, got {result.layer_count}"

    def test_all_projects_have_valid_layer_config(self, layer_calculator):
        """All project recommendations should have valid layer configs."""
        for project in ALL_PROJECTS:
            result = layer_calculator.calculate_layers_from_dict({
                "components": [c["model"] for c in project["bom"]],
                "requirements": project["requirements"],
                "nets": project["nets"],
            })
            config = layer_calculator.get_layer_config(result.layer_count)
            assert "name" in config, f"{project['name']}: missing layer config name"
            assert "cost" in config, f"{project['name']}: missing layer config cost"
            assert result.confidence > 0, f"{project['name']}: invalid confidence"

    def test_esp32_rf_warning(self, layer_calculator):
        """ESP32 with RF should produce RF-specific warning."""
        result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in ESP32_IOT_BOARD["bom"]],
            "requirements": ESP32_IOT_BOARD["requirements"],
            "nets": ESP32_IOT_BOARD["nets"],
        })
        assert result.analysis.has_rf
        assert any("RF" in w for w in result.warnings), \
            f"Expected RF warning, got: {result.warnings}"


# ============================================================================
# Test: Schematic Generator with Real Components
# ============================================================================

class TestRealWorldSchematicGeneration:
    """Validate schematic generation for real PCB projects."""

    def test_stm32_component_categorization(self, schematic_generator):
        """STM32 BOM should correctly categorize: MCU, crystal, passive, LED, power, connector."""
        components = STM32_MIN_SYSTEM["bom"]
        categorized = schematic_generator._categorize_components(components)

        mcu_comps = categorized.get(ComponentCategory.MCU, [])
        assert len(mcu_comps) >= 1, f"Expected MCU category, got: {list(categorized.keys())}"
        assert any("STM32" in c.get("model", "") or "stm32" in c.get("name", "").lower()
                    for c in mcu_comps), "STM32 should be in MCU category"

        crystal_comps = categorized.get(ComponentCategory.CRYSTAL, [])
        assert len(crystal_comps) >= 1, "Expected crystal in Crystal category"

        power_comps = categorized.get(ComponentCategory.POWER, [])
        assert len(power_comps) >= 1, "Expected AMS1117 in Power category"

        led_comps = categorized.get(ComponentCategory.LED, [])
        assert len(led_comps) >= 1, "Expected LED in LED category"

    def test_esp32_component_categorization(self, schematic_generator):
        """ESP32 BOM: ESP32 as MCU, CH340 as Interface, AMS1117 as Power."""
        components = ESP32_IOT_BOARD["bom"]
        categorized = schematic_generator._categorize_components(components)

        mcu_comps = categorized.get(ComponentCategory.MCU, [])
        assert len(mcu_comps) >= 1, "ESP32 should be in MCU category"

        interface_comps = categorized.get(ComponentCategory.INTERFACE, [])
        assert len(interface_comps) >= 1, "CH340 should be in Interface category"

        power_comps = categorized.get(ComponentCategory.POWER, [])
        assert len(power_comps) >= 1, "AMS1117 should be in Power category"

    def test_ne555_categorization(self, schematic_generator):
        """NE555 should be categorized correctly (not as MCU)."""
        components = NE555_TIMER_CIRCUIT["bom"]
        categorized = schematic_generator._categorize_components(components)

        mcu_comps = categorized.get(ComponentCategory.MCU, [])
        assert len(mcu_comps) == 0, "NE555 should NOT be in MCU category"

    def test_usb_c_charger_categorization(self, schematic_generator):
        """USB-C charger: power regulators in Power, USB connector in Connector."""
        components = USB_C_CHARGER["bom"]
        categorized = schematic_generator._categorize_components(components)

        power_comps = categorized.get(ComponentCategory.POWER, [])
        assert len(power_comps) >= 2, "Expected LM7805 + AMS1117 in Power category"

        connector_comps = categorized.get(ComponentCategory.CONNECTOR, [])
        assert len(connector_comps) >= 1, "Expected USB-C connector"

    def test_quantity_expansion(self, schematic_generator):
        """BOM with quantity > 1 should expand to multiple instances."""
        components = [
            {"name": "100nF Capacitor", "model": "C 100nF", "quantity": 4},
        ]
        categorized = schematic_generator._categorize_components(components)

        passive_comps = categorized.get(ComponentCategory.PASSIVE, [])
        assert len(passive_comps) == 4, \
            f"Expected 4 capacitors after expansion, got {len(passive_comps)}"

    def test_quantity_zero_clamped_to_one(self, schematic_generator):
        """Quantity of 0 or negative should be clamped to 1."""
        components = [
            {"name": "Resistor", "model": "R", "quantity": 0},
            {"name": "Capacitor", "model": "C", "quantity": -1},
        ]
        categorized = schematic_generator._categorize_components(components)

        passive_count = len(categorized.get(ComponentCategory.PASSIVE, []))
        assert passive_count == 2, f"Expected 2 (clamped from 0 and -1), got {passive_count}"

    def test_generate_stm32_schematic(self, schematic_generator):
        """STM32 full schematic generation should produce components, nets, wires."""
        components = STM32_MIN_SYSTEM["bom"]
        sheet = schematic_generator.generate(components, circuit_type="mcu")

        assert len(sheet.components) > 0, "Sheet should have components"
        assert len(sheet.nets) > 0, "Sheet should have nets"
        assert len(sheet.wires) > 0, "Sheet should have wires"

    def test_generate_esp32_schematic(self, schematic_generator):
        """ESP32 full schematic generation."""
        components = ESP32_IOT_BOARD["bom"]
        sheet = schematic_generator.generate(components, circuit_type="mcu")

        assert len(sheet.components) > 0
        assert len(sheet.nets) > 0

    def test_generate_ne555_schematic(self, schematic_generator):
        """NE555 timer schematic generation."""
        components = NE555_TIMER_CIRCUIT["bom"]
        sheet = schematic_generator.generate(components, circuit_type="general")

        assert len(sheet.components) > 0
        assert len(sheet.power_symbols) > 0, "Should have VCC and GND power symbols"

    def test_generate_empty_schematic(self, schematic_generator):
        """Empty component list should produce valid (empty) sheet."""
        sheet = schematic_generator.generate([], circuit_type="general")
        assert sheet is not None
        assert isinstance(sheet.components, list)


# ============================================================================
# Test: Cross-Module Integration Pipeline
# ============================================================================

class TestFullDesignPipeline:
    """Test the complete design pipeline: Recommend → Analyze → Generate."""

    def test_stm32_full_pipeline(self, recommender, layer_calculator, schematic_generator):
        """STM32: Recommend components → Calculate layers → Generate schematic."""
        recs = recommender.recommend_from_requirements(
            STM32_MIN_SYSTEM["requirements"]
        )
        assert isinstance(recs, dict)
        assert len(recs) >= 1

        layer_result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in STM32_MIN_SYSTEM["bom"]],
            "requirements": STM32_MIN_SYSTEM["requirements"],
            "nets": STM32_MIN_SYSTEM["nets"],
        })
        assert layer_result.layer_count >= 2

        sheet = schematic_generator.generate(
            STM32_MIN_SYSTEM["bom"], circuit_type="mcu"
        )
        assert len(sheet.components) > 0
        assert len(sheet.nets) > 0

        expected_count = len(STM32_MIN_SYSTEM["bom"])
        actual_count = len(sheet.components)
        assert actual_count >= expected_count * 0.8, \
            f"Expected ~{expected_count} components, got {actual_count}"

    def test_esp32_full_pipeline(self, recommender, layer_calculator, schematic_generator):
        """ESP32: Full design pipeline validation."""
        recs = recommender.recommend_from_requirements(
            ESP32_IOT_BOARD["requirements"]
        )
        assert len(recs) >= 1

        layer_result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in ESP32_IOT_BOARD["bom"]],
            "requirements": ESP32_IOT_BOARD["requirements"],
            "nets": ESP32_IOT_BOARD["nets"],
        })
        assert layer_result.layer_count >= 4, "ESP32 + WiFi should need 4+ layers"
        assert layer_result.analysis.has_rf, "Should detect RF for ESP32"

        sheet = schematic_generator.generate(
            ESP32_IOT_BOARD["bom"], circuit_type="mcu"
        )
        assert len(sheet.components) > 0

    def test_ne555_full_pipeline(self, recommender, layer_calculator, schematic_generator):
        """NE555: Simple circuit should stay at 2 layers."""
        recs = recommender.recommend_by_function("NE555 timer IC")
        assert len(recs) > 0

        layer_result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in NE555_TIMER_CIRCUIT["bom"]],
            "requirements": NE555_TIMER_CIRCUIT["requirements"],
            "nets": NE555_TIMER_CIRCUIT["nets"],
        })
        assert layer_result.layer_count <= 2, \
            f"Simple NE555 circuit should need <= 2 layers, got {layer_result.layer_count}"

        sheet = schematic_generator.generate(
            NE555_TIMER_CIRCUIT["bom"], circuit_type="general"
        )
        assert len(sheet.components) >= 7  # 7 BOM items

    def test_usb_c_charger_full_pipeline(self, recommender, layer_calculator, schematic_generator):
        """USB-C charger: Power design with USB interface."""
        recs = recommender.recommend_from_requirements(
            USB_C_CHARGER["requirements"]
        )
        assert len(recs) >= 1

        layer_result = layer_calculator.calculate_layers_from_dict({
            "components": [c["model"] for c in USB_C_CHARGER["bom"]],
            "requirements": USB_C_CHARGER["requirements"],
            "nets": USB_C_CHARGER["nets"],
        })
        assert layer_result.layer_count >= 4, \
            f"USB-C charger should need >= 4 layers, got {layer_result.layer_count}"

        sheet = schematic_generator.generate(
            USB_C_CHARGER["bom"], circuit_type="power_supply"
        )
        assert len(sheet.components) > 0


# ============================================================================
# Test: Edge Cases & Boundary Conditions
# ============================================================================

class TestEdgeCases:
    """Edge cases discovered from real-world PCB design scenarios."""

    def test_chinese_component_names(self, recommender):
        """Components described in Chinese should still match patterns."""
        recs_reg = recommender.recommend_by_function("稳压器 3.3V")
        assert len(recs_reg) > 0, "Chinese regulator name should match"

    def test_mixed_case_component_names(self, recommender):
        """Component names with mixed case should match."""
        recs = recommender.recommend_by_function("UsB TyPe-C CoNnEcToR")
        assert len(recs) > 0, "Mixed case should still match"

    def test_extra_whitespace_in_requirements(self, recommender):
        """Requirements with extra spaces should still parse."""
        params = recommender._extract_parameters("  10K   resistor  ")
        assert "resistance" in params

    def test_layer_calculator_empty_components(self, layer_calculator):
        """Empty component list should return valid result (1 layer minimum)."""
        result = layer_calculator.calculate_layers_from_dict({})
        assert result.layer_count >= 1
        assert result.confidence > 0

    def test_component_count_estimation(self, layer_calculator):
        """Pin count estimation: component_count * 4."""
        analysis = layer_calculator.analyze_circuit({
            "components": ["IC1", "IC2", "IC3"]
        })
        assert analysis.component_count == 3
        assert analysis.estimated_pins == 12  # 3 * 4

    def test_schematic_quantity_string_type(self, schematic_generator):
        """Quantity as string should not crash the categorization."""
        components = [
            {"name": "Resistor", "model": "R", "quantity": "3"},
        ]
        categorized = schematic_generator._categorize_components(components)
        passive = categorized.get(ComponentCategory.PASSIVE, [])
        assert len(passive) == 3

    def test_schematic_quantity_none_type(self, schematic_generator):
        """Quantity as None should default to 1."""
        components = [
            {"name": "Resistor", "model": "R", "quantity": None},
        ]
        categorized = schematic_generator._categorize_components(components)
        passive = categorized.get(ComponentCategory.PASSIVE, [])
        assert len(passive) == 1

    def test_recommendation_score_range(self, recommender):
        """All recommendation scores should be in [0, 1] range."""
        results = recommender.recommend_by_function("ESP32 WiFi module with USB")
        for r in results:
            assert 0 <= r.score <= 1, f"Score {r.score} out of range [0,1]"

    def test_recommendation_limit_enforcement(self, recommender):
        """Recommendation limit should be respected."""
        for limit in [1, 3, 10]:
            results = recommender.recommend_by_function("resistor", limit=limit)
            assert len(results) <= limit, \
                f"Limit={limit} but got {len(results)} results"

    def test_layer_config_all_standard_values(self, layer_calculator):
        """Standard layer configs (1,2,4,6,8) should all have valid data."""
        for n in [1, 2, 4, 6, 8]:
            config = layer_calculator.get_layer_config(n)
            assert "name" in config, f"Layer {n}: missing name"
            assert "cost" in config, f"Layer {n}: missing cost"
            assert config["cost"] > 0, f"Layer {n}: cost must be positive"


# ============================================================================
# Test: Project Comparison Matrix
# ============================================================================

class TestProjectComparisonMatrix:
    """Cross-project comparison to validate design complexity scaling."""

    def test_layer_count_increases_with_complexity(self, layer_calculator):
        """More complex projects should get equal or more layers."""
        results = {}
        for project in ALL_PROJECTS:
            result = layer_calculator.calculate_layers_from_dict({
                "components": [c["model"] for c in project["bom"]],
                "requirements": project["requirements"],
                "nets": project["nets"],
            })
            results[project["name"]] = result.layer_count

        assert results["NE555 Timer Circuit"] <= results["ESP32-WROOM IoT Development Board"], \
            f"NE555 ({results['NE555 Timer Circuit']}) should have <= layers than ESP32 ({results['ESP32-WROOM IoT Development Board']})"

    def test_confidence_decreases_for_ambiguous_projects(self, layer_calculator):
        """Projects with clear requirements should have higher confidence."""
        clear = layer_calculator.calculate_layers_from_dict({
            "requirements": "5GHz RF circuit with impedance control",
            "components": ["RF_IC"],
        })
        assert clear.confidence >= 0.85

    def test_all_projects_produce_valid_analysis(self, layer_calculator):
        """Every project should produce a complete CircuitAnalysis."""
        for project in ALL_PROJECTS:
            analysis = layer_calculator.analyze_circuit({
                "components": [c["model"] for c in project["bom"]],
                "requirements": project["requirements"],
                "nets": project["nets"],
            })
            assert isinstance(analysis.complexity, CircuitComplexity), \
                f"{project['name']}: invalid complexity"
            assert analysis.component_count > 0, \
                f"{project['name']}: should have components"
            analysis_dict = analysis.to_dict()
            assert "circuit_type" in analysis_dict, \
                f"{project['name']}: to_dict missing circuit_type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

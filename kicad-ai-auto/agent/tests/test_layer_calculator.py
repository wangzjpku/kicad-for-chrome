"""
Tests for Layer Calculator Service

Tests the automatic PCB layer calculation engine.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.layer_calculator import (
    LayerCalculator,
    CircuitAnalysis,
    CircuitComplexity,
    LayerRecommendation
)


class TestLayerCalculator:
    """Test suite for LayerCalculator"""

    def setup_method(self):
        """Setup test fixtures"""
        self.calculator = LayerCalculator()

    def test_simple_circuit_single_layer(self):
        """Test: Simple circuit should recommend single layer"""
        circuit_data = {
            "components": ["R1", "R2", "C1"],
            "requirements": "simple LED circuit with resistor",
            "nets": [{"name": "VCC"}, {"name": "GND"}],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count == 1
        assert "简单电路" in result.reasons[0]

    def test_standard_digital_two_layers(self):
        """Test: Standard digital circuit should recommend 2 layers"""
        circuit_data = {
            "components": ["U1", "R1", "R2", "C1", "C2", "LED1", "LED2"],
            "requirements": "digital logic circuit with microcontroller",
            "nets": [
                {"name": "VCC"},
                {"name": "GND"},
                {"name": "NET1"},
                {"name": "NET2"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count == 2
        assert result.analysis.complexity in [
            CircuitComplexity.SIMPLE,
            CircuitComplexity.STANDARD
        ]

    def test_high_speed_4_layers(self):
        """Test: High speed circuit (>1GHz) should recommend 4 layers"""
        circuit_data = {
            "components": ["DDR3_IC", "U1_MCU"],
            "requirements": "high speed DDR memory interface at 1.6 GHz",
            "high_speed_signals": [
                {"name": "DDR_DQ", "frequency_ghz": 1.6},
                {"name": "DDR_DQS", "frequency_ghz": 1.6},
            ],
            "nets": [
                {"name": "DDR_VDD"},
                {"name": "DDR_VSS"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert any("高频信号" in r or "1" in r for r in result.reasons)

    def test_very_high_speed_6_layers(self):
        """Test: Very high speed circuit (>5GHz) should recommend 6 layers"""
        circuit_data = {
            "components": ["USB3_IC", "PCIe_IC"],
            "requirements": "USB 3.2 and PCIe 4.0 interface at 8 GHz",
            "high_speed_signals": [
                {"name": "USB3_TX", "frequency_ghz": 10.0},
                {"name": "USB3_RX", "frequency_ghz": 10.0},
            ],
            "nets": [
                {"name": "USB_VBUS"},
                {"name": "GND"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 6
        assert any("5" in r or "GHz" in r for r in result.reasons)

    def test_differential_pairs_6_layers(self):
        """Test: Many differential pairs (>4) should recommend 6 layers"""
        circuit_data = {
            "components": ["PHY1", "PHY2", "MAC"],
            "requirements": "ethernet with 8 differential pairs",
            "nets": [
                {"name": "ETH_RX_P1", "type": "differential"},
                {"name": "ETH_RX_N1", "type": "differential"},
                {"name": "ETH_TX_P1", "type": "differential"},
                {"name": "ETH_TX_N1", "type": "differential"},
                {"name": "ETH_RX_P2", "type": "differential"},
                {"name": "ETH_RX_N2", "type": "differential"},
                {"name": "ETH_TX_P2", "type": "differential"},
                {"name": "ETH_TX_N2", "type": "differential"},
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 6
        assert any("差分对" in r for r in result.reasons)

    def test_multi_power_rails_4_layers(self):
        """Test: Multiple power rails (>3) should recommend 4 layers"""
        circuit_data = {
            "components": ["LDO_3V3", "LDO_1V8", "LDO_1V2", "DC-DC", "IC1", "IC2"],
            "requirements": "multi-rail power supply with 3.3V, 1.8V, 1.2V and 5V rails",
            "power_rails": [
                {"name": "VDD_3V3", "voltage": 3.3, "current_ma": 500},
                {"name": "VDD_1V8", "voltage": 1.8, "current_ma": 300},
                {"name": "VDD_1V2", "voltage": 1.2, "current_ma": 1000},
                {"name": "VDD_5V", "voltage": 5.0, "current_ma": 2000},
            ],
            "nets": [
                {"name": "VCC"},
                {"name": "GND"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert any("电源" in r or "多电源" in r for r in result.reasons)

    def test_high_current_4_layers(self):
        """Test: High current (>10A) should recommend 4 layers"""
        circuit_data = {
            "components": ["MOSFET", "Driver", "Inductor"],
            "requirements": "motor driver circuit handling 15A current",
            "power_rails": [
                {"name": "VMOTOR", "voltage": 24, "current_ma": 15000},
            ],
            "nets": [
                {"name": "MOTOR_PWR"},
                {"name": "GND"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert any("电流" in r for r in result.reasons)

    def test_impedance_control_4_layers(self):
        """Test: Impedance control requirement should recommend 4 layers"""
        circuit_data = {
            "components": ["USB_IC", "Connector"],
            "requirements": "USB 2.0 with impedance control for 90 ohm differential",
            "nets": [
                {"name": "USB_DP"},
                {"name": "USB_DM"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert result.analysis.has_impedance_control

    def test_rf_circuit(self):
        """Test: RF circuit should recommend 4+ layers"""
        circuit_data = {
            "components": ["RF_IC", "Filter", "Antenna"],
            "requirements": "2.4 GHz RF transceiver module",
            "nets": [
                {"name": "RF_IN"},
                {"name": "GND"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert result.analysis.has_rf
        assert any("RF" in w for w in result.warnings)

    def test_analog_mixed_signal(self):
        """Test: Analog mixed signal should recommend 4 layers"""
        circuit_data = {
            "components": ["ADC", "Opamp", "MCU"],
            "requirements": "analog sensor interface with ADC and operational amplifier",
            "nets": [
                {"name": "VCC"},
                {"name": "GND"},
                {"name": "SENSOR_IN"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert result.analysis.has_analog_mixed

    def test_high_speed_io_threshold(self):
        """Test: High speed IO count threshold triggers 4 layers"""
        circuit_data = {
            "components": ["FPGA"],
            "requirements": "FPGA with 32 high speed IO pins for parallel bus",
            "high_speed_signals": [
                {"name": f"DATA{i}", "frequency_ghz": 0.2} for i in range(32)
            ],
            "nets": [{"name": "VCC"}, {"name": "GND"}],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert result.analysis.high_speed_io_count >= 20

    def test_usb_ethernet_detection(self):
        """Test: USB/Ethernet requirements should be detected as high speed"""
        circuit_data = {
            "components": ["USB_IC", "ETH_PHY"],
            "requirements": "USB-C and Ethernet interface",
            "nets": [
                {"name": "USB_P"},
                {"name": "USB_N"},
                {"name": "ETH_TX"},
                {"name": "ETH_RX"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.analysis.high_speed_io_count >= 4
        assert result.layer_count >= 4

    def test_motor_driver_detection(self):
        """Test: Motor driver should be detected as power critical"""
        circuit_data = {
            "components": ["H_BRIDGE", "MOSFET", "Motor"],
            "requirements": "DC motor driver with H-bridge",
            "nets": [
                {"name": "MOTOR_PWR"},
                {"name": "GND"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.analysis.circuit_type == "power"
        assert result.analysis.is_power_critical

    def test_complexity_assignment(self):
        """Test: Circuit complexity is correctly determined"""
        # Simple
        simple = CircuitAnalysis(component_count=3)
        calc = self.calculator
        assert calc._determine_complexity(simple) == CircuitComplexity.SIMPLE

        # Standard
        standard = CircuitAnalysis(component_count=15)
        assert calc._determine_complexity(standard) == CircuitComplexity.STANDARD

        # Complex (multi-rail power)
        complex_circuit = CircuitAnalysis(
            component_count=20,
            power_rails_count=4
        )
        assert calc._determine_complexity(complex_circuit) == CircuitComplexity.COMPLEX

        # High Speed
        high_speed = CircuitAnalysis(
            component_count=15,
            high_speed_signal_ghz=2.0
        )
        assert calc._determine_complexity(high_speed) == CircuitComplexity.HIGH_SPEED

        # Advanced
        advanced = CircuitAnalysis(
            component_count=25,
            high_speed_signal_ghz=6.0,
            differential_pair_count=6
        )
        assert calc._determine_complexity(advanced) == CircuitComplexity.ADVANCED

    def test_circuit_analysis_from_components(self):
        """Test: Circuit analysis extracts info from component list"""
        circuit_data = {
            "components": [
                "USB_C_Connector",
                "ESP32_WROOM",
                "CH340C",
                "LDO_3V3",
                "Crystal_8MHz"
            ],
            "requirements": "USB-C development board with ESP32",
        }

        analysis = self.calculator.analyze_circuit(circuit_data)

        assert analysis.component_count == 5
        assert analysis.estimated_pins == 20  # 5 * 4
        assert analysis.high_speed_io_count >= 4  # USB detected

    def test_layer_recommendation_to_dict(self):
        """Test: LayerRecommendation serializes correctly"""
        analysis = CircuitAnalysis(
            circuit_type="digital",
            complexity=CircuitComplexity.STANDARD,
            component_count=10
        )

        recommendation = LayerRecommendation(
            layer_count=2,
            primary_reason="标准双层板设计",
            reasons=["普通数字电路"],
            confidence=0.9,
            alternatives={4: "增加层数以提高性能"},
            warnings=["高密度设计建议"],
            analysis=analysis
        )

        result = recommendation.to_dict()

        assert result["layer_count"] == 2
        assert result["primary_reason"] == "标准双层板设计"
        assert result["confidence"] == 0.9
        assert "analysis" in result
        assert result["analysis"]["circuit_type"] == "digital"

    def test_get_layer_config(self):
        """Test: Layer config returns correct information"""
        config = self.calculator.get_layer_config(4)

        assert config["name"] == "四层板"
        assert config["cost"] == 3.0
        assert "高速电路" in config["best_for"]

    def test_estimate_cost_factor(self):
        """Test: Cost factor estimation"""
        assert self.calculator.estimate_cost_factor(1) == 0.6
        assert self.calculator.estimate_cost_factor(2) == 1.0
        assert self.calculator.estimate_cost_factor(4) == 2.5
        assert self.calculator.estimate_cost_factor(6) == 4.5
        assert self.calculator.estimate_cost_factor(8) == 7.0

    def test_empty_circuit_data(self):
        """Test: Empty circuit data returns single layer (minimum cost)"""
        circuit_data = {}

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        # Empty circuit defaults to 1 layer (minimum cost for simple/unknown designs)
        assert result.layer_count == 1
        assert result.confidence == 0.9

    def test_frequency_parsing_from_requirements(self):
        """Test: Frequency is correctly parsed from requirements text"""
        circuit_data = {
            "requirements": "high speed interface running at 3.5 GHz",
            "components": ["IC1"],
            "nets": [{"name": "VCC"}, {"name": "GND"}],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.analysis.high_speed_signal_ghz == 3.5
        assert result.layer_count >= 4

    def test_multiple_thresholds_trigger(self):
        """Test: Multiple thresholds can trigger higher layer count"""
        circuit_data = {
            "components": ["CPU", "DDR", "USB", "ETH"],
            "requirements": "embedded system with DDR at 2GHz and USB 3.0",
            "high_speed_signals": [
                {"name": "DDR", "frequency_ghz": 2.0},
                {"name": "USB", "frequency_ghz": 5.0},
            ],
            "nets": [
                {"name": "VCC"},
                {"name": "GND"},
                {"name": "DDR_VDD"},
                {"name": "USB_VBUS"}
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        # Should trigger both high speed and very high speed
        assert result.layer_count >= 6
        assert len(result.reasons) >= 2

    def test_power_rail_detection_from_nets(self):
        """Test: Power rails are detected from net names"""
        circuit_data = {
            "components": ["IC1", "IC2"],
            "nets": [
                {"name": "VCC_3V3"},
                {"name": "VCC_1V8"},
                {"name": "VDDA"},
                {"name": "AGND"},
                {"name": "GND"},
            ],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        # Should detect multiple power-related nets
        assert result.analysis.power_rails_count >= 1

    def test_different_io_count_threshold(self):
        """Test: High IO count (>20) triggers 4 layers"""
        circuit_data = {
            "components": ["FPGA"],
            "requirements": "FPGA with 24 parallel IO for data acquisition",
            "high_speed_signals": [
                {"name": f"IO{i}", "frequency_ghz": 0.1} for i in range(24)
            ],
            "nets": [{"name": "VCC"}, {"name": "GND"}],
        }

        result = self.calculator.calculate_layers_from_dict(circuit_data)

        assert result.layer_count >= 4
        assert any("高速 IO" in r for r in result.reasons)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

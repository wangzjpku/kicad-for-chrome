"""
Tests for Component Recommender
"""
import pytest
import sys
from pathlib import Path

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.component_recommender import (
    ComponentRecommender,
    ComponentRecommendation
)


class TestComponentRecommender:
    """Test cases for ComponentRecommender"""

    def test_recommend_usb_connector(self):
        """Test recommending USB connector"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("USB type-c connector")

        assert len(results) > 0
        # Should find USB connector
        symbols = [r.symbol for r in results]
        assert any("USB" in s for s in symbols)

    def test_recommend_regulator(self):
        """Test recommending voltage regulator"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("5V regulator")

        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("Regulator" in s or "7805" in s for s in symbols)

    def test_recommend_resistor(self):
        """Test recommending resistor"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("10k resistor")

        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("Device:R" in s for s in symbols)

    def test_recommend_capacitor(self):
        """Test recommending capacitor"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("100nF capacitor")

        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("Device:C" in s for s in symbols)

    def test_recommend_led(self):
        """Test recommending LED"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("LED indicator")

        assert len(results) > 0
        symbols = [r.symbol for r in results]
        assert any("LED" in s for s in symbols)

    def test_recommend_microcontroller(self):
        """Test recommending microcontroller"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("ESP32 microcontroller")

        assert len(results) > 0

    def test_recommend_ch340_bridge(self):
        """Test recommending USB to UART bridge"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("USB to UART bridge CH340")

        assert len(results) > 0
        symbols = [r.symbol for r in results]
        # Should find CH340 or similar
        found = any("CH340" in s or "USB" in s for s in symbols)
        assert found

    def test_recommend_by_parameters(self):
        """Test recommending by specific parameters"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_parameters(
            "resistor",
            {"resistance": "4.7k", "tolerance": "1%", "power": "0.25W"}
        )

        assert len(results) > 0
        assert results[0].symbol == "Device:R"
        assert "4.7k" in results[0].description

    def test_recommend_capacitor_by_voltage(self):
        """Test recommending capacitor with voltage rating"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_parameters(
            "capacitor",
            {"capacitance": "10uF", "voltage": "25V"}
        )

        assert len(results) > 0
        assert results[0].symbol == "Device:C"

    def test_recommend_from_requirements(self):
        """Test analyzing requirements and recommending all components"""
        recommender = ComponentRecommender()

        result = recommender.recommend_from_requirements(
            "I need a USB to 3.3V regulator circuit with some LEDs"
        )

        assert isinstance(result, dict)
        # Should have categories
        assert len(result) > 0

    def test_extract_resistance(self):
        """Test extracting resistance value from description"""
        recommender = ComponentRecommender()

        params = recommender._extract_parameters("10kΩ resistor")

        assert "resistance" in params
        assert params["resistance"] == "10k"

    def test_extract_capacitance(self):
        """Test extracting capacitance value from description"""
        recommender = ComponentRecommender()

        params = recommender._extract_parameters("100nF capacitor")

        assert "capacitance" in params
        assert params["capacitance"] == "100n"

    def test_extract_voltage(self):
        """Test extracting voltage from description"""
        recommender = ComponentRecommender()

        params = recommender._extract_parameters("5V power supply")

        assert "voltage" in params
        assert params["voltage"] == "5"

    def test_extract_current(self):
        """Test extracting current from description"""
        recommender = ComponentRecommender()

        params = recommender._extract_parameters("3A current limit")

        assert "current" in params
        assert params["current"] == "3"

    def test_select_resistor_footprint_by_power(self):
        """Test selecting resistor footprint based on power rating"""
        recommender = ComponentRecommender()

        # 0.1W or less -> 0603
        fp = recommender._select_resistor_footprint("0.1W")
        assert "0603" in fp

        # 0.125W -> 0805
        fp = recommender._select_resistor_footprint("0.125W")
        assert "0805" in fp

        # 0.25W -> 1206
        fp = recommender._select_resistor_footprint("0.25W")
        assert "1206" in fp

    def test_recommendation_to_dict(self):
        """Test ComponentRecommendation to_dict conversion"""
        rec = ComponentRecommendation(
            symbol="Device:R",
            footprint="Resistor_SMD:R_0805",
            description="8.5kΩ Resistor",
            parameters={"resistance": "8.5k"},
            score=0.95,
            source="test"
        )

        d = rec.to_dict()

        assert d["symbol"] == "Device:R"
        assert d["footprint"] == "Resistor_SMD:R_0805"
        assert d["score"] == 0.95
        assert d["parameters"]["resistance"] == "8.5k"

    def test_recommend_with_limit(self):
        """Test that recommendation respects limit"""
        recommender = ComponentRecommender()

        results = recommender.recommend_by_function("capacitor resistor led switch", limit=3)

        assert len(results) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

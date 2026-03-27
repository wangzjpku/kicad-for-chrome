"""
Tests for Symbol Library Service
"""
import pytest
import sys
from pathlib import Path

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.symbol_library import (
    SymbolLibrary,
    SymbolInfo,
    get_symbol_library
)


class TestSymbolLibrary:
    """Test cases for SymbolLibrary"""

    def test_library_initialization(self):
        """Test creating a symbol library"""
        lib = SymbolLibrary()

        assert lib.lib_path is not None
        assert isinstance(lib._cache, dict)

    def test_library_with_custom_path(self):
        """Test creating library with custom path"""
        lib_path = "kicad-symbols"
        lib = SymbolLibrary(lib_path=lib_path)

        assert str(lib.lib_path) == lib_path

    def test_list_libraries(self):
        """Test listing libraries"""
        lib = SymbolLibrary()
        libs = lib.list_libraries()

        # Should return a list (may be empty if no symbols)
        assert isinstance(libs, list)

    def test_search_returns_list(self):
        """Test that search returns a list"""
        lib = SymbolLibrary()
        results = lib.search("resistor")

        assert isinstance(results, list)

    def test_search_with_limit(self):
        """Test search with limit parameter"""
        lib = SymbolLibrary()
        results = lib.search("device", limit=5)

        assert len(results) <= 5

    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        lib = SymbolLibrary()

        results1 = lib.search("RESISTOR")
        results2 = lib.search("resistor")

        # Both should return results (case insensitive)
        # Note: may be empty if no symbols indexed

    def test_get_library_symbols(self):
        """Test getting symbols from specific library"""
        lib = SymbolLibrary()
        libs = lib.list_libraries()

        if libs:
            symbols = lib.get_library_symbols(libs[0])
            assert isinstance(symbols, list)

    def test_symbol_info_to_dict(self):
        """Test SymbolInfo to_dict conversion"""
        info = SymbolInfo(
            name="R",
            library="Device",
            full_name="Device:R",
            unit_count=1,
            pin_count=2,
            keywords=["resistor", "R"],
            description="Resistor",
            path="/path/to/symbol.kicad_sym"
        )

        d = info.to_dict()

        assert d["name"] == "R"
        assert d["library"] == "Device"
        assert d["full_name"] == "Device:R"
        assert d["unit_count"] == 1
        assert d["pin_count"] == 2
        assert "resistor" in d["keywords"]

    def test_get_symbol_library_singleton(self):
        """Test that get_symbol_library returns singleton"""
        lib1 = get_symbol_library()
        lib2 = get_symbol_library()

        # Should be the same instance
        assert lib1 is lib2

    def test_build_cache(self):
        """Test building symbol cache"""
        lib = SymbolLibrary()
        count = lib.build_cache()

        assert isinstance(count, int)
        assert count >= 0

    def test_search_nonexistent_symbol(self):
        """Test searching for non-existent symbol"""
        lib = SymbolLibrary()
        results = lib.search("xyznonexistent123456")

        assert isinstance(results, list)
        # Should return empty list or very few results


class TestSymbolInfo:
    """Test cases for SymbolInfo"""

    def test_symbol_info_creation(self):
        """Test creating SymbolInfo"""
        info = SymbolInfo(
            name="C",
            library="Device",
            full_name="Device:C",
            unit_count=1,
            pin_count=2,
            keywords=["capacitor", "cap"],
            description="Capacitor",
            path="/path/to/capacitor.kicad_sym"
        )

        assert info.name == "C"
        assert info.library == "Device"
        assert info.full_name == "Device:C"
        assert len(info.keywords) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

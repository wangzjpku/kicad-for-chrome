"""
Symbol Library Service

Provides access to KiCad symbol libraries with search and metadata retrieval.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set
import re
import json
from pathlib import Path


@dataclass
class SymbolInfo:
    """Information about a KiCad symbol"""
    name: str                 # Symbol name (e.g., "R")
    library: str              # Library name (e.g., "Device")
    full_name: str           # Full name (e.g., "Device:R")
    unit_count: int          # Number of units in symbol
    pin_count: int           # Total number of pins
    keywords: List[str]      # Keywords for searching
    description: str         # Human-readable description
    path: str               # Path to symbol file

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "library": self.library,
            "full_name": self.full_name,
            "unit_count": self.unit_count,
            "pin_count": self.pin_count,
            "keywords": self.keywords,
            "description": self.description,
            "path": self.path
        }


class SymbolLibrary:
    """
    KiCad Symbol Library Search and Access

    Provides:
    - Search symbols by keyword
    - Get symbol metadata
    - List available libraries
    - Cache symbol information
    """

    def __init__(self, lib_path: Optional[str] = None):
        """
        Initialize symbol library

        Args:
            lib_path: Path to KiCad symbols directory
                     Defaults to project kicad-symbols folder
        """
        if lib_path:
            self.lib_path = Path(lib_path)
        else:
            # Default to project symbols directory
            self.lib_path = Path(__file__).parent.parent.parent / "kicad-symbols"

        self._cache: Dict[str, SymbolInfo] = {}
        self._libraries: List[str] = []
        self._indexed = False

    def search(
        self,
        keyword: str,
        limit: int = 20,
        library: Optional[str] = None
    ) -> List[SymbolInfo]:
        """
        Search symbols by keyword

        Args:
            keyword: Search keyword (matches name, library, keywords)
            limit: Maximum number of results
            library: Optional library name to search within

        Returns:
            List of matching SymbolInfo objects
        """
        if not self._indexed:
            self._index_symbols()

        keyword_lower = keyword.lower()
        results = []

        for symbol in self._cache.values():
            # Filter by library if specified
            if library and symbol.library != library:
                continue

            # Match against name, keywords, description
            if (keyword_lower in symbol.name.lower() or
                keyword_lower in symbol.library.lower() or
                any(keyword_lower in kw.lower() for kw in symbol.keywords) or
                keyword_lower in symbol.description.lower()):
                results.append(symbol)

        # Sort by relevance (exact match first)
        results.sort(key=lambda s: (
            keyword_lower == s.name.lower(),
            keyword_lower == s.full_name.lower(),
            keyword_lower in s.keywords,
            s.name.lower().startswith(keyword_lower)
        ), reverse=True)

        return results[:limit]

    def get_symbol(self, library: str, name: str) -> Optional[SymbolInfo]:
        """
        Get a specific symbol by library and name

        Args:
            library: Library name
            name: Symbol name

        Returns:
            SymbolInfo or None if not found
        """
        if not self._indexed:
            self._index_symbols()

        full_name = f"{library}:{name}"
        return self._cache.get(full_name)

    def list_libraries(self) -> List[str]:
        """List all available libraries"""
        if not self._indexed:
            self._index_symbols()
        return sorted(self._libraries)

    def get_library_symbols(self, library: str) -> List[SymbolInfo]:
        """Get all symbols in a library"""
        if not self._indexed:
            self._index_symbols()

        return [s for s in self._cache.values() if s.library == library]

    def _index_symbols(self):
        """Index all symbols in the library"""
        self._cache.clear()
        self._libraries.clear()

        if not self.lib_path.exists():
            return

        # Find sym-lib-table
        lib_table = self.lib_path / "sym-lib-table"
        if not lib_table.exists():
            return

        # Parse library table
        current_library = None

        try:
            content = lib_table.read_text(encoding='utf-8')

            for line in content.split('\n'):
                line = line.strip()

                # Library declaration
                if line.startswith("(lib "):
                    # Extract library name
                    match = re.search(r'\(name\s+"([^"]+)"\)', line)
                    if match:
                        current_library = match.group(1)
                        if current_library not in self._libraries:
                            self._libraries.append(current_library)

                # Symbol entry
                elif line.startswith("(symbol ") and current_library:
                    symbol_info = self._parse_symbol_line(line, current_library)
                    if symbol_info:
                        self._cache[symbol_info.full_name] = symbol_info

        except Exception as e:
            print(f"Warning: Failed to parse sym-lib-table: {e}")

        self._indexed = True

    def _parse_symbol_line(self, line: str, library: str) -> Optional[SymbolInfo]:
        """Parse a symbol entry line from sym-lib-table"""
        try:
            # Extract name
            name_match = re.search(r'\(name\s+"([^"]+)"\)', line)
            if not name_match:
                return None
            name = name_match.group(1)

            # Extract description if present
            desc_match = re.search(r'\(description\s+"([^"]*)"\)', line)
            description = desc_match.group(1) if desc_match else ""

            # Extract keywords if present
            kw_match = re.search(r'\(keywords\s+"([^"]*)"\)', line)
            keywords = kw_match.group(1).split() if kw_match else []

            # Count pins (rough estimate from "pin" occurrences)
            pin_count = line.count("(pin ")

            # Unit count
            unit_match = re.search(r'\(units\s+(\d+)\)', line)
            unit_count = int(unit_match.group(1)) if unit_match else 1

            return SymbolInfo(
                name=name,
                library=library,
                full_name=f"{library}:{name}",
                unit_count=unit_count,
                pin_count=pin_count,
                keywords=keywords,
                description=description,
                path=str(self.lib_path / library / f"{name}.kicad_sym")
            )

        except Exception:
            return None

    def build_cache(self) -> int:
        """
        Force rebuild of symbol cache

        Returns:
            Number of symbols indexed
        """
        self._indexed = False
        self._index_symbols()
        return len(self._cache)


# Global instance for convenience
_global_library: Optional[SymbolLibrary] = None


def get_symbol_library(lib_path: Optional[str] = None) -> SymbolLibrary:
    """
    Get global symbol library instance

    Args:
        lib_path: Optional path to symbols directory

    Returns:
        SymbolLibrary instance
    """
    global _global_library

    if _global_library is None or lib_path is not None:
        _global_library = SymbolLibrary(lib_path)

    return _global_library

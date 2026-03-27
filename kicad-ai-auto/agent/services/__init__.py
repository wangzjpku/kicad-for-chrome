"""
AI Services for kicad-ai-auto

Provides AI-powered services:
- Component recommendation engine
- Symbol library search
- Circuit analysis
"""

from .component_recommender import ComponentRecommender, ComponentRecommendation
from .symbol_library import SymbolLibrary, SymbolInfo

__all__ = [
    "ComponentRecommender",
    "ComponentRecommendation",
    "SymbolLibrary",
    "SymbolInfo"
]

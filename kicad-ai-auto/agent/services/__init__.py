"""
AI Services for kicad-ai-auto

Provides AI-powered services:
- Component recommendation engine
- Symbol library search
- Circuit analysis
- Spatial indexing (Phase 12A)
- Cache service (Phase 12A)
- Auth service (Phase 12B)
- Collaboration service (Phase 12B)
- i18n service (Phase 12C)
"""

from .component_recommender import ComponentRecommender, ComponentRecommendation
from .symbol_library import SymbolLibrary, SymbolInfo
from .lcsc_api import LCSCAPIClient, get_lcsc_client
from .component_alternative import ComponentAlternativeRecommender, get_alternative_recommender
from .bom_optimizer import BOMOptimizer, get_bom_optimizer
from .spatial_index import PCBSpatialIndex, get_spatial_index
from .cache_service import CacheService, get_cache_service
from .auth_service import AuthService, get_auth_service
from .sharing_service import SharingService, get_sharing_service
from .collaboration_service import CollaborationService, get_collaboration_service
from .version_service import VersionService, get_version_service
from .marketplace_service import MarketplaceService, get_marketplace
from .custom_drc_service import CustomDRCService, get_custom_drc_service
from .sdk_generator import SDKGenerator, get_sdk_generator
from .i18n_service import I18nService, get_i18n_service

__all__ = [
    "ComponentRecommender",
    "ComponentRecommendation",
    "SymbolLibrary",
    "SymbolInfo",
    "LCSCAPIClient",
    "get_lcsc_client",
    "ComponentAlternativeRecommender",
    "get_alternative_recommender",
    "BOMOptimizer",
    "get_bom_optimizer",
    "PCBSpatialIndex",
    "get_spatial_index",
    "CacheService",
    "get_cache_service",
    "AuthService",
    "get_auth_service",
    "SharingService",
    "get_sharing_service",
    "CollaborationService",
    "get_collaboration_service",
    "VersionService",
    "get_version_service",
    "MarketplaceService",
    "get_marketplace",
    "CustomDRCService",
    "get_custom_drc_service",
    "SDKGenerator",
    "get_sdk_generator",
    "I18nService",
    "get_i18n_service",
]

"""Cache module."""

from app.core.cache.cache_service import (
    CacheService,
    get_cache_service,
)

__all__ = ["CacheService", "get_cache_service"]

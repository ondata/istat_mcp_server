"""Cache manager providing unified interface to two-layer cache."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .memory import MemoryCache
from .persistent import PersistentCache

logger = logging.getLogger(__name__)


class CacheManager:
    """Unified cache manager with two-layer caching (memory + persistent)."""

    def __init__(
        self,
        memory_cache: MemoryCache,
        persistent_cache: PersistentCache,
    ):
        """Initialize cache manager.

        Args:
            memory_cache: In-memory cache instance
            persistent_cache: Persistent cache instance
        """
        self._memory = memory_cache
        self._persistent = persistent_cache
        logger.info('CacheManager initialized with two-layer cache')

    def get(self, key: str) -> Any | None:
        """Get value from cache (checks memory first, then persistent).

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        # Check memory cache first
        value = self._memory.get(key)
        if value is not None:
            logger.debug(f'[Memory cache hit] {key}')
            return value

        # Check persistent cache
        value = self._persistent.get(key)
        if value is not None:
            # Populate memory cache
            self._memory.set(key, value)
            logger.debug(f'[Persistent cache hit] {key} (populating memory cache)')
            return value

        return None

    def set(
        self,
        key: str,
        value: Any,
        persistent_ttl: int | None = None,
    ) -> None:
        """Set value in both cache layers.

        Args:
            key: Cache key
            value: Value to cache
            persistent_ttl: TTL for persistent cache (None = no expiration)
        """
        # Store in both layers
        self._memory.set(key, value)
        self._persistent.set(key, value, ttl=persistent_ttl)
        logger.debug(f'[Set in both layers] {key} (TTL={persistent_ttl}s)')

    def delete(self, key: str) -> None:
        """Delete value from both cache layers.

        Args:
            key: Cache key
        """
        self._memory.delete(key)
        self._persistent.delete(key)
        logger.debug(f'CacheManager: Deleted from both layers for {key}')

    def clear(self) -> None:
        """Clear both cache layers."""
        self._memory.clear()
        self._persistent.clear()
        logger.info('CacheManager: Cleared both layers')

    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        persistent_ttl: int | None = None,
    ) -> Any:
        """Get from cache or fetch and cache the result.

        Args:
            key: Cache key
            fetch_func: Async function to fetch data if not cached
            persistent_ttl: TTL for persistent cache

        Returns:
            Cached or fetched value
        """
        # Try to get from cache
        value = self.get(key)
        if value is not None:
            logger.info(f'Cache HIT for {key}')
            return value

        # Cache miss - fetch from source
        logger.info(f'Cache MISS for {key} - Calling API...')
        value = await fetch_func()

        # Store in both layers
        self.set(key, value, persistent_ttl=persistent_ttl)
        logger.info(f'Cached {key} (TTL={persistent_ttl}s)')

        return value

    def close(self) -> None:
        """Close persistent cache connection."""
        self._persistent.close()
        logger.info('CacheManager: Closed')

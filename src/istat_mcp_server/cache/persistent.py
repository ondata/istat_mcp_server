"""Persistent cache implementation using diskcache."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from diskcache import Cache
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PersistentCache:
    """Persistent disk-based cache using diskcache."""

    def __init__(self, cache_dir: str = './cache'):
        """Initialize persistent cache.

        Args:
            cache_dir: Directory for cache files
        """
        self._cache_dir = Path(cache_dir)

        # Try to create the cache directory
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            # Test if we can write to the directory
            test_file = self._cache_dir / '.test_write'
            test_file.touch()
            test_file.unlink()
            logger.info(f'PersistentCache initialized at {self._cache_dir}')
        except (PermissionError, OSError) as e:
            # Fallback to temp directory
            logger.warning(
                f'Cannot create cache directory at {self._cache_dir}: {e}. '
                f'Using temp directory instead.'
            )
            self._cache_dir = Path(tempfile.gettempdir()) / 'istat_mcp_cache'
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f'PersistentCache using fallback directory: {self._cache_dir}')

        self._cache = Cache(str(self._cache_dir))

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        value = self._cache.get(key)
        if value is not None:
            logger.debug(f'PersistentCache HIT: {key}')
            # Deserialize if it's JSON-serialized data
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
        else:
            logger.debug(f'PersistentCache MISS: {key}')
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = no expiration)
        """
        # Serialize Pydantic models and lists
        if isinstance(value, BaseModel):
            value = json.dumps(value.model_dump())
            logger.debug('PersistentCache: Serialized BaseModel to JSON')
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], BaseModel):
            value = json.dumps([item.model_dump() for item in value])
            logger.debug(f'PersistentCache: Serialized list of {len(value)} BaseModel to JSON')

        if ttl is not None:
            self._cache.set(key, value, expire=ttl)
        else:
            self._cache.set(key, value)
        logger.debug(f'PersistentCache SET: {key} (TTL={ttl})')

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f'PersistentCache DELETE: {key}')

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.info('PersistentCache cleared')

    def close(self) -> None:
        """Close cache connection."""
        self._cache.close()
        logger.info('PersistentCache closed')

    def __len__(self) -> int:
        """Return number of items in cache."""
        return len(self._cache)

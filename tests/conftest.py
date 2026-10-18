"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from istat_mcp_server.api.client import ApiClient
from istat_mcp_server.cache.manager import CacheManager
from istat_mcp_server.cache.memory import MemoryCache
from istat_mcp_server.cache.persistent import PersistentCache


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    mock = AsyncMock(spec=ApiClient)
    return mock


@pytest.fixture
def memory_cache():
    """Create a memory cache instance for testing."""
    return MemoryCache(ttl=60, max_size=100)


@pytest.fixture
def persistent_cache(tmp_path):
    """Create a persistent cache instance for testing."""
    cache = PersistentCache(cache_dir=str(tmp_path / 'test_cache'))
    yield cache
    cache.close()


@pytest.fixture
def cache_manager(memory_cache, persistent_cache):
    """Create a cache manager for testing."""
    return CacheManager(memory_cache, persistent_cache)


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager for testing."""
    mock = MagicMock(spec=CacheManager)
    mock.get_or_fetch = AsyncMock()
    return mock

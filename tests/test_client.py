"""Tests for API client error handling."""

import pytest
import httpx

from istat_mcp_server.api.client import ApiClient, ApiError, RateLimiter


def _make_api_client(dummy_http_client):
    """Create a minimal ApiClient instance for testing, bypassing __init__."""
    client = ApiClient.__new__(ApiClient)
    client._base_url = "https://example.com"
    client._timeout = 30.0
    client._rate_limiter = RateLimiter(max_calls=100, time_window=1.0)
    client._client = dummy_http_client
    return client


@pytest.mark.asyncio
async def test_404_no_records_found_returns_helpful_message():
    """HTTP 404 with 'NoRecordsFound' body should raise ApiError with helpful message."""

    class DummyClientNoRecords:
        async def get(self, *args, **kwargs):
            response = httpx.Response(status_code=404, content=b"NoRecordsFound")
            request = httpx.Request("GET", "https://example.com/test")
            raise httpx.HTTPStatusError(
                "Not Found",
                request=request,
                response=response,
            )

    client = _make_api_client(DummyClientNoRecords())

    with pytest.raises(ApiError) as exc_info:
        await client._get("/test")

    assert exc_info.value.status_code == 404
    # The helper logic should transform "NoRecordsFound" into a more helpful message.
    assert "No data found" in str(exc_info.value)
    assert "filters/period" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generic_404_preserves_original_message():
    """HTTP 404 without 'NoRecordsFound' should raise generic HTTP error."""

    class DummyClientGeneric404:
        async def get(self, *args, **kwargs):
            response = httpx.Response(status_code=404, content=b"Some other 404 error")
            request = httpx.Request("GET", "https://example.com/test")
            raise httpx.HTTPStatusError(
                "HTTP error: 404",
                request=request,
                response=response,
            )

    client = _make_api_client(DummyClientGeneric404())

    with pytest.raises(ApiError) as exc_info:
        await client._get("/test")

    assert exc_info.value.status_code == 404
    # For a generic 404 body, the original HTTP error message should be preserved.
    assert "HTTP error: 404" in str(exc_info.value)

"""Tests for API client error handling."""

import pytest

from istat_mcp_server.api.client import ApiError


@pytest.mark.asyncio
async def test_404_no_records_found_returns_helpful_message():
    """HTTP 404 with 'NoRecordsFound' body should raise ApiError with helpful message."""
    with pytest.raises(ApiError) as exc_info:
        raise ApiError(
            'No data found for the requested filters/period. '
            'Try using a different time period or broader filters. '
            'Note: get_constraints may report a wider EndPeriod than what is actually available at municipal level.',
            404,
        )

    assert exc_info.value.status_code == 404
    assert 'No data found' in str(exc_info.value)
    assert 'filters/period' in str(exc_info.value)


@pytest.mark.asyncio
async def test_generic_404_preserves_original_message():
    """HTTP 404 without 'NoRecordsFound' should raise generic HTTP error."""
    with pytest.raises(ApiError) as exc_info:
        raise ApiError('HTTP error: 404', 404)

    assert exc_info.value.status_code == 404
    assert 'HTTP error: 404' in str(exc_info.value)

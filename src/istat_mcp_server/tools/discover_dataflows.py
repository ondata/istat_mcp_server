"""Tool: discover_dataflows - Discover available dataflows from ISTAT SDMX API."""

import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import DiscoverDataflowsInput
from ..cache.manager import CacheManager
from ..utils.blacklist import DataflowBlacklist
from ..utils.tool_helpers import (
    format_json_response,
    get_cached_dataflows,
    handle_tool_errors,
)
from ..utils.validators import validate_keywords

logger = logging.getLogger(__name__)

@handle_tool_errors
async def handle_discover_dataflows(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
    blacklist: DataflowBlacklist,
) -> list[TextContent]:
    """Handle discover_dataflows tool.

    Args:
        arguments: Raw arguments dict from MCP
        cache: Cache manager instance
        api: API client instance
        blacklist: Dataflow blacklist instance

    Returns:
        List of TextContent with JSON-formatted response or error message
    """
    # Validate input
    params = DiscoverDataflowsInput.model_validate(arguments)
    keywords = validate_keywords(params.keywords)

    logger.info(f'discover_dataflows: keywords={keywords}')

    dataflows = await get_cached_dataflows(cache, api)

    # Apply blacklist filter
    dataflows = blacklist.filter_dataflows(dataflows)

    # Filter by keywords if provided
    if keywords:
        dataflows = [
            df for df in dataflows
            if any(kw in ' '.join([
                df.id, df.name_it, df.name_en,
                df.description_it, df.description_en, df.id_datastructure
            ]).lower() for kw in keywords)
        ]
        logger.info(f'Filtered to {len(dataflows)} dataflows')

    # Format response
    response = {
        'count': len(dataflows),
        'dataflows': [df.model_dump() for df in dataflows],
    }

    return format_json_response(response)

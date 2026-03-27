"""Tool: discover_dataflows - Discover available dataflows from ISTAT SDMX API."""

import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import DiscoverDataflowsInput
from ..cache.manager import CacheManager
from ..utils.validators import validate_keywords
from ..utils.blacklist import DataflowBlacklist
from ..utils.tool_helpers import (
    format_toon_dataflows,
    get_cached_dataflows,
    handle_tool_errors,
)

logger = logging.getLogger(__name__)


@handle_tool_errors
async def handle_discover_dataflows(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
    blacklist: DataflowBlacklist,
) -> list[TextContent]:
    """Handle discover_dataflows tool."""
    params = DiscoverDataflowsInput.model_validate(arguments)
    keywords = validate_keywords(params.keywords)

    logger.info(f'discover_dataflows: keywords={keywords}')

    dataflows = await get_cached_dataflows(cache, api)
    dataflows = blacklist.filter_dataflows(dataflows)

    if keywords:
        dataflows = [
            df for df in dataflows
            if any(kw in ' '.join([
                df.id, df.name_it, df.name_en,
                df.description_it, df.description_en, df.id_datastructure
            ]).lower() for kw in keywords)
        ]
        logger.info(f'Filtered to {len(dataflows)} dataflows')

    return format_toon_dataflows(dataflows)

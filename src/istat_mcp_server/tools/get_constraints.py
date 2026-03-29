"""Tool: get_constraints - Get available constraints with descriptions for a dataflow."""

import logging
from typing import Any  # noqa: F401

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import (
    CompactConstraintsOutput,
    CompactDimensionConstraint,
    GetConstraintsInput,
    TimeConstraintOutput,
    TimeConstraintValue,
)
from ..cache.manager import CacheManager
from ..utils.validators import validate_dataflow_id
from ..utils.tool_helpers import (
    find_dataflow_info,
    format_json_response,
    get_cached_codelist,
    get_cached_constraints,
    get_cached_dataflows,
    get_cached_datastructure,
    handle_tool_errors,
)

logger = logging.getLogger(__name__)

@handle_tool_errors
async def handle_get_constraints(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
) -> list[TextContent]:
    """Handle get_constraints tool.

    This tool combines data from multiple sources to provide complete constraint
    information with descriptions:

    Workflow:
    1. Fetch dataflow info to get datastructure ID
    2. Fetch constraints (availableconstraint endpoint) - valid values per dimension
    3. Fetch datastructure (get_structure) - dimension to codelist mapping
    4. For each dimension, fetch codelist (get_codelist_description) - descriptions

    All data is cached for 1 month. After first call, no API calls are needed.

    Args:
        arguments: Raw arguments dict from MCP
        cache: Cache manager instance
        api: API client instance

    Returns:
        List of TextContent with JSON-formatted constraints and descriptions
    """
    # Validate input
    params = GetConstraintsInput.model_validate(arguments)
    dataflow_id = params.dataflow_id

    if not validate_dataflow_id(dataflow_id):
        return [
            TextContent(
                type='text', text=f'Invalid dataflow ID: {dataflow_id}'
            )
        ]

    logger.info(f'get_constraints: dataflow_id={dataflow_id}')

    # Step 1: Get dataflow info to find the datastructure ID
    dataflows = await get_cached_dataflows(cache, api)
    dataflow_info = find_dataflow_info(dataflows, dataflow_id)

    if not dataflow_info:
        return [
            TextContent(
                type='text', text=f'Dataflow not found: {dataflow_id}'
            )
        ]

    id_datastructure = dataflow_info.id_datastructure
    logger.info(f'Found datastructure: {id_datastructure}')

    # Step 2: Fetch constraints (available values for each dimension)
    # This returns only the values that are actually available for this dataflow
    logger.info(f'Getting constraints (checks cache first, then API if needed)')
    constraints = await get_cached_constraints(cache, api, dataflow_id)

    # Step 3: Call get_structure internally to get dimension-codelist mapping
    # This is equivalent to calling the get_structure tool
    logger.info(f'Getting datastructure (checks cache first, then API if needed)')
    datastructure = await get_cached_datastructure(
        cache,
        api,
        id_datastructure,
    )

    # Build dimension -> codelist mapping from datastructure
    dim_to_codelist = {
        dim.dimension: dim.codelist for dim in datastructure.dimensions
    }
    logger.info(f'Mapped {len(dim_to_codelist)} dimensions to codelists')

    # Step 4: Build compact output and pre-cache codelists
    compact_dimensions: list[CompactDimensionConstraint | TimeConstraintOutput] = []

    for constraint_dim in constraints.dimensions:
        dimension_id = constraint_dim.dimension

        # Check if this is TIME_PERIOD
        if (
            constraint_dim.values
            and isinstance(constraint_dim.values[0], TimeConstraintValue)
        ):
            time_val = constraint_dim.values[0]
            compact_dimensions.append(
                TimeConstraintOutput(
                    dimension='TIME_PERIOD',
                    StartPeriod=time_val.StartPeriod,
                    EndPeriod=time_val.EndPeriod,
                )
            )
        else:
            # Regular dimension — pre-cache codelist for search_constraint_values
            codelist_id = dim_to_codelist.get(dimension_id, '')
            value_count = len(constraint_dim.values)

            if codelist_id:
                try:
                    logger.info(
                        f'Pre-caching codelist {codelist_id} for dimension {dimension_id}'
                    )
                    await get_cached_codelist(cache, api, codelist_id)
                except Exception as e:
                    logger.warning(
                        f'Failed to pre-cache codelist {codelist_id}: {e}'
                    )

            compact_dimensions.append(
                CompactDimensionConstraint(
                    dimension=dimension_id,
                    codelist=codelist_id,
                    value_count=value_count,
                )
            )

    # All data is now cached (constraints, datastructure, codelists)
    # Use search_constraint_values to find specific codes
    logger.info(
        f'Successfully built compact constraints for {dataflow_id} '
        f'with {len(compact_dimensions)} dimensions (all cached for 1 month)'
    )

    output = CompactConstraintsOutput(
        id_dataflow=dataflow_id, dimensions=compact_dimensions
    )

    return format_json_response(output)
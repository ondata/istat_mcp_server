"""Tool: search_constraint_values - Search for specific values within a dimension."""

import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import (
    CodeValue,
    SearchConstraintValuesInput,
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
async def handle_search_constraint_values(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
) -> list[TextContent]:
    """Search for values within a specific dimension of a dataflow.

    Uses cached data from get_constraints when available.
    """
    params = SearchConstraintValuesInput.model_validate(arguments)
    dataflow_id = params.dataflow_id
    dimension = params.dimension
    search = params.search.strip().lower()

    if not validate_dataflow_id(dataflow_id):
        return [TextContent(type='text', text=f'Invalid dataflow ID: {dataflow_id}')]

    logger.info(
        f'search_constraint_values: dataflow={dataflow_id}, '
        f'dimension={dimension}, search="{search}"'
    )

    # Step 1: Get dataflow info
    dataflows = await get_cached_dataflows(cache, api)
    dataflow_info = find_dataflow_info(dataflows, dataflow_id)
    if not dataflow_info:
        return [TextContent(type='text', text=f'Dataflow not found: {dataflow_id}')]

    # Step 2: Get constraints (should be cached from get_constraints call)
    constraints = await get_cached_constraints(cache, api, dataflow_id)

    # Find the requested dimension
    target_dim = None
    for constraint_dim in constraints.dimensions:
        if constraint_dim.dimension == dimension:
            target_dim = constraint_dim
            break

    if target_dim is None:
        available = [d.dimension for d in constraints.dimensions]
        return [
            TextContent(
                type='text',
                text=f'Dimension "{dimension}" not found. Available: {", ".join(available)}',
            )
        ]

    # Handle TIME_PERIOD
    if target_dim.values and isinstance(target_dim.values[0], TimeConstraintValue):
        time_val = target_dim.values[0]
        return format_json_response({
            'dimension': 'TIME_PERIOD',
            'type': 'range',
            'StartPeriod': time_val.StartPeriod,
            'EndPeriod': time_val.EndPeriod,
        })

    # Step 3: Get codelist descriptions
    id_datastructure = dataflow_info.id_datastructure
    datastructure = await get_cached_datastructure(cache, api, id_datastructure)
    dim_to_codelist = {dim.dimension: dim.codelist for dim in datastructure.dimensions}
    codelist_id = dim_to_codelist.get(dimension, '')

    # Build valid codes set from constraints
    valid_codes = {v.value for v in target_dim.values}

    # Get descriptions from codelist
    matching_values: list[CodeValue] = []

    if codelist_id:
        try:
            codelist = await get_cached_codelist(cache, api, codelist_id)
            code_to_desc = {cv.code: cv for cv in codelist.values}

            for code in valid_codes:
                cv = code_to_desc.get(code)
                if cv is None:
                    cv = CodeValue(code=code)

                # Apply search filter
                if search:
                    text = f'{cv.code} {cv.description_it} {cv.description_en}'.lower()
                    if search not in text:
                        continue

                matching_values.append(cv)
        except Exception as e:
            logger.warning(f'Failed to fetch codelist {codelist_id}: {e}')
            # Fallback: return codes without descriptions
            for code in valid_codes:
                if not search or search in code.lower():
                    matching_values.append(CodeValue(code=code))
    else:
        for code in valid_codes:
            if not search or search in code.lower():
                matching_values.append(CodeValue(code=code))

    # Sort by code
    matching_values.sort(key=lambda v: v.code)

    result = {
        'dimension': dimension,
        'codelist': codelist_id,
        'search': search or None,
        'total_values': len(valid_codes),
        'matched_values': len(matching_values),
        'values': [v.model_dump() for v in matching_values],
    }

    return format_json_response(result)

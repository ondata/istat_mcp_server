"""Tool: search_constraint_values - Search dimension values for a dataflow."""

import json
import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import (
    CodeValue,
    ConstraintValue,
    SearchConstraintValuesInput,
    TimeConstraintValue,
)
from ..cache.manager import CacheManager
from ..utils.validators import validate_dataflow_id
from ..utils.tool_helpers import (
    find_dataflow_info,
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
    """Handle search_constraint_values tool.

    Reads dimension values from cache (populated by get_constraints).
    If cache is empty, fetches from API automatically.

    Args:
        arguments: Raw arguments dict from MCP
        cache: Cache manager instance
        api: API client instance

    Returns:
        List of TextContent with JSON array of matching {code, description_it, description_en}
    """
    params = SearchConstraintValuesInput.model_validate(arguments)
    dataflow_id = params.dataflow_id
    dimension = params.dimension
    search = params.search

    if not validate_dataflow_id(dataflow_id):
        return [TextContent(type='text', text=f'Invalid dataflow ID: {dataflow_id}')]

    logger.info(
        f'search_constraint_values: dataflow_id={dataflow_id}, '
        f'dimension={dimension}, search={search!r}'
    )

    # Step 1: Get dataflow info to find the datastructure ID
    dataflows = await get_cached_dataflows(cache, api)
    dataflow_info = find_dataflow_info(dataflows, dataflow_id)
    if not dataflow_info:
        return [TextContent(type='text', text=f'Dataflow not found: {dataflow_id}')]

    # Step 2: Get constraints to know which values are valid for this dimension
    constraints = await get_cached_constraints(cache, api, dataflow_id)

    dim_constraint = next(
        (d for d in constraints.dimensions if d.dimension == dimension), None
    )
    if dim_constraint is None:
        available = [d.dimension for d in constraints.dimensions]
        return [TextContent(
            type='text',
            text=f'Dimension "{dimension}" not found. Available dimensions: {available}',
        )]

    # Handle TIME_PERIOD dimension
    if dim_constraint.values and isinstance(dim_constraint.values[0], TimeConstraintValue):
        tv = dim_constraint.values[0]
        return [TextContent(
            type='text',
            text=f'TIME_PERIOD: StartPeriod={tv.StartPeriod}, EndPeriod={tv.EndPeriod}',
        )]

    # Step 3: Get dimension → codelist mapping from datastructure
    datastructure = await get_cached_datastructure(cache, api, dataflow_info.id_datastructure)
    dim_to_codelist = {d.dimension: d.codelist for d in datastructure.dimensions}
    codelist_id = dim_to_codelist.get(dimension, '')

    # Step 4: Get codelist descriptions, filtered to valid constraint values
    # dim_constraint.values can be ConstraintValue | TimeConstraintValue; TIME_PERIOD already handled above
    regular_values = [v for v in dim_constraint.values if isinstance(v, ConstraintValue)]
    valid_codes = {v.value for v in regular_values}
    code_values: list[CodeValue] = []

    if codelist_id:
        try:
            codelist = await get_cached_codelist(cache, api, codelist_id)
            code_values = [cv for cv in codelist.values if cv.code in valid_codes]
        except Exception as e:
            logger.warning(f'Could not fetch codelist {codelist_id}: {e}')
            code_values = [
                CodeValue(code=v.value, description_en='', description_it='')
                for v in regular_values
            ]
    else:
        code_values = [
            CodeValue(code=v.value, description_en='', description_it='')
            for v in regular_values
        ]

    # Step 5: Apply optional search filter (substring on code or descriptions)
    if search:
        search_lower = search.lower()
        code_values = [
            cv for cv in code_values
            if search_lower in cv.code.lower()
            or search_lower in cv.description_it.lower()
            or search_lower in cv.description_en.lower()
        ]

    result = [cv.model_dump() for cv in code_values]
    return [TextContent(type='text', text=json.dumps(result, ensure_ascii=False, indent=2))]

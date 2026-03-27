"""Tool: check_code_exists - Check if dimension codes exist in a dataflow."""

import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import ConstraintValue, TimeConstraintValue
from ..cache.manager import CacheManager
from ..utils.tool_helpers import (
    format_json_response,
    get_cached_constraints,
    get_cached_dataflows,
    find_dataflow_info,
    handle_tool_errors,
)

logger = logging.getLogger(__name__)


@handle_tool_errors
async def handle_check_code_exists(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
) -> list[TextContent]:
    """Check if codes exist for a given dimension in a dataflow.

    Uses get_constraints (cached) to verify existence without downloading data.
    First call fetches constraints from API (~10-60s); subsequent calls use cache (instant).

    Args:
        arguments:
            'dataflow_id': Dataflow ID to check
            'dimension': Dimension ID to check (e.g., 'REF_AREA', 'AGE', 'SEX')
            'codes': List of codes to verify (e.g., ['082053', 'ITG12'])

    Returns:
        JSON: {dataflow_id, dimension, results: [{code, exists}]}
    """
    dataflow_id = arguments.get('dataflow_id', '').strip()
    dimension = arguments.get('dimension', '').strip().upper()
    codes = arguments.get('codes', [])

    if not dataflow_id:
        return format_json_response({'error': "Missing 'dataflow_id'"})
    if not dimension:
        return format_json_response({'error': "Missing 'dimension'"})
    if not codes:
        return format_json_response({'error': "Missing 'codes'"})

    if dimension == 'TIME_PERIOD':
        return format_json_response({
            'error': (
                "TIME_PERIOD is a range dimension and cannot be checked with this tool. "
                "Use get_constraints to retrieve the available StartPeriod/EndPeriod range."
            )
        })

    if isinstance(codes, str):
        codes = [c.strip() for c in codes.split(',')]

    # Verify dataflow exists
    dataflows = await get_cached_dataflows(cache, api)
    dataflow_info = find_dataflow_info(dataflows, dataflow_id)
    if not dataflow_info:
        return format_json_response({'error': f'Dataflow not found: {dataflow_id}'})

    # Get constraints (cached after first call)
    constraints = await get_cached_constraints(cache, api, dataflow_id)

    dim_constraint = next(
        (d for d in constraints.dimensions if d.dimension == dimension), None
    )
    if dim_constraint is None:
        available = [d.dimension for d in constraints.dimensions]
        return format_json_response({
            'error': f"Dimension '{dimension}' not found in this dataflow",
            'available_dimensions': available,
        })

    # Build set of valid codes for this dimension (ConstraintValue only;
    # TimeConstraintValue entries are range-based and handled above)
    valid_codes = {
        v.value for v in dim_constraint.values if isinstance(v, ConstraintValue)
    }

    results = [{'code': code, 'exists': code in valid_codes} for code in codes]

    return format_json_response({
        'dataflow_id': dataflow_id,
        'dimension': dimension,
        'results': results,
    })

"""Tool: get_constraints - Get available constraints with descriptions for a dataflow."""

import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import (
    CodeValue,
    ConstraintInfo,
    ConstraintValue,
    ConstraintsSummaryOutput,
    DimensionConstraint,
    DimensionConstraintSummary,
    DimensionConstraintWithDescriptions,
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
    get_cached_constraints_keyed,
    get_cached_dataflows,
    get_cached_datastructure,
    handle_tool_errors,
)

logger = logging.getLogger(__name__)

def _code_values_without_descriptions(
    constraint_values: list[Any],
) -> list[CodeValue]:
    """Build CodeValue entries when codelist descriptions are unavailable."""
    return [
        CodeValue(code=value.value, description_en='', description_it='')
        for value in constraint_values
    ]


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
    dimensions_filter = {d.upper() for d in params.dimensions} if params.dimensions else None

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

    # Step 2: Fetch datastructure to get dimension-codelist mapping
    logger.info(f'Getting datastructure (checks cache first, then API if needed)')
    datastructure = await get_cached_datastructure(cache, api, id_datastructure)

    dim_to_codelist = {
        dim.dimension: dim.codelist for dim in datastructure.dimensions
    }
    logger.info(f'Mapped {len(dim_to_codelist)} dimensions to codelists')

    # Step 3: Choose strategy.
    #
    # - dimensions specified → key filtering: fix safe defaults for non-requested
    #   dims and call availableconstraint with a partial key (~2s).
    #   Fallback to codelists if key filtering returns nothing (safe defaults
    #   not valid for this dataflow).
    #
    # - no dimensions filter → cardinality check: fetch all codelists, compute
    #   the product of their sizes. If > threshold use codelists directly
    #   (avoids the 300s+ availableconstraint timeout on large dataflows).

    _SAFE_DEFAULTS = {'FREQ': 'A', 'REF_AREA': 'IT', 'SEX': '9'}
    _COMPLEXITY_THRESHOLD = 1_000_000

    if dimensions_filter:
        # Key filtering path
        key_parts = [
            _SAFE_DEFAULTS.get(dim.dimension, '')
            if dim.dimension not in dimensions_filter
            else ''
            for dim in datastructure.dimensions
        ]
        key = '.'.join(key_parts)
        logger.info(f'Key filtering: key={key!r}, requested={dimensions_filter}')
        constraints = await get_cached_constraints_keyed(cache, api, dataflow_id, key)

        if not constraints.dimensions:
            # Safe defaults not valid for this dataflow — fall back to codelists
            logger.warning(
                f'Key filtering returned empty for {dataflow_id}, falling back to codelists'
            )
            for dim in datastructure.dimensions:
                if dim.codelist and dim.dimension in dimensions_filter:
                    await get_cached_codelist(cache, api, dim.codelist)
            # Build constraints from codelists for requested dimensions only
            dim_constraints_fb: list[DimensionConstraint] = []
            for dim in datastructure.dimensions:
                if not dim.codelist or dim.dimension not in dimensions_filter:
                    continue
                cl = await get_cached_codelist(cache, api, dim.codelist)
                vals_fb: list[ConstraintValue | TimeConstraintValue] = [
                    ConstraintValue(value=cv.code) for cv in cl.values
                ]
                dim_constraints_fb.append(
                    DimensionConstraint(dimension=dim.dimension, values=vals_fb)
                )
            constraints = ConstraintInfo(id=dataflow_id, dimensions=dim_constraints_fb)
    else:
        # Cardinality check path
        cardinality = 1
        codelists_by_id: dict[str, Any] = {}
        for dim in datastructure.dimensions:
            if dim.codelist:
                cl = await get_cached_codelist(cache, api, dim.codelist)
                codelists_by_id[dim.codelist] = cl
                cardinality *= len(cl.values)

        logger.info(f'Theoretical cardinality for {dataflow_id}: {cardinality:,}')

        if cardinality > _COMPLEXITY_THRESHOLD:
            logger.info(
                f'Cardinality {cardinality:,} > {_COMPLEXITY_THRESHOLD:,}: using codelist path'
            )
            dim_constraints_cl: list[DimensionConstraint] = []
            for dim in datastructure.dimensions:
                if not dim.codelist or dim.codelist not in codelists_by_id:
                    continue
                vals_cl: list[ConstraintValue | TimeConstraintValue] = [
                    ConstraintValue(value=cv.code)
                    for cv in codelists_by_id[dim.codelist].values
                ]
                dim_constraints_cl.append(
                    DimensionConstraint(dimension=dim.dimension, values=vals_cl)
                )
            constraints = ConstraintInfo(id=dataflow_id, dimensions=dim_constraints_cl)
        else:
            logger.info(
                f'Cardinality {cardinality:,} <= {_COMPLEXITY_THRESHOLD:,}: using availableconstraint'
            )
            constraints = await get_cached_constraints(cache, api, dataflow_id)

    # Step 4: Build output with descriptions
    output_constraints: list[
        DimensionConstraintWithDescriptions | TimeConstraintOutput
    ] = []

    for constraint_dim in constraints.dimensions:
        dimension_id = constraint_dim.dimension

        # Skip dimensions not in the filter (if a filter was specified)
        if dimensions_filter and dimension_id not in dimensions_filter:
            continue

        # Check if this is TIME_PERIOD
        if (
            constraint_dim.values
            and isinstance(constraint_dim.values[0], TimeConstraintValue)
        ):
            time_val = constraint_dim.values[0]
            output_constraints.append(
                TimeConstraintOutput(
                    dimension='TIME_PERIOD',
                    StartPeriod=time_val.StartPeriod,
                    EndPeriod=time_val.EndPeriod,
                )
            )
        else:
            # Regular dimension with values
            codelist_id = dim_to_codelist.get(dimension_id, '')

            # Step 4: Call get_codelist_description internally to get value descriptions
            # This is equivalent to calling the get_codelist_description tool for each codelist
            code_values: list[CodeValue] = []

            if codelist_id:
                try:
                    logger.info(
                        f'Getting codelist {codelist_id} for dimension {dimension_id} '
                        f'(checks cache first, then API if needed)'
                    )
                    codelist = await get_cached_codelist(
                        cache,
                        api,
                        codelist_id,
                    )

                    # Build code -> description mapping
                    code_to_desc = {cv.code: cv for cv in codelist.values}

                    # Match constraint values with descriptions
                    for constraint_val in constraint_dim.values:
                        code = constraint_val.value
                        if code in code_to_desc:
                            code_values.append(code_to_desc[code])
                        else:
                            code_values.extend(
                                _code_values_without_descriptions(
                                    [constraint_val]
                                )
                            )
                except Exception as e:
                    logger.warning(
                        f'Failed to fetch codelist {codelist_id}: {e}'
                    )
                    code_values = _code_values_without_descriptions(
                        constraint_dim.values
                    )
            else:
                code_values = _code_values_without_descriptions(
                    constraint_dim.values
                )

            output_constraints.append(
                DimensionConstraintWithDescriptions(
                    dimension=dimension_id,
                    codelist=codelist_id,
                    values=code_values,
                )
            )

    # All data is now cached (constraints, datastructure, codelists)
    # Subsequent calls will not need to fetch from API
    logger.info(
        f'Successfully built constraints output for {dataflow_id} '
        f'with {len(output_constraints)} dimensions (all cached for 1 month)'
    )

    # Build compact summary — full values stay in cache, queryable via search_constraint_values
    summary_dims = []
    for dim in output_constraints:
        if isinstance(dim, TimeConstraintOutput):
            summary_dims.append(dim)
        else:
            summary_dims.append(
                DimensionConstraintSummary(
                    dimension=dim.dimension,
                    codelist=dim.codelist,
                    value_count=len(dim.values),
                )
            )

    output = ConstraintsSummaryOutput(
        id_dataflow=dataflow_id, dimensions=summary_dims
    )

    return format_json_response(output)
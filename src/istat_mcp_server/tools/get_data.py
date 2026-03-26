"""Tool: get_data - Fetch actual data from a dataflow."""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from lxml import etree
from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import GetDataInput
from ..cache.manager import CacheManager
from ..utils.validators import validate_dataflow_id
from ..utils.blacklist import DataflowBlacklist
from ..utils.tool_helpers import (
    find_dataflow_info,
    get_cached_dataflows,
    get_observed_data_cache_ttl,
    handle_tool_errors,
)
from .get_constraints import handle_get_constraints

logger = logging.getLogger(__name__)

# SDMX XML namespaces
NAMESPACES = {
    'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
    'generic': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic',
    'common': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
}


def parse_sdmx_to_table(xml_content: str, dataflow_full_id: str) -> str:
    """Parse SDMX XML and convert to TSV table format.
    
    Args:
        xml_content: Raw SDMX XML content
        dataflow_full_id: Full dataflow ID (e.g., 'IT1:149_577_DF_DCSC_OROS_1_1(1.0)')
        
    Returns:
        TSV formatted table as string
    """
    root = etree.fromstring(xml_content.encode('utf-8'))
    
    # Extract all series
    series_list = root.xpath('//generic:Series', namespaces=NAMESPACES)
    
    if not series_list:
        return "DATAFLOW\tERROR\nNo data found in response"
    
    rows = []
    header = ['DATAFLOW']
    header_set = False
    
    for series in series_list:
        # Extract series-level dimensions
        series_dims = {}
        for series_key in series.xpath('.//generic:SeriesKey/generic:Value', namespaces=NAMESPACES):
            dim_id = series_key.get('id', '')
            dim_value = series_key.get('value', '')
            series_dims[dim_id] = dim_value
        
        # Extract observations
        for obs in series.xpath('.//generic:Obs', namespaces=NAMESPACES):
            row_data = {'DATAFLOW': dataflow_full_id}
            
            # Add series dimensions
            row_data.update(series_dims)
            
            # Extract observation-level dimensions and attributes
            for obs_dim in obs.xpath('.//generic:ObsDimension', namespaces=NAMESPACES):
                dim_id = obs_dim.get('id', '')
                dim_value = obs_dim.get('value', '')
                row_data[dim_id] = dim_value
            
            # Extract observation value
            obs_value_elem = obs.xpath('.//generic:ObsValue', namespaces=NAMESPACES)
            if obs_value_elem:
                row_data['OBS_VALUE'] = obs_value_elem[0].get('value', '')
            
            # Extract attributes
            for attr in obs.xpath('.//generic:Attributes/generic:Value', namespaces=NAMESPACES):
                attr_id = attr.get('id', '')
                attr_value = attr.get('value', '')
                row_data[attr_id] = attr_value
            
            # Build header from first row
            if not header_set:
                # Preserve order: DATAFLOW, dimensions (except TIME_PERIOD), TIME_PERIOD, OBS_VALUE, attributes
                dim_keys = [k for k in row_data.keys() if k not in ['DATAFLOW', 'TIME_PERIOD', 'OBS_VALUE']]
                header = ['DATAFLOW'] + sorted(dim_keys)
                if 'TIME_PERIOD' in row_data:
                    header.append('TIME_PERIOD')
                header.append('OBS_VALUE')
                
                # Add attribute columns
                attr_keys = [k for k in row_data.keys() if k.startswith('OBS_') and k != 'OBS_VALUE']
                attr_keys.extend([k for k in row_data.keys() if k.startswith('NOTE_')])
                header.extend(sorted(set(attr_keys)))
                
                header_set = True
            
            # Build row respecting header order
            row = []
            for col in header:
                row.append(row_data.get(col, ''))
            
            rows.append(row)
    
    # Build TSV output
    output_lines = ['\t'.join(header)]
    for row in rows:
        output_lines.append('\t'.join(row))
    
    return '\n'.join(output_lines)


def _parse_period(period_str: str) -> tuple[int, int, int] | None:
    """Parse a period string into a (year, start_month, end_month) tuple.

    Supported formats:
    - ``YYYY``          → full year  (year, 1, 12)
    - ``YYYY-MM``       → month      (year, month, month)
    - ``YYYY-MM-DD``    → day        (year, month, month)
    - ``YYYY-Qn``       → quarter    (year, first_month, last_month)
    - ``YYYY-Sn``/``YYYY-Hn`` → semester (year, first_month, last_month)

    Returns:
        Tuple (year, start_month, end_month) or None if the string cannot be parsed.
    """
    if not period_str:
        return None
    s = period_str.strip()
    try:
        # YYYY
        if re.match(r'^\d{4}$', s):
            return (int(s), 1, 12)

        # YYYY-Qn  (quarterly)
        m = re.match(r'^(\d{4})-[Qq]([1-4])$', s)
        if m:
            year, q = int(m.group(1)), int(m.group(2))
            return (year, (q - 1) * 3 + 1, q * 3)

        # YYYY-Sn or YYYY-Hn  (semester / half-year)
        m = re.match(r'^(\d{4})-[SsHh]([12])$', s)
        if m:
            year, h = int(m.group(1)), int(m.group(2))
            return (year, (h - 1) * 6 + 1, h * 6)

        # YYYY-MM or YYYY-MM-DD
        m = re.match(r'^(\d{4})-(\d{2})(?:-\d{2})?$', s)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            return (year, month, month)

    except (ValueError, AttributeError):
        pass

    return None


def filter_tsv_by_time_period(tsv_data: str, start_period: str | None, end_period: str | None) -> str:
    """Filter TSV rows by TIME_PERIOD range (workaround for ISTAT endPeriod+1 bug).

    The ISTAT SDMX API returns one extra year beyond the requested endPeriod.
    This function filters out rows whose TIME_PERIOD falls outside the requested range.

    Supported period formats: ``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD``, ``YYYY-Qn``,
    ``YYYY-Sn``/``YYYY-Hn``.  Rows whose TIME_PERIOD cannot be parsed are kept.

    Args:
        tsv_data: TSV string with header row
        start_period: Requested start period (e.g. '2024', '2024-Q1', '2024-01-01')
        end_period: Requested end period (e.g. '2024', '2024-Q4', '2024-12-31')

    Returns:
        Filtered TSV string
    """
    if not start_period and not end_period:
        return tsv_data

    lines = tsv_data.split('\n')
    if not lines:
        return tsv_data

    header = lines[0].split('\t')
    if 'TIME_PERIOD' not in header:
        return tsv_data

    tp_idx = header.index('TIME_PERIOD')

    start_parsed = _parse_period(start_period) if start_period else None
    end_parsed = _parse_period(end_period) if end_period else None

    if start_parsed is None and start_period:
        logger.warning(f'filter_tsv_by_time_period: cannot parse start_period "{start_period}", skipping start filter')
    if end_parsed is None and end_period:
        logger.warning(f'filter_tsv_by_time_period: cannot parse end_period "{end_period}", skipping end filter')

    filtered = [lines[0]]
    removed = 0
    for line in lines[1:]:
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) <= tp_idx:
            filtered.append(line)
            continue
        row_parsed = _parse_period(parts[tp_idx])
        if row_parsed is None:
            filtered.append(line)
            continue
        row_year, row_start_month, row_end_month = row_parsed

        # Exclude row if its period ends before the requested start
        if start_parsed:
            start_year, start_start_month, _ = start_parsed
            if (row_year, row_end_month) < (start_year, start_start_month):
                removed += 1
                continue

        # Exclude row if its period starts after the requested end
        if end_parsed:
            end_year, _, end_end_month = end_parsed
            if (row_year, row_start_month) > (end_year, end_end_month):
                removed += 1
                continue

        filtered.append(line)

    if removed:
        logger.info(f'filter_tsv_by_time_period: removed {removed} rows outside [{start_period}, {end_period}]')

    return '\n'.join(filtered)


def filter_tsv_by_dimensions(tsv_data: str, dimension_filters: dict[str, list[str]]) -> str:
    """Filter TSV rows by dimension values (client-side, post-API).

    Args:
        tsv_data: TSV string with header row
        dimension_filters: dict of dimension_id -> list of allowed codes

    Returns:
        Filtered TSV string
    """
    if not dimension_filters:
        return tsv_data

    lines = tsv_data.split('\n')
    if not lines:
        return tsv_data

    header = lines[0].split('\t')
    # Build index map for dimensions we need to filter
    col_index: dict[str, int] = {}
    for dim, values in dimension_filters.items():
        if values and dim in header:
            col_index[dim] = header.index(dim)

    if not col_index:
        return tsv_data

    # Precompute allowed values as sets for efficient membership checks
    allowed_values: dict[str, set[str]] = {
        dim: set(dimension_filters[dim]) for dim in col_index
    }

    filtered = [lines[0]]
    for line in lines[1:]:
        if not line:
            continue
        parts = line.split('\t')
        if all(
            len(parts) > idx and parts[idx] in allowed_values[dim]
            for dim, idx in col_index.items()
        ):
            filtered.append(line)

    return '\n'.join(filtered)


def _extract_constraints_info(constraints_data: dict[str, Any]) -> tuple[list[str], str | None, str | None]:
    """Extract dimension order and TIME_PERIOD info from constraints JSON.
    
    Args:
        constraints_data: Parsed JSON from get_constraints output
        
    Returns:
        Tuple of (dimension_order, time_period_start, time_period_end)
    """
    dimension_order = []
    time_period_start = None
    time_period_end = None

    for constraint in constraints_data.get('dimensions', []):
        dimension_id = constraint.get('dimension', '')
        
        if dimension_id == 'TIME_PERIOD':
            # Extract time period range
            time_period_start = constraint.get('StartPeriod', '')
            time_period_end = constraint.get('EndPeriod', '')
            # TIME_PERIOD is not included in dimension_order for filters
        else:
            # Regular dimension - add to order
            dimension_order.append(dimension_id)
    
    return dimension_order, time_period_start, time_period_end


def _determine_default_periods(time_period_end: str | None) -> tuple[str, str]:
    """Determine default start/end periods if not specified by user.
    
    Args:
        time_period_end: End period from TIME_PERIOD constraint
        
    Returns:
        Tuple of (start_period, end_period) as strings
    """
    if time_period_end:
        # Extract year from end period (format: YYYY-MM-DD or YYYY)
        try:
            end_year = time_period_end.split('-')[0] if '-' in time_period_end else time_period_end[:4]
            logger.info(f'get_data: No periods specified, using last available year: {end_year}')
            return end_year, end_year
        except (IndexError, ValueError):
            logger.warning(f'get_data: Could not parse TIME_PERIOD: {time_period_end}, using fallback')
    
    # Fallback: use previous year
    current_year = datetime.now().year - 1
    logger.info(f'get_data: No TIME_PERIOD info, using fallback year: {current_year}')
    return str(current_year), str(current_year)


API_BASE_URL = os.getenv('API_BASE_URL', 'https://esploradati.istat.it/SDMXWS/rest')


def _build_curl_info(
    dataflow_id: str,
    dimension_order: list[str],
    ordered_dimension_filters: list[list[str]],
    start_period: str | None,
    end_period: str | None,
    detail: str,
) -> str:
    """Build a curl command and query explanation for the user.

    Returns:
        Markdown string with URL, curl command, and filter explanation.
    """
    # Build dimension path (same logic as fetch_data)
    dim_path = '.'.join(
        '+'.join(f) if f else '' for f in ordered_dimension_filters
    ) if ordered_dimension_filters else ''

    base_path = f'{API_BASE_URL}/data/{dataflow_id}/{dim_path}/ALL/' if dim_path else f'{API_BASE_URL}/data/{dataflow_id}/ALL/'

    # Build query params
    qp: dict[str, str] = {'detail': detail}
    if start_period:
        qp['startPeriod'] = start_period
    if end_period:
        qp['endPeriod'] = end_period

    url = f'{base_path}?{urlencode(qp)}'

    # Build filter explanation table
    filter_rows = []
    for dim, filters in zip(dimension_order, ordered_dimension_filters):
        value_str = '+'.join(filters) if filters else '(tutti i valori)'
        filter_rows.append(f'  - `{dim}`: `{value_str}`')
    filters_md = '\n'.join(filter_rows) if filter_rows else '  - (nessun filtro)'

    curl_cmd = (
        f'curl -H "Accept: application/vnd.sdmx.data+csv;version=1.0.0" \\\n'
        f'  "{url}"'
    )

    return (
        '\n\n---\n'
        '## Come riprodurre questa query\n\n'
        f'**URL SDMX:**\n```\n{url}\n```\n\n'
        f'**cURL per scaricare i dati in CSV:**\n```bash\n{curl_cmd}\n```\n\n'
        '**Come è costruita la query:**\n'
        f'- Dataflow: `{dataflow_id}`\n'
        f'- Filtri per dimensione (nell\'ordine della struttura dati):\n{filters_md}\n'
        f'- Periodo: `{start_period or "n/d"}` → `{end_period or "n/d"}`\n'
        f'- Formato risposta API: XML SDMX (il server converte in tabella); per CSV usa il curl sopra\n'
        '\n> Le dimensioni nel percorso URL seguono l\'ordine fisso della struttura dati SDMX. '
        'I valori multipli per la stessa dimensione si separano con `+`.'
    )


@handle_tool_errors
async def handle_get_data(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
    blacklist: DataflowBlacklist,
) -> list[TextContent]:
    """Handle get_data tool.

    Args:
        arguments: Raw arguments dict from MCP
        cache: Cache manager instance
        api: API client instance
        blacklist: Dataflow blacklist instance

    Returns:
        List of TextContent with TSV table or error message
    """
    # Validate input
    params = GetDataInput.model_validate(arguments)

    if not validate_dataflow_id(params.id_dataflow):
        return [TextContent(type='text', text=f'Invalid dataflow ID: {params.id_dataflow}')]

    # Check blacklist
    if blacklist.is_blacklisted(params.id_dataflow):
        error_msg = f'Dataflow {params.id_dataflow} is blacklisted and cannot be accessed'
        logger.warning(error_msg)
        return [TextContent(type='text', text=error_msg)]

    # Step 1: Get constraints output (uses cache if available, otherwise generates it)
    # This provides: dimension order, valid values, and TIME_PERIOD range
    logger.info(f'get_data: Fetching constraints for {params.id_dataflow}')
    constraints_response = await handle_get_constraints(
        arguments={'dataflow_id': params.id_dataflow},
        cache=cache,
        api=api,
    )

    # Parse constraints response
    if not constraints_response or not constraints_response[0].text:
        return [TextContent(type='text', text=f'Failed to get constraints for dataflow: {params.id_dataflow}')]

    try:
        constraints_data = json.loads(constraints_response[0].text)
    except json.JSONDecodeError:
        # If parsing fails, the response might be an error message
        return constraints_response

    # Extract dimension order and TIME_PERIOD info from constraints
    dimension_order, time_period_start, time_period_end = _extract_constraints_info(constraints_data)

    logger.info(f'get_data: Found {len(dimension_order)} dimensions in order: {dimension_order}')
    if time_period_start and time_period_end:
        logger.info(f'get_data: TIME_PERIOD range: {time_period_start} to {time_period_end}')

    # Step 2: Determine start/end periods
    # If user didn't specify periods, use the last year from TIME_PERIOD range
    start_period = params.start_period
    end_period = params.end_period
    
    if not start_period and not end_period:
        start_period, end_period = _determine_default_periods(time_period_end)
    
    logger.info(f'get_data: Requesting data for period={start_period} to {end_period}')

    # Step 3: Get dataflow info to extract agency and version (needed for API call)
    dataflows = await get_cached_dataflows(cache, api)
    dataflow_info = find_dataflow_info(dataflows, params.id_dataflow)

    if not dataflow_info:
        return [TextContent(type='text', text=f'Dataflow not found: {params.id_dataflow}')]

    agency = dataflow_info.agency
    version = dataflow_info.version
    dataflow_full_id = f'{agency}:{params.id_dataflow}({version})'

    # Step 4: Build ordered dimension filters based on constraints dimension order
    # Use '.' for dimensions without filters
    ordered_dimension_filters = []
    for dimension_id in dimension_order:
        filter_values = params.dimension_filters.get(dimension_id, []) if params.dimension_filters else []
        ordered_dimension_filters.append(filter_values)
    
    logger.info(f'get_data: Built ordered filters: {ordered_dimension_filters}')

    # Step 5: Build cache key
    filter_str = '.'.join('+'.join(f) if f else '.' for f in ordered_dimension_filters) if ordered_dimension_filters else ''
    cache_key = f'api:data:{params.id_dataflow}:{filter_str}:{start_period or ""}_{end_period or ""}:{params.detail}:{params.dimension_at_observation or "none"}'

    # Step 6: Fetch data (cached)
    data_xml = await cache.get_or_fetch(
        key=cache_key,
        fetch_func=lambda: api.fetch_data(
            agency=agency,
            dataflow_id=params.id_dataflow,
            version=version,
            ordered_dimension_filters=ordered_dimension_filters,
            start_period=start_period,
            end_period=end_period,
            detail=params.detail,
            dimension_at_observation=params.dimension_at_observation,
        ),
        persistent_ttl=get_observed_data_cache_ttl(),
    )

    # Step 7: Parse XML to table format
    table_data = parse_sdmx_to_table(data_xml, dataflow_full_id)

    # Step 8: Apply dimension filters client-side (API may not honor all filters)
    if params.dimension_filters:
        table_data = filter_tsv_by_dimensions(table_data, params.dimension_filters)

    # Step 8b: Filter by TIME_PERIOD (workaround for ISTAT endPeriod+1 bug)
    table_data = filter_tsv_by_time_period(table_data, start_period, end_period)

    # Step 9: Append curl command and query explanation
    curl_info = _build_curl_info(
        dataflow_id=params.id_dataflow,
        dimension_order=dimension_order,
        ordered_dimension_filters=ordered_dimension_filters,
        start_period=start_period,
        end_period=end_period,
        detail=params.detail,
    )

    return [TextContent(type='text', text=table_data + curl_info)]

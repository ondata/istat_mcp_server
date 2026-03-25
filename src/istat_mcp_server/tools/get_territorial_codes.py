"""Tool: get_territorial_codes - Get ISTAT REF_AREA codes for a territorial level or place name."""

import logging
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from mcp.types import TextContent

from ..utils.tool_helpers import format_json_response

logger = logging.getLogger(__name__)

_PARQUET_PATH = Path(__file__).parent.parent.parent.parent / 'resources' / 'territorial_subdivisions.parquet'

_VALID_LEVELS = ('italia', 'ripartizione', 'regione', 'provincia', 'comune')


def _load_table() -> list[dict]:
    return pq.read_table(_PARQUET_PATH).to_pylist()


def _find_codes_by_name(rows: list[dict], name: str, level: str | None = None) -> list[str]:
    """Return codes for rows whose name matches the substring (case-insensitive), optionally filtered by level."""
    name_lower = name.lower()
    return [
        r['code'] for r in rows
        if name_lower in r['name_it'].lower() and (level is None or r['level'] == level)
    ]


def _province_codes_for_region(rows: list[dict], region_codes: list[str]) -> set[str]:
    """Return all province codes whose parent is one of the given region codes."""
    return {r['code'] for r in rows if r['level'] == 'provincia' and r.get('parent_code') in region_codes}


def _row_to_dict(r: dict, include_level: bool = False) -> dict:
    """Build a result dict from a parquet row, adding capoluogo fields for comuni."""
    result: dict = {'code': r['code'], 'name_it': r['name_it']}
    if include_level:
        result['level'] = r['level']
    if r.get('level') == 'comune':
        if r.get('capoluogo_provincia') is not None:
            result['capoluogo_provincia'] = r['capoluogo_provincia']
        if r.get('capoluogo_regione') is not None:
            result['capoluogo_regione'] = r['capoluogo_regione']
    return result


async def handle_get_territorial_codes(arguments: dict[str, Any]) -> list[TextContent]:
    """Return REF_AREA codes for a given territorial level or place name search.

    Args:
        arguments:
            'level': one of italia, ripartizione, regione, provincia, comune
            'name': place name to search (substring, case-insensitive)
            'region': filter comuni/province by region name or code (e.g. 'Lombardia', 'ITC4')
            'province': filter comuni by province name or code (e.g. 'Milano', 'ITC45')
            'capoluogo': if true, return only comuni that are capoluogo di provincia

    Returns:
        JSON: {codes: [{code, name_it, level?, capoluogo_provincia?, capoluogo_regione?}]}
    """
    level = arguments.get('level', '').strip().lower()
    name = arguments.get('name', '').strip()
    region = arguments.get('region', '').strip()
    province = arguments.get('province', '').strip()
    capoluogo = arguments.get('capoluogo', False)

    # Normalize capoluogo to bool
    if isinstance(capoluogo, str):
        capoluogo = capoluogo.lower() in ('true', '1', 'yes')

    has_filter = level or name or region or province or capoluogo

    if not has_filter:
        return format_json_response({
            'error': "Provide at least one of: 'level', 'name', 'region', 'province', 'capoluogo'."
        })

    if level and level not in _VALID_LEVELS:
        return format_json_response({'error': f"Invalid level '{level}'. Valid: {list(_VALID_LEVELS)}"})

    rows = _load_table()

    # --- Name search (no other filters) ---
    if name and not region and not province and not capoluogo and not level:
        name_lower = name.lower()
        result = [
            _row_to_dict(r, include_level=True)
            for r in rows
            if name_lower in r['name_it'].lower()
        ]
        return format_json_response({'query': name, 'codes': result})

    # --- Level-only (no territorial filters) ---
    if level and not region and not province and not capoluogo and not name:
        result = [_row_to_dict(r) for r in rows if r['level'] == level]
        return format_json_response({'level': level, 'codes': result})

    # --- Territorial filters: resolve region/province to codes ---
    target_level = level if level else 'comune'

    # Resolve region → set of province codes (for comuni filtering)
    province_codes_filter: set[str] | None = None
    if region:
        # Try as code first, then as name
        region_codes = [region] if any(r['code'] == region and r['level'] == 'regione' for r in rows) \
            else _find_codes_by_name(rows, region, level='regione')
        if not region_codes:
            return format_json_response({'error': f"Region not found: '{region}'"})
        province_codes_filter = _province_codes_for_region(rows, region_codes)
        logger.info(f'get_territorial_codes: region={region} → {len(province_codes_filter)} province codes')

    # Resolve province → single province code (for comuni filtering)
    province_code_filter: str | None = None
    if province:
        prov_codes = [province] if any(r['code'] == province and r['level'] == 'provincia' for r in rows) \
            else _find_codes_by_name(rows, province, level='provincia')
        if not prov_codes:
            return format_json_response({'error': f"Province not found: '{province}'"})
        if len(prov_codes) > 1:
            return format_json_response({
                'error': f"Multiple provinces match '{province}': {prov_codes}. Use a more specific name or the code."
            })
        province_code_filter = prov_codes[0]
        logger.info(f'get_territorial_codes: province={province} → {province_code_filter}')

    # --- Apply filters ---
    result = []
    for r in rows:
        row_level = r['level']

        # Level filter
        if target_level and row_level != target_level:
            continue

        # Region filter (for comuni: parent_code must be in province_codes_filter)
        if province_codes_filter is not None and row_level == 'comune':
            if r.get('parent_code') not in province_codes_filter:
                continue

        # Province filter (for comuni: parent_code must match)
        if province_code_filter is not None and row_level == 'comune':
            if r.get('parent_code') != province_code_filter:
                continue

        # Capoluogo filter
        if capoluogo and row_level == 'comune':
            if not r.get('capoluogo_provincia'):
                continue

        result.append(_row_to_dict(r, include_level=bool(not level)))

    filters_applied = {k: v for k, v in {'level': level, 'region': region, 'province': province, 'capoluogo': capoluogo if capoluogo else None}.items() if v}
    return format_json_response({'filters': filters_applied, 'count': len(result), 'codes': result})

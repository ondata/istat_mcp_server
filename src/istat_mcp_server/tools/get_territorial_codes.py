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


async def handle_get_territorial_codes(arguments: dict[str, Any]) -> list[TextContent]:
    """Return REF_AREA codes for a given territorial level or place name search.

    Args:
        arguments:
            'level': one of italia, ripartizione, regione, provincia (returns all codes for that level)
            'name': place name to search (e.g. 'Lombardia', 'Puglia') - returns matching codes

    Returns:
        List of TextContent with JSON: {level?, codes: [{code, name_it, level}]}
    """
    level = arguments.get('level', '').strip().lower()
    name = arguments.get('name', '').strip()

    if not level and not name:
        return format_json_response({
            'error': "Provide 'level' (one of: italia, ripartizione, regione, provincia, comune) or 'name' (place name to search)."
        })

    table = pq.read_table(_PARQUET_PATH)

    if name:
        # Search by name (case-insensitive substring match)
        logger.info(f'get_territorial_codes: name search="{name}"')
        name_lower = name.lower()
        rows = [
            _row_to_dict(r, include_level=True)
            for r in table.to_pylist()
            if name_lower in r['name_it'].lower()
        ]
        return format_json_response({'query': name, 'codes': rows})

    if level not in _VALID_LEVELS:
        return format_json_response({
            'error': f"Invalid level '{level}'. Valid values: {list(_VALID_LEVELS)}"
        })

    logger.info(f'get_territorial_codes: level={level}')
    rows = [
        _row_to_dict(r)
        for r in table.to_pylist()
        if r['level'] == level
    ]

    return format_json_response({'level': level, 'codes': rows})


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

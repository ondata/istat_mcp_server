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
            {'code': r['code'], 'name_it': r['name_it'], 'level': r['level']}
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
        {'code': r['code'], 'name_it': r['name_it']}
        for r in table.to_pylist()
        if r['level'] == level
    ]

    return format_json_response({'level': level, 'codes': rows})

"""Tool: get_territorial_codes - Get ISTAT REF_AREA codes for a territorial level or place name."""

import logging
from pathlib import Path
from typing import Any

import duckdb
from mcp.types import TextContent

from ..utils.tool_helpers import format_json_response

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent.parent.parent.parent / 'resources' / 'istat_lookup.duckdb'

_VALID_LEVELS = ('italia', 'ripartizione', 'regione', 'provincia', 'comune')


def _get_conn() -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to the lookup database."""
    return duckdb.connect(str(_DB_PATH), read_only=True)


def _rows_to_dicts(rows: list[tuple], columns: list[str]) -> list[dict]:
    """Convert DuckDB result rows to list of dicts."""
    return [dict(zip(columns, r)) for r in rows]


def _clean_row(d: dict, include_level: bool = False) -> dict:
    """Build a result dict, adding capoluogo fields only for comuni."""
    result: dict = {'code': d['code'], 'name_it': d['name_it']}
    if include_level:
        result['level'] = d['level']
    if d.get('level') == 'comune':
        if d.get('capoluogo_provincia') is not None:
            result['capoluogo_provincia'] = d['capoluogo_provincia']
        if d.get('capoluogo_regione') is not None:
            result['capoluogo_regione'] = d['capoluogo_regione']
    return result


async def handle_get_territorial_codes(arguments: dict[str, Any]) -> list[TextContent]:
    """Return REF_AREA codes for a given territorial level or place name search.

    Args:
        arguments:
            'level': one of italia, ripartizione, regione, provincia, comune
            'name': place name to search (substring, case-insensitive)
            'region': filter comuni/province by region name or code
            'province': filter comuni by province name or code
            'capoluogo': if true, return only comuni that are capoluogo di provincia
    """
    level = arguments.get('level', '').strip().lower()
    name = arguments.get('name', '').strip()
    region = arguments.get('region', '').strip()
    province = arguments.get('province', '').strip()
    capoluogo = arguments.get('capoluogo', False)

    if isinstance(capoluogo, str):
        capoluogo = capoluogo.lower() in ('true', '1', 'yes')

    has_filter = level or name or region or province or capoluogo

    if not has_filter:
        return format_json_response({
            'error': "Provide at least one of: 'level', 'name', 'region', 'province', 'capoluogo'."
        })

    if level and level not in _VALID_LEVELS:
        return format_json_response({'error': f"Invalid level '{level}'. Valid: {list(_VALID_LEVELS)}"})

    conn = _get_conn()

    try:
        # --- Name search (no other filters) ---
        if name and not region and not province and not capoluogo and not level:
            rows = conn.execute(
                'SELECT code, name_it, level, capoluogo_provincia, capoluogo_regione '
                'FROM territorial_subdivisions WHERE lower(name_it) LIKE ?',
                [f'%{name.lower()}%'],
            ).fetchall()
            cols = ['code', 'name_it', 'level', 'capoluogo_provincia', 'capoluogo_regione']
            result = [_clean_row(d, include_level=True) for d in _rows_to_dicts(rows, cols)]
            return format_json_response({'query': name, 'codes': result})

        # --- Level-only (no territorial filters) ---
        if level and not region and not province and not capoluogo and not name:
            rows = conn.execute(
                'SELECT code, name_it, level, capoluogo_provincia, capoluogo_regione '
                'FROM territorial_subdivisions WHERE level = ?',
                [level],
            ).fetchall()
            cols = ['code', 'name_it', 'level', 'capoluogo_provincia', 'capoluogo_regione']
            result = [_clean_row(d) for d in _rows_to_dicts(rows, cols)]
            return format_json_response({'level': level, 'codes': result})

        # --- Territorial filters ---
        target_level = level if level else 'comune'

        # Resolve region to province codes
        province_codes_filter: set[str] | None = None
        if region:
            # Try as code first
            region_codes = conn.execute(
                "SELECT code FROM territorial_subdivisions WHERE level = 'regione' AND code = ?",
                [region],
            ).fetchall()
            if not region_codes:
                region_codes = conn.execute(
                    "SELECT code FROM territorial_subdivisions WHERE level = 'regione' AND lower(name_it) LIKE ?",
                    [f'%{region.lower()}%'],
                ).fetchall()
            if not region_codes:
                return format_json_response({'error': f"Region not found: '{region}'"})
            region_code_list = [r[0] for r in region_codes]
            placeholders = ','.join(['?'] * len(region_code_list))
            prov_rows = conn.execute(
                f"SELECT code FROM territorial_subdivisions WHERE level = 'provincia' AND parent_code IN ({placeholders})",
                region_code_list,
            ).fetchall()
            province_codes_filter = {r[0] for r in prov_rows}

        # Resolve province to single code
        province_code_filter: str | None = None
        if province:
            prov_codes = conn.execute(
                "SELECT code FROM territorial_subdivisions WHERE level = 'provincia' AND code = ?",
                [province],
            ).fetchall()
            if not prov_codes:
                prov_codes = conn.execute(
                    "SELECT code FROM territorial_subdivisions WHERE level = 'provincia' AND lower(name_it) LIKE ?",
                    [f'%{province.lower()}%'],
                ).fetchall()
            if not prov_codes:
                return format_json_response({'error': f"Province not found: '{province}'"})
            if len(prov_codes) > 1:
                codes = [r[0] for r in prov_codes]
                return format_json_response({
                    'error': f"Multiple provinces match '{province}': {codes}. Use a more specific name or the code."
                })
            province_code_filter = prov_codes[0][0]

        # Build filtered query
        conditions = ['level = ?']
        params: list[Any] = [target_level]

        if name:
            conditions.append('lower(name_it) LIKE ?')
            params.append(f'%{name.lower()}%')

        if capoluogo and target_level == 'comune':
            conditions.append('capoluogo_provincia = true')

        where = ' AND '.join(conditions)
        rows = conn.execute(
            f'SELECT code, name_it, level, parent_code, capoluogo_provincia, capoluogo_regione '
            f'FROM territorial_subdivisions WHERE {where}',
            params,
        ).fetchall()
        cols = ['code', 'name_it', 'level', 'parent_code', 'capoluogo_provincia', 'capoluogo_regione']
        all_rows = _rows_to_dicts(rows, cols)

        # Apply parent-based filters in Python (simpler than complex SQL joins)
        result = []
        for r in all_rows:
            if province_codes_filter is not None and r['level'] == 'comune':
                if r.get('parent_code') not in province_codes_filter:
                    continue
            if province_code_filter is not None and r['level'] == 'comune':
                if r.get('parent_code') != province_code_filter:
                    continue
            result.append(_clean_row(r, include_level=bool(not level)))

        filters_applied = {
            k: v for k, v in {
                'level': level, 'name': name, 'region': region,
                'province': province, 'capoluogo': capoluogo if capoluogo else None,
            }.items() if v
        }
        return format_json_response({'filters': filters_applied, 'count': len(result), 'codes': result})
    finally:
        conn.close()

"""Tests for get_territorial_codes tool."""

import json
from unittest.mock import patch

import pytest

from istat_mcp_server.tools.get_territorial_codes import handle_get_territorial_codes

# Minimal representative sample of territorial rows used across tests
_SAMPLE_ROWS = [
    {
        'code': 'IT',
        'name_it': 'Italia',
        'level': 'italia',
        'nuts_level': 0,
        'parent_code': None,
        'capoluogo_provincia': None,
        'capoluogo_regione': None,
    },
    {
        'code': 'ITE',
        'name_it': 'Centro (IT)',
        'level': 'ripartizione',
        'nuts_level': 1,
        'parent_code': 'IT',
        'capoluogo_provincia': None,
        'capoluogo_regione': None,
    },
    {
        'code': 'ITE4',
        'name_it': 'Lazio',
        'level': 'regione',
        'nuts_level': 2,
        'parent_code': 'ITE',
        'capoluogo_provincia': None,
        'capoluogo_regione': None,
    },
    {
        'code': 'ITE43',
        'name_it': 'Roma',
        'level': 'provincia',
        'nuts_level': 3,
        'parent_code': 'ITE4',
        'capoluogo_provincia': None,
        'capoluogo_regione': None,
    },
    {
        'code': '058091',
        'name_it': 'Roma',
        'level': 'comune',
        'nuts_level': 4,
        'parent_code': 'ITE43',
        'capoluogo_provincia': True,
        'capoluogo_regione': True,
    },
    {
        'code': 'ITC1',
        'name_it': 'Piemonte',
        'level': 'regione',
        'nuts_level': 2,
        'parent_code': 'ITC',
        'capoluogo_provincia': None,
        'capoluogo_regione': None,
    },
    {
        'code': 'ITC11',
        'name_it': 'Torino',
        'level': 'provincia',
        'nuts_level': 3,
        'parent_code': 'ITC1',
        'capoluogo_provincia': None,
        'capoluogo_regione': None,
    },
    {
        'code': '001272',
        'name_it': 'Torino',
        'level': 'comune',
        'nuts_level': 4,
        'parent_code': 'ITC11',
        'capoluogo_provincia': True,
        'capoluogo_regione': True,
    },
    {
        'code': '001001',
        'name_it': 'Agliè',
        'level': 'comune',
        'nuts_level': 4,
        'parent_code': 'ITC11',
        'capoluogo_provincia': False,
        'capoluogo_regione': False,
    },
]


def _parse(result) -> dict:
    return json.loads(result[0].text)


@pytest.mark.asyncio
class TestLevelNameFilter:
    """Tests for combined level + name filtering."""

    async def test_level_comune_name_roma_returns_only_comune(self):
        """level='comune' + name='Roma' must return only the comune (058091), not the provincia."""
        with patch('istat_mcp_server.tools.get_territorial_codes._load_table', return_value=_SAMPLE_ROWS):
            result = await handle_get_territorial_codes({'level': 'comune', 'name': 'Roma'})

        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert '058091' in codes
        assert 'ITE43' not in codes

    async def test_level_provincia_name_torino_returns_only_provincia(self):
        """level='provincia' + name='Torino' must return only the provincia (ITC11), not the comune."""
        with patch('istat_mcp_server.tools.get_territorial_codes._load_table', return_value=_SAMPLE_ROWS):
            result = await handle_get_territorial_codes({'level': 'provincia', 'name': 'Torino'})

        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert 'ITC11' in codes
        assert '001272' not in codes

    async def test_filters_applied_includes_name(self):
        """The response 'filters' field must include 'name' when name is provided."""
        with patch('istat_mcp_server.tools.get_territorial_codes._load_table', return_value=_SAMPLE_ROWS):
            result = await handle_get_territorial_codes({'level': 'comune', 'name': 'Roma'})

        data = _parse(result)
        assert 'filters' in data
        assert data['filters'].get('name') == 'Roma'
        assert data['filters'].get('level') == 'comune'

    async def test_filters_applied_includes_level(self):
        """The response 'filters' field must include 'level' when level is provided."""
        with patch('istat_mcp_server.tools.get_territorial_codes._load_table', return_value=_SAMPLE_ROWS):
            result = await handle_get_territorial_codes({'level': 'provincia', 'name': 'Torino'})

        data = _parse(result)
        assert data['filters'].get('level') == 'provincia'
        assert data['filters'].get('name') == 'Torino'

    async def test_level_comune_no_false_positives_from_other_levels(self):
        """level='comune' must not return rows from regione, provincia, etc."""
        with patch('istat_mcp_server.tools.get_territorial_codes._load_table', return_value=_SAMPLE_ROWS):
            result = await handle_get_territorial_codes({'level': 'comune'})

        data = _parse(result)
        for row in data['codes']:
            assert row['code'] in {'058091', '001272', '001001'}

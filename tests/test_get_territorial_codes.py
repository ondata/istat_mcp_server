"""Tests for get_territorial_codes tool (DuckDB backend)."""

import json
from unittest.mock import patch

import duckdb
import pytest

from istat_mcp_server.tools.get_territorial_codes import handle_get_territorial_codes

# Minimal representative sample
_SAMPLE_ROWS = [
    ('IT', 'Italia', 'italia', 0, None, None, None),
    ('ITE', 'Centro (IT)', 'ripartizione', 1, 'IT', None, None),
    ('ITE4', 'Lazio', 'regione', 2, 'ITE', None, None),
    ('ITE43', 'Roma', 'provincia', 3, 'ITE4', None, None),
    ('058091', 'Roma', 'comune', 4, 'ITE43', True, True),
    ('ITC1', 'Piemonte', 'regione', 2, 'ITC', None, None),
    ('ITC11', 'Torino', 'provincia', 3, 'ITC1', None, None),
    ('001272', 'Torino', 'comune', 4, 'ITC11', True, True),
    ('001001', 'Aglie', 'comune', 4, 'ITC11', False, False),
]


@pytest.fixture(autouse=True)
def _mock_db(tmp_path):
    """Create a temp DuckDB with sample data and patch _get_conn."""
    db_path = tmp_path / 'test_lookup.duckdb'
    conn = duckdb.connect(str(db_path))
    conn.execute('''
        CREATE TABLE territorial_subdivisions (
            code VARCHAR NOT NULL,
            name_it VARCHAR NOT NULL,
            level VARCHAR NOT NULL,
            nuts_level TINYINT,
            parent_code VARCHAR,
            capoluogo_provincia BOOLEAN,
            capoluogo_regione BOOLEAN
        )
    ''')
    conn.executemany(
        'INSERT INTO territorial_subdivisions VALUES (?, ?, ?, ?, ?, ?, ?)',
        _SAMPLE_ROWS,
    )
    conn.execute('CREATE INDEX idx_level ON territorial_subdivisions(level)')
    conn.execute('CREATE INDEX idx_parent ON territorial_subdivisions(parent_code)')
    conn.execute('CREATE INDEX idx_code ON territorial_subdivisions(code)')
    conn.close()

    def mock_conn():
        return duckdb.connect(str(db_path), read_only=True)

    with patch('istat_mcp_server.tools.get_territorial_codes._get_conn', mock_conn):
        yield


def _parse(result) -> dict:
    return json.loads(result[0].text)


@pytest.mark.asyncio
class TestNoFilter:
    async def test_no_args_returns_error(self):
        result = await handle_get_territorial_codes({})
        data = _parse(result)
        assert 'error' in data

    async def test_invalid_level_returns_error(self):
        result = await handle_get_territorial_codes({'level': 'quartiere'})
        data = _parse(result)
        assert 'error' in data


@pytest.mark.asyncio
class TestLevelFilter:
    async def test_level_regione(self):
        result = await handle_get_territorial_codes({'level': 'regione'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert 'ITE4' in codes
        assert 'ITC1' in codes
        assert len(codes) == 2

    async def test_level_comune(self):
        result = await handle_get_territorial_codes({'level': 'comune'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert '058091' in codes
        assert '001272' in codes
        assert '001001' in codes
        # Must not include provincia or regione
        assert 'ITE43' not in codes


@pytest.mark.asyncio
class TestNameSearch:
    async def test_name_roma(self):
        result = await handle_get_territorial_codes({'name': 'Roma'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        # Both provincia and comune Roma
        assert 'ITE43' in codes
        assert '058091' in codes

    async def test_name_case_insensitive(self):
        result = await handle_get_territorial_codes({'name': 'torino'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert 'ITC11' in codes
        assert '001272' in codes


@pytest.mark.asyncio
class TestLevelNameFilter:
    async def test_level_comune_name_roma(self):
        """level='comune' + name='Roma' must return only the comune, not the provincia."""
        result = await handle_get_territorial_codes({'level': 'comune', 'name': 'Roma'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert '058091' in codes
        assert 'ITE43' not in codes

    async def test_level_provincia_name_torino(self):
        result = await handle_get_territorial_codes({'level': 'provincia', 'name': 'Torino'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert 'ITC11' in codes
        assert '001272' not in codes


@pytest.mark.asyncio
class TestRegionFilter:
    async def test_region_by_name(self):
        result = await handle_get_territorial_codes({'region': 'Piemonte'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert '001272' in codes
        assert '001001' in codes
        # Roma comune should NOT be included
        assert '058091' not in codes

    async def test_region_by_code(self):
        result = await handle_get_territorial_codes({'region': 'ITC1'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert '001272' in codes

    async def test_region_not_found(self):
        result = await handle_get_territorial_codes({'region': 'Atlantide'})
        data = _parse(result)
        assert 'error' in data


@pytest.mark.asyncio
class TestCapoluogo:
    async def test_capoluogo_filter(self):
        result = await handle_get_territorial_codes({'capoluogo': True, 'region': 'Piemonte'})
        data = _parse(result)
        codes = [c['code'] for c in data['codes']]
        assert '001272' in codes  # Torino is capoluogo
        assert '001001' not in codes  # Aglie is not

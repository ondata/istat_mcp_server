"""Tests for discover_dataflows tool — TOON output format."""

import pytest

from istat_mcp_server.api.models import DataflowInfo
from istat_mcp_server.tools.discover_dataflows import handle_discover_dataflows
from istat_mcp_server.utils.blacklist import DataflowBlacklist


def _make_dataflow(df_id: str, name_it: str, description_it: str = '') -> DataflowInfo:
    return DataflowInfo(
        id=df_id,
        name_it=name_it,
        name_en='',
        description_it=description_it,
        description_en='',
        version='1.0',
        agency='IT1',
        id_datastructure='DS_' + df_id,
        last_update='',
    )


@pytest.fixture
def sample_dataflows():
    return [
        _make_dataflow('100_1_DF_DCIS_DISOCCUPATI_1', 'Tasso di disoccupazione', 'Desc disoccupazione'),
        _make_dataflow('200_2_DF_DCSP_COLTIVAZIONI_1', 'Coltivazioni agricole', 'Produzione agricola'),
        _make_dataflow('300_3_DF_DCIS_POPOLAZIONE_1', 'Popolazione residente', 'Demo Italia'),
    ]


@pytest.fixture
def empty_blacklist():
    return DataflowBlacklist()


@pytest.mark.asyncio
async def test_discover_dataflows_toon_header(mock_cache_manager, mock_api_client, sample_dataflows, empty_blacklist):
    """TOON output starts with a header line containing count and field names."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return sample_dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows({}, mock_cache_manager, mock_api_client, empty_blacklist)

    assert len(result) == 1
    lines = result[0].text.split('\n')
    assert lines[0] == f'dataflows[{len(sample_dataflows)}]{{id,name_it,description_it}}:'


@pytest.mark.asyncio
async def test_discover_dataflows_toon_row_count(mock_cache_manager, mock_api_client, sample_dataflows, empty_blacklist):
    """TOON output has one row per dataflow plus the header."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return sample_dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows({}, mock_cache_manager, mock_api_client, empty_blacklist)

    lines = result[0].text.split('\n')
    # header + one line per dataflow
    assert len(lines) == len(sample_dataflows) + 1


@pytest.mark.asyncio
async def test_discover_dataflows_toon_contains_ids(mock_cache_manager, mock_api_client, sample_dataflows, empty_blacklist):
    """TOON output includes all dataflow IDs."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return sample_dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows({}, mock_cache_manager, mock_api_client, empty_blacklist)

    text = result[0].text
    for df in sample_dataflows:
        assert df.id in text


@pytest.mark.asyncio
async def test_discover_dataflows_keyword_filtering(mock_cache_manager, mock_api_client, sample_dataflows, empty_blacklist):
    """Keyword filtering returns only matching dataflows."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return sample_dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows(
        {'keywords': 'disoccupazione'},
        mock_cache_manager,
        mock_api_client,
        empty_blacklist,
    )

    lines = result[0].text.split('\n')
    # header + 1 matching dataflow
    assert len(lines) == 2
    assert '100_1_DF_DCIS_DISOCCUPATI_1' in result[0].text
    assert 'COLTIVAZIONI' not in result[0].text


@pytest.mark.asyncio
async def test_discover_dataflows_comma_keywords(mock_cache_manager, mock_api_client, sample_dataflows, empty_blacklist):
    """Multiple comma-separated keywords each filter independently (OR logic)."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return sample_dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows(
        {'keywords': 'disoccupazione,popolazione'},
        mock_cache_manager,
        mock_api_client,
        empty_blacklist,
    )

    lines = result[0].text.split('\n')
    # header + 2 matching dataflows
    assert len(lines) == 3
    assert '100_1_DF_DCIS_DISOCCUPATI_1' in result[0].text
    assert '300_3_DF_DCIS_POPOLAZIONE_1' in result[0].text
    assert 'COLTIVAZIONI' not in result[0].text


@pytest.mark.asyncio
async def test_discover_dataflows_empty_keywords_returns_all(mock_cache_manager, mock_api_client, sample_dataflows, empty_blacklist):
    """Empty keywords return all dataflows."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return sample_dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows(
        {'keywords': ''},
        mock_cache_manager,
        mock_api_client,
        empty_blacklist,
    )

    lines = result[0].text.split('\n')
    assert len(lines) == len(sample_dataflows) + 1


@pytest.mark.asyncio
async def test_discover_dataflows_csv_quoting(mock_cache_manager, mock_api_client, empty_blacklist):
    """Commas inside field values are properly CSV-quoted."""
    dataflows = [_make_dataflow('TEST_DF', 'Name, with comma', 'Desc, also comma')]

    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        return dataflows

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_discover_dataflows({}, mock_cache_manager, mock_api_client, empty_blacklist)

    text = result[0].text
    # The name with comma should be CSV-quoted
    assert '"Name, with comma"' in text
    assert '"Desc, also comma"' in text

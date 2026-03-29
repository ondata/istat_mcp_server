"""Tests for search_constraint_values tool."""

import json

import pytest

from istat_mcp_server.api.models import (
    CodeValue,
    CodelistInfo,
    ConstraintInfo,
    ConstraintValue,
    DataflowInfo,
    DatastructureInfo,
    DimensionConstraint,
    DimensionInfo,
    TimeConstraintValue,
)
from istat_mcp_server.tools.search_constraint_values import (
    handle_search_constraint_values,
)


# Shared test fixtures

DATAFLOWS = [
    DataflowInfo(
        id='TEST_DF',
        name_it='Test',
        name_en='Test',
        version='1.0',
        agency='IT1',
        id_datastructure='TEST_DS',
    )
]

DATASTRUCTURE = DatastructureInfo(
    id_datastructure='TEST_DS',
    dimensions=[
        DimensionInfo(dimension='FREQ', codelist='CL_FREQ'),
        DimensionInfo(dimension='REF_AREA', codelist='CL_AREA'),
        DimensionInfo(dimension='TIME_PERIOD', codelist=''),
    ],
)

CONSTRAINTS = ConstraintInfo(
    id='TEST_DF',
    dimensions=[
        DimensionConstraint(
            dimension='FREQ', values=[ConstraintValue(value='A')]
        ),
        DimensionConstraint(
            dimension='REF_AREA',
            values=[
                ConstraintValue(value='ITE1'),
                ConstraintValue(value='ITF4'),
                ConstraintValue(value='ITG1'),
            ],
        ),
        DimensionConstraint(
            dimension='TIME_PERIOD',
            values=[
                TimeConstraintValue(
                    StartPeriod='2000-01-01', EndPeriod='2025-12-31'
                )
            ],
        ),
    ],
)

CODELIST_AREA = CodelistInfo(
    id_codelist='CL_AREA',
    values=[
        CodeValue(code='ITE1', description_it='Toscana', description_en='Tuscany'),
        CodeValue(code='ITF4', description_it='Puglia', description_en='Apulia'),
        CodeValue(code='ITG1', description_it='Sicilia', description_en='Sicily'),
    ],
)

CODELIST_FREQ = CodelistInfo(
    id_codelist='CL_FREQ',
    values=[
        CodeValue(code='A', description_it='Annuale', description_en='Annual'),
    ],
)


def _make_mock_cache(mock_cache_manager):
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return DATAFLOWS
        elif 'datastructure:TEST_DS' in key:
            return DATASTRUCTURE
        elif 'constraints:TEST_DF' in key:
            return CONSTRAINTS
        elif 'codelist:CL_AREA' in key:
            return CODELIST_AREA
        elif 'codelist:CL_FREQ' in key:
            return CODELIST_FREQ
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch


@pytest.mark.asyncio
async def test_search_finds_matching_values(mock_cache_manager, mock_api_client):
    """Search text matches description."""
    _make_mock_cache(mock_cache_manager)

    result = await handle_search_constraint_values(
        {'dataflow_id': 'TEST_DF', 'dimension': 'REF_AREA', 'search': 'sicil'},
        mock_cache_manager,
        mock_api_client,
    )

    response = json.loads(result[0].text)
    assert response['matched_values'] == 1
    assert response['total_values'] == 3
    assert response['values'][0]['code'] == 'ITG1'
    assert response['values'][0]['description_it'] == 'Sicilia'


@pytest.mark.asyncio
async def test_search_empty_returns_all(mock_cache_manager, mock_api_client):
    """Empty search returns all values."""
    _make_mock_cache(mock_cache_manager)

    result = await handle_search_constraint_values(
        {'dataflow_id': 'TEST_DF', 'dimension': 'REF_AREA', 'search': ''},
        mock_cache_manager,
        mock_api_client,
    )

    response = json.loads(result[0].text)
    assert response['matched_values'] == 3
    assert response['total_values'] == 3


@pytest.mark.asyncio
async def test_search_no_match(mock_cache_manager, mock_api_client):
    """Search with no match returns empty."""
    _make_mock_cache(mock_cache_manager)

    result = await handle_search_constraint_values(
        {'dataflow_id': 'TEST_DF', 'dimension': 'REF_AREA', 'search': 'xyz'},
        mock_cache_manager,
        mock_api_client,
    )

    response = json.loads(result[0].text)
    assert response['matched_values'] == 0
    assert response['values'] == []


@pytest.mark.asyncio
async def test_search_invalid_dimension(mock_cache_manager, mock_api_client):
    """Invalid dimension returns error with available list."""
    _make_mock_cache(mock_cache_manager)

    result = await handle_search_constraint_values(
        {'dataflow_id': 'TEST_DF', 'dimension': 'UNKNOWN', 'search': 'x'},
        mock_cache_manager,
        mock_api_client,
    )

    assert 'not found' in result[0].text
    assert 'REF_AREA' in result[0].text


@pytest.mark.asyncio
async def test_search_time_period(mock_cache_manager, mock_api_client):
    """TIME_PERIOD returns range info."""
    _make_mock_cache(mock_cache_manager)

    result = await handle_search_constraint_values(
        {'dataflow_id': 'TEST_DF', 'dimension': 'TIME_PERIOD'},
        mock_cache_manager,
        mock_api_client,
    )

    response = json.loads(result[0].text)
    assert response['type'] == 'range'
    assert response['StartPeriod'] == '2000-01-01'


@pytest.mark.asyncio
async def test_search_case_insensitive(mock_cache_manager, mock_api_client):
    """Search is case-insensitive."""
    _make_mock_cache(mock_cache_manager)

    result = await handle_search_constraint_values(
        {'dataflow_id': 'TEST_DF', 'dimension': 'REF_AREA', 'search': 'PUGLIA'},
        mock_cache_manager,
        mock_api_client,
    )

    response = json.loads(result[0].text)
    assert response['matched_values'] == 1
    assert response['values'][0]['code'] == 'ITF4'

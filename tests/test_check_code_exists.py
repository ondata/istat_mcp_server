"""Tests for check_code_exists tool."""

import json

import pytest

from istat_mcp_server.api.models import (
    ConstraintInfo,
    ConstraintValue,
    DataflowInfo,
    DimensionConstraint,
    TimeConstraintValue,
)
from istat_mcp_server.tools.check_code_exists import handle_check_code_exists


def _make_dataflow(df_id: str = 'TEST_DF') -> DataflowInfo:
    return DataflowInfo(
        id=df_id,
        name_it='Test dataflow',
        name_en='Test dataflow',
        description_it='',
        description_en='',
        version='1.0',
        agency='IT1',
        id_datastructure='TEST_DS',
        last_update='',
    )


def _make_constraints(df_id: str = 'TEST_DF') -> ConstraintInfo:
    return ConstraintInfo(
        id=df_id,
        dimensions=[
            DimensionConstraint(
                dimension='REF_AREA',
                values=[
                    ConstraintValue(value='IT'),
                    ConstraintValue(value='ITC1'),
                    ConstraintValue(value='ITC4'),
                ],
            ),
            DimensionConstraint(
                dimension='SEX',
                values=[
                    ConstraintValue(value='1'),
                    ConstraintValue(value='2'),
                    ConstraintValue(value='9'),
                ],
            ),
            DimensionConstraint(
                dimension='TIME_PERIOD',
                values=[
                    TimeConstraintValue(
                        StartPeriod='2010-01-01T00:00:00',
                        EndPeriod='2024-12-31T23:59:59',
                    )
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_check_code_exists_valid_codes(mock_cache_manager, mock_api_client):
    """Known codes return exists=True; unknown codes return exists=False."""
    dataflows = [_make_dataflow()]
    constraints = _make_constraints()

    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return dataflows
        if 'constraints:TEST_DF' in key:
            return constraints
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_check_code_exists(
        {'dataflow_id': 'TEST_DF', 'dimension': 'REF_AREA', 'codes': ['IT', 'ITC1', 'XYZ']},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    response = json.loads(result[0].text)
    assert response['dataflow_id'] == 'TEST_DF'
    assert response['dimension'] == 'REF_AREA'
    results_map = {r['code']: r['exists'] for r in response['results']}
    assert results_map['IT'] is True
    assert results_map['ITC1'] is True
    assert results_map['XYZ'] is False


@pytest.mark.asyncio
async def test_check_code_exists_time_period_rejected(mock_cache_manager, mock_api_client):
    """TIME_PERIOD dimension returns a descriptive error, not exists=False."""
    dataflows = [_make_dataflow()]

    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return dataflows
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_check_code_exists(
        {'dataflow_id': 'TEST_DF', 'dimension': 'TIME_PERIOD', 'codes': ['2023']},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    response = json.loads(result[0].text)
    assert 'error' in response
    assert 'TIME_PERIOD' in response['error']
    assert 'range' in response['error'].lower()


@pytest.mark.asyncio
async def test_check_code_exists_unknown_dataflow(mock_cache_manager, mock_api_client):
    """Returns an error when the dataflow is not found."""
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return []
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_check_code_exists(
        {'dataflow_id': 'NONEXISTENT_DF', 'dimension': 'REF_AREA', 'codes': ['IT']},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    response = json.loads(result[0].text)
    assert 'error' in response
    assert 'NONEXISTENT_DF' in response['error']


@pytest.mark.asyncio
async def test_check_code_exists_unknown_dimension(mock_cache_manager, mock_api_client):
    """Returns an error with available_dimensions when dimension is not found."""
    dataflows = [_make_dataflow()]
    constraints = _make_constraints()

    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return dataflows
        if 'constraints:TEST_DF' in key:
            return constraints
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_check_code_exists(
        {'dataflow_id': 'TEST_DF', 'dimension': 'NONEXISTENT_DIM', 'codes': ['A']},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    response = json.loads(result[0].text)
    assert 'error' in response
    assert 'available_dimensions' in response
    assert 'REF_AREA' in response['available_dimensions']


@pytest.mark.asyncio
async def test_check_code_exists_codes_as_string(mock_cache_manager, mock_api_client):
    """Codes passed as a comma-separated string are parsed correctly."""
    dataflows = [_make_dataflow()]
    constraints = _make_constraints()

    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return dataflows
        if 'constraints:TEST_DF' in key:
            return constraints
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    result = await handle_check_code_exists(
        {'dataflow_id': 'TEST_DF', 'dimension': 'SEX', 'codes': '1, 9, 99'},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    response = json.loads(result[0].text)
    results_map = {r['code']: r['exists'] for r in response['results']}
    assert results_map['1'] is True
    assert results_map['9'] is True
    assert results_map['99'] is False


@pytest.mark.asyncio
async def test_check_code_exists_missing_arguments(mock_cache_manager, mock_api_client):
    """Missing required arguments return appropriate error messages."""
    result_no_df = await handle_check_code_exists(
        {'dimension': 'REF_AREA', 'codes': ['IT']},
        mock_cache_manager,
        mock_api_client,
    )
    assert 'dataflow_id' in json.loads(result_no_df[0].text)['error']

    result_no_dim = await handle_check_code_exists(
        {'dataflow_id': 'TEST_DF', 'codes': ['IT']},
        mock_cache_manager,
        mock_api_client,
    )
    assert 'dimension' in json.loads(result_no_dim[0].text)['error']

    result_no_codes = await handle_check_code_exists(
        {'dataflow_id': 'TEST_DF', 'dimension': 'REF_AREA'},
        mock_cache_manager,
        mock_api_client,
    )
    assert 'codes' in json.loads(result_no_codes[0].text)['error']

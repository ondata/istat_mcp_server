"""Tests for get_constraints tool."""

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
from istat_mcp_server.tools.get_constraints import handle_get_constraints


@pytest.mark.asyncio
async def test_get_constraints_success(mock_cache_manager, mock_api_client):
    """Test successful get_constraints with complete data."""
    # Setup mock dataflows
    dataflows = [
        DataflowInfo(
            id='101_1015_DF_DCSP_COLTIVAZIONI_1',
            name_it='Coltivazioni',
            name_en='Crops',
            description_it='',
            description_en='',
            version='1.0',
            agency='IT1',
            id_datastructure='DCSP_COLTIVAZIONI',
            last_update='',
        )
    ]

    # Setup mock datastructure
    datastructure = DatastructureInfo(
        id_datastructure='DCSP_COLTIVAZIONI',
        dimensions=[
            DimensionInfo(dimension='FREQ', codelist='CL_FREQ'),
            DimensionInfo(dimension='TYPE_OF_CROP', codelist='CL_AGRI_MADRE'),
            DimensionInfo(dimension='TIME_PERIOD', codelist=''),
        ],
    )

    # Setup mock constraints
    constraints = ConstraintInfo(
        id='101_1015_DF_DCSP_COLTIVAZIONI_1',
        dimensions=[
            DimensionConstraint(
                dimension='FREQ', values=[ConstraintValue(value='A')]
            ),
            DimensionConstraint(
                dimension='TYPE_OF_CROP',
                values=[
                    ConstraintValue(value='APPLE'),
                    ConstraintValue(value='WHEAT'),
                ],
            ),
            DimensionConstraint(
                dimension='TIME_PERIOD',
                values=[
                    TimeConstraintValue(
                        StartPeriod='2006-01-01T00:00:00',
                        EndPeriod='2026-12-31T23:59:59',
                    )
                ],
            ),
        ],
    )

    # Setup mock codelists
    codelist_freq = CodelistInfo(
        id_codelist='CL_FREQ',
        values=[
            CodeValue(code='A', description_en='Annual', description_it='Annuale')
        ],
    )

    codelist_crops = CodelistInfo(
        id_codelist='CL_AGRI_MADRE',
        values=[
            CodeValue(
                code='APPLE',
                description_en='Apples',
                description_it='Mele',
            ),
            CodeValue(
                code='WHEAT',
                description_en='Wheat',
                description_it='Grano',
            ),
        ],
    )

    # Configure mock returns
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return dataflows
        elif 'datastructure:DCSP_COLTIVAZIONI' in key:
            return datastructure
        elif 'constraints:101_1015_DF_DCSP_COLTIVAZIONI_1' in key:
            return constraints
        elif 'codelist:CL_FREQ' in key:
            return codelist_freq
        elif 'codelist:CL_AGRI_MADRE' in key:
            return codelist_crops
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    # Execute tool
    arguments = {'dataflow_id': '101_1015_DF_DCSP_COLTIVAZIONI_1'}
    result = await handle_get_constraints(
        arguments, mock_cache_manager, mock_api_client
    )

    # Verify result
    assert len(result) == 1
    assert result[0].type == 'text'
    
    # Parse JSON response
    import json
    response = json.loads(result[0].text)
    
    # Verify compact response structure
    assert response['id_dataflow'] == '101_1015_DF_DCSP_COLTIVAZIONI_1'
    assert len(response['dimensions']) == 3

    # Verify FREQ dimension (compact: no values, just count)
    freq_dim = response['dimensions'][0]
    assert freq_dim['dimension'] == 'FREQ'
    assert freq_dim['codelist'] == 'CL_FREQ'
    assert freq_dim['value_count'] == 1
    assert 'values' not in freq_dim

    # Verify TYPE_OF_CROP dimension
    crop_dim = response['dimensions'][1]
    assert crop_dim['dimension'] == 'TYPE_OF_CROP'
    assert crop_dim['codelist'] == 'CL_AGRI_MADRE'
    assert crop_dim['value_count'] == 2
    assert 'values' not in crop_dim

    # Verify TIME_PERIOD dimension
    time_dim = response['dimensions'][2]
    assert time_dim['dimension'] == 'TIME_PERIOD'
    assert time_dim['StartPeriod'] == '2006-01-01T00:00:00'
    assert time_dim['EndPeriod'] == '2026-12-31T23:59:59'


@pytest.mark.asyncio
async def test_get_constraints_dataflow_not_found(
    mock_cache_manager, mock_api_client
):
    """Test get_constraints with non-existent dataflow."""
    # Setup mock empty dataflows
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return []
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    # Execute tool
    arguments = {'dataflow_id': 'NON_EXISTENT_DF'}
    result = await handle_get_constraints(
        arguments, mock_cache_manager, mock_api_client
    )

    # Verify result
    assert len(result) == 1
    assert 'Dataflow not found' in result[0].text


@pytest.mark.asyncio
async def test_get_constraints_invalid_dataflow_id(
    mock_cache_manager, mock_api_client
):
    """Test get_constraints with invalid dataflow ID format."""
    # Execute tool with invalid ID
    arguments = {'dataflow_id': 'invalid-id-with-dash'}
    result = await handle_get_constraints(
        arguments, mock_cache_manager, mock_api_client
    )

    # Verify result
    assert len(result) == 1
    assert 'Invalid dataflow ID' in result[0].text


@pytest.mark.asyncio
async def test_get_constraints_missing_codelist(
    mock_cache_manager, mock_api_client
):
    """Test get_constraints when codelist fetch fails."""
    # Setup mocks
    dataflows = [
        DataflowInfo(
            id='TEST_DF',
            name_it='Test',
            name_en='Test',
            description_it='',
            description_en='',
            version='1.0',
            agency='IT1',
            id_datastructure='TEST_DS',
            last_update='',
        )
    ]

    datastructure = DatastructureInfo(
        id_datastructure='TEST_DS',
        dimensions=[
            DimensionInfo(dimension='TEST_DIM', codelist='CL_TEST'),
        ],
    )

    constraints = ConstraintInfo(
        id='TEST_DF',
        dimensions=[
            DimensionConstraint(
                dimension='TEST_DIM',
                values=[ConstraintValue(value='VAL1'), ConstraintValue(value='VAL2')],
            ),
        ],
    )

    # Configure mock to fail on codelist fetch
    async def mock_get_or_fetch(key, fetch_func, persistent_ttl=None):
        if 'dataflows:all' in key:
            return dataflows
        elif 'datastructure:TEST_DS' in key:
            return datastructure
        elif 'constraints:TEST_DF' in key:
            return constraints
        elif 'codelist:CL_TEST' in key:
            raise Exception('Codelist not found')
        return None

    mock_cache_manager.get_or_fetch.side_effect = mock_get_or_fetch

    # Execute tool
    arguments = {'dataflow_id': 'TEST_DF'}
    result = await handle_get_constraints(
        arguments, mock_cache_manager, mock_api_client
    )

    # Verify result - should still return values without descriptions
    assert len(result) == 1
    assert result[0].type == 'text'
    
    import json
    response = json.loads(result[0].text)
    
    # Should have dimension with count but no values listed
    assert len(response['dimensions']) == 1
    dim = response['dimensions'][0]
    assert dim['dimension'] == 'TEST_DIM'
    assert dim['value_count'] == 2
    assert 'values' not in dim

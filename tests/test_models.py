"""Tests for Pydantic input models."""

import pytest

from istat_mcp_server.api.models import GetConstraintsInput, GetDataInput


def test_get_data_input_accepts_primary_fields():
    """get_data accepts canonical field names."""
    params = GetDataInput.model_validate(
        {
            'id_dataflow': '22_315_DF_DCIS_POPORESBIL1_2',
            'dimension_filters': {'SEX': ['T']},
            'start_period': '2024',
            'end_period': '2025',
        }
    )

    assert params.id_dataflow == '22_315_DF_DCIS_POPORESBIL1_2'
    assert params.dimension_filters == {'SEX': ['T']}


def test_get_data_input_accepts_compat_aliases():
    """get_data accepts compatibility aliases used by some clients."""
    params = GetDataInput.model_validate(
        {
            'dataflow_id': '22_315_DF_DCIS_POPORESBIL1_2',
            'filters': {'SEX': ['T']},
            'start_period': '2024',
            'end_period': '2025',
        }
    )

    assert params.id_dataflow == '22_315_DF_DCIS_POPORESBIL1_2'
    assert params.dimension_filters == {'SEX': ['T']}


def test_get_data_input_coerces_dimension_filters_json_string():
    """get_data coerces dimension_filters from JSON string to dict."""
    params = GetDataInput.model_validate(
        {
            'id_dataflow': '22_315_DF_DCIS_POPORESBIL1_2',
            'dimension_filters': '{"SEX": ["9"], "FREQ": ["A"]}',
        }
    )

    assert params.dimension_filters == {'SEX': ['9'], 'FREQ': ['A']}


def test_get_constraints_input_coerces_dimensions_json_string():
    """get_constraints coerces dimensions from JSON string to list."""
    params = GetConstraintsInput.model_validate(
        {
            'dataflow_id': '41_288_DF_DCIS_VEICOLIPRA_1',
            'dimensions': '["AGE", "SEX"]',
        }
    )

    assert params.dimensions == ['AGE', 'SEX']


def test_get_data_input_invalid_json_string_raises():
    """get_data raises on invalid JSON string for dimension_filters."""
    with pytest.raises(Exception):
        GetDataInput.model_validate(
            {
                'id_dataflow': '22_315_DF_DCIS_POPORESBIL1_2',
                'dimension_filters': 'not valid json',
            }
        )

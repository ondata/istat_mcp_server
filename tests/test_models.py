"""Tests for Pydantic input models."""

from istat_mcp_server.api.models import GetDataInput


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


def test_get_data_input_coerces_dimension_filters_from_string():
    """dimension_filters passed as JSON string should be parsed automatically."""
    params = GetDataInput.model_validate(
        {
            'id_dataflow': '22_315_DF_DCIS_POPORESBIL1_2',
            'dimension_filters': '{"REF_AREA": ["IT"], "SEX": ["1", "2"]}',
        }
    )

    assert params.dimension_filters == {'REF_AREA': ['IT'], 'SEX': ['1', '2']}


def test_get_data_input_coerces_filters_alias_from_string():
    """filters alias passed as JSON string should also be parsed."""
    params = GetDataInput.model_validate(
        {
            'dataflow_id': 'test_df',
            'filters': '{"AGE": ["Y15-64"]}',
        }
    )

    assert params.dimension_filters == {'AGE': ['Y15-64']}


def test_get_data_input_dimension_filters_none_unchanged():
    """None dimension_filters should remain None."""
    params = GetDataInput.model_validate(
        {
            'id_dataflow': 'test_df',
        }
    )

    assert params.dimension_filters is None

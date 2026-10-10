"""Tests for get-constraints-cli."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from istat_mcp_server.api.models import (
    CodeValue,
    ConstraintsOutput,
    DimensionConstraintWithDescriptions,
    TimeConstraintOutput,
)
from istat_mcp_server.cli import get_constraints_cli


@pytest.fixture(autouse=True)
def no_real_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_run` builds a real CacheManager/ApiClient; stub them so a test never opens the cache."""
    monkeypatch.setattr(get_constraints_cli, 'MemoryCache', lambda **kwargs: MagicMock())
    monkeypatch.setattr(get_constraints_cli, 'PersistentCache', lambda **kwargs: MagicMock())
    monkeypatch.setattr(get_constraints_cli, 'CacheManager', lambda *args: MagicMock())
    monkeypatch.setattr(get_constraints_cli, 'ApiClient', lambda **kwargs: MagicMock())


def _output(dataflow_id: str = '151_914') -> ConstraintsOutput:
    return ConstraintsOutput(
        id_dataflow=dataflow_id,
        constraints=[
            DimensionConstraintWithDescriptions(
                dimension='FREQ',
                codelist='CL_FREQ',
                values=[CodeValue(code='A', description_en='Annual', description_it='Annuale')],
            ),
            DimensionConstraintWithDescriptions(
                dimension='SEX',
                codelist='CL_SEX',
                values=[CodeValue(code='9', description_en='Total', description_it='Totale')],
            ),
            TimeConstraintOutput(
                dimension='TIME_PERIOD',
                StartPeriod='2001',
                EndPeriod='2024',
            ),
        ],
    )


@pytest.mark.asyncio
async def test_run_prints_every_dimension(capsys):
    """Without --dimension the CLI prints the same JSON the MCP tool returns."""
    with patch.object(
        get_constraints_cli,
        'build_constraints_output',
        AsyncMock(return_value=_output()),
    ):
        await get_constraints_cli._run('151_914', None)

    payload = json.loads(capsys.readouterr().out)
    assert payload['id_dataflow'] == '151_914'
    assert [c['dimension'] for c in payload['constraints']] == [
        'FREQ',
        'SEX',
        'TIME_PERIOD',
    ]
    assert payload['constraints'][0]['values'][0] == {
        'code': 'A',
        'description_en': 'Annual',
        'description_it': 'Annuale',
    }


@pytest.mark.asyncio
async def test_run_filters_one_dimension(capsys):
    """--dimension keeps only that dimension, and does not care about case."""
    with patch.object(
        get_constraints_cli,
        'build_constraints_output',
        AsyncMock(return_value=_output()),
    ):
        await get_constraints_cli._run('151_914', 'sex')

    payload = json.loads(capsys.readouterr().out)
    assert [c['dimension'] for c in payload['constraints']] == ['SEX']


@pytest.mark.asyncio
async def test_run_reports_an_unknown_dimension(capsys):
    with patch.object(
        get_constraints_cli,
        'build_constraints_output',
        AsyncMock(return_value=_output()),
    ):
        await get_constraints_cli._run('151_914', 'NOPE')

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        'id_dataflow': '151_914',
        'dimension': 'NOPE',
        'found': False,
    }


@pytest.mark.asyncio
async def test_run_reports_an_unknown_dataflow(capsys):
    with patch.object(
        get_constraints_cli,
        'build_constraints_output',
        AsyncMock(return_value=None),
    ):
        await get_constraints_cli._run('NOPE', None)

    assert json.loads(capsys.readouterr().out) == {
        'id_dataflow': 'NOPE',
        'found': False,
    }


@pytest.mark.asyncio
async def test_run_passes_the_dataflow_through(capsys):
    build = AsyncMock(return_value=_output('101_1015_DF_DCSP_COLTIVAZIONI_1'))

    with patch.object(get_constraints_cli, 'build_constraints_output', build):
        await get_constraints_cli._run('101_1015_DF_DCSP_COLTIVAZIONI_1', None)

    assert build.await_args.args[0] == '101_1015_DF_DCSP_COLTIVAZIONI_1'
    assert json.loads(capsys.readouterr().out)['id_dataflow'] == '101_1015_DF_DCSP_COLTIVAZIONI_1'


def test_main_reports_api_errors_as_json(capsys, monkeypatch):
    """An API failure must not end in a traceback: callers parse stdout."""
    from istat_mcp_server.api.models import ApiError

    def explode(*_args, **_kwargs):
        raise ApiError('Request timeout after 120.2s')

    monkeypatch.setattr(get_constraints_cli, 'asyncio', get_constraints_cli.asyncio)
    monkeypatch.setattr(get_constraints_cli, '_run', explode)
    monkeypatch.setattr('sys.argv', ['istat-get-constraints-cli', '151_914'])

    with pytest.raises(SystemExit) as exit_info:
        get_constraints_cli.main()

    assert exit_info.value.code == 1
    assert json.loads(capsys.readouterr().out) == {
        'id_dataflow': '151_914',
        'error': 'Request timeout after 120.2s',
    }


def test_main_reports_unreadable_responses_as_json(capsys, monkeypatch):
    """A body the API sent successfully but that cannot be parsed is not an ApiError."""
    from xml.etree.ElementTree import ParseError

    def explode(*_args, **_kwargs):
        raise ParseError('not well-formed (invalid token)')

    monkeypatch.setattr(get_constraints_cli, '_run', explode)
    monkeypatch.setattr('sys.argv', ['istat-get-constraints-cli', '151_914'])

    with pytest.raises(SystemExit) as exit_info:
        get_constraints_cli.main()

    assert exit_info.value.code == 1
    assert json.loads(capsys.readouterr().out) == {
        'id_dataflow': '151_914',
        'error': 'Unexpected error: not well-formed (invalid token)',
    }

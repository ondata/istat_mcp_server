"""Tests for get_concepts tool and get_concepts_cli."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from istat_mcp_server.tools.get_concepts import handle_get_concepts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_process_mock(returncode: int, stdout: bytes, stderr: bytes = b'') -> MagicMock:
    """Return a mock subprocess whose communicate() returns (stdout, stderr)."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


def _concept_output(concept_id: str, name_it: str, name_en: str, scheme_id: str = 'CS_TEST') -> bytes:
    payload = {
        'concept_id': concept_id,
        'found': True,
        'name_it': name_it,
        'name_en': name_en,
        'scheme_id': scheme_id,
    }
    return json.dumps(payload, ensure_ascii=False).encode()


def _not_found_output(concept_id: str) -> bytes:
    return json.dumps({'concept_id': concept_id, 'found': False}).encode()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_concepts_returns_italian_description(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns the Italian name when lang='it'."""
    stdout = _concept_output('AGRIT_AUTHORIZATION', 'Tipo di autorizzazione agrituristica', 'Kind of agri-tourism authorization')
    proc = _make_process_mock(returncode=0, stdout=stdout)

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'AGRIT_AUTHORIZATION', 'lang': 'it'},
            mock_cache_manager,
            mock_api_client,
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].text == 'Tipo di autorizzazione agrituristica'


@pytest.mark.asyncio
async def test_get_concepts_returns_english_description(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns the English name when lang='en'."""
    stdout = _concept_output('AGRIT_AUTHORIZATION', 'Tipo di autorizzazione agrituristica', 'Kind of agri-tourism authorization')
    proc = _make_process_mock(returncode=0, stdout=stdout)

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'AGRIT_AUTHORIZATION', 'lang': 'en'},
            mock_cache_manager,
            mock_api_client,
        )

    assert result[0].text == 'Kind of agri-tourism authorization'


@pytest.mark.asyncio
async def test_get_concepts_not_found(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns an informative message when concept is not found."""
    stdout = _not_found_output('UNKNOWN_CONCEPT')
    proc = _make_process_mock(returncode=0, stdout=stdout)

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'UNKNOWN_CONCEPT', 'lang': 'it'},
            mock_cache_manager,
            mock_api_client,
        )

    assert len(result) == 1
    assert 'UNKNOWN_CONCEPT' in result[0].text
    assert 'non trovato' in result[0].text.lower() or 'not found' in result[0].text.lower()


@pytest.mark.asyncio
async def test_get_concepts_subprocess_error(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns an error message when subprocess fails to start."""
    with patch('asyncio.create_subprocess_exec', AsyncMock(side_effect=OSError('not found'))):
        result = await handle_get_concepts(
            {'concept_id': 'AGRIT_AUTHORIZATION', 'lang': 'it'},
            mock_cache_manager,
            mock_api_client,
        )

    assert len(result) == 1
    assert 'Errore' in result[0].text


@pytest.mark.asyncio
async def test_get_concepts_cli_nonzero_exit(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns an error message when CLI exits with non-zero code."""
    proc = _make_process_mock(returncode=1, stdout=b'', stderr=b'some error from CLI')

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'AGRIT_AUTHORIZATION', 'lang': 'it'},
            mock_cache_manager,
            mock_api_client,
        )

    assert len(result) == 1
    assert 'Errore' in result[0].text


@pytest.mark.asyncio
async def test_get_concepts_invalid_lang(mock_cache_manager, mock_api_client):
    """handle_get_concepts rejects lang values other than 'it' and 'en'."""
    result = await handle_get_concepts(
        {'concept_id': 'AGRIT_AUTHORIZATION', 'lang': 'fr'},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    assert "lang" in result[0].text.lower() or "'it'" in result[0].text or "'en'" in result[0].text


@pytest.mark.asyncio
async def test_get_concepts_missing_concept_id(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns an error when concept_id is missing."""
    result = await handle_get_concepts(
        {'lang': 'it'},
        mock_cache_manager,
        mock_api_client,
    )

    assert len(result) == 1
    assert 'Invalid input' in result[0].text


@pytest.mark.asyncio
async def test_get_concepts_defaults_to_italian(mock_cache_manager, mock_api_client):
    """handle_get_concepts uses 'it' as default language when lang is omitted."""
    stdout = _concept_output('FREQ', 'Frequenza', 'Frequency')
    proc = _make_process_mock(returncode=0, stdout=stdout)

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'FREQ'},  # no lang key
            mock_cache_manager,
            mock_api_client,
        )

    assert result[0].text == 'Frequenza'


@pytest.mark.asyncio
async def test_get_concepts_fallback_to_english_when_italian_missing(mock_cache_manager, mock_api_client):
    """handle_get_concepts falls back to English when the Italian name is empty."""
    payload = {
        'concept_id': 'SOME_CONCEPT',
        'found': True,
        'name_it': '',
        'name_en': 'English description',
        'scheme_id': 'CS_TEST',
    }
    stdout = json.dumps(payload).encode()
    proc = _make_process_mock(returncode=0, stdout=stdout)

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'SOME_CONCEPT', 'lang': 'it'},
            mock_cache_manager,
            mock_api_client,
        )

    assert result[0].text == 'English description'


@pytest.mark.asyncio
async def test_get_concepts_invalid_json_output(mock_cache_manager, mock_api_client):
    """handle_get_concepts returns an error when CLI emits invalid JSON."""
    proc = _make_process_mock(returncode=0, stdout=b'not valid json {{{')

    with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
        result = await handle_get_concepts(
            {'concept_id': 'FREQ', 'lang': 'it'},
            mock_cache_manager,
            mock_api_client,
        )

    assert len(result) == 1
    assert 'Errore' in result[0].text

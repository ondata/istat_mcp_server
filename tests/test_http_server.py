"""Tests for the streamable-HTTP host (auth and health endpoints)."""

import importlib
import logging

import pytest

pytest.importorskip('starlette')
pytest.importorskip('uvicorn')

from starlette.testclient import TestClient  # noqa: E402

MCP_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream',
}
TOOLS_LIST = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}


@pytest.fixture(autouse=True)
def _isolate_logging(monkeypatch, tmp_path):
    """Each reload runs create_server(), which adds file/console handlers to the root logger:
    log to tmp_path and close the handlers the test added."""
    monkeypatch.setattr('istat_mcp_server.server.LOG_DIR', str(tmp_path))
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in root.handlers[:]:
        if handler not in before:
            root.removeHandler(handler)
            handler.close()


def _load(monkeypatch, token):
    """Import http_server with MCP_ISTAT_TOKEN set (or unset) before module load."""
    if token is None:
        monkeypatch.delenv('MCP_ISTAT_TOKEN', raising=False)
    else:
        monkeypatch.setenv('MCP_ISTAT_TOKEN', token)
    from istat_mcp_server import http_server

    return importlib.reload(http_server)


def test_health_is_open(monkeypatch):
    module = _load(monkeypatch, 's3cret')
    response = TestClient(module.app).get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_mcp_without_token_is_rejected(monkeypatch):
    module = _load(monkeypatch, 's3cret')
    response = TestClient(module.app).post('/mcp/', json=TOOLS_LIST, headers=MCP_HEADERS)
    assert response.status_code == 401


def test_mcp_with_wrong_token_is_rejected(monkeypatch):
    module = _load(monkeypatch, 's3cret')
    response = TestClient(module.app).post(
        '/mcp/',
        json=TOOLS_LIST,
        headers={**MCP_HEADERS, 'Authorization': 'Bearer nope'},
    )
    assert response.status_code == 401


def test_mcp_with_token_lists_tools(monkeypatch):
    module = _load(monkeypatch, 's3cret')
    with TestClient(module.app) as client:
        response = client.post(
            '/mcp/',
            json=TOOLS_LIST,
            headers={**MCP_HEADERS, 'Authorization': 'Bearer s3cret'},
        )
    assert response.status_code == 200
    assert 'discover_dataflows' in response.text


def test_empty_token_aborts_startup(monkeypatch):
    with pytest.raises(SystemExit):
        _load(monkeypatch, '  ')

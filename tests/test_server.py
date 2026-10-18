"""Tests for the MCP server factory."""

import logging
from importlib.metadata import version

import pytest

from istat_mcp_server.server import create_server


@pytest.fixture(autouse=True)
def _isolate_logging(monkeypatch, tmp_path):
    """create_server() adds file/console handlers to the root logger:
    log to tmp_path and close the handlers the test added."""
    monkeypatch.setattr('istat_mcp_server.server.LOG_DIR', str(tmp_path))
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in root.handlers[:]:
        if handler not in before:
            root.removeHandler(handler)
            handler.close()


def test_server_info_reports_project_version():
    options = create_server().create_initialization_options()
    assert options.server_name == 'istat-mcp-server'
    assert options.server_version == version('istat-mcp-server')

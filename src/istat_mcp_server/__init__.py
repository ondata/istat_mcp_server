"""Main package exports."""

from importlib.metadata import version

from .server import create_server

__version__ = version('istat-mcp-server')

__all__ = ['create_server']

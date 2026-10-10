"""HTTP host for the ISTAT MCP server.

The server in this package speaks MCP over stdio (see ``__main__``). This module mounts the
same ``mcp.server.Server`` behind a stateless streamable-HTTP ASGI application so that it
can run as a long-lived network service, for example in Kubernetes:

* ``/mcp/``   MCP streamable-HTTP endpoint (``/mcp`` redirects to ``/mcp/`` with 307).
* ``/health`` liveness/readiness endpoint, always unauthenticated.

Optional bearer authentication: when ``MCP_ISTAT_TOKEN`` is set, requests to ``/mcp`` must
carry ``Authorization: Bearer <token>``. An empty value is a configuration error and aborts
startup, so a misconfigured deployment never runs unauthenticated by accident. The check runs at the ASGI layer instead of a
``BaseHTTPMiddleware`` because the latter buffers the body and breaks SSE streaming.

Run with ``istat-mcp-http`` (console script) or ``python -m istat_mcp_server.http_server``.
Requires the ``http`` extra: ``pip install "istat-mcp-server[http]"``.
"""

from __future__ import annotations

import contextlib
import hmac
import logging
import os
from collections.abc import AsyncIterator

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from .server import create_server

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"
HEALTH_PATH = "/health"
TOKEN_ENV = os.environ.get("MCP_ISTAT_TOKEN")
if TOKEN_ENV is not None and not TOKEN_ENV.strip():
    raise SystemExit(
        "MCP_ISTAT_TOKEN is set but empty: provide a token, or unset it to run without authentication"
    )
MCP_TOKEN = TOKEN_ENV or None


def _authorized(scope: Scope) -> bool:
    if not MCP_TOKEN:
        return True
    headers = dict(scope.get("headers") or [])
    return hmac.compare_digest(headers.get(b"authorization", b""), f"Bearer {MCP_TOKEN}".encode())


# Stateless mode: every request is self-contained, no server-side session store, so any
# replica can serve any request and the Deployment scales horizontally.
_server = create_server()
_session_manager = StreamableHTTPSessionManager(
    app=_server,
    event_store=None,
    json_response=False,
    stateless=True,
)


async def _handle_mcp(scope: Scope, receive: Receive, send: Send) -> None:
    if not _authorized(scope):
        await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
        return
    await _session_manager.handle_request(scope, receive, send)


async def _health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@contextlib.asynccontextmanager
async def _lifespan(_app: Starlette) -> AsyncIterator[None]:
    async with _session_manager.run():
        logger.info("ISTAT MCP server listening over streamable-HTTP at %s/", MCP_PATH)
        yield


app = Starlette(
    debug=False,
    routes=[
        Route(HEALTH_PATH, _health, methods=["GET"]),
        Mount(MCP_PATH, app=_handle_mcp),
    ],
    lifespan=_lifespan,
)


def main() -> None:
    """Serve ``app`` with uvicorn on ``HOST``:``PORT`` (defaults 0.0.0.0:8000)."""
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )


if __name__ == "__main__":
    main()

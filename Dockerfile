# ISTAT MCP server — HTTP host image.
# Serves the MCP server over streamable-HTTP on :8000 (src/istat_mcp_server/http_server.py).
# Dependencies are installed from uv.lock (--frozen) so the image uses the same pinned
# versions as the project; `pip install .` would resolve a newer, incompatible `mcp` SDK.
#
#   docker build -t istat-mcp-server .
#   docker run --rm -p 8000:8000 istat-mcp-server
#   curl localhost:8000/health
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PORT=8000 \
    # The server writes logs and cache next to the package by default, which is not
    # writable for a non-root user: use single-level paths under /tmp (created with os.mkdir).
    LOG_DIR=/tmp/istat-log \
    PERSISTENT_CACHE_DIR=/tmp/istat-cache

WORKDIR /app

# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock README.md LICENSE.txt ./
RUN uv sync --frozen --no-dev --no-install-project --extra http
COPY src ./src
RUN uv sync --frozen --no-dev --extra http

# Unprivileged user; uid 1000 matches the Helm chart security context.
RUN useradd --uid 1000 --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"
CMD ["istat-mcp-http"]

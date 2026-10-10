"""CLI command: get-constraints-cli — print the constraints of an ISTAT dataflow.

Usage:
    istat-get-constraints-cli <dataflow_id>
    istat-get-constraints-cli <dataflow_id> --dimension FREQ
    python -m istat_mcp_server.cli.get_constraints_cli <dataflow_id>

Output (stdout, JSON): the same JSON as the `get_constraints` MCP tool, without
routing it through the LLM context.

    {"id_dataflow": "151_914", "constraints": [
        {"dimension": "FREQ", "codelist": "CL_FREQ", "values": [
            {"code": "A", "description_it": "...", "description_en": "..."}]},
        {"dimension": "TIME_PERIOD", "StartPeriod": "2001", "EndPeriod": "2024"}]}

With --dimension the list holds that dimension only. When the dataflow does not
exist: {"id_dataflow": "...", "found": false}. When the requested dimension does
not exist: {"id_dataflow": "...", "dimension": "...", "found": false}.
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

from ..api.client import ApiClient
from ..api.models import ApiError
from ..cache.manager import CacheManager
from ..cache.memory import MemoryCache
from ..cache.persistent import PersistentCache
from ..tools.get_constraints import build_constraints_output

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'https://esploradati.istat.it/SDMXWS/rest')
API_TIMEOUT = float(os.getenv('API_TIMEOUT_SECONDS', '120'))
AVAILABLECONSTRAINT_TIMEOUT = float(os.getenv('AVAILABLECONSTRAINT_TIMEOUT_SECONDS', '180'))
API_MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))

_DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'cache'
)
PERSISTENT_CACHE_DIR = os.getenv('PERSISTENT_CACHE_DIR', _DEFAULT_CACHE_DIR)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


async def _run(dataflow_id: str, dimension: str | None) -> None:
    memory_cache = MemoryCache(ttl=300, max_size=512)
    persistent_cache = PersistentCache(cache_dir=PERSISTENT_CACHE_DIR)
    cache = CacheManager(memory_cache, persistent_cache)

    api = ApiClient(
        base_url=API_BASE_URL,
        timeout=API_TIMEOUT,
        availableconstraint_timeout=AVAILABLECONSTRAINT_TIMEOUT,
        max_retries=API_MAX_RETRIES,
    )

    constraints = await build_constraints_output(dataflow_id, cache, api)

    if constraints is None:
        _print_json({'id_dataflow': dataflow_id, 'found': False})
        return

    if dimension is not None:
        wanted = dimension.upper()
        selected = [
            constraint
            for constraint in constraints.constraints
            if constraint.dimension.upper() == wanted
        ]
        if not selected:
            _print_json({
                'id_dataflow': dataflow_id,
                'dimension': dimension,
                'found': False,
            })
            return
        constraints = constraints.model_copy(update={'constraints': selected})

    print(json.dumps(constraints.model_dump(exclude_none=True), ensure_ascii=False))


def main() -> None:
    """Entry point for the istat-get-constraints-cli command."""
    parser = argparse.ArgumentParser(
        description='Print the available constraints of an ISTAT dataflow.'
    )
    parser.add_argument('dataflow_id', help="Dataflow ID (e.g. '151_914')")
    parser.add_argument(
        '--dimension',
        help="Limit the output to one dimension (e.g. FREQ)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.dataflow_id, args.dimension))
    except KeyboardInterrupt:
        sys.exit(0)
    except ApiError as e:
        # The ISTAT API is slow and rate-limits by IP (see LOG.md), so a failed
        # call has to stay machine-readable for whoever runs this in a script
        # rather than ending in a traceback.
        _print_json({'id_dataflow': args.dataflow_id, 'error': str(e)})
        sys.exit(1)
    except Exception as e:
        # A response the API sends successfully but that cannot be parsed is not
        # an ApiError, and `handle_tool_errors` catches it in the MCP tool: the
        # CLI keeps the same contract, so stdout stays JSON.
        _print_json(
            {'id_dataflow': args.dataflow_id, 'error': f'Unexpected error: {e}'}
        )
        sys.exit(1)


if __name__ == '__main__':
    main()

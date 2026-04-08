"""CLI command: get-concepts-cli — cerca un concept per ID negli schemi ISTAT.

Usage:
    istat-get-concepts-cli <concept_id>
    python -m istat_mcp_server.cli.get_concepts_cli <concept_id>

Output (stdout, JSON):
    {"concept_id": "AGRIT_AUTHORIZATION", "found": true,
     "name_it": "Tipo di autorizzazione agrituristica",
     "name_en": "Kind of agri-tourism authorization",
     "scheme_id": "CS_AGRITUR"}

Se il concept non esiste: {"concept_id": "...", "found": false}
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

from ..api.client import ApiClient
from ..cache.manager import CacheManager
from ..cache.memory import MemoryCache
from ..cache.persistent import PersistentCache
from ..utils.tool_helpers import get_cached_conceptschemes

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'https://esploradati.istat.it/SDMXWS/rest')
API_TIMEOUT = float(os.getenv('API_TIMEOUT_SECONDS', '120'))
AVAILABLECONSTRAINT_TIMEOUT = float(os.getenv('AVAILABLECONSTRAINT_TIMEOUT_SECONDS', '180'))
API_MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))

_DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'cache'
)
PERSISTENT_CACHE_DIR = os.getenv('PERSISTENT_CACHE_DIR', _DEFAULT_CACHE_DIR)


async def _run(concept_id: str) -> None:
    memory_cache = MemoryCache(ttl=300, max_size=512)
    persistent_cache = PersistentCache(cache_dir=PERSISTENT_CACHE_DIR)
    cache = CacheManager(memory_cache, persistent_cache)

    api = ApiClient(
        base_url=API_BASE_URL,
        timeout=API_TIMEOUT,
        availableconstraint_timeout=AVAILABLECONSTRAINT_TIMEOUT,
        max_retries=API_MAX_RETRIES,
    )

    schemes = await get_cached_conceptschemes(cache, api)

    for scheme in schemes:
        for concept in scheme.concepts:
            if concept.id == concept_id:
                output = {
                    'concept_id': concept_id,
                    'found': True,
                    'name_it': concept.name_it,
                    'name_en': concept.name_en,
                    'scheme_id': scheme.id,
                }
                print(json.dumps(output, ensure_ascii=False))
                return

    print(json.dumps({'concept_id': concept_id, 'found': False}, ensure_ascii=False))


def main() -> None:
    """Entry point per il comando istat-get-concepts-cli."""
    parser = argparse.ArgumentParser(
        description='Cerca la descrizione di un concept ISTAT per ID.'
    )
    parser.add_argument('concept_id', help="Concept ID (es. 'AGRIT_AUTHORIZATION')")
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.concept_id))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()

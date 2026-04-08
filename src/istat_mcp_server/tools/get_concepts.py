"""Tool: get_concepts - Restituisce la descrizione di un concept ISTAT per ID.

Il tool chiama il CLI get_concepts_cli via subprocess (pattern bash_tool + jq):
  istat-get-concepts-cli <concept_id>  →  JSON  →  estrae name_it o name_en
"""

import json
import logging
import sys
from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field, ValidationError

from ..api.client import ApiClient
from ..cache.manager import CacheManager

logger = logging.getLogger(__name__)


class GetConceptsInput(BaseModel):
    concept_id: str = Field(..., description="Concept ID da cercare (es. 'AGRIT_AUTHORIZATION')")
    lang: str = Field('it', description="Lingua della descrizione: 'it' o 'en'")


async def handle_get_concepts(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
) -> list[TextContent]:
    """Handle get_concepts tool.

    Chiama il CLI get_concepts_cli come subprocess e ne legge il JSON di output
    (equivalente a: istat-get-concepts-cli <concept_id> | jq '.name_it').

    Args:
        arguments: Raw arguments dict from MCP (concept_id, lang)
        cache: Cache manager instance (non usato direttamente: il subprocess usa la disk cache)
        api: API client instance (non usato direttamente)

    Returns:
        List of TextContent con la descrizione del concept o un messaggio di errore
    """
    try:
        params = GetConceptsInput.model_validate(arguments)
    except ValidationError as e:
        return [TextContent(type='text', text=f'Invalid input: {e}')]

    if params.lang not in ('it', 'en'):
        return [TextContent(type='text', text="Il parametro 'lang' deve essere 'it' o 'en'")]

    logger.info(f'get_concepts: concept_id={params.concept_id!r} lang={params.lang!r}')

    # Chiama il CLI come subprocess: equivalente a bash_tool + jq
    import asyncio

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            '-m',
            'istat_mcp_server.cli.get_concepts_cli',
            params.concept_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except Exception as e:
        logger.error(f'get_concepts: subprocess error: {e}')
        return [TextContent(type='text', text=f'Errore avvio subprocess: {e}')]

    if proc.returncode != 0:
        err = stderr.decode(errors='replace').strip()
        logger.error(f'get_concepts: CLI exited {proc.returncode}: {err}')
        return [TextContent(type='text', text=f'Errore CLI: {err}')]

    try:
        data = json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        return [TextContent(type='text', text=f'Errore parsing output CLI: {e}')]

    if not data.get('found'):
        return [TextContent(type='text', text=f"Concept '{params.concept_id}' non trovato")]

    # Equivalente jq: .name_it  oppure  .name_en
    lang_field = f'name_{params.lang}'
    description = data.get(lang_field) or data.get('name_en') or data.get('name_it', '')

    if not description:
        return [TextContent(type='text', text=f"Nessuna descrizione disponibile per '{params.concept_id}'")]

    return [TextContent(type='text', text=description)]

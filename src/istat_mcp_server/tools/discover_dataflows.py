"""Tool: discover_dataflows - Discover available dataflows from ISTAT SDMX API."""

import logging
from typing import Any

from mcp.types import TextContent

from ..api.client import ApiClient
from ..api.models import DataflowInfo, DiscoverDataflowsInput
from ..cache.manager import CacheManager
from ..utils.validators import validate_keywords
from ..utils.blacklist import DataflowBlacklist
from ..utils.tool_helpers import (
    format_json_response,
    get_cached_dataflows,
    handle_tool_errors,
)
from ..search import semantic as sem

logger = logging.getLogger(__name__)

EMBEDDINGS_CACHE_KEY = sem.EMBEDDINGS_CACHE_KEY
EMBEDDINGS_CACHE_TTL = 604800  # 7 days, same as dataflows

_CANDIDATE_MULTIPLIER = 2  # fetch 2x max_results from each source before merging


def _keyword_search(dataflows: list[DataflowInfo], keywords: list[str], limit: int) -> list[DataflowInfo]:
    """Return dataflows matching any keyword via substring search."""
    results = [
        df for df in dataflows
        if any(kw in ' '.join([
            df.id, df.name_it, df.name_en,
            df.description_it, df.description_en, df.id_datastructure
        ]).lower() for kw in keywords)
    ]
    return results[:limit]


def _format_markdown(query: str, semantic: list[DataflowInfo], keyword: list[DataflowInfo]) -> str:
    """Format both result sets as markdown for LLM reranking."""

    def _rows(dfs: list[DataflowInfo]) -> str:
        if not dfs:
            return '_Nessun risultato._\n'
        lines = ['| ID | Nome IT | Nome EN |', '|---|---|---|']
        for df in dfs:
            lines.append(f'| `{df.id}` | {df.name_it} | {df.name_en} |')
        return '\n'.join(lines) + '\n'

    md = f'## Query: {query}\n\n'
    md += '### Ricerca semantica\n'
    md += _rows(semantic)
    md += '\n### Ricerca testuale\n'
    md += _rows(keyword)
    return md


@handle_tool_errors
async def handle_discover_dataflows(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
    blacklist: DataflowBlacklist,
) -> list[TextContent]:
    """Handle discover_dataflows tool."""
    params = DiscoverDataflowsInput.model_validate(arguments)
    keywords = validate_keywords(params.keywords)
    max_results = getattr(params, 'max_results', 10)

    logger.info(f'discover_dataflows: keywords={keywords}')

    dataflows = await get_cached_dataflows(cache, api)
    dataflows = blacklist.filter_dataflows(dataflows)

    if keywords:
        query = ' '.join(keywords)

        if sem.is_available():
            candidates = max_results * _CANDIDATE_MULTIPLIER
            cached_embeddings = cache.get(EMBEDDINGS_CACHE_KEY)

            sem_results, embeddings = sem.semantic_search(
                query=query,
                dataflows=dataflows,
                cached_embeddings=cached_embeddings,
                max_results=candidates,
            )
            cache.set(EMBEDDINGS_CACHE_KEY, embeddings, persistent_ttl=EMBEDDINGS_CACHE_TTL)

            kw_results = _keyword_search(dataflows, keywords, limit=candidates)

            logger.info(f'Semantic: {len(sem_results)}, keyword: {len(kw_results)}')
        else:
            # Fallback: string matching only
            logger.info('sentence-transformers not installed, falling back to keyword matching')
            sem_results = []
            kw_results = _keyword_search(dataflows, keywords, limit=max_results)
            logger.info(f'Keyword results: {len(kw_results)}')

        md = _format_markdown(query, sem_results, kw_results)
        return [TextContent(type='text', text=md)]

    response = {
        'count': len(dataflows),
        'dataflows': [df.model_dump() for df in dataflows],
    }

    return format_json_response(response)

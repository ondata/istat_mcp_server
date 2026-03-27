"""Helper utilities for tool handlers to reduce code duplication."""

import json
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from mcp.types import TextContent
from pydantic import BaseModel, ValidationError

from ..api.client import ApiClient
from ..api.models import (
    ApiError,
    CodelistInfo,
    ConceptSchemeInfo,
    ConstraintInfo,
    DataflowInfo,
    DatastructureInfo,
)
from ..cache.manager import CacheManager

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

DATAFLOWS_CACHE_KEY = 'api:dataflows:all'
CONCEPTSCHEMES_CACHE_KEY = 'api:conceptschemes:all'

DATAFLOWS_CACHE_TTL = 604800
METADATA_CACHE_TTL = 2592000
OBSERVED_DATA_CACHE_TTL = 3600


def configure_cache_ttls(
    dataflows_ttl: int | None = None,
    metadata_ttl: int | None = None,
    observed_data_ttl: int | None = None,
) -> None:
    """Configure shared TTL values used by cache helper functions.

    Args:
        dataflows_ttl: Optional TTL for cached dataflow lists
        metadata_ttl: Optional TTL for metadata such as constraints and codelists
        observed_data_ttl: Optional TTL for observed data responses
    """
    global DATAFLOWS_CACHE_TTL, METADATA_CACHE_TTL, OBSERVED_DATA_CACHE_TTL

    if dataflows_ttl is not None:
        DATAFLOWS_CACHE_TTL = dataflows_ttl
    if metadata_ttl is not None:
        METADATA_CACHE_TTL = metadata_ttl
    if observed_data_ttl is not None:
        OBSERVED_DATA_CACHE_TTL = observed_data_ttl


def get_dataflows_cache_key() -> str:
    """Return the shared cache key for dataflows."""
    return DATAFLOWS_CACHE_KEY


def get_conceptschemes_cache_key() -> str:
    """Return the shared cache key for concept schemes."""
    return CONCEPTSCHEMES_CACHE_KEY


def get_constraints_cache_key(dataflow_id: str) -> str:
    """Return the cache key for dataflow constraints."""
    return f'api:constraints:{dataflow_id}'


def get_datastructure_cache_key(id_datastructure: str) -> str:
    """Return the cache key for a datastructure."""
    return f'api:datastructure:{id_datastructure}'


def get_codelist_cache_key(codelist_id: str) -> str:
    """Return the cache key for a codelist."""
    return f'api:codelist:{codelist_id}'


def get_constraints_keyed_cache_key(dataflow_id: str, key: str) -> str:
    """Return the cache key for key-filtered constraints."""
    return f'api:constraints_keyed:{dataflow_id}:{key}'


def get_metadata_cache_ttl() -> int:
    """Return the shared metadata TTL in seconds."""
    return METADATA_CACHE_TTL


def get_dataflows_cache_ttl() -> int:
    """Return the shared dataflows TTL in seconds."""
    return DATAFLOWS_CACHE_TTL


def get_observed_data_cache_ttl() -> int:
    """Return the shared observed data TTL in seconds."""
    return OBSERVED_DATA_CACHE_TTL


def format_toon_dataflows(dataflows: list[DataflowInfo]) -> list[TextContent]:
    """Format dataflows as TOON (Token-Oriented Object Notation).

    Includes only id, name_it, description_it to minimise token usage.
    Values are CSV-quoted to handle commas inside field content.
    """
    import csv
    import io

    lines = [f'dataflows[{len(dataflows)}]{{id,name_it,description_it}}:']
    for df in dataflows:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([df.id, df.name_it, df.description_it])
        lines.append(' ' + buf.getvalue().rstrip('\r\n'))
    return [TextContent(type='text', text='\n'.join(lines))]


def format_json_response(data: dict[str, Any] | BaseModel) -> list[TextContent]:
    """Format data as JSON TextContent response.
    
    Args:
        data: Dictionary or Pydantic model to serialize
        
    Returns:
        List containing single TextContent with JSON-formatted text
    """
    if isinstance(data, BaseModel):
        data = data.model_dump()
    
    response_text = json.dumps(data, indent=2, ensure_ascii=False)
    return [TextContent(type='text', text=response_text)]


def ensure_model(data: Any, model_class: type[T]) -> T:
    """Convert dict to Pydantic model if needed.
    
    Args:
        data: Data that may be dict or already a model instance
        model_class: Target Pydantic model class
        
    Returns:
        Instance of model_class
    """
    if isinstance(data, dict):
        return model_class.model_validate(data)
    return data


def ensure_model_list(data_list: list[Any], model_class: type[T]) -> list[T]:
    """Convert list of dicts to list of Pydantic models if needed.
    
    Args:
        data_list: List of items that may be dicts or model instances
        model_class: Target Pydantic model class
        
    Returns:
        List of model_class instances
    """
    if not data_list:
        return []
    
    if isinstance(data_list[0], dict):
        return [model_class.model_validate(item) for item in data_list]
    return data_list


async def get_cached_dataflows(
    cache: CacheManager,
    api: ApiClient,
) -> list[DataflowInfo]:
    """Fetch all dataflows using the shared cache key and TTL.

    Args:
        cache: Cache manager instance
        api: API client instance

    Returns:
        List of validated DataflowInfo models
    """
    dataflows = await cache.get_or_fetch(
        key=get_dataflows_cache_key(),
        fetch_func=lambda: api.fetch_dataflows(),
        persistent_ttl=get_dataflows_cache_ttl(),
    )
    return ensure_model_list(dataflows, DataflowInfo)


async def get_cached_constraints(
    cache: CacheManager,
    api: ApiClient,
    dataflow_id: str,
) -> ConstraintInfo:
    """Fetch constraints for a dataflow using shared cache conventions."""
    constraints = await cache.get_or_fetch(
        key=get_constraints_cache_key(dataflow_id),
        fetch_func=lambda: api.fetch_constraints(dataflow_id),
        persistent_ttl=get_metadata_cache_ttl(),
    )
    return ensure_model(constraints, ConstraintInfo)


async def get_cached_constraints_keyed(
    cache: CacheManager,
    api: ApiClient,
    dataflow_id: str,
    key: str,
) -> ConstraintInfo:
    """Fetch constraints using an SDMX key filter (fast path for large dataflows)."""
    constraints = await cache.get_or_fetch(
        key=get_constraints_keyed_cache_key(dataflow_id, key),
        fetch_func=lambda: api.fetch_constraints(dataflow_id, key=key),
        persistent_ttl=get_metadata_cache_ttl(),
    )
    return ensure_model(constraints, ConstraintInfo)


async def get_cached_datastructure(
    cache: CacheManager,
    api: ApiClient,
    id_datastructure: str,
) -> DatastructureInfo:
    """Fetch a datastructure using shared cache conventions."""
    datastructure = await cache.get_or_fetch(
        key=get_datastructure_cache_key(id_datastructure),
        fetch_func=lambda: api.fetch_datastructure(id_datastructure),
        persistent_ttl=get_metadata_cache_ttl(),
    )
    return ensure_model(datastructure, DatastructureInfo)


async def get_cached_codelist(
    cache: CacheManager,
    api: ApiClient,
    codelist_id: str,
) -> CodelistInfo:
    """Fetch a codelist using shared cache conventions."""
    codelist = await cache.get_or_fetch(
        key=get_codelist_cache_key(codelist_id),
        fetch_func=lambda: api.fetch_codelist(codelist_id),
        persistent_ttl=get_metadata_cache_ttl(),
    )
    return ensure_model(codelist, CodelistInfo)


async def get_cached_conceptschemes(
    cache: CacheManager,
    api: ApiClient,
) -> list[ConceptSchemeInfo]:
    """Fetch concept schemes using shared cache conventions."""
    schemes = await cache.get_or_fetch(
        key=get_conceptschemes_cache_key(),
        fetch_func=lambda: api.fetch_conceptschemes(),
        persistent_ttl=get_metadata_cache_ttl(),
    )
    return ensure_model_list(schemes, ConceptSchemeInfo)


def find_dataflow_info(
    dataflows: list[DataflowInfo],
    dataflow_id: str,
) -> DataflowInfo | None:
    """Find a dataflow by ID in a validated list of dataflows."""
    return next((df for df in dataflows if df.id == dataflow_id), None)


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator to handle common tool errors consistently.
    
    Catches ValidationError, ApiError, and generic Exception,
    logs them appropriately, and returns error messages as TextContent.
    
    Args:
        func: Async tool handler function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> list[TextContent]:
        try:
            return await func(*args, **kwargs)
        
        except ValidationError as e:
            error_msg = f'Invalid input: {e}'
            logger.error(error_msg)
            return [TextContent(type='text', text=error_msg)]
        
        except ApiError as e:
            error_msg = f'API error {e.status_code}: {e.message}'
            logger.error(error_msg)
            return [TextContent(type='text', text=error_msg)]
        
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            logger.exception(error_msg)
            return [TextContent(type='text', text=error_msg)]
    
    return wrapper

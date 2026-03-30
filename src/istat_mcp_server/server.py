"""MCP server for ISTAT SDMX API."""

import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool

from .api.client import ApiClient
from .cache.manager import CacheManager
from .cache.memory import MemoryCache
from .cache.persistent import PersistentCache
from .tools import (
    get_cache_diagnostics_handler,
    handle_discover_dataflows,
    handle_get_codelist_description,
    handle_get_concepts,
    handle_get_constraints,
    handle_get_data,
    handle_get_structure,
    handle_get_territorial_codes,
)
from .utils.tool_helpers import configure_cache_ttls
from .utils.logging import setup_logging
from .utils.blacklist import DataflowBlacklist

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration from environment
API_BASE_URL = os.getenv('API_BASE_URL', 'https://esploradati.istat.it/SDMXWS/rest')
API_TIMEOUT = float(os.getenv('API_TIMEOUT_SECONDS', '120'))
AVAILABLECONSTRAINT_TIMEOUT = float(
    os.getenv('AVAILABLECONSTRAINT_TIMEOUT_SECONDS', '180')
)
API_MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))

# Use absolute path for cache directory to avoid issues with different working directories
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'cache')
PERSISTENT_CACHE_DIR = os.getenv('PERSISTENT_CACHE_DIR', DEFAULT_CACHE_DIR)

# Use absolute path for log directory
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'log')
LOG_DIR = os.getenv('LOG_DIR', DEFAULT_LOG_DIR)

MEMORY_CACHE_TTL = int(os.getenv('MEMORY_CACHE_TTL_SECONDS', '300'))
DATAFLOWS_CACHE_TTL = int(os.getenv('DATAFLOWS_CACHE_TTL_SECONDS', '604800'))
METADATA_CACHE_TTL = int(os.getenv('METADATA_CACHE_TTL_SECONDS', '2592000'))
OBSERVED_DATA_CACHE_TTL = int(os.getenv('OBSERVED_DATA_CACHE_TTL_SECONDS', '86400'))
MAX_MEMORY_CACHE_ITEMS = int(os.getenv('MAX_MEMORY_CACHE_ITEMS', '512'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


def create_server() -> Server:
    """Create and configure the MCP server.

    Returns:
        Configured MCP Server instance
    """
    # Setup logging
    setup_logging(LOG_LEVEL, log_dir=LOG_DIR)
    logger.info('Initializing ISTAT MCP Server')

    configure_cache_ttls(
        dataflows_ttl=DATAFLOWS_CACHE_TTL,
        metadata_ttl=METADATA_CACHE_TTL,
        observed_data_ttl=OBSERVED_DATA_CACHE_TTL,
    )

    # Initialize cache layers
    memory_cache = MemoryCache(ttl=MEMORY_CACHE_TTL, max_size=MAX_MEMORY_CACHE_ITEMS)
    persistent_cache = PersistentCache(cache_dir=PERSISTENT_CACHE_DIR)
    cache_manager = CacheManager(memory_cache, persistent_cache)
    logger.info(f'Cache system initialized at: {os.path.abspath(PERSISTENT_CACHE_DIR)}')

    # Initialize API client
    api_client = ApiClient(
        base_url=API_BASE_URL,
        timeout=API_TIMEOUT,
        availableconstraint_timeout=AVAILABLECONSTRAINT_TIMEOUT,
        max_retries=API_MAX_RETRIES,
    )
    logger.info('API client initialized')

    # Initialize blacklist
    blacklist = DataflowBlacklist()
    logger.info('Dataflow blacklist initialized')

    # Create MCP server
    server = Server('istat-mcp-server')
    logger.info('MCP server created')

    # Register tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name='discover_dataflows',
                description='Discover available dataflows from ISTAT SDMX API. Optionally filter by comma-separated keywords.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'keywords': {
                            'type': 'string',
                            'description': "Comma-separated keywords (e.g., 'population,employment'). Leave empty for all dataflows.",
                        }
                    },
                },
            ),
            Tool(
                name='get_structure',
                description='Get data structure definition for a datastructure ID. Returns dimensions and their codelists.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'id_datastructure': {
                            'type': 'string',
                            'description': "Datastructure ID (e.g., 'DCSP_COLTIVAZIONI')",
                        }
                    },
                    'required': ['id_datastructure'],
                },
            ),
            Tool(
                name='get_constraints',
                description='Get available constraints (dimension values) for a dataflow with descriptions. Returns all valid values for each dimension.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'dataflow_id': {
                            'type': 'string',
                            'description': "Dataflow ID (e.g., '101_1015_DF_DCSP_COLTIVAZIONI_1')",
                        }
                    },
                    'required': ['dataflow_id'],
                },
            ),
            Tool(
                name='get_codelist_description',
                description='Get Italian and English descriptions for all values in a codelist.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'codelist_id': {
                            'type': 'string',
                            'description': "Codelist ID (e.g., 'CL_AGRI_MADRE')",
                        }
                    },
                    'required': ['codelist_id'],
                },
            ),
            Tool(
                name='get_concepts',
                description='Get all concept schemes and their concepts with descriptions. Shows all available concepts used in the ISTAT datawarehouse.',
                inputSchema={
                    'type': 'object',
                    'properties': {},
                },
            ),
            Tool(
                name='get_data',
                description='Fetch actual data from a dataflow in TSV table format. Supports dimension filtering and time ranges. If no time period specified, fetches last complete year. Output includes reproducible URLs: a CSV URL (openable in browser via format=csv), the SDMX XML URL, and a curl command.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'id_dataflow': {
                            'type': 'string',
                            'description': "Dataflow ID (e.g., '22_315_DF_DCIS_POPORESBIL1_2')",
                        },
                        'dataflow_id': {
                            'type': 'string',
                            'description': "Alias of id_dataflow (for compatibility).",
                        },
                        'dimension_filters': {
                            'type': 'object',
                            'description': 'Optional dimension filters. Keys are dimension IDs, values are arrays of codes.',
                            'additionalProperties': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                        },
                        'filters': {
                            'type': 'object',
                            'description': 'Alias of dimension_filters (for compatibility).',
                            'additionalProperties': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                        },
                        'start_period': {
                            'type': 'string',
                            'description': "Start period (e.g., '2024-11-01' or '2024'). Omit for last year only.",
                        },
                        'end_period': {
                            'type': 'string',
                            'description': "End period (e.g., '2025-11-30' or '2025'). Omit for last year only.",
                        },
                        'detail': {
                            'type': 'string',
                            'description': "Detail level: 'full', 'dataonly', 'serieskeysonly', or 'nodata'",
                            'default': 'full',
                        },
                        'dimension_at_observation': {
                            'type': 'string',
                            'description': "Dimension at observation level (e.g., 'TIME_PERIOD'). Optional.",
                        },
                    },
                    'required': ['id_dataflow'],
                },
            ),
            Tool(
                name='get_cache_diagnostics',
                description='Get diagnostic information about the cache system (path, size, keys). For debugging.',
                inputSchema={
                    'type': 'object',
                    'properties': {},
                },
            ),
            Tool(
                name='get_territorial_codes',
                description='Get ISTAT REF_AREA territorial codes by level (italia, ripartizione, regione, provincia, comune) or place name search. Supports filtering by region, province, and capoluogo status. Contains the full territorial hierarchy (9142 entries) with parent-child relationships. Use cases: find REF_AREA codes for get_data queries (e.g. all comuni capoluogo for accident statistics, all provinces in Southern regions for olive oil production, all comuni in a specific province for demographic analysis).',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'level': {
                            'type': 'string',
                            'description': "Territorial level: 'italia', 'ripartizione', 'regione', 'provincia', 'comune'",
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Place name to search (substring, case-insensitive)',
                        },
                        'region': {
                            'type': 'string',
                            'description': "Filter by region name or code (e.g. 'Lombardia', 'ITC4')",
                        },
                        'province': {
                            'type': 'string',
                            'description': "Filter by province name or code (e.g. 'Milano', 'ITC45')",
                        },
                        'capoluogo': {
                            'type': 'boolean',
                            'description': 'If true, return only comuni that are capoluogo di provincia',
                            'default': False,
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        """Handle tool calls with detailed logging."""
        start_time = time.time()
        
        # Log inizio chiamata
        logger.info('=' * 80)
        logger.info(f'MCP TOOL CALL: {name}')
        logger.info(f'Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}')
        
        result = None
        error = None

        try:
            if name == 'discover_dataflows':
                result = await handle_discover_dataflows(arguments, cache_manager, api_client, blacklist)
            elif name == 'get_structure':
                result = await handle_get_structure(arguments, cache_manager, api_client)
            elif name == 'get_constraints':
                result = await handle_get_constraints(arguments, cache_manager, api_client)
            elif name == 'get_codelist_description':
                result = await handle_get_codelist_description(
                    arguments, cache_manager, api_client
                )
            elif name == 'get_concepts':
                result = await handle_get_concepts(arguments, cache_manager, api_client)
            elif name == 'get_data':
                result = await handle_get_data(arguments, cache_manager, api_client, blacklist)
            elif name == 'get_cache_diagnostics':
                result = await get_cache_diagnostics_handler()
            elif name == 'get_territorial_codes':
                result = await handle_get_territorial_codes(arguments)
            else:
                raise ValueError(f'Unknown tool: {name}')
            
            # Log successo
            elapsed_time = time.time() - start_time
            response_size = len(str(result)) if result else 0
            logger.info(f'TOOL SUCCESS: {name}')
            logger.info(f'Execution time: {elapsed_time:.3f}s')
            logger.info(f'Response size: {response_size} bytes')
            logger.info('=' * 80)
            
            return result

        except Exception as e:
            # Log errore dettagliato
            elapsed_time = time.time() - start_time
            logger.error(f'TOOL ERROR: {name}')
            logger.error(f'Error type: {type(e).__name__}')
            logger.error(f'Error message: {str(e)}')
            logger.error(f'Execution time: {elapsed_time:.3f}s')
            logger.exception(f'Full traceback:')
            logger.info('=' * 80)
            raise

    logger.info('MCP server configured with 8 tools')
    return server

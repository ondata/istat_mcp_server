# Copilot Instructions — MCP Server: istat_mcp_server

## Goal
This MCP server exposes data from the ISTAT SDMX API (https://esploradati.istat.it/SDMXWS/rest/) to Claude Desktop. It implements a two-layer caching mechanism (in-memory + persistent) to minimize API calls and provides **eight tools** for discovering, querying, and retrieving Italian statistical data. A companion **CLI layer** (`src/istat_mcp_server/cli/`) exposes lightweight commands for offline use and internal tool delegation. All tool inputs are validated with Pydantic, errors are handled gracefully, and the caching mechanism is implemented with appropriate TTLs. The server follows best practices for code organization, error handling, and documentation.

## General Principles

### Code Quality
- Write **readable, maintainable, and well-documented** code following the project structure
- Follow the DRY principle — reuse code and abstractions, especially for cache access and API calls
- Use descriptive names for variables, functions, and classes
- Include docstrings for all public interfaces using Google-style format
- Keep code simple and focused — each function or class should have a single responsibility
- Avoid over-engineering or adding unnecessary complexity

### Code Style
- **Python 3.11+** — use modern Python features (`match`, `X | Y` union types, etc.)
- Use **single quotes** for string literals (except when the string contains a single quote)
- Format with **ruff** (already configured in project)
- Type hints for all function parameters and returns
- All I/O operations must be **async/await** (API calls, cache reads/writes)

### API Usage
- **Rate limiting**: Maximum 3 API calls per minute (enforced by `RateLimiter` in `ApiClient`)
- Implement proper error handling and retries with exponential backoff
- Never hit live API endpoints in tests — always mock API calls
- Use the shared `ApiClient` instance passed to tool handlers

### Error Handling
- All tool handlers must catch and handle exceptions gracefully
- Use Pydantic `ValidationError` for input validation errors
- Use custom `ApiError` for API-related failures
- Return `list[TextContent]` with error messages, never raise unhandled exceptions
- Log all errors with appropriate log levels


## Project Overview

This project implements a **Model Context Protocol (MCP) server** written in **Python 3.11+**, designed to run with **Claude Desktop**.

The server acts as a bridge between Claude and the **ISTAT SDMX API** (https://esploradati.istat.it/SDMXWS/rest/), exposing Italian statistical data through MCP tools. It includes a **two-layer cache** (in-memory + persistent) to minimize API calls and store both raw data and associated metadata.

### Key Technologies

- **Transport**: stdio (Claude Desktop default)
- **Language**: Python 3.11+
- **MCP SDK**: [`mcp`](https://github.com/modelcontextprotocol/python-sdk) ≥ 0.9.0
- **HTTP Client**: `httpx` ≥ 0.27.0 (async)
- **XML Parsing**: `lxml` ≥ 5.0.0 (for SDMX XML responses)
- **Memory Cache**: `cachetools` ≥ 5.3.0 (TTL-based in-memory cache)
- **Persistent Cache**: `diskcache` ≥ 5.6.0 (disk-based cache)
- **Retry Logic**: `tenacity` ≥ 8.2.0 (exponential backoff)
- **Validation**: `pydantic` ≥ 2.0.0 (input/output models)
- **Config**: `python-dotenv` ≥ 1.0.0 (environment variables)
- **Territorial Lookup**: `duckdb` ≥ 1.0.0 (local DB for REF_AREA code resolution)

---

## Repository Structure

```
.
├── src/
│   └── [server_name]/
│       ├── __init__.py
│       ├── server.py          # MCP server init, tool/resource registration
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py      # API client wrapper (auth, retries, rate limiting)
│       │   └── models.py      # Pydantic models for API request/response
│       ├── cache/
│       │   ├── __init__.py
│       │   ├── manager.py     # Cache façade — unified get/set/invalidate interface
│       │   ├── memory.py      # In-memory cache (TTL-based, e.g. cachetools)
│       │   └── persistent.py  # Disk/DB cache for data and metadata
│       ├── cli/
│       │   ├── __init__.py
│       │   └── get_concepts_cli.py        # CLI: cerca concept per ID, stampa JSON su stdout
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── discover_dataflows.py      # Dataflow discovery with blacklist filtering
│       │   ├── get_structure.py           # Datastructure definitions
│       │   ├── get_constraints.py         # Constraints + descriptions (3-in-1 tool)
│       │   ├── get_codelist_description.py # Codelist descriptions
│       │   ├── get_concepts.py            # MCP tool: wraps CLI via subprocess
│       │   ├── get_data.py                # Data fetching with blacklist validation
│       │   ├── get_cache_diagnostics.py   # Cache inspection tool
│       │   └── get_territorial_codes.py   # REF_AREA lookup via DuckDB
│       ├── resources/
│       │   ├── __init__.py
│       │   └── istat_lookup.duckdb        # Pre-built territorial hierarchy (read-only)
│       └── utils/
│           ├── __init__.py
│           ├── logging.py     # Structured logging setup
│           ├── validators.py  # Shared input validation helpers
│           └── blacklist.py   # Dataflow blacklist management
├── tests/
│   ├── conftest.py
│   ├── test_blacklist.py                  # Blacklist system tests (12 tests)
│   ├── test_cache.py                      # Cache layer tests (4 tests)
│   ├── test_client.py                     # API client tests (2 tests)
│   ├── test_get_cache_diagnostics.py      # get_cache_diagnostics tests (3 tests)
│   ├── test_get_concepts.py               # get_concepts tool tests (10 tests)
│   ├── test_get_constraints.py            # get_constraints tool tests (4 tests)
│   ├── test_get_data.py                   # get_data tool tests (21 tests)
│   ├── test_get_territorial_codes.py      # get_territorial_codes tests (13 tests)
│   ├── test_models.py                     # Pydantic model tests (5 tests)
│   └── test_validators.py                 # Validator tests (2 tests)
├── cache/                                  # Runtime cache directory (git-ignored)
├── .env.example
├── pyproject.toml
└── README.md
```

---

## MCP Capabilities Implemented

| Capability | Included | Notes |
|------------|----------|-------|
| Tools      | ✅       | 8 tools: `discover_dataflows`, `get_structure`, `get_constraints`, `get_codelist_description`, `get_concepts`, `get_data`, `get_cache_diagnostics`, `get_territorial_codes` |
| CLI        | ✅       | `istat-get-concepts-cli` — command-line lookup per concept ID (wrappato da `get_concepts`) |
| Resources  | ❌       | Not implemented yet |
| Prompts    | ❌       | Not implemented yet |
| Sampling   | ❌       | Not used |
| Roots      | ❌       | Not used |

---

## Recent Changes (April 2026)

### Refactoring `get_concepts` — CLI + MCP wrapper (April 5-6, 2026)
- **Restructured**: `get_concepts` è ora suddiviso in due livelli:
  - **CLI** (`src/istat_mcp_server/cli/get_concepts_cli.py`): comando standalone `istat-get-concepts-cli <concept_id>`
    - Accetta un `concept_id` come argomento posizionale
    - Controlla la cache persistente (TTL 1 mese) — se mancante, chiama `GET /conceptscheme` e popola la cache
    - Output JSON su stdout: `{"concept_id": "...", "found": true, "name_it": "...", "name_en": "...", "scheme_id": "..."}`
    - Registrato come console script in `pyproject.toml`: `istat-get-concepts-cli`
  - **MCP tool** (`src/istat_mcp_server/tools/get_concepts.py`): wrappa il CLI via `asyncio.create_subprocess_exec`
    - Input: `concept_id` (required), `lang` (`'it'` o `'en'`, default `'it'`)
    - Lancia `python -m istat_mcp_server.cli.get_concepts_cli <concept_id>` come subprocess
    - Legge il JSON di output (equivalente a `bash_tool + jq .name_it`)
    - Ritorna la singola stringa di descrizione come `TextContent`
- **Rimosso**: il vecchio `cli/get_concepts.py` (che stampava tutti gli scheme senza filtro per concept_id)
- **Invariato**: cache chiave `api:conceptschemes:all`, TTL 1 mese, condivisa tra CLI e server MCP

### Token Optimization — `get_data` refactoring (April 3, 2026)
- **Changed**: `get_data` no longer calls `handle_get_constraints` internally
  - Previous: invoked the full `handle_get_constraints` tool (loaded all codelist descriptions, serialized to JSON, then re-deserialized)
  - Now: calls `get_cached_constraints()` directly to read only the raw `ConstraintInfo` model (dimension order + TIME_PERIOD range) — no codelist descriptions loaded
  - New function `_extract_dimension_order(ConstraintInfo)` reads the Pydantic model directly without JSON roundtrip
- **Changed**: `get_data` now caches the processed TSV result instead of raw SDMX-XML
  - `_fetch_parse_filter()` inner function: fetch XML → parse to TSV → filter by time period — cached as a unit
  - Cache hits return ready-to-use TSV with no re-parsing
- **Cache TTL for observed data**: updated default from 1 hour → **24 hours** (86400 seconds)
- **Files changed**: `src/istat_mcp_server/tools/get_data.py`

### Tool 8: `get_territorial_codes` (March 2026)
- **Added**: New MCP tool for resolving ISTAT REF_AREA codes from territory names
  - Backed by a pre-built DuckDB file: `src/istat_mcp_server/resources/istat_lookup.duckdb`
  - Contains full Italian territorial hierarchy: italia → ripartizione → regione → provincia → comune
  - Supports queries by: level, name (substring), region, province, capoluogo flag
  - Read-only access; no API calls — pure local lookup
  - Override DB path via `ISTAT_DB_PATH` environment variable
- **Files**: `src/istat_mcp_server/tools/get_territorial_codes.py`
- **Data source**: `resources/build_territorial_subdivisions.py` (offline script)
- **Tests**: 13 tests in `tests/test_get_territorial_codes.py`

### Get Constraints Tool (March 14, 2026)
- **Added**: New MCP tool `get_constraints` that combines three data sources in one call
  - Fetches availableconstraint endpoint (valid values per dimension)
  - Internally calls get_structure (dimension-to-codelist mapping)
  - Internally calls get_codelist_description for each dimension (IT/EN descriptions)
  - Returns complete JSON with dimensions, codelists, codes, and descriptions
  - Cache TTL: 1 month for all components
  - Special handling for TIME_PERIOD dimension (StartPeriod/EndPeriod)
  - Maintains dimension order from datastructure
- **Files**: `src/istat_mcp_server/tools/get_constraints.py` (handler)
- **Models**: `DimensionConstraintWithDescriptions`, `TimeConstraintOutput`, `ConstraintsOutput`
- **Tests**: 4 comprehensive tests added

### Dataflow Blacklist System (March 13, 2026)
- **Added**: Filter out specific dataflows from all queries
  - Environment variable: `DATAFLOW_BLACKLIST` (comma-separated list)
  - Module: `src/istat_mcp_server/utils/blacklist.py` with `DataflowBlacklist` class
  - Automatic filtering in `discover_dataflows` tool
  - Validation blocking in `get_data` tool
  - Methods: `is_blacklisted()`, `filter_dataflows()`, `add_to_blacklist()`, `remove_from_blacklist()`
- **Use Cases**: Exclude deprecated/problematic/internal dataflows
- **Tests**: 12 comprehensive tests added
- **Documentation**: `BLACKLIST_GUIDE.md`, updated README.md

### Query String Format Fixes (March 12-13, 2026)
- **Fixed**: ISTAT API query construction for empty dimensions
  - Empty dimensions now represented with `.` between separators (not `...`)
  - Added conditional `/ALL/` suffix based on dimension path presence
  - Example: `/data/{id}/{dim1.dim2.}/ALL/` instead of `/data/{id}/{dim1.dim2...}/ALL/`

### Empty Dimension Filtering (March 13, 2026)
- **Implemented**: Automatic filtering of empty dimensions in `fetch_datastructure()`
  - Location: `src/istat_mcp_server/api/client.py` line ~296
  - Code: `if not dimension: continue` in dimension parsing loop
  - Prevents malformed queries with excessive empty dimensions

### Enhanced Logging (March 13, 2026)
- **Added**: Comprehensive logging for MCP tool calls and HTTP requests
  - Tool calls: JSON arguments, execution time, response size
  - HTTP requests: → (request), ← (response), ✗ (error) symbols with timing
  - Location: `src/istat_mcp_server/server.py` and `src/istat_mcp_server/api/client.py`
  - Documentation: `LOGGING_FORMAT.md`

### Code Optimizations (March 12-13, 2026)
- **Optimized**: Reduced ~80 lines across multiple files
  - List comprehensions for filtering operations
  - Dict comprehensions for mappings
  - `next()` instead of loops for single-item searches
  - Context managers for diskcache access
  - Inline cache key construction

### Testing

**Total**: 76 pytest tests (0.20s)

**Test Breakdown**:
- 12 tests for blacklist system (`test_blacklist.py`)
- 4 tests for cache manager (`test_cache.py`)
- 2 tests for API client (`test_client.py`)
- 3 tests for cache diagnostics (`test_get_cache_diagnostics.py`)
- 4 tests for get_constraints tool (`test_get_constraints.py`)
- 10 tests for get_concepts tool (`test_get_concepts.py`)
- 21 tests for get_data tool (`test_get_data.py`)
- 13 tests for get_territorial_codes tool (`test_get_territorial_codes.py`)
- 5 tests for Pydantic models (`test_models.py`)
- 2 tests for validators (`test_validators.py`)

---

## Known Issues

### Claude Desktop Configuration Management

**Issue**: Claude Desktop rewrites `claude_desktop_config.json` on startup, removing the `mcpServers` section.

**Impact**: The ISTAT MCP server fails to load automatically when Claude Desktop starts.

**Status**: Active investigation. Server code works correctly (verified by manual testing).

**Workarounds**:
1. **Manual Configuration Scripts**:
   - `setup_claude_config.ps1` - Configure file before starting Claude Desktop
   - `verify_claude_config.ps1` - Verify configuration after startup
   - `CONFIGURAZIONE_CLAUDE.md` - Complete setup guide
   - `TROUBLESHOOTING_CLAUDE.md` - Detailed troubleshooting

2. **Manual Server Testing**:
   ```powershell
   .venv\Scripts\python.exe -m istat_mcp_server
   ```

**Evidence**: Server logs show successful operation on previous runs:
- Log file: `%APPDATA%\Claude\logs\mcp-server-istat.log` (5.2 MB)
- Last successful run: March 12, 2026 21:50
- All tools executed successfully in previous sessions

**Investigation Needed**:
- Check if Claude Desktop has UI for managing MCP servers
- Verify if configuration is stored in SQLite database (`DIPS` file)
- Check if newer Claude Desktop versions support persistent MCP configuration

---

## Tools Reference

All inputs are validated with Pydantic models before the handler runs. All handlers return `list[TextContent]` with JSON-formatted data or error messages.

---

### Tool 1: `discover_dataflows`

**Description**: Discovers available dataflows from the ISTAT SDMX API. Optionally filters results by comma-separated keywords across all metadata fields (id, names, descriptions, datastructure ID). Results are cached for 7 days by default.

**API Endpoint**: `https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1`

**Cache TTL**: 7 days (604800 seconds)

**Input Schema**:
```python
class DiscoverDataflowsInput(BaseModel):
    keywords: str = Field('', description="Comma-separated keywords (e.g., 'population,employment'). Leave empty to return all dataflows.")
```

**Implementation Details**:
- Fetch XML from API endpoint
- Parse with `lxml` and extract dataflow elements
- **Exclude** dataflows with `<common:AnnotationType>NonProductionDataflow</common:AnnotationType>`
- Extract for each dataflow:
  - `id`: from attribute `id`
  - `version`: from attribute `version`
  - `agency`: from attribute `agencyID`
  - `name_it`, `name_en`: from `<common:Name xml:lang="it|en">`
  - `description_it`, `description_en`: from annotation `LAYOUT_DATAFLOW_KEYWORDS` → `<common:AnnotationText xml:lang="it|en">`
  - `last_update`: from annotation `LAST_UPDATE` → `<common:AnnotationTitle>`
  - `id_datastructure`: from `<structure:Structure><Ref id="..."/>`
- Cache the full list with key: `api:dataflows:all`
- If keywords provided, filter cached results by searching in all text fields (case-insensitive)
- Return JSON with structure:
  ```json
  {
    "count": 123,
    "dataflows": [
      {
        "id": "101_1015_DF_DCSP_COLTIVAZIONI_1",
        "name_it": "Superfici e produzione - dati in complesso",
        "name_en": "Areas and production - overall data",
        "description_it": "Tipo di coltivazione+Strutturale...",
        "description_en": "Type of crop+structural...",
        "version": "1.0",
        "agency": "IT1",
        "id_datastructure": "DCSP_COLTIVAZIONI",
        "last_update": "2026-02-13T14:23:41.926Z"
      }
    ]
  }
  ```

**Handler**: `src/istat_mcp_server/tools/discover_dataflows.py::handle_discover_dataflows()`

**Validation**: `utils.validators.validate_keywords()` parses comma-separated keywords into a list

**Blacklist Integration**: 
- Dataflows in the `DATAFLOW_BLACKLIST` environment variable are automatically filtered out
- Blacklist is loaded from `src/istat_mcp_server/utils/blacklist.py`
- Filter applied after keyword matching, before returning results
- Use case: Exclude deprecated, problematic, or internal dataflows from discovery

---

### Tool 2: `get_structure`

**Description**: Gets the data structure definition for a given datastructure ID. Returns the list of dimensions and their associated codelists. Results are cached for 1 month.

**API Endpoint**: `https://esploradati.istat.it/SDMXWS/rest/datastructure/IT1/{id_datastructure}`

**Cache TTL**: 1 month (2592000 seconds)

**Input Schema**:
```python
class GetStructureInput(BaseModel):
    id_datastructure: str = Field(..., description="Datastructure ID to analyze (e.g., 'DCSP_COLTIVAZIONI')")
```

**Implementation Details**:
- Validate input with Pydantic model
- Cache key: `api:datastructure:{id_datastructure}`
- Fetch XML from API endpoint
- Parse `<structure:Dimension>` elements to extract:
  - `id` attribute as `dimension`
  - `<structure:LocalRepresentation><structure:Enumeration><Ref id="..."/>` as `codelist`
- Return JSON structure:
  ```json
  {
    "id_dataflow": "101_1015_DF_DCSP_COLTIVAZIONI_1",
    "id_datastructure": "DCSP_COLTIVAZIONI",
    "dimensions": [
      {
        "dimension": "REF_AREA",
        "codelist": "CL_REF_AREA"
      },
      {
        "dimension": "TIPO_COLT",
        "codelist": "CL_AGRI_MADRE"
      }
    ]
  }
  ```

**Handler**: `src/istat_mcp_server/tools/get_structure.py::handle_get_structure()`

**Model**: `api.models.DatastructureInfo` with `list[DimensionInfo]`

---

### Tool 3: `get_constraints`

**Description**: Gets available constraint values for all dimensions in a dataflow WITH descriptions in Italian and English. This tool combines three data sources in a single call: constraints (valid values), datastructure (dimension-to-codelist mapping), and codelist descriptions (IT/EN labels). This is the recommended approach instead of calling get_structure and get_codelist_description separately. Results are cached for 1 month.

**API Endpoints**: Combines three ISTAT endpoints:
1. `https://esploradati.istat.it/SDMXWS/rest/availableconstraint/{dataflow_id}/all/all?mode=available` - Get valid values
2. `https://esploradati.istat.it/SDMXWS/rest/datastructure/IT1/{id_datastructure}` - Get dimension-to-codelist mapping
3. `https://esploradati.istat.it/SDMXWS/rest/codelist/IT1/{codelist_id}` - Get descriptions (repeated for each dimension)

**Cache TTL**: 1 month (2592000 seconds) for all components

**Input Schema**:
```python
class GetConstraintsInput(BaseModel):
  dataflow_id: str = Field(..., description="Dataflow ID to analyze (e.g., '101_1015_DF_DCSP_COLTIVAZIONI_1')")
```

**Implementation Details**:
- **Step 1**: Fetch dataflow info to get datastructure ID
- **Step 2**: Fetch constraints from availableconstraint endpoint (valid values per dimension)
- **Step 3**: Fetch datastructure to build dimension → codelist mapping (internally calls get_structure)
- **Step 4**: For each dimension, fetch codelist to get IT/EN descriptions (internally calls get_codelist_description)
- All fetches use cache with 1 month TTL → subsequent calls are instant
- Maintains dimension order from datastructure
- Special handling for TIME_PERIOD dimension (StartPeriod/EndPeriod format)
- Return JSON structure with complete information:
  ```json
  {
    "id_dataflow": "101_1015_DF_DCSP_COLTIVAZIONI_1",
    "constraints": [
      {
        "dimension": "TYPE_OF_CROP",
        "codelist": "CL_AGRI_MADRE",
        "values": [
          {
            "code": "APPLE",
            "description_en": "Apples",
            "description_it": "Mele"
          },
          {
            "code": "WHEAT",
            "description_en": "Wheat",
            "description_it": "Grano"
          }
        ]
      },
      {
        "dimension": "TIME_PERIOD",
        "StartPeriod": "2006-01-01T00:00:00",
        "EndPeriod": "2023-12-31T23:59:59"
      }
    ]
  }
  ```

**Handler**: `src/istat_mcp_server/tools/get_constraints.py::handle_get_constraints()`

**Models**: 
- `api.models.ConstraintsOutput` - Top-level output
- `api.models.DimensionConstraintWithDescriptions` - Regular dimension with values and descriptions
- `api.models.TimeConstraintOutput` - TIME_PERIOD dimension
- `api.models.CodeValue` - Individual code with IT/EN descriptions

**Workflow**:
1. User calls `get_constraints` once
2. Tool internally fetches: constraints → structure → codelists (for each dimension)
3. All data cached for 1 month
4. Returns complete information ready for building `get_data` filters
5. Subsequent calls return cached data instantly (no API calls)

**Advantages over manual approach**:
- One call instead of 1 + N calls (N = number of dimensions)
- All descriptions included automatically
- Dimension order preserved from datastructure
- Everything cached together for consistency

---

### Tool 4: `get_codelist_description`

**Description**: Gets Italian and English descriptions for all values in a codelist. Returns code values with their descriptions in both languages. Results are cached for 1 month.

**API Endpoint**: `https://esploradati.istat.it/SDMXWS/rest/codelist/IT1/{codelist_id}`

**Cache TTL**: 1 month (2592000 seconds)

**Input Schema**:
```python
class GetCodelistDescriptionInput(BaseModel):
    codelist_id: str = Field(..., description="Codelist ID to analyze (e.g., 'CL_AGRI_MADRE')")
```

**Implementation Details**:
- Validate input with Pydantic model
- Cache key: `api:codelist:{codelist_id}`
- Fetch XML from API endpoint
- Parse `<structure:Codelist>` and extract `<structure:Code>` elements:
  - `id` attribute as `code`
  - `<common:Name xml:lang="en">` as `description_en`
  - `<common:Name xml:lang="it">` as `description_it`
- Return JSON structure:
  ```json
  {
    "id_codelist": "CL_AGRI_MADRE",
    "values": [
      {
        "code": "T00",
        "description_en": "Total",
        "description_it": "Totale"
      },
      {
        "code": "CEREALS",
        "description_en": "Cereals",
        "description_it": "Cereali"
      }
    ]
  }
  ```

**Handler**: `src/istat_mcp_server/tools/get_codelist_description.py::handle_get_codelist_description()`

**Model**: `api.models.CodelistInfo` with `list[CodeValue]`

---

### Tool 5: `get_data`

**Description**: Fetches statistical data from an ISTAT dataflow and returns it as a TSV (tab-separated) table. Supports filtering by dimensions (respecting the order from datastructure), time periods, and detail level. Internally reads only the raw constraints (dimension order + TIME_PERIOD range) from cache — codelist descriptions are NOT loaded, keeping this call lightweight. The processed TSV is cached directly, so cache hits return the ready-to-use table with no re-parsing. Results are cached for 24 hours.

**API Endpoint**: `https://esploradati.istat.it/SDMXWS/rest/data/{agency},{id_dataflow},{version}/{dim1.dim2.dim3...}/ALL/?detail=full&startPeriod=YYYY-MM-DD&endPeriod=YYYY-MM-DD`

**Cache TTL**: 24 hours (86400 seconds) — stores processed TSV, not raw XML

**Input Schema**:
```python
class GetDataInput(BaseModel):
    id_dataflow: str = Field(..., description="Dataflow ID to fetch data from (e.g., '22_315_DF_DCIS_POPORESBIL1_2')")
    dimension_filters: dict[str, list[str]] | None = Field(
        None,
        description="Optional filters for dimensions. Keys are dimension IDs, values are lists of codes."
    )
    start_period: str | None = Field(None, description="Start period for time filter (e.g., '2024-11-01')")
    end_period: str | None = Field(None, description="End period for time filter (e.g., '2025-11-30')")
    detail: str = Field('full', description="Detail level: 'full', 'dataonly', 'serieskeysonly', or 'nodata'")
```

**Implementation Details**:
- Validate input with Pydantic model and `utils.validators.validate_dataflow_id()`
- **Step 1**: Get dataflow info from cache to extract `agency`, `version`, and `id_datastructure`
- **Step 2**: Read raw constraints via `get_cached_constraints()` — extracts dimension order and TIME_PERIOD range using `_extract_dimension_order(ConstraintInfo)`. Does NOT load codelist descriptions (only needed by `get_constraints`).
- **Step 3**: Determine start/end periods (from user input or last available year from TIME_PERIOD)
- **Step 4**: Map user-provided dimension filters to the correct order from constraints
- **Step 5**: Build cache key and call `_fetch_parse_filter()` inner function:
  - Fetch SDMX-XML from API
  - Parse with `parse_sdmx_to_table()` → TSV string
  - Apply `filter_tsv_by_time_period()` (workaround for ISTAT endPeriod+1 bug)
  - Cache the final TSV (cache hits skip all XML processing)
- **Step 6**: Append curl command and CSV URL via `_build_curl_info()`

**Example Query Construction**:

For dataflow `22_315_DF_DCIS_POPORESBIL1_2` with dimensions `[FREQ, REF_AREA, INDICATOR]`:

- **All data**: `data/IT1,22_315_DF_DCIS_POPORESBIL1_2,1.0/../ALL/?detail=full`
- **Monthly, Italy only**: `data/IT1,22_315_DF_DCIS_POPORESBIL1_2,1.0/M.IT./ALL/?detail=full`
- **Monthly, Italy or France, all indicators**: `data/IT1,22_315_DF_DCIS_POPORESBIL1_2,1.0/M.IT+FR./ALL/?detail=full`
- **With time filter**: `data/IT1,22_315_DF_DCIS_POPORESBIL1_2,1.0/M.IT./ALL/?detail=full&startPeriod=2024-11-01&endPeriod=2025-11-30`

**Response Format**: TSV table with columns: `DATAFLOW`, dimension columns (in datastructure order), `TIME_PERIOD`, `OBS_VALUE`, and any observation attributes. Followed by a markdown section with the CSV URL and curl command to reproduce the query.

**Handler**: `src/istat_mcp_server/tools/get_data.py::handle_get_data()`

**Input Model**: `api.models.GetDataInput`

**API Method**: `api.client.ApiClient.fetch_data()` — constructs URL path and query parameters

**Blacklist Integration**:
- Before fetching data, validates that `id_dataflow` is NOT in the blacklist
- If blacklisted, returns error message: "Dataflow {id} is blacklisted and cannot be accessed"
- Blacklist is loaded from `DATAFLOW_BLACKLIST` environment variable

**ISTAT API workaround**: The ISTAT `endPeriod` parameter returns one extra period beyond the requested end. `filter_tsv_by_time_period()` removes these extra rows from the cached TSV.

---

### Tool 8: `get_territorial_codes`

**Description**: Resolves ISTAT REF_AREA codes for Italian territorial units. Queries a pre-built local DuckDB database — no API calls at all. Supports lookup by level (italia, ripartizione, regione, provincia, comune), name (substring, case-insensitive), region, province, and capoluogo flag.

**No API endpoint** — reads from `src/istat_mcp_server/resources/istat_lookup.duckdb` (read-only).

**Cache TTL**: N/A (no external calls; DuckDB query is fast)

**Input Schema**:
```python
# All parameters are optional; at least one must be provided
{
    'level': 'regione',       # one of: italia, ripartizione, regione, provincia, comune
    'name': 'Milano',         # substring match on name_it (case-insensitive)
    'region': 'Lombardia',    # filter by parent region name or REF_AREA code
    'province': 'MI',         # filter comuni by parent province name or code
    'capoluogo': True,        # if True, return only comuni that are capoluogo di provincia
}
```

**Implementation Details**:
- Opens a read-only DuckDB connection to `istat_lookup.duckdb`
- DB path overridable via `ISTAT_DB_PATH` environment variable
- Table: `territorial_subdivisions` — full hierarchy: italia → ripartizione → regione → provincia → comune
- Each row has: `code` (REF_AREA), `name_it`, `level`, `cod_rip`, `den_rip`, `cod_reg`, `den_reg`, `capoluogo_provincia`, `capoluogo_regione`
- Returns only comuni that match all specified filters
- Extra fields `capoluogo_provincia` / `capoluogo_regione` included only for comuni

**Example Output**:
```json
{
  "codes": [
    {"code": "ITC41", "name_it": "Milano", "level": "provincia"},
    {"code": "ITC4C", "name_it": "Monza e della Brianza", "level": "provincia"}
  ]
}
```

**Handler**: `src/istat_mcp_server/tools/get_territorial_codes.py::handle_get_territorial_codes()`

**Data Source**: Built offline by `resources/build_territorial_subdivisions.py` from CL_ITTER107 and ISTAT geo data.

**Tests**: 13 tests in `tests/test_get_territorial_codes.py`

**Use Case**: Always call this tool before `get_data` whenever the user mentions a specific place. Never guess REF_AREA codes.

---

### Tool 6: `get_concepts`

**Description**: Gets the Italian or English description of a single ISTAT SDMX concept by its ID. Internally calls the CLI `get_concepts_cli` via subprocess (bash_tool + jq pattern). Results are cached for 1 month.

**Architecture**: MCP tool → subprocess → CLI (`istat-get-concepts-cli`) → disk cache → ISTAT API (on miss)

**API Endpoint (indirect)**: `https://esploradati.istat.it/SDMXWS/rest/conceptscheme` (called by CLI only on cache miss)

**Cache TTL**: 1 month (2592000 seconds) — chiave `api:conceptschemes:all`, condivisa tra CLI e server

**Input Schema**:
```python
class GetConceptsInput(BaseModel):
    concept_id: str = Field(..., description="Concept ID (e.g. 'AGRIT_AUTHORIZATION')")
    lang: str = Field('it', description="Language: 'it' or 'en'")
```

**Implementation Details**:
- Valida input con `GetConceptsInput`
- Lancia subprocess: `sys.executable -m istat_mcp_server.cli.get_concepts_cli <concept_id>`
- Il CLI controlla la cache; se mancante scarica e persiste tutti gli scheme
- Legge stdout JSON e estrae `name_it` o `name_en` (equivalente a `jq .name_it`)
- Se concept non trovato restituisce messaggio d'errore
- Ritorna la singola descrizione come `TextContent`

**CLI** (`src/istat_mcp_server/cli/get_concepts_cli.py`):
- Invocabile come `istat-get-concepts-cli <concept_id>` (dopo `pip install -e .`)
- Output JSON su stdout:
  ```json
  {"concept_id": "AGRIT_AUTHORIZATION", "found": true,
   "name_it": "Tipo di autorizzazione agrituristica",
   "name_en": "Kind of agri-tourism authorization",
   "scheme_id": "CS_AGRITUR"}
  ```
- Se non trovato: `{"concept_id": "...", "found": false}`

**Handler**: `src/istat_mcp_server/tools/get_concepts.py::handle_get_concepts()`

**Model**: `api.models.ConceptSchemeInfo` / `api.models.ConceptInfo` (usati dal CLI)

**Use Cases**:
- Capire il significato semantico di un dimension ID
- Tradurre codici SDMX in descrizioni leggibili (IT/EN)
- Usato da Claude per disambiguare concetti senza caricare tutti gli scheme in contesto

---

### Tool 7: `get_cache_diagnostics`

**Description**: Debug tool to inspect cache status and performance. Returns statistics about memory and persistent cache layers, including hit rates, item counts, and storage information. Useful for troubleshooting caching issues and monitoring performance.

**No API Endpoint**: This tool only inspects local cache state, does not call ISTAT API.

**Input Schema**:
```python
# No input parameters - returns current cache diagnostics
```

**Implementation Details**:
- Query memory cache (cachetools.TTLCache) for:
  - Current item count
  - Maximum size
  - List of all cached keys
  - TTL configuration
- Query persistent cache (diskcache.Cache) for:
  - Number of items stored
  - Total disk size (bytes)
  - Cache directory path
  - List of all cached keys
- Return JSON structure:
  ```json
  {
    "memory_cache": {
      "type": "TTLCache",
      "current_size": 42,
      "max_size": 512,
      "ttl_seconds": 300,
      "keys": [
        "api:dataflows:all",
        "api:datastructure:DCSP_COLTIVAZIONI",
        "api:codelist:CL_AGRI_MADRE"
      ]
    },
    "persistent_cache": {
      "type": "diskcache",
      "directory": "./cache",
      "item_count": 156,
      "total_size_bytes": 2457600,
      "total_size_mb": 2.34,
      "keys": [
        "api:dataflows:all",
        "api:constraints:101_1015_DF_DCSP_COLTIVAZIONI_1",
        "api:data:22_315_DF_DCIS_POPORESBIL1_2:..."
      ]
    }
  }
  ```

**Handler**: `src/istat_mcp_server/tools/get_cache_diagnostics.py::get_cache_diagnostics_handler()`

**Use Cases**:
- Debug why data seems stale (check if cached version is being used)
- Monitor cache performance (hit rates, storage usage)
- Verify cache configuration is working correctly
- Identify which resources are cached
- Troubleshoot cache-related issues

**Note**: This is a read-only diagnostic tool that does not modify cache state.

---

## Cache Architecture

### Two-Layer Design

The project uses a sophisticated two-layer caching strategy implemented in `src/istat_mcp_server/cache/`:

```
Claude Desktop
      │  MCP stdio
      ▼
┌─────────────────────────────────┐
│      Cache Manager              │
│ (cache/manager.py)              │
│                                 │
│  1. Check MemoryCache           │  ← Fast, in-process, TTL: 5 min (default)
│     (cachetools.TTLCache)       │     Max items: 512 (configurable)
│           │ miss                │
│           ▼                     │
│  2. Check PersistentCache       │  ← Disk-based, survives restarts
│     (diskcache.Cache)           │     TTL: 24h or 1 month (by data type)
│           │ miss                │
│           ▼                     │
│  3. Fetch from ISTAT API        │  ← Rate-limited: 3 calls/min
│     (api/client.py)             │     Retry with backoff
│           │                     │
│           ▼                     │
│     Store in both layers        │
│     Return to Claude            │
└─────────────────────────────────┘
```

### Cache Implementation

**Memory Layer** (`cache/memory.py`):
- Implemented with `cachetools.TTLCache`
- Process lifetime only (cleared on restart)
- Default TTL: 300 seconds (5 minutes)
- Default max size: 512 items
- LRU eviction when full

**Persistent Layer** (`cache/persistent.py`):
- Implemented with `diskcache.Cache`
- Survives server restarts
- Default directory: `./cache`
- TTLs vary by data type:
  - Dataflows list: 7 days (604800 seconds)
  - Datastructures: 1 month (2592000 seconds)
  - Constraints: 1 month
  - Codelists: 1 month
  - Complete metadata: 1 month

**Cache Manager** (`cache/manager.py`):
- Unified interface: `get()`, `set()`, `delete()`, `clear()`
- `get_or_fetch()` method: check cache → fetch from API → populate cache → return
- Automatic population of both layers on cache miss
- Thread-safe operations

### Cache Key Convention

```
{namespace}:{resource_type}:{identifier}[:{variant}]
```

Examples:
- `api:dataflows:all` — Full list of dataflows
- `api:datastructure:DCSP_COLTIVAZIONI` — Datastructure definition
- `api:constraints:101_1015_DF_DCSP_COLTIVAZIONI_1` — Constraints for a dataflow
- `api:codelist:CL_AGRI_MADRE` — Codelist descriptions
- `api:metadata:28_185_DF_DCIS_MIGRAZIONI_2` — Complete metadata
- `api:data:22_315_DF_DCIS_POPORESBIL1_2:M.IT.:2024-11-01_2025-11-30:full` — Actual data with filters

### TTL Configuration

| Data Type | Cache Key Pattern | TTL | Rationale |
|-----------|-------------------|-----|-----------|
| Dataflows list | `api:dataflows:all` | 7 days | List changes occasionally |
| Datastructure | `api:datastructure:*` | 1 month | Structure rarely changes |
| Constraints | `api:constraints:*` | 1 month | Available values stable |
| Codelist | `api:codelist:*` | 1 month | Descriptions rarely change |
| Complete metadata | `api:metadata:*` | 1 month | Composite, very stable |
| Data (TSV) | `api:data:*` | 24 hours | Processed TSV; refreshed daily |

## API Client

The API client in `src/istat_mcp_server/api/client.py` handles all HTTP communication with the ISTAT SDMX API.

### Responsibilities

- **Rate Limiting**: Enforces maximum 3 API calls per 60-second window using `RateLimiter` class
- **Retry Logic**: Automatic retries with exponential backoff (tenacity library)
  - Retries on: `httpx.HTTPStatusError`, `httpx.NetworkError`
  - Max attempts: 3
  - Backoff: exponential (1s, 2s, 4s...)
- **Error Handling**: Custom `ApiError(message, status_code)` exception
- **XML Parsing**: Uses `lxml` to parse SDMX XML responses
- **Async Operations**: All methods are `async` for non-blocking I/O
- **Type Safety**: Returns typed Pydantic models (never raw dicts)

### Key Components

**RateLimiter Class**:
```python
class RateLimiter:
    def __init__(self, max_calls: int = 3, time_window: float = 60.0):
        # Tracks API call timestamps
        # Automatically waits if limit reached
```

**ApiClient Class**:
```python
class ApiClient:
    def __init__(self, base_url: str, timeout: float, max_retries: int):
        self._client = httpx.AsyncClient(timeout=timeout)
        self._rate_limiter = RateLimiter(max_calls=3, time_window=60.0)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    async def _get(self, path: str) -> httpx.Response:
        await self._rate_limiter.acquire()  # Wait if rate limit reached
        response = await self._client.get(url)
        response.raise_for_status()
        return response
    
    async def fetch_dataflows(self) -> list[DataflowInfo]:
        # Calls API and parses XML into Pydantic models
    
    async def fetch_datastructure(self, id_datastructure: str) -> DatastructureInfo:
        # Fetch and parse datastructure XML
    
    async def fetch_constraints(self, dataflow_id: str) -> ConstraintInfo:
        # Fetch and parse constraints XML
    
    async def fetch_codelist(self, codelist_id: str) -> CodelistInfo:
        # Fetch and parse codelist XML
    
    async def fetch_data(
        self,
        id_dataflow: str,
        agency: str,
        version: str,
        ordered_dimension_filters: list[list[str]],
        start_period: str | None = None,
        end_period: str | None = None,
        detail: str = 'full',
    ) -> str:
        # Fetch SDMX-XML from API, parse to TSV, filter by time period
        # Returns processed TSV string (cached directly)
    
    async def close(self) -> None:
        await self._client.aclose()
```

### XML Parsing

All API responses are in SDMX 2.1 XML format. The client uses `lxml.etree` for parsing:

```python
from lxml import etree

root = etree.fromstring(xml_content)

ns = {
    'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
    'structure': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
    'common': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
}

# Extract elements with XPath
dataflow_elems = root.xpath('//structure:Dataflow', namespaces=ns)
name_en = elem.xpath('.//common:Name[@xml:lang="en"]', namespaces=ns)[0].text
```

### Error Handling Pattern

```python
try:
    response = await self._client.get(url)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f'HTTP error {e.response.status_code} for {url}')
    raise ApiError(f'HTTP error: {e.response.status_code}', e.response.status_code) from e
except httpx.NetworkError as e:
    logger.error(f'Network error for {url}: {e}')
    raise ApiError(f'Network error: {e}', 0) from e
```

## Environment Variables

Configuration is managed through environment variables (loaded via `python-dotenv` from `.env` file).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | ❌ | `https://esploradati.istat.it/SDMXWS/rest` | Base URL of the ISTAT SDMX API |
| `API_TIMEOUT_SECONDS` | ❌ | `120` | Default HTTP request timeout in seconds |
| `AVAILABLECONSTRAINT_TIMEOUT_SECONDS` | ❌ | `180` | Timeout for the `availableconstraint` endpoint used by `get_constraints` |
| `API_MAX_RETRIES` | ❌ | `3` | Maximum retry attempts on transient errors |
| `PERSISTENT_CACHE_DIR` | ❌ | `./cache` | Directory for persistent cache files (diskcache) |
| `MEMORY_CACHE_TTL_SECONDS` | ❌ | `300` | TTL for the in-memory cache layer (5 minutes) |
| `DATAFLOWS_CACHE_TTL_SECONDS` | ❌ | `604800` | TTL for cached dataflow lists (7 days) |
| `METADATA_CACHE_TTL_SECONDS` | ❌ | `2592000` | TTL for cached metadata such as constraints, structures, codelists, and concepts (1 month) |
| `OBSERVED_DATA_CACHE_TTL_SECONDS` | ❌ | `86400` | TTL for cached observed data responses (24 hours) |
| `MAX_MEMORY_CACHE_ITEMS` | ❌ | `512` | Maximum items in the in-memory TTL cache |
| `DATAFLOW_BLACKLIST` | ❌ | `''` | Comma-separated list of dataflow IDs to exclude from discovery and data access (e.g., `DF_OLD_1,DF_TEST_2`) |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Environment File Example

Create a `.env` file in the project root (see `.env.example`):

```env
# API Configuration
API_BASE_URL=https://esploradati.istat.it/SDMXWS/rest
API_TIMEOUT_SECONDS=120
AVAILABLECONSTRAINT_TIMEOUT_SECONDS=180
API_MAX_RETRIES=3

# Cache Configuration
PERSISTENT_CACHE_DIR=./cache
MEMORY_CACHE_TTL_SECONDS=300
DATAFLOWS_CACHE_TTL_SECONDS=604800
METADATA_CACHE_TTL_SECONDS=2592000
OBSERVED_DATA_CACHE_TTL_SECONDS=86400
MAX_MEMORY_CACHE_ITEMS=512

# Dataflow Blacklist (comma-separated IDs to exclude)
DATAFLOW_BLACKLIST=149_577_DF_DCSC_OROS_1_1,22_315_DF_DCIS_POPORESBIL1_2

# Logging
LOG_LEVEL=INFO
```

### Usage in Code

```python
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'https://esploradati.istat.it/SDMXWS/rest')
API_TIMEOUT = float(os.getenv('API_TIMEOUT_SECONDS', '30'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

---

## Dataflow Blacklist System

The blacklist system allows filtering out specific dataflows from discovery and preventing data access to problematic or deprecated datasets.

### Configuration

Set the `DATAFLOW_BLACKLIST` environment variable with a comma-separated list of dataflow IDs:

```env
DATAFLOW_BLACKLIST=149_577_DF_DCSC_OROS_1_1,22_315_DF_DCIS_POPORESBIL1_2,DEPRECATED_DF
```

### Implementation

**Module**: `src/istat_mcp_server/utils/blacklist.py`

**Class**: `DataflowBlacklist`

```python
class DataflowBlacklist:
    """Manages a blacklist of dataflow IDs to exclude from queries."""
    
    def __init__(self, blacklisted_ids: list[str] | None = None):
        """Initialize with optional list of IDs."""
        
    @classmethod
    def from_env(cls) -> 'DataflowBlacklist':
        """Load blacklist from DATAFLOW_BLACKLIST environment variable."""
        
    def is_blacklisted(self, dataflow_id: str) -> bool:
        """Check if a dataflow ID is blacklisted."""
        
    def filter_dataflows(self, dataflows: list[DataflowInfo]) -> list[DataflowInfo]:
        """Remove blacklisted dataflows from a list."""
        
    def add_to_blacklist(self, dataflow_id: str) -> None:
        """Add a dataflow ID to the blacklist."""
        
    def remove_from_blacklist(self, dataflow_id: str) -> None:
        """Remove a dataflow ID from the blacklist."""
        
    def get_blacklisted_ids(self) -> list[str]:
        """Get a copy of all blacklisted IDs."""
```

### Integration Points

**1. Tool: `discover_dataflows`**
- Automatic filtering after keyword matching
- Blacklisted dataflows are excluded from results
- Filter applied in `handle_discover_dataflows()` before returning

**2. Tool: `get_data`**
- Validation check before fetching data
- Returns error if dataflow is blacklisted: "Dataflow {id} is blacklisted and cannot be accessed"
- Validation in `handle_get_data()` before API call

### Use Cases

1. **Exclude deprecated datasets**: Old dataflows that should no longer be used
2. **Filter problematic dataflows**: Datasets with known data quality issues
3. **Hide internal/test dataflows**: Non-production dataflows for internal use only
4. **Temporary exclusions**: Dataflows under maintenance or migration

### Testing

The blacklist system has 12 comprehensive tests in `tests/test_blacklist.py`:
- Initialization (empty, with IDs)
- Blacklist checking
- Dataflow filtering
- Adding/removing IDs
- Environment variable loading
- Edge cases (whitespace, duplicates)

### Example Usage

```python
from istat_mcp_server.utils.blacklist import DataflowBlacklist

# Load from environment
blacklist = DataflowBlacklist.from_env()

# Check if dataflow is blacklisted
if blacklist.is_blacklisted('149_577_DF_DCSC_OROS_1_1'):
    return error_response('This dataflow is not available')

# Filter list of dataflows
all_dataflows = api.fetch_dataflows()
available_dataflows = blacklist.filter_dataflows(all_dataflows)
```

---

## Development Guidelines

### Code Organization

**Tool Pattern** — Each tool has its own module in `tools/`:
```
tools/
├── __init__.py
├── discover_dataflows.py       # handle_discover_dataflows()
├── get_structure.py            # handle_get_structure()
├── get_constraints.py          # handle_get_constraints()
├── get_codelist_description.py # handle_get_codelist_description()
├── get_concepts.py             # handle_get_concepts()
├── get_data.py                 # handle_get_data()
├── get_cache_diagnostics.py    # get_cache_diagnostics_handler()
└── get_territorial_codes.py    # handle_get_territorial_codes()
```

Each tool handler follows this signature:
```python
async def handle_tool_name(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
) -> list[TextContent]:
    """Tool description.
    
    Args:
        arguments: Raw arguments dict from MCP
        cache: Cache manager instance
        api: API client instance
        
    Returns:
        List of TextContent with JSON-formatted response or error message
    """
```

### Pydantic Models

All data structures are defined in `api/models.py`:

**Input Models** (for tool arguments):
- `DiscoverDataflowsInput`
- `GetStructureInput`
- `GetCodelistDescriptionInput`
- `GetDataInput`

**Response Models** (for API data):
- `DataflowInfo` → returned by `fetch_dataflows()`
- `DatastructureInfo` → returned by `fetch_datastructure()`
- `CodelistInfo` → returned by `fetch_codelist()`

**Component Models**:
- `DimensionInfo` — dimension + codelist mapping
- `CodeValue` — code with English/Italian descriptions

### Error Handling Pattern

All tool handlers must follow this pattern:

```python
async def handle_my_tool(
    arguments: dict[str, Any],
    cache: CacheManager,
    api: ApiClient,
) -> list[TextContent]:
    try:
        # 1. Validate input with Pydantic
        params = MyToolInput.model_validate(arguments)
        
        # 2. Additional validation if needed
        if not validate_id(params.id):
            return [TextContent(type='text', text=f'Invalid ID: {params.id}')]
        
        # 3. Fetch data (from cache or API)
        data = await cache.get_or_fetch(
            key=f'api:resource:{params.id}',
            fetch_func=lambda: api.fetch_something(params.id),
            persistent_ttl=CACHE_TTL,
        )
        
        # 4. Format response as JSON
        import json
        response_text = json.dumps(
            data.model_dump(),
            indent=2,
            ensure_ascii=False,  # Important for Italian text
        )
        
        return [TextContent(type='text', text=response_text)]
        
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
```

### Adding a New Tool

1. **Create tool module**: `src/istat_mcp_server/tools/my_new_tool.py`
   
2. **Define input model** in `api/models.py`:
   ```python
   class MyNewToolInput(BaseModel):
       param1: str = Field(..., description='Parameter description')
       param2: int = Field(default=10, description='Optional parameter')
   ```

3. **Implement handler** in `tools/my_new_tool.py`:
   ```python
   async def handle_my_new_tool(
       arguments: dict[str, Any],
       cache: CacheManager,
       api: ApiClient,
   ) -> list[TextContent]:
       # Follow error handling pattern above
       ...
   ```

4. **Register in server.py**:
   ```python
   # Import handler
   from .tools.my_new_tool import handle_my_new_tool
   
   # Add to list_tools()
   Tool(
       name='my_new_tool',
       description='Tool description',
       inputSchema={
           'type': 'object',
           'properties': {
               'param1': {'type': 'string', 'description': '...'},
           },
           'required': ['param1'],
       },
   ),
   
   # Add to call_tool()
   if name == 'my_new_tool':
       return await handle_my_new_tool(arguments, cache_manager, api_client)
   ```

5. **Add API method** (if needed) in `api/client.py`:
   ```python
   async def fetch_my_resource(self, resource_id: str) -> MyResourceModel:
       response = await self._get(f'/endpoint/{resource_id}')
       # Parse XML and return Pydantic model
   ```

6. **Write tests** in `tests/test_my_new_tool.py`:
   ```python
   @pytest.mark.asyncio
   async def test_my_new_tool_success(mock_api, cache_manager):
       mock_api.fetch_my_resource.return_value = MyResourceModel(...)
       result = await handle_my_new_tool({'param1': 'test'}, cache_manager, mock_api)
       assert 'expected_value' in result[0].text
   ```

7. **Update this documentation**: Add tool to Tools Reference section above

### Logging

Logging is configured in `utils/logging.py`:

```python
import logging

logger = logging.getLogger(__name__)

# Usage
logger.debug('Detailed diagnostic info')
logger.info('General information')
logger.warning('Warning message')
logger.error('Error message')
logger.exception('Error with traceback')  # Use in except blocks
```

**Log Level Guidelines**:
- `DEBUG`: XML parsing details, cache hits/misses, API response sizes
- `INFO`: Tool calls, cache operations, API calls
- `WARNING`: Recoverable errors, deprecated features
- `ERROR`: API errors, validation failures, unexpected errors
- `EXCEPTION`: Same as ERROR but includes stack trace (use in except blocks)

## Testing

### Test Setup

Development dependencies are installed with:
```bash
pip install -e ".[dev]"
```

This includes:
- `pytest` — test framework
- `pytest-asyncio` — async test support
- `pytest-cov` — coverage reporting
- `pytest-httpx` — HTTP mocking for httpx
- `mypy` — static type checking
- `ruff` — linting and formatting

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_blacklist.py
pytest tests/test_get_constraints.py

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run with coverage HTML report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Structure

```
tests/
├── conftest.py                      # Shared fixtures
├── test_blacklist.py                # Blacklist system tests (12 tests)
├── test_cache.py                    # Cache layer tests (4 tests)
├── test_client.py                   # API client tests (2 tests)
├── test_get_cache_diagnostics.py    # get_cache_diagnostics tests (3 tests)
├── test_get_constraints.py          # get_constraints tool tests (4 tests)
├── test_get_data.py                 # get_data tool tests (21 tests)
├── test_get_territorial_codes.py    # get_territorial_codes tests (13 tests)
├── test_models.py                   # Pydantic model tests (5 tests)
└── test_validators.py               # Validator tests (2 tests)
```

### Test Patterns

**Mock API Calls** — Never hit live endpoints:
```python
@pytest.mark.asyncio
async def test_tool_with_mocked_api(mock_api_client, cache_manager):
    # Setup mock
    mock_api_client.fetch_dataflows.return_value = [
        DataflowInfo(
            id='test_df',
            name_it='Test IT',
            name_en='Test EN',
            # ... other fields
        )
    ]
    
    # Call handler
    result = await handle_discover_dataflows({'keywords': ''}, cache_manager, mock_api_client)
    
    # Assert
    assert 'test_df' in result[0].text
    mock_api_client.fetch_dataflows.assert_called_once()
```

**Test Cache Behavior**:
```python
@pytest.mark.asyncio
async def test_cache_hit(cache_manager, mock_api_client):
    # Pre-populate cache
    cache_manager.set('test_key', 'test_value')
    
    # Call handler (should use cache, not API)
    result = await handle_my_tool({'id': 'test'}, cache_manager, mock_api_client)
    
    # API should not be called
    mock_api_client.fetch_something.assert_not_called()
```

**Test Error Handling**:
```python
@pytest.mark.asyncio
async def test_api_error_handling(cache_manager, mock_api_client):
    # Mock API error
    mock_api_client.fetch_dataflows.side_effect = ApiError('API down', 503)
    
    # Call handler
    result = await handle_discover_dataflows({'keywords': ''}, cache_manager, mock_api_client)
    
    # Should return error message
    assert 'API error 503' in result[0].text
```

**Test Input Validation**:
```python
@pytest.mark.asyncio
async def test_invalid_input(cache_manager, mock_api_client):
    # Call with invalid input
    result = await handle_my_tool({'invalid_field': 'value'}, cache_manager, mock_api_client)
    
    # Should return validation error
    assert 'Invalid input' in result[0].text
```

### Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def cache_manager():
    """Provides a clean CacheManager instance for each test."""
    manager = CacheManager(cache_dir='./test_cache', memory_ttl=60, persistent_ttl=300)
    yield manager
    manager.clear()  # Cleanup

@pytest.fixture
def mock_api_client():
    """Provides a mocked ApiClient."""
    client = AsyncMock(spec=ApiClient)
    return client
```

### Type Checking

```bash
# Check all source files
mypy src/

# Check with strict mode
mypy --strict src/
```

### Linting and Formatting

```bash
# Check code style
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Check formatting without changes
ruff format --check src/ tests/
```

### CI/CD Considerations

When setting up CI (GitHub Actions, etc.):
1. **Never use real API credentials** — use mocks or test fixtures
2. **Cache should use temp directories** — don't pollute CI environment
3. **Run all checks**: pytest, mypy, ruff
4. **Generate coverage reports** for visibility

## Installation & Running

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/istat_mcp_server.git
   cd istat_mcp_server
   ```

2. **Install the package**:
   ```bash
   # Install in development mode
   pip install -e .
   
   # Or with development dependencies
   pip install -e ".[dev]"
   ```

3. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env if you want to customize settings
   ```

4. **Test the server** (manual run):
   ```bash
   # Run server (stdio mode for Claude Desktop)
   python -m istat_mcp_server.server
   
   # Or using the installed command
   istat-mcp-server
   ```

### Claude Desktop Configuration

The server is designed to run with Claude Desktop via the Model Context Protocol.

**Configuration File Location**:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Option 1: Using Python Directly

Edit your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server.server"],
      "env": {
        "PERSISTENT_CACHE_DIR": "C:\\Users\\YourName\\istat_cache",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Important**: 
- Use absolute paths for `PERSISTENT_CACHE_DIR`
- On Windows, use double backslashes `\\` or forward slashes `/` in paths
- Make sure `python` is in your system PATH and points to the environment where you installed the package

#### Option 2: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and environment manager.

```json
{
  "mcpServers": {
    "istat": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:/Users/YourName/istat_mcp_server",
        "-m",
        "istat_mcp_server.server"
      ],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Benefits of uv**:
- Automatic environment isolation
- Faster dependency resolution
- No need to manually activate virtual environments

#### Option 3: Using Virtual Environment

If you're using a virtual environment:

**macOS/Linux**:
```json
{
  "mcpServers": {
    "istat": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["-m", "istat_mcp_server.server"],
      "env": {
        "PERSISTENT_CACHE_DIR": "/absolute/path/to/cache"
      }
    }
  }
}
```

**Windows**:
```json
{
  "mcpServers": {
    "istat": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["-m", "istat_mcp_server.server"],
      "env": {
        "PERSISTENT_CACHE_DIR": "C:\\path\\to\\cache"
      }
    }
  }
}
```

### Verifying Installation

1. **Restart Claude Desktop** after updating the configuration

2. **Check if tools are available**:
   - Open Claude Desktop
   - Look for the MCP tools icon (hammer/wrench icon)
   - You should see 7 tools: `discover_dataflows`, `get_structure`, `get_constraints`, `get_codelist_description`, `get_concepts`, `get_data`, `get_cache_diagnostics`

3. **Test a simple query**:
   ```
   Use the discover_dataflows tool to find dataflows about "population"
   ```

4. **Test data retrieval**:
   ```
   First discover a dataflow, then use get_data to fetch actual data
   ```

4. **Test data retrieval**:
   ```
   First discover a dataflow, then use get_data to fetch actual data
   ```

4. **Check logs**:
   - Set `LOG_LEVEL=DEBUG` in configuration for detailed logs
   - Logs appear in Claude Desktop's developer console (if available)
   - Or check your system's logs for stderr output

## Debugging

### MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is an interactive tool for testing MCP servers:

```bash
# Install MCP Inspector (requires Node.js)
npm install -g @modelcontextprotocol/inspector

# Run server with inspector
npx @modelcontextprotocol/inspector python -m istat_mcp_server.server
```

This opens a web interface where you can:
- See all available tools
- Call tools with custom arguments
- View responses in real-time
- Inspect errors and logs

### Verbose Logging

Enable debug logging for detailed information:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG  # macOS/Linux
set LOG_LEVEL=DEBUG     # Windows CMD
$env:LOG_LEVEL="DEBUG"  # Windows PowerShell

# Run server
python -m istat_mcp_server.server
```

Debug logs include:
- API URLs being called
- Cache hits/misses
- XML parsing details
- Rate limiter state
- Retry attempts

### Manual Testing

Test individual tools directly:

```python
import asyncio
from istat_mcp_server.api.client import ApiClient
from istat_mcp_server.cache.manager import CacheManager
from istat_mcp_server.tools.discover_dataflows import handle_discover_dataflows

async def test():
    api = ApiClient(base_url='https://esploradati.istat.it/SDMXWS/rest')
    cache = CacheManager(cache_dir='./test_cache')
    
    result = await handle_discover_dataflows({'keywords': 'population'}, cache, api)
    print(result[0].text)
    
    await api.close()
    cache.close()

asyncio.run(test())
```

### Inspecting Cache

View cache contents:

```python
# Python script to inspect cache
import diskcache
import json

cache_dir = './cache'
cache = diskcache.Cache(cache_dir)

print(f'Cache contains {len(cache)} entries')
print('\nKeys:')
for key in cache:
    value = cache[key]
    print(f'  {key}: {str(value)[:100]}...')
```

Or use the included utility:

```bash
# View cache contents
python view_cache.py
```

### Common Issues

**Problem**: Tools not appearing in Claude Desktop
- **Solution**: Check Claude Desktop config file syntax (valid JSON)
- **Solution**: Restart Claude Desktop completely
- **Solution**: Verify Python path is correct and package is installed

**Problem**: API rate limit errors
- **Solution**: Wait 60 seconds between test runs
- **Solution**: Check rate limiter logs (`LOG_LEVEL=DEBUG`)
- **Solution**: Cached data should prevent most API calls

**Problem**: Cache not persisting
- **Solution**: Check `PERSISTENT_CACHE_DIR` path exists and is writable
- **Solution**: Check disk space
- **Solution**: Look for permission errors in logs

**Problem**: XML parsing errors
- **Solution**: Check API is returning valid XML
- **Solution**: Enable debug logging to see raw XML
- **Solution**: ISTAT API may be down or changed format

## Security Considerations

### Environment Variables
- All configuration via environment variables (never hardcoded)
- No API keys required (ISTAT API is public)
- `.env` file should be in `.gitignore` (already configured)

### Cache Directory
- Persistent cache directory may contain sensitive data
- Set appropriate file permissions (not world-readable)
- On shared systems, use user-specific cache directory

### Input Validation
- All tool inputs validated with Pydantic models
- Cache keys sanitized to prevent path traversal (`utils.validators.sanitize_cache_key()`)
- Dataflow IDs validated with regex patterns

### Network Security
- All API calls use HTTPS only
- No authentication credentials transmitted (public API)
- Rate limiting prevents abuse

### Code Execution
- No `eval()` or `exec()` used
- No dynamic code generation
- No shell command execution (except in tests with mocks)

## Known Limitations

### Current Limitations

1. **No authentication**: ISTAT API is public, no auth mechanism implemented
   - Not needed for current use case
   
2. **No streaming**: Large responses loaded fully into memory
   - Future: Implement streaming for very large datasets
   
3. **Single-process cache**: Memory cache not shared across processes
   - Persistent cache is shared, memory cache is per-process
   
4. **No cache invalidation API**: No way to manually invalidate cache via tools
   - Must delete cache directory manually or wait for TTL expiry
   
5. **Raw SDMX-XML output**: `get_data` returns raw XML, no built-in parsing to CSV/JSON
   - Future: Add data transformation and export formats

### ISTAT API Limitations

1. **Rate limiting**: 3 calls per minute (enforced by client)
2. **XML only**: No JSON endpoint available (we parse XML)
3. **Italian focus**: Most data is Italy-specific
4. **SDMX 2.1**: Older SDMX version (not 3.0)

### Future Enhancements

- [x] Add tool to fetch actual data (`get_data`) — ✅ Completed
- [ ] Implement cache invalidation tool
- [ ] Add data parsing and export formats (CSV, JSON, Parquet)
- [ ] Add data transformation capabilities (aggregations, filters)
- [ ] Support for SDMX 3.0 (when available)
- [ ] Distributed cache support (Redis)
- [ ] Streaming for large datasets
- [ ] Interactive dataflow exploration prompts

## References

### Official Documentation

- [MCP Specification](https://spec.modelcontextprotocol.io) — Model Context Protocol spec
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — Official Python SDK
- [Claude Desktop MCP Guide](https://docs.anthropic.com/en/docs/agents-and-tools/mcp) — Anthropic's MCP documentation
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) — Interactive testing tool

### ISTAT API

- [ISTAT SDMX API](https://esploradati.istat.it/SDMXWS/rest/) — Main API endpoint
- [SDMX 2.1 Standard](https://sdmx.org/?page_id=5008) — SDMX specification
- [Italian SDMX Guide](https://ondata.github.io/guida-api-istat/) — Community guide (Italian)

### Python Libraries

- [httpx](https://www.python-httpx.org/) — Async HTTP client
- [Pydantic](https://docs.pydantic.dev/) — Data validation with Python types
- [lxml](https://lxml.de/) — XML processing library
- [diskcache](https://grantjenks.com/docs/diskcache/) — Disk-based cache
- [cachetools](https://cachetools.readthedocs.io/) — In-memory cache utilities
- [tenacity](https://tenacity.readthedocs.io/) — Retry library
- [python-dotenv](https://saurabh-kumar.com/python-dotenv/) — Environment variable management

### Development Tools

- [pytest](https://docs.pytest.org/) — Testing framework
- [mypy](https://mypy.readthedocs.io/) — Static type checker
- [ruff](https://docs.astral.sh/ruff/) — Fast Python linter and formatter
- [uv](https://github.com/astral-sh/uv) — Fast Python package installer

---

## Project Information

---

## Lessons Learned & Best Practices

### ISTAT API Query Construction

**Lesson**: The ISTAT SDMX API has specific requirements for dimension path formatting:
- **Empty dimensions**: Must be represented as `.` between separators, NOT `...` or omitted
- **Path suffix**: Must include `/ALL/` after dimension path
- **Example**: `/data/{id}/{dim1.dim2.}/ALL/` where dim1 and dim2 have values, dim3 is empty

**Implementation**:
```python
# In client.py fetch_data()
dim_path = '.'.join(ordered_dimension_filters)
path = f'/data/{dataflow_id}/{dim_path}/ALL/' if dim_path else f'/data/{dataflow_id}/ALL/'
```

### Empty Dimension Filtering

**Problem**: Some datastructures returned empty dimension elements, causing malformed queries with excessive dots (e.g., `............/ALL/`).

**Solution**: Filter out empty dimensions during datastructure parsing:
```python
# In client.py fetch_datastructure()
for dim_elem in dimension_elements:
    dimension = dim_elem.get('id', '')
    if not dimension:  # Skip empty dimensions
        continue
    # ... process dimension
```

**Impact**: Prevents 404 errors from malformed query paths.

### Code Optimization Strategies

**Applied optimizations** (~80 lines reduced):
1. **List comprehensions** for filtering operations instead of loops
2. **Dict comprehensions** for key-value mappings
3. **`next()` with default** instead of loops for single-item searches
4. **Context managers** for resource cleanup (diskcache)
5. **Inline cache key construction** instead of separate variables

**Example transformation**:
```python
# Before
dimension_filters = {}
for dim_name, codes in filters.items():
    dimension_filters[dim_name] = codes

# After
dimension_filters = {dim: codes for dim, codes in filters.items()}
```

### Enhanced Logging Strategy

**Implementation**: Two-level logging for MCP server:
1. **Tool call logging**: Arguments (JSON), execution time, response size
2. **HTTP request logging**: Request (→), response (←), error (✗) with timing

**Benefits**:
- Easy debugging of tool calls
- Performance monitoring
- Request/response size tracking
- Visual symbols for quick log scanning

**Format**:
```
2026-03-13 07:40:20 - istat_mcp_server.server - INFO - Tool called: get_data
2026-03-13 07:40:20 - istat_mcp_server.api.client - INFO - → GET /rest/data/...
2026-03-13 07:40:21 - istat_mcp_server.api.client - INFO - ← 200 OK (1.2s, 45KB)
```

### Configuration Management Challenges

**Discovery**: Claude Desktop may rewrite `claude_desktop_config.json` on startup, removing custom server configurations.

**Best practices**:
1. **Always validate JSON** before saving configuration files
2. **Use UTF-8 without BOM** encoding for JSON files
3. **Create backup copies** before modifying configuration
4. **Provide setup scripts** for users to easily reconfigure
5. **Document manual testing** procedures independent of IDE/client
6. **Check logs** in `%APPDATA%\Claude\logs\` for startup issues

**Tools created**:
- `setup_claude_config.ps1` - Pre-startup configuration
- `verify_claude_config.ps1` - Post-startup verification
- `CONFIGURAZIONE_CLAUDE.md` - User guide
- `TROUBLESHOOTING_CLAUDE.md` - Debug procedures

### Testing Best Practices

**Key principles**:
1. **Mock all API calls** in tests - never hit live endpoints
2. **Test edge cases**: empty responses, malformed XML, rate limiting
3. **Verify both cache layers**: memory and persistent
4. **Test error handling paths**: network errors, validation errors, API errors
5. **Use fixtures** for common test data (XML responses, dataflow objects)

**Current status**: 6/6 tests passing, execution time ~0.2s

### Python Modern Features Usage

**Adopted Python 3.11+ features**:
- **Union types with `|`**: `str | None` instead of `Optional[str]`
- **Structural pattern matching**: `match/case` for complex conditionals
- **List comprehensions**: For filtering and transformations
- **Type hints**: Full coverage for function signatures
- **Async/await**: All I/O operations are non-blocking

**Style guide**:
- Single quotes for strings (project standard)
- Format with `ruff` (configured in `pyproject.toml`)
- Google-style docstrings for public interfaces

---

**Version**: 0.1.0  
**License**: MIT  
**Python**: 3.11+  
**MCP Protocol**: 0.9.0+  

**Repository**: [GitHub](https://github.com/yourusername/istat_mcp_server)  
**Issues**: [GitHub Issues](https://github.com/yourusername/istat_mcp_server/issues)  

For questions or contributions, please open an issue on GitHub.

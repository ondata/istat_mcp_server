# ISTAT MCP Server

[English](README.md) | [Italiano](./README_IT.md)

MCP server for accessing Italian statistical data from the ISTAT SDMX API.

## Overview

This Model Context Protocol (MCP) server provides Claude Desktop with access to Italian statistical data from ISTAT (Istituto Nazionale di Statistica) through the SDMX REST API. It implements a two-layer caching mechanism to minimize API calls and provides seven tools for discovering, querying, and retrieving statistical data.

## Features

- **9 MCP Tools** for data discovery and retrieval:
  - `discover_dataflows` - Find available datasets by keywords (with blacklist filtering)
  - `get_structure` - Get dimension definitions and codelists for a datastructure ID
  - `get_constraints` - Get available constraint values for each dimension with descriptions (combines structure + constraints + codelist descriptions)
  - `get_codelist_description` - Get descriptions in Italian/English for codelist values
  - `get_concepts` - Get semantic definitions of SDMX concepts
  - `get_data` - Fetch actual statistical data in SDMXXML format (with blacklist validation)
  - `get_cache_diagnostics` - Debug tool to inspect cache status
  - `search_constraint_values` - Search codes for a specific dimension (with optional name filter)
  - `get_territorial_codes` - Get ISTAT territorial codes by level (comune, provincia, regione, ripartizione)

- **Recommended Workflow** (simple and efficient):
  1. **Discover**: Use `discover_dataflows` to find the dataflow you're interested in
  2. **Get Complete Metadata**: Use `get_constraints` to see all dimensions with valid values AND descriptions in one call
     - This is the **RECOMMENDED** approach - one call instead of many
     - Internally combines `get_structure` + `get_codelist_description` for all dimensions
     - All data cached for 1 month → subsequent calls are instant
     - Returns complete information ready for building filters in `get_data`
  3. **Fetch Data**: Use `get_data` with the appropriate dimension filters to retrieve actual data
  
  **Alternative workflow** (manual approach):
  - Use `get_structure` with a datastructure ID to see dimensions and their codelists
  - Then call `get_codelist_description` manually for each codelist you need
  - Use `get_concepts` if you need semantic definitions of dimensions/attributes

- **Two-Layer Cache**:
  - In-memory cache (cachetools) for fast access during session
  - Persistent disk cache (diskcache) that survives restarts

- **Rate Limiting**: Maximum 3 API calls per minute with automatic queuing

- **Retry Logic**: Exponential backoff on transient errors

- **Dataflow Blacklist**: Filter out specific dataflows from all queries

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd istat_mcp_server
```

2. Create a virtual environment and install dependencies (Python >=3.11 required):

**With uv (recommended):**
```bash
uv sync
```
`uv sync` automatically creates a `.venv` directory and installs all dependencies into it. To run commands manually, activate it first:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**With pip:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

3. Create a `.env` file (optional, uses defaults if not present):
```bash
cp .env.example .env
```

Optional: for slow `availableconstraint` responses used by `get_constraints`, set:
```bash
AVAILABLECONSTRAINT_TIMEOUT_SECONDS=180
```

## MCP Client Configuration

This server works with any MCP-compatible client. The sections below cover the most common ones.

[Claude Desktop](#claude-desktop) | [Claude Code](#claude-code) | [Gemini CLI](#gemini-cli) | [VS Code](#vs-code) | [Codex CLI](#codex-cli) | [Claude Desktop on Windows with Python on WSL2](#claude-desktop-on-windows-with-python-on-wsl2)

> In all examples, replace `/path/to/istat_mcp_server` with the actual path to this directory, and `python` with `python3` if needed on your system.

### Claude Desktop

Add to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

### Claude Code

**Add globally** (available in all your projects):

```bash
claude mcp add -s user istat -- python -m istat_mcp_server --cwd /path/to/istat_mcp_server
```

**Add for the current project only** (creates or updates `.mcp.json` in the project folder):

```bash
claude mcp add istat -- python -m istat_mcp_server --cwd /path/to/istat_mcp_server
```

Or add manually to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

> `-s user` makes the server available globally across all your projects. Without it, the server is scoped to the current project only.

### Gemini CLI

**Add globally:**

```bash
gemini mcp add -s user istat -- python -m istat_mcp_server --cwd /path/to/istat_mcp_server
```

Or add manually to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

### VS Code

Add to your User Settings or `.vscode/settings.json`:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

### Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.istat]
command = "python"
args = ["-m", "istat_mcp_server"]
cwd = "/path/to/istat_mcp_server"
```

### Claude Desktop on Windows with Python on WSL2

If you run Claude Desktop on Windows but have Python and this server installed inside WSL2, use `wsl.exe -e` to bridge the two environments. Point to the Python executable inside your virtual environment:

```json
{
  "mcpServers": {
    "istat": {
      "command": "wsl.exe",
      "args": [
        "-e",
        "/home/<your-user>/path/to/istat_mcp_server/.venv/bin/python",
        "-m", "istat_mcp_server"
      ]
    }
  }
}
```

Replace `/home/<your-user>/path/to/istat_mcp_server` with the actual WSL path to this directory.

> **Note:** Claude Code runs natively inside WSL2 and uses the standard configuration above. The `wsl.exe` wrapper is only needed for Claude Desktop running on the Windows side.

## Dataflow Blacklist Configuration

You can exclude specific dataflows from all queries using environment variables. This is useful for filtering out problematic or unwanted datasets.

### Configuration via .env file

Add the `DATAFLOW_BLACKLIST` variable to your `.env` file:

```bash
# Exclude specific dataflows (comma-separated list)
DATAFLOW_BLACKLIST=149_577_DF_DCSC_OROS_1_1,22_315_DF_DCIS_POPORESBIL1_2
```

### Behavior

- **discover_dataflows**: Blacklisted dataflows are automatically filtered out from results
- **get_data**: Attempts to fetch data from blacklisted dataflows will return an error message

### Use Cases

- Exclude deprecated dataflows
- Filter out problematic datasets that cause errors
- Hide internal or test dataflows from users

## Usage Examples

Once configured, you can ask Claude questions like:

**Step 1: Discover dataflows**
- "Show me all available dataflows about population"
- "Find dataflows related to agriculture"

**Step 2: Get complete constraint information (RECOMMENDED)**
- "Get constraints for dataflow 101_1015_DF_DCSP_COLTIVAZIONI_1"
  - Returns all dimensions with valid values AND Italian/English descriptions
  - One call instead of multiple `get_structure` + `get_codelist_description` calls
  - Everything cached for 1 month

**Step 2 Alternative: Explore structure and codelists manually**
- "Show me the structure of datastructure DCSP_COLTIVAZIONI"
- "Get descriptions for codelist CL_ITTER107 to find Italian regions"
- "Show me all values in codelist CL_AGRI_MADRE for crop types"

**Step 3: Fetch data with filters**
- "Fetch population data for Italy from 2020 to 2023"
- "Get agricultural data for dataflow 101_1015_DF_DCSP_COLTIVAZIONI_1 filtered by REF_AREA=IT and TYPE_OF_CROP=APPLE"

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
ruff format .
```

Check code:
```bash
ruff check .
```

## Project Structure

```
.
├── src/
│   └── istat_mcp_server/
│       ├── __init__.py
│       ├── __main__.py        # Entry point for `python -m istat_mcp_server`
│       ├── server.py          # MCP server initialization
│       ├── api/               # API client and models
│       │   ├── client.py      # HTTP client with rate limiting
│       │   └── models.py      # Pydantic models
│       ├── cache/             # Two-layer cache system
│       │   ├── manager.py     # Cache façade
│       │   ├── memory.py      # In-memory cache
│       │   └── persistent.py  # Disk cache
│       ├── tools/             # MCP tool handlers
│       │   ├── discover_dataflows.py
│       │   ├── get_structure.py
│       │   ├── get_constraints.py
│       │   ├── get_codelist_description.py
│       │   ├── get_concepts.py
│       │   ├── get_data.py
│       │   └── get_cache_diagnostics.py
│       └── utils/             # Utilities
│           ├── logging.py
│           ├── validators.py
│           └── blacklist.py
├── tests/                     # Test suite
├── cache/                     # Runtime cache (git-ignored)
├── log/                       # Log files (git-ignored)
├── .env.example
├── pyproject.toml
└── README.md
```

## Cache Configuration

The server uses a sophisticated two-layer caching strategy:

- **Memory Cache**: Fast in-process cache with 5-minute TTL
- **Persistent Cache**: Disk-based cache with configurable TTLs:
  - Dataflows: 7 days
  - Structures/Codelists: 1 month
  - Data: 1 hour

Relevant `.env` variables:
- `MEMORY_CACHE_TTL_SECONDS=300`
- `DATAFLOWS_CACHE_TTL_SECONDS=604800`
- `METADATA_CACHE_TTL_SECONDS=2592000`
- `OBSERVED_DATA_CACHE_TTL_SECONDS=3600`
- `AVAILABLECONSTRAINT_TIMEOUT_SECONDS=180`

Cache is stored in the `./cache` directory by default.

## Logging and Debugging

The server automatically creates log files in the `./log` directory with the following features:

- **Automatic Rotation**: Log files are rotated when they reach 10MB
- **Retention**: Last 5 log files are kept
- **Dual Output**: Logs are written both to file and stderr (for Claude Desktop logs)

### Log Levels

Control the verbosity via the `LOG_LEVEL` environment variable in `.env`:

```bash
LOG_LEVEL=DEBUG  # Maximum detail for debugging
LOG_LEVEL=INFO   # Default, standard operations
LOG_LEVEL=WARNING # Only warnings and errors
LOG_LEVEL=ERROR  # Only errors
```

### Finding Logs

- **Server Logs**: `./log/istat_mcp_server.log`
- **Claude Desktop Logs**: 
  - Windows: `%APPDATA%\Claude\logs\`
  - macOS: `~/Library/Logs/Claude/`

### Debug Cache Issues

The log file shows:
- Cache directory path at startup
- Cache operations (with DEBUG level)
- API calls and retries
- Tool invocations

Use the `get_cache_diagnostics` tool in Claude Desktop to inspect cache status in real-time.

## API Rate Limiting

The ISTAT SDMX API is rate-limited to 3 calls per minute. The server automatically handles this by queuing requests when the limit is reached.

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or pull request.

## Author

- Vincenzo Patruno: https://www.linkedin.com/in/vincenzopatruno/

## References

- ISTAT SDMX API: https://esploradati.istat.it/SDMXWS/rest/
- Model Context Protocol: https://modelcontextprotocol.io/

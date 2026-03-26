# ISTAT MCP Server - Workflow Skills

## Overview

This document describes the end-to-end workflow for using the ISTAT MCP server effectively to retrieve and analyze statistical data published by ISTAT (Italian National Institute of Statistics).

7 MCP tools available:
1. discover_dataflows - Find datasets by keywords (with blacklist filtering)
2. get_constraints - Retrieve constraints plus structure plus descriptions in one call
3. get_structure - Retrieve dimensions and codelists definitions
4. get_codelist_description - Retrieve IT/EN descriptions for codelist values
5. get_concepts - Retrieve semantic definitions of SDMX concepts
6. get_data - Retrieve statistical observations in SDMX XML format
7. get_cache_diagnostics - Debug tool to inspect cache status

## Complete Workflow

### Step 1: Identify Dataflows

Tool: discover_dataflows

Use this tool to identify ISTAT dataflows that may contain the data you need.

Note: Dataflows in the blacklist (environment variable DATAFLOW_BLACKLIST) are automatically excluded from results.

Example:
```json
{
  "keywords": "employment,labour,work"
}
```

Output: List of dataflows with ID, names, and descriptions in Italian and English.

---

### Step 2: Retrieve Constraints and Descriptions

Tool: get_constraints

Recommended approach: once the dataflow is identified, use this tool to retrieve in a single call:
- Dataflow dimensions (correct order)
- Valid values for each dimension (only values available for that specific dataflow)
- Italian and English descriptions for each value
- Codelist IDs associated with each dimension

Example:
```json
{
  "dataflow_id": "101_1015_DF_DCSP_COLTIVAZIONI_1"
}
```

Advantages:
- Automatic workflow: internally calls get_structure plus get_codelist_description for each dimension
- Smart caching: everything cached for 1 month, follow-up calls are fast
- Complete output: ready to build filters for get_data

Typical output:
```json
{
  "id_dataflow": "101_1015_DF_DCSP_COLTIVAZIONI_1",
  "constraints": [
    {
      "dimension": "FREQ",
      "codelist": "CL_FREQ",
      "values": [
        {
          "code": "A",
          "description_en": "Annual",
          "description_it": "Annuale"
        }
      ]
    },
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
      "EndPeriod": "2026-12-31T23:59:59"
    }
  ]
}
```

If you need the meaning of a specific activity code (for example, wholesale trade of frozen or preserved fish products), use:
```json
{
  "codelist_id": "CL_ATECO_2007"
}
```

Typical get_codelist_description output:
```json
{
  "id_codelist": "CL_ATECO_2007",
  "values": [
    {
      "code": "46382",
      "description_en": "wholesale trade of frozen, deep-frozen, preserved, and dried fish products",
      "description_it": "commercio all'ingrosso di prodotti della pesca congelati, surgelati, conservati, secchi"
    }
  ]
}
```

---

### Step 3: Understand SDMX Concepts (Optional)

Tool: get_concepts

Use this tool to identify concept semantics and understand the meaning of dimensions and attributes used in the dataflow. Call it when you need conceptual clarity about the metadata you are working with.

Example concept:
```json
{
  "id": "NOTE_INFORM_TECH_LEVEL",
  "name_en": "IT level",
  "name_it": "Informatizzazione"
}
```

Output: Contains concept schemes with all concepts and descriptions in English and Italian.

When to use it:
- To understand the meaning of a dimension (for example FREQ equals Frequency)
- To understand statistical concepts used in the ISTAT data warehouse
- For metadata documentation and semantic interpretation

---

### Step 4: Retrieve Observed Data

Tool: get_data

This is the final call to the ISTAT endpoint to retrieve observation values.

#### get_data behavior

Automatic query string construction:
1. Constraint lookup: the tool uses output from get_constraints. If cached, it reuses cache; if not cached, it rebuilds constraints.
2. Limited history by default: if a historical range is not explicitly requested, the tool selects only the latest available year to keep responses smaller.
3. Dimension order: filter order must follow the datastructure order retrieved through get_constraints.
4. Dimension filters: use codes returned by get_constraints. Multiple codes for the same dimension are joined with +.
5. No filter on one dimension: use a single dot . for that dimension slot.

#### Query examples

Query 1 - Monthly resident population time series:
```text
Dataflow 22_315_DF_DCIS_POPORESBIL1_2 filtered on all dimensions:
FREQ=M (Monthly)
REF_AREA=IT (Italy)
DATA_TYPE=DEROTHREAS
SEX=9 (Total)

https://esploradati.istat.it/SDMXWS/rest/data/IT1,22_315_DF_DCIS_POPORESBIL1_2/M.IT.DEROTHREAS.9?detail=full&startPeriod=2019-01-01&endPeriod=2025-11-30
```

Query 2 - Quarterly data with historical range:
```text
Dataflow 149_577_DF_DCSC_OROS_1_1 filtered as:
FREQ=Q (Quarterly)
REF_AREA=. (All values)
DATA_TYPE=. (All values)
ADJUSTMENT=. (All values)
ECON_ACTIVITY_NACE_2007=. (All values)

https://esploradati.istat.it/SDMXWS/rest/data/IT1,149_577_DF_DCSC_OROS_1_1,1.0/Q..../?detail=full&startPeriod=2020-09-01&endPeriod=2023-12-31
```

Query 3 - With dimensionAtObservation:
```text
Dataflow 149_577_DF_DCSC_OROS_1_1 filtered as:
FREQ=Q (Quarterly)
REF_AREA=. (All values)
DATA_TYPE=. (All values)
ADJUSTMENT=. (All values)
ECON_ACTIVITY_NACE_2007=0011+0013+0015

https://esploradati.istat.it/SDMXWS/rest/data/IT1,149_577_DF_DCSC_OROS_1_1,1.0/Q....0011+0013+0015./?detail=full&startPeriod=2020-09-01&endPeriod=2023-12-31
```

#### Input parameters

```json
{
  "id_dataflow": "149_577_DF_DCSC_OROS_1_1",
  "dimension_filters": {
    "FREQ": ["Q"],
    "REF_AREA": ["."],
    "DATA_TYPE": ["."],
    "ADJUSTMENT": ["."],
    "ECON_ACTIVITY_NACE_2007": ["0011", "0013", "0015"]
  },
  "start_period": "2020-09-01",
  "end_period": "2023-12-31",
  "detail": "full"
}
```

---

## End-to-End Use Case: Employment by Sector

### Scenario

We want to analyze employment in Italian manufacturing sectors from 2020 to 2023.

### Step 1: Find the dataflow
```json
{
  "tool": "discover_dataflows",
  "input": {
    "keywords": "employment,hours,worked"
  }
}
```

Result: identify 149_577_DF_DCSC_OROS_1_1 (hours worked by sector).

### Step 2: Retrieve constraints and descriptions
```json
{
  "tool": "get_constraints",
  "input": {
    "dataflow_id": "149_577_DF_DCSC_OROS_1_1"
  }
}
```

Result: one call returns dimensions, valid codes, codelists, and labels (IT/EN), including TIME_PERIOD range.

### Step 3: Retrieve data
```json
{
  "tool": "get_data",
  "input": {
    "id_dataflow": "149_577_DF_DCSC_OROS_1_1",
    "dimension_filters": {
      "FREQ": ["Q"],
      "REF_AREA": ["IT"],
      "DATA_TYPE": ["FT_EMPL_1"],
      "ADJUSTMENT": ["N"],
      "ECON_ACTIVITY_NACE_2007": ["0011", "0013", "0015"]
    },
    "start_period": "2020-01-01",
    "end_period": "2023-12-31",
    "detail": "full"
  }
}
```

Result: data ready for analysis.

---

## Best Practices

1. Cache strategy: metadata (structure, codelists, concepts) is cached for 1 month, dataflows for 7 days, and observed data for 1 hour.
2. Incremental filters: start with fewer filters and add constraints progressively to avoid empty datasets.
3. Time windows: omit start_period and end_period for a quick latest-year pull, specify full ranges for historical analysis.
4. Dimension order: always call get_constraints before get_data to use correct dimension order and valid filter values.
5. Codelists: inspect codelists to pick exact, valid codes.
6. Environment configuration: use `DATAFLOWS_CACHE_TTL_SECONDS`, `METADATA_CACHE_TTL_SECONDS`, `OBSERVED_DATA_CACHE_TTL_SECONDS`, and `AVAILABLECONSTRAINT_TIMEOUT_SECONDS` when runtime behavior needs tuning.

---

## Troubleshooting

Problem: dataset too large
Solution: add more dimension filters or reduce the time range.

Problem: no data returned
Solution: verify that dimension codes exist in the codelist and are compatible.

Problem: wrong dimension order
Solution: check get_constraints output for the correct order.

Problem: malformed query string (404 errors)
Solution: empty dimensions must be represented with . in the path. When a filter exists, keep the trailing dot pattern consistent with dimension slots.

Problem: server not loaded in Claude Desktop
Solution: see the Claude Desktop configuration section below.

---

## Claude Desktop Configuration

### Known issue: configuration file rewritten

Claude Desktop may rewrite %APPDATA%\\Claude\\claude_desktop_config.json at startup and potentially remove the mcpServers section.

### Available scripts

The project includes PowerShell scripts to manage configuration.

1. setup_claude_config.ps1 - Configure the file before launching Claude Desktop.
```powershell
.\setup_claude_config.ps1
```

2. verify_claude_config.ps1 - Verify the configuration after startup.
```powershell
.\verify_claude_config.ps1
```

### Expected configuration

claude_desktop_config.json should contain:
```json
{
  "mcpServers": {
    "istat": {
      "command": "C:\\Users\\patru\\Dropbox\\mcp\\istat_mcp_server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "C:\\Users\\patru\\Dropbox\\mcp\\istat_mcp_server"
    }
  },
  "preferences": {
    "coworkWebSearchEnabled": true,
    "coworkScheduledTasksEnabled": true,
    "ccdScheduledTasksEnabled": true
  }
}
```

### Manual server test

To verify the server works independently from Claude Desktop:
```powershell
cd C:\Users\patru\Dropbox\mcp\istat_mcp_server
.venv\Scripts\python.exe -m istat_mcp_server
```

Expected output:
```text
Starting ISTAT MCP Server on stdio
MCP server configured with 7 tools
```

### Additional documentation

- CONFIGURAZIONE_CLAUDE.md - Full setup and verification guide
- TROUBLESHOOTING_CLAUDE.md - Detailed analysis and alternatives
- LOGGING_FORMAT.md - Implemented advanced logging format

---

## API Reference

- Base URL: https://esploradati.istat.it/SDMXWS/rest
- Format: SDMX 2.1 XML
- Rate limit: 3 calls per minute (handled automatically)
- Cache: automatic multi-layer cache system
- Query format: /data/{dataflow_id}/{dim1.dim2.dim3...}/ALL/?params
- Empty dimensions: represented with . between separators
- Multiple values in one dimension: separated by + (example IT+FR)
- All dimensions must be present in the correct order from get_structure

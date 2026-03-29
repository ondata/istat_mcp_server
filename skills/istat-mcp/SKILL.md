---
name: istat-mcp
description: >
  Workflow guide for querying Italian ISTAT statistical data via this MCP server.
  Use this skill whenever working with ISTAT data, SDMX dataflows, Italian statistics,
  regional/provincial data, unemployment, population, GDP, agriculture, or any other
  ISTAT dataset. Guides the discover -> constraints -> data workflow step by step.
license: MIT
compatibility: Requires the istat MCP server to be running (provides 8 tools for ISTAT SDMX API access).
metadata:
  author: ondata
  version: "1.0"
  repository: https://github.com/ondata/istat_mcp_server
---

# ISTAT MCP Server - Workflow Guide

## Quick Start

Always follow this 3-step workflow:

1. **Discover** the dataflow with `discover_dataflows`
2. **Get metadata** with `get_constraints` (one call returns dimensions + valid codes + descriptions)
3. **Fetch data** with `get_data` using the codes from step 2

## Available Tools

| # | Tool | Purpose |
|---|------|---------|
| 1 | `discover_dataflows` | Find datasets by keywords (with blacklist filtering) |
| 2 | `get_constraints` | Retrieve constraints + structure + descriptions in one call |
| 3 | `get_structure` | Retrieve dimensions and codelists definitions |
| 4 | `get_codelist_description` | Retrieve IT/EN descriptions for codelist values |
| 5 | `get_concepts` | Retrieve semantic definitions of SDMX concepts |
| 6 | `get_data` | Retrieve statistical observations |
| 7 | `get_cache_diagnostics` | Debug tool to inspect cache status |
| 8 | `get_territorial_codes` | Lookup REF_AREA codes by level, name, region, province, or capoluogo |

## Detailed Workflow

### Step 1: Identify Dataflows

Use `discover_dataflows` with comma-separated keywords (Italian or English).

```json
{ "keywords": "employment,labour,work" }
```

**Output**:  list of dataflows with ID, names (IT/EN), and descriptions.

Note: dataflows in the blacklist (env var `DATAFLOW_BLACKLIST`) are automatically excluded.

### Step 2: Retrieve Constraints and Descriptions

Use `get_constraints` with the dataflow ID from step 1. This is the **recommended** approach - one call instead of many.

```json
{ "dataflow_id": "101_1015_DF_DCSP_COLTIVAZIONI_1" }
```

This internally calls `get_structure` + `get_codelist_description` for each dimension. Everything is cached for 1 month.

Output includes:
- Dimension names and order
- Valid codes for each dimension (only values available for that dataflow)
- Italian and English descriptions for each code
- Codelist IDs

**Typical output**:
```json
{
  "id_dataflow": "101_1015_DF_DCSP_COLTIVAZIONI_1",
  "constraints": [
    {
      "dimension": "FREQ",
      "codelist": "CL_FREQ",
      "values": [
        {"code": "A", "description_en": "Annual", "description_it": "Annuale"}
      ]
    },
    {
      "dimension": "TYPE_OF_CROP",
      "codelist": "CL_AGRI_MADRE",
      "values": [
        {"code": "APPLE", "description_en": "Apples", "description_it": "Mele"},
        {"code": "WHEAT", "description_en": "Wheat", "description_it": "Grano"}
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

**Alternative manual approach**: call `get_structure` first, then `get_codelist_description` for each codelist you need.


To explore the values of a specific codelist:
```json
{
  "codelist_id": "CL_ATECO_2007"
}
```
### Step 3: Understand SDMX Concepts (optional)

**Tool**: `get_concepts`

Use this tool to understand the semantics of the dataflow's concepts (dimensions and attributes).

**When to use it**:
- To understand the meaning of a dimension (e.g. FREQ = Frequency)
- To understand the statistical concepts of the ISTAT datawarehouse
- For documentation and semantic understanding of metadata

---

### Step 4: Fetch Data

**Tool**: `get_data`

This tool makes the final call to the ISTAT endpoint to retrieve observations.

#### Rules for building filters

1. **Time periods**: If no historical series is requested, the tool automatically selects
   only the last available year. For historical series, specify `start_period` and `end_period`.

2. **Dimension order**: The order of filters must match the one returned by `get_constraints`.

3. **Dimensions without filter**: Use `.` to indicate "all values".

4. **Multiple filters on a dimension**: Concatenate codes with `+` (OR operator).



Use `get_data` with dimension filters built from step 2 output.

```json
{
  "id_dataflow": "149_577_DF_DCSC_OROS_1_1",
  "dimension_filters": {
    "FREQ": ["Q"],
    "REF_AREA": ["IT"],
    "DATA_TYPE": ["FT_EMPL_1"],
    "ADJUSTMENT": ["N"],
    "ECON_ACTIVITY_NACE_2007": ["0011", "0013", "0015"]
  },
  "start_period": "2020-01-01",
  "end_period": "2023-12-31"
}
```

#### Query examples

**Query 1 — Monthly historical series**:
```json
{
  "id_dataflow": "22_315_DF_DCIS_POPORESBIL1_2",
  "dimension_filters": {
    "FREQ": ["M"],
    "REF_AREA": ["IT"],
    "DATA_TYPE": ["DEROTHREAS"],
    "SEX": ["9"]
  },
  "start_period": "2019-01-01",
  "end_period": "2025-11-30",
  "detail": "full"
}
```

**Query 2 — Quarterly data with sector filter**:
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



Key rules for `get_data`:
- **Dimension order** must follow the order from `get_constraints`
- **Multiple codes** for the same dimension: use an array `["0011", "0013"]`
- **No filter** on a dimension: omit it from `dimension_filters`
- **Default behavior**: if no time range is specified, only the latest available year is returned
- **Rate limit**: the ISTAT API allows max 3 calls per minute (handled automatically)

---
## Complete Use Case: Employment by Sector

### Scenario
Analyze employment in Italian manufacturing sectors from 2020 to 2023.

### Step 1 — Find the dataflow
```json
{
  "keywords": "occupazione,ore,lavorate"
}
```
→ We identify `149_577_DF_DCSC_OROS_1_1`.

### Step 2 — Get constraints
```json
{
  "dataflow_id": "149_577_DF_DCSC_OROS_1_1"
}
```
→ We obtain dimensions, valid codes and time range.

### Step 3 — Understand SDMX Concepts (optional)


### Step 4 — Retrieve data
```json
{
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
```

---

## Best Practices

- **Always use `get_constraints` before `get_data`** to know the correct dimension order
  and available codes.
- **Start with few filters** and add more progressively to avoid empty datasets.
- **For recent data**: omit `start_period`/`end_period` (automatically uses the last year).
- **For historical series**: always specify the full range.
- **Dimensions without filter**: always represent with `.`, never omit.
- **Multiple filters**: concatenate with `+` (e.g. `"ECON_ACTIVITY_NACE_2007": ["0011", "0013"]`).
- **Inspect codelist values** to pick exact, valid codes
- **Cache is your friend**: metadata cached 1 month, dataflows 7 days, data 1 hour

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Dataset too large | Add dimensional filters or reduce the time range |
| No data returned | Verify that codes exist in the codelist and are compatible with each other |
| Wrong dimension order | Check `get_constraints` output for the correct order |
| Malformed query string (404) | Empty dimensions must be `.`; when there is a filter, `.` still follows |

---

## Territorial Codes Lookup

The `get_territorial_codes` tool resolves place names and territorial levels to ISTAT REF_AREA codes. Use it when you need to build dimension filters for `REF_AREA`.

**Parameters:**
- `level`: one of `italia`, `ripartizione`, `regione`, `provincia`, `comune`
- `name`: substring search (case-insensitive) across all levels
- `region`: filter comuni by region name or code
- `province`: filter comuni by province name or code
- `capoluogo`: if `true`, return only capoluoghi di provincia

**Examples:**

```json
{"level": "regione"}
{"name": "Milano"}
{"level": "comune", "region": "Lombardia", "capoluogo": true}
```

The data is stored in a local DuckDB database (`resources/istat_lookup.duckdb`). To rebuild it after ISTAT updates, run:

```bash
python3 resources/build_territorial_subdivisions.py <itter107_json> [comuni_csv]
```

---

## API Reference

- **Base URL**: `https://esploradati.istat.it/SDMXWS/rest`
- **Format**: SDMX 2.1 XML → TSV output
- **Rate Limit**: 3 calls/minute (automatically managed by the MCP server)
- **Cache**: metadata 1 month · dataflow 7 days · observed data 1 hour
- **Query path format**: `/data/{dataflow_id}/{dim1.dim2.dim3...}/ALL/?params`
  - Empty dimensions: `.`
  - Multiple values: `+` (e.g. `IT+FR`)
  - All dimensions must be present in the order from `get_structure`





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

If the query targets a specific territory (region, province, municipality), **start by resolving the territory**:

0. **Resolve territory** with `get_territorial_codes` → get REF_AREA codes
1. **Discover** the dataflow with `discover_dataflows`
2. **Get metadata** with `get_constraints` (one call returns dimensions + valid codes + descriptions)
3. **Fetch data** with `get_data` using the codes from steps 0 and 2

Skip step 0 only when the query is about Italy as a whole (`REF_AREA: IT`).

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

### Step 0: Resolve Territory (when needed)

**Tool**: `get_territorial_codes`

Use this tool **before querying data** whenever the user mentions a specific place, area, or territorial grouping. Never guess REF_AREA codes — always resolve them through this tool.

**When to use it:**
- User mentions a region, province, or municipality by name (e.g. "dati sulla Campania", "province del Veneto")
- User asks about a group of territories (e.g. "regioni del Sud", "capoluoghi di provincia")
- User needs to compare territories (e.g. "Nord vs Sud vs Centro")
- User asks about comuni with specific characteristics (e.g. "capoluoghi della Lombardia")
- The dataflow has a REF_AREA dimension and the query is not about Italy as a whole

**Examples:**

```json
[
  { "level": "regione" },
  { "name": "Milano" },
  { "level": "provincia", "region": "Sicilia" },
  { "level": "comune", "region": "Lombardia", "capoluogo": true }
]
```

The tool contains 9,142 entries with the full Italian territorial hierarchy (italia → ripartizione → regione → provincia → comune) and parent-child relationships. It also flags capoluoghi di provincia and di regione.

Use the returned codes directly in the `REF_AREA` dimension filter of `get_data`.

> For map visualizations, TopoJSON boundaries matching these territorial levels are available — see [Cartographic Resources](#cartographic-resources).

---

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

### Optional: Understand SDMX Concepts

**Tool**: `get_concepts`

Use this tool to understand the semantics of the dataflow's concepts (dimensions and attributes) when the meaning of a dimension is unclear from `get_constraints` output alone.

---

### Step 3: Fetch Data

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

### Step 3 — Retrieve data
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
- **Never guess REF_AREA codes**: always use `get_territorial_codes` to resolve place names to codes. Territory is often the starting point of any ISTAT query.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Dataset too large | Add dimensional filters or reduce the time range |
| No data returned | Verify that codes exist in the codelist and are compatible with each other |
| Wrong dimension order | Check `get_constraints` output for the correct order |
| Malformed query string (404) | Empty dimensions must be `.`; when there is a filter, `.` still follows |
| Don't know the REF_AREA code | Use `get_territorial_codes` with name or level to find the right code |
| Error 500 on a dataflow ID | The ID may be a parent container (e.g. `39_493`). Use `discover_dataflows` to find the sub-dataflows (e.g. `39_493_DF_DCIS_CMORTE1_EV_1`) |

---

## Cartographic Resources

TopoJSON boundary files for map visualizations are available in the repository:

| File | Level |
|---|---|
| [`resources/geo/comuni.topojson`](https://github.com/ondata/istat_mcp_server/tree/main/resources/geo/comuni.topojson) | Comuni |
| [`resources/geo/province.topojson`](https://github.com/ondata/istat_mcp_server/tree/main/resources/geo/province.topojson) | Province / Città metropolitane |
| [`resources/geo/regioni.topojson`](https://github.com/ondata/istat_mcp_server/tree/main/resources/geo/regioni.topojson) | Regioni |

Source: ISTAT administrative boundaries 2026 (generalizzati), EPSG:4326.

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





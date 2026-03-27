---
name: istat-mcp
description: >
  Workflow guide for querying Italian ISTAT statistical data via this MCP server.
  Use this skill whenever working with ISTAT data, SDMX dataflows, Italian statistics,
  regional/provincial data, unemployment, population, GDP, agriculture, or any other
  ISTAT indicator — even when the user doesn't explicitly mention ISTAT or SDMX.
  Triggers on requests like "trova dati ISTAT su X", "disoccupazione per regione",
  "dati popolazione Italia", "statistiche agricoltura", or any query that could be
  answered with official Italian statistical data.
license: MIT
compatibility: Requires the ISTAT MCP server (mcp__istat__* tools).
metadata:
  author: ondata
  version: "1.1"
---

# ISTAT MCP Server — Query Workflow

This MCP server exposes 9 tools to access Italian ISTAT statistical data via the SDMX REST API.
Always follow the **3-step workflow** below. Never skip steps.

---

## Pre-flight check — territory level

> **Do this BEFORE Step 1 if the user mentions a city, municipality, or specific place name.**

When the request contains "città", "comune", or a named city (e.g. "Roma", "Firenze", "Venezia"):

1. Call `get_territorial_codes(level="comune", name="<city>")` → get the **comune** code (e.g. `058091`)
2. After Step 2, verify the code exists: `search_constraint_values(dataflow_id, dimension="REF_AREA", search="058091")`
3. If **absent** → tell the user: *"Il dataflow non ha dati a livello comunale; i dati disponibili sono provinciali. Vuoi procedere?"* Then use the province code.
4. **Never silently fall back to province codes** without informing the user.

This check is **mandatory** — skipping it means returning province data mislabelled as city data.

---

## The 3-Step Workflow

### Step 1 — `discover_dataflows`

Search for relevant dataflows. The tool runs both **semantic search** and **keyword search**
and returns results as markdown with two sections.

Your job: read both sections and pick the most relevant dataflow ID for the user's request.
Prefer dataflows whose `name_it`/`name_en` directly match the topic. When in doubt, check
the top semantic results first, then look for keyword matches that might be more precise.

```
discover_dataflows(keywords="disoccupazione regioni")
```

Parameters:
- `keywords`: free text, Italian or English, can be a full question or a few words

#### Fallback — when results are not relevant

If the top semantic results don't match the user's topic (e.g., names are about unrelated subjects),
**do not stop** — try `discover_dataflows` again with different keywords before concluding that
data doesn't exist. Strategies to try, in order:

1. **Synonyms or related terms** — e.g., if "olio oliva" fails, try "olive", "oleario", "grassi vegetali"
2. **Switch language** — if Italian keywords fail, try English (or vice versa)
3. **Broader category** — e.g., if "olio d'oliva" fails, try "agricoltura", "prodotti alimentari", "agroalimentare"
4. **Different keywords** — think about how ISTAT might classify the topic (e.g., by sector ATECO, by transport mode, by price index)

Only after 2–3 failed `discover_dataflows` attempts with diverse keywords should you conclude
that the data is not available in this MCP server and suggest alternative sources.

#### Use technical prefixes as first keyword

ISTAT dataflow IDs follow a naming convention based on thematic prefixes. **Always start with a technical prefix keyword** rather than a generic description — this hits the keyword search directly and avoids multiple fallback attempts.

| Thematic area | Prefix | Example topic |
|---|---|---|
| Demographic / population structure | `DCIS_` | `DCIS_POPSTRRES` (resident pop.), `DCIS_INDDEMOG` (demographic indicators) |
| Living conditions / labour / poverty | `DCCV_` | `DCCV_TAXDISOCCU` (unemployment), `DCCV_FORZLVDE` (labour force) |
| Agricultural / industrial production | `DCSP_` | crop yields, livestock, industrial output |
| National accounts | `DCCN_` | GDP, value added, quarterly population |
| Health / vital statistics | `DCIS_` | `DCIS_MORTALITA` (mortality), `DCIS_NATM` (births) |

**Rule:** map the user's topic to the most likely prefix, then combine it with a specific term:

```
# User asks about adult population → demographic → DCIS_ + POPSTRRES
discover_dataflows(keywords="DCIS_POPSTRRES")

# User asks about unemployment → living conditions → DCCV_ + TAXDISOCCU
discover_dataflows(keywords="DCCV_TAXDISOCCU")
```

If you don't know the exact suffix, use just the prefix + a key noun (e.g., `DCIS_POP`, `DCCV_DISOC`).
Only fall back to generic Italian/English descriptions if the technical prefix approach yields no results.

#### Generic vs specific dataflow IDs

`discover_dataflows` may return both a **generic ID** (e.g., `29_317`) and one or more **specific IDs**
with a `_DF_` suffix (e.g., `29_317_DF_DCIS_POPSTRCIT1_1`).

**Always prefer the specific `_DF_` variant.** Generic IDs are parent containers that aggregate many
series — calling `get_constraints` or `get_data` on them causes timeouts (180s+).

If only a generic ID appears in the results, run `discover_dataflows` again with more specific keywords
to surface the concrete `_DF_` variant before proceeding.

#### Granularity signals in dataflow names

The dataflow name often contains a suffix that reveals its territorial granularity.
**Read this before selecting a dataflow** — high-granularity dataflows will almost always
timeout when queried at national level.

| Name suffix | Granularity | Timeout risk |
|---|---|---|
| `- comuni` | Municipality-level | Very high — avoid for national queries |
| `- prov.` or `- province` | Province-level | High — use only when provincial detail is needed |
| `- reg.` or `- regioni` | Regional-level | Medium — acceptable for regional breakdowns |
| `Italia, regioni, province` | Multi-level (includes national) | Low — safe for national queries |
| *(no suffix)* | Usually national | Low |

**Rule:** if the user asks for national or aggregate data, always prefer a dataflow whose name
contains "Italia" or has no territorial suffix over one ending in "- comuni" or "- prov.".
When both options appear in `discover_dataflows` results, pick the less granular one first.

### Step 2 — `get_constraints`

**Always verify** the data is available with the desired cut before fetching.
Returns a **compact summary**: for each dimension, the codelist ID and the number of available values,
plus the time range. Full values are cached server-side.

**Always pass only the dimensions you actually need** via the `dimensions` parameter — fetching all
dimensions on complex dataflows often causes timeouts (180s+). In practice you rarely need more than
2–3 dimensions at this stage.

**Do NOT include dimensions for which you already have a default value** — there is no need to verify
them. Specifically:
- **Never include `SEX`** unless the user asked for a breakdown by sex. Default is `9` (total) — apply it directly in `get_data`.
- **Never include `FREQ`** unless the user asked for a specific frequency. Default is `A` (annual) — apply it directly in `get_data`.
- **Never include `TIME_PERIOD`** unless you need to verify coverage. If the user didn't specify a date, apply the default period directly in `get_data` (previous calendar year).

Only request constraints for dimensions whose codes you genuinely need to discover — typically `AGE`
(when filtering by age) and `REF_AREA` (when filtering by territory other than Italy).

```
# User asks: "quanti maggiorenni in Italia?" → only need AGE codes
get_constraints(dataflow_id="29_7_DF_DCIS_POPSTRRES1_1", dimensions=["AGE"])

# User asks: "disoccupazione per regione" → need REF_AREA codes
get_constraints(dataflow_id="151_914_DF_DCCV_TAXDISOCCU1_7", dimensions=["REF_AREA"])
```

What to check:
- **REF_AREA**: is the value_count > 0? Do you need specific territory codes?
- **AGE**: what age group codes are available? (needed when filtering by age)

If the desired cut is not available, go back to Step 1 and try a different dataflow.

### Step 2b — `search_constraint_values` (when you need actual codes)

After `get_constraints` populates the cache, use this to look up specific codes.
Supports optional substring search on code or description.

```
# Get all values for a dimension
search_constraint_values(dataflow_id="41_983_...", dimension="REF_AREA")

# Search by name (case-insensitive substring)
search_constraint_values(dataflow_id="41_983_...", dimension="REF_AREA", search="Palermo")
# → [{"code": "082053", "description_it": "Palermo", "description_en": "Palermo"}]

# Get all SEX codes
search_constraint_values(dataflow_id="151_914_...", dimension="SEX")
# → [{"code": "1", ...maschi}, {"code": "2", ...femmine}, {"code": "9", ...totale}]
```

Use this instead of reading the full constraints output when a dimension has many values (e.g., REF_AREA
with all municipalities). For small dimensions (SEX, FREQ, AGE) you can also read them directly.

**Important limitation:** `search_constraint_values` returns codes available **across the entire dataflow**,
not for a specific combination of other dimensions. A code may appear in the list but return no data
when combined with certain values of other dimensions (e.g., `TP_THOQUIN_EXT` exists for some crops
but not for olive oil `PRESIL`). If `get_data` returns no records despite a seemingly valid filter,
explore which codes actually have data for your specific combination using curl with `lastNObservations=1`:

```bash
# Omit the uncertain dimension (e.g., DATA_TYPE) to discover which values have data
curl -kL -H "Accept: application/vnd.sdmx.data+csv;version=1.0.0" \
  "https://esploradati.istat.it/SDMXWS/rest/data/{dataflow_id}/{FREQ}.{REF_AREA}..{TYPE_OF_CROP}.{DEST}?lastNObservations=1"
# The response shows which DATA_TYPE codes actually exist for that specific combination
```

This is the fastest way to discover valid code combinations without downloading the full dataset.

### Step 3 — `get_data`

Fetch actual data, applying the filters you identified in Step 2.

```
get_data(
  id_dataflow="151_914_DF_DCCV_TAXDISOCCU1_7",
  dimension_filters={
    "REF_AREA": ["ITC1", "ITC4", "ITD3"],   # codes from get_constraints
    "SEX": ["9"],                             # 9 = totale
    "FREQ": ["A"],                            # A = annual
    "DURATION_UNEMPLOYMENT": ["TOTAL"]
  },
  start_period="2020-01-01",
  end_period="2024-12-31"
)
```

Notes:
- `dimension_filters` is a dict mapping dimension IDs → list of code strings
- Omit a dimension to get all its values — **this can produce enormous responses and cause timeouts**
- `start_period` / `end_period` filter the time series

---

## Avoiding Timeouts — Always Filter

The ISTAT API times out (180s) on broad, unfiltered requests. The payload grows multiplicatively
with every dimension you leave open: 20 regions × 3 sexes × 5 age groups × 200 citizenships × 10 years
= millions of cells. Always apply filters.

**Safe defaults when the user hasn't specified a breakdown:**

| Dimension | Safe default | Meaning |
|---|---|---|
| `REF_AREA` | `["IT"]` | Italy total (not regional breakdown) |
| `SEX` | `["9"]` | Both sexes combined |
| `FREQ` | `["A"]` | Annual (not monthly/quarterly) |

**Default territory:** if the user does not specify a territory, always use Italy (`REF_AREA: ["IT"]`).
Do not ask — apply this silently and mention it in the answer.

> **Warning — `IT` is not universal.** Most dataflows use `IT` for the national total, but
> some (e.g., PRA vehicle registry, certain agricultural series) use a different code such as
> `ITTOT`. **Strategy:** always try `REF_AREA: ["IT"]` first. If `get_data` returns a 404 or
> empty result, immediately run `search_constraint_values(dataflow_id="...", dimension="REF_AREA")`
> to discover the correct national code, then retry `get_data` with that code.

**Default period:** if the user does not specify a time range, use the last available year.
Concretely: set `start_period` and `end_period` both to the previous calendar year
(e.g., if today is 2026, use `start_period="2025-01-01"`, `end_period="2025-12-31"`).
Do not ask — apply this silently and mention it in the answer.

Start narrow, then expand if the user asks for more granularity. A fast partial answer
is always better than a timeout.

**Example — generic question → safe first call:**
```
# User asks: "quanti stranieri in Italia per paese di provenienza?"
# Wrong: get_data(id_dataflow="29_317_...", dimension_filters={})  ← TIMEOUT
# Right:
get_data(
  id_dataflow="29_317_DF_DCIS_POPSTRCIT1_1",
  dimension_filters={"REF_AREA": ["IT"], "SEX": ["9"], "FREQ": ["A"]},
  start_period="2022-01-01",
  end_period="2023-12-31"
)
```

---

## Large Responses

`get_data` returns a TSV. When the result set is large, the server truncates the output
and includes a note with the total row count. If truncation occurs:
- The data returned is still valid — just the first N rows
- Ask the user if they want a narrower filter to get the complete dataset
- The full data is cached server-side and can be re-fetched with tighter filters

---

## Territorial Codes — `get_territorial_codes`

> **Mandatory rule:** whenever the user asks for data at a specific geographic level
> (city, province, region), **immediately call `get_territorial_codes(level=..., name=...)`**
> to obtain the correct territorial code. Do this **before** any `search_constraint_values`
> call on the dataflow. Never try to discover territorial codes by searching names inside
> `search_constraint_values` — that approach returns whatever happens to be in the dataflow
> and leads to silently using the wrong geographic level (e.g., province instead of city).

Use this **before Step 3** when the user asks for data by territory and you need REF_AREA codes.

```
# All codes for a level
get_territorial_codes(level="regione")       # 21 regions → ITC1, ITC2, ...
get_territorial_codes(level="provincia")     # all provinces
get_territorial_codes(level="comune")        # all municipalities
get_territorial_codes(level="ripartizione")  # Nord-Ovest, Nord-Est, Centro, Sud, Isole
get_territorial_codes(level="italia")        # national level → IT

# Search by name (substring, case-insensitive)
get_territorial_codes(name="Lombardia")   # → ITC4
get_territorial_codes(name="Torino")      # → search across all levels (returns multiple hits)
```

### Always match the geographic level to user intent

`get_territorial_codes(name="Roma")` returns results across **all levels** (comune, provincia,
regione). The results include codes like `058091` (comune di Roma) and `ITE43` (provincia di Roma).
**Picking the wrong level silently produces incorrect data** — province data passed off as city data.

**Rule: infer the intended level from context, then filter explicitly:**

| User says | Intended level | `get_territorial_codes` call |
|---|---|---|
| "città", "comune", specific city name | `comune` | `get_territorial_codes(level="comune", name="Roma")` |
| "provincia", "province of…" | `provincia` | `get_territorial_codes(level="provincia", name="Roma")` |
| "regione", "region" | `regione` | `get_territorial_codes(level="regione", name="Lazio")` |

**Always pass `level=` explicitly** when searching by name. Do not call
`get_territorial_codes(name="Roma")` without `level=` — the multi-level results
make it ambiguous which code to pick.

> **Anti-pattern — never use `search_constraint_values` to discover territorial codes by name.**
> Calling `search_constraint_values(dataflow_id, dimension="REF_AREA", search="Roma")` returns
> whatever codes are *in the dataflow* that match the string "Roma" — often a **province code**
> (e.g., `ITE43 — Roma`) that looks like the city but is actually the province.
> **Always call `get_territorial_codes(level=..., name=...)` first** to get the correct code,
> then use `search_constraint_values` only to *verify* that specific code exists in the dataflow.

**Then verify the code exists in the dataflow.** After getting the comune code (e.g., `058091`),
run `search_constraint_values(dataflow_id="...", dimension="REF_AREA", search="058091")` to
confirm it appears. If the comune code is absent but the provincia code is present, the dataflow
only has provincial granularity — **tell the user explicitly** before proceeding with province data.

```
# Example: user asks for "città d'arte" → need comune codes
get_territorial_codes(level="comune", name="Roma")
# → {"code": "058091", "name_it": "Roma", ...}

search_constraint_values(dataflow_id="...", dimension="REF_AREA", search="058091")
# If empty → dataflow has no municipality data. Try province code ITE43 and tell the user.
# If found → use "058091" in get_data
```

Cross-reference the returned codes with what `get_constraints` shows under `REF_AREA`
to confirm the territory is available in that specific dataflow.

---

## Supporting Tools

Use these when you need more detail beyond Step 2.

| Tool | When to use |
|---|---|
| `search_constraint_values(dataflow_id, dimension, search)` | Look up codes for a specific dimension (with optional name filter) |
| `get_structure(id_datastructure)` | Get the full list of dimensions for a dataflow's data structure |
| `get_codelist_description(codelist_id)` | Get human-readable descriptions for all codes in a codelist |
| `get_concepts` | Explore concept schemes (rare — only needed for deep metadata) |
| `get_cache_diagnostics` | Debug cache state (not needed for normal queries) |

The `codelist` values come from `get_constraints` output (field `codelist` on each dimension summary).

---

## Rate Limiting

**Never make more than one ISTAT API call every 12 seconds.**

The server has a built-in rate limiter that enforces this pause automatically — if you call
two tools back-to-back, the second one will block until 12 seconds have elapsed since the first.
This is expected behavior, not an error. A typical 3-step workflow (discover → constraints → data)
takes at least 24 seconds of enforced wait time.

Do not retry a call that appears to be hanging — it is likely queued behind the rate limiter.

---

## Common Patterns

### Regional data for all Italy
```
1. discover_dataflows(keywords="tasso disoccupazione regionale")
2. get_constraints(dataflow_id="...")      # confirm REF_AREA has ITC1–ITG2
3. get_territorial_codes(level="regione") # get all 21 region codes
4. get_data(id_dataflow="...", dimension_filters={
     "REF_AREA": ["ITC1","ITC2","ITC3","ITC4","ITD1","ITD2","ITD3","ITD4","ITD5",
                  "ITE1","ITE2","ITE3","ITE4","ITF1","ITF2","ITF3","ITF4","ITF5","ITF6",
                  "ITG1","ITG2"],
     "SEX": ["9"], "FREQ": ["A"]
   })
```

### Filter by sex and age
```
# From get_constraints you know: SEX: 1=maschi, 2=femmine, 9=totale
#                                 AGE: Y15-74, Y15-64, Y20-64
get_data(..., dimension_filters={"SEX": ["2"], "AGE": ["Y15-74"]})
```

### Annual vs quarterly data
```
# FREQ: A=annuale, Q=trimestrale, M=mensile
get_data(..., dimension_filters={"FREQ": ["A"]}, start_period="2015-01-01")
```

### Specific province or city
```
# Step 1: get the code at the RIGHT level (infer from user context)
get_territorial_codes(level="comune", name="Torino")
# → {"code": "001272", "name_it": "Torino", ...}

# Step 2: verify the code exists in the dataflow
search_constraint_values(dataflow_id="...", dimension="REF_AREA", search="001272")
# If found → use "001272" in get_data (municipality data)
# If empty → the dataflow has no municipality data; try the province code
get_territorial_codes(level="provincia", name="Torino")
# → {"code": "ITC11", ...}
search_constraint_values(dataflow_id="...", dimension="REF_AREA", search="ITC11")
# If found → inform user that data is only available at province level, then proceed

get_data(..., dimension_filters={"REF_AREA": ["<verified_code>"]})
```

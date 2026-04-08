# Log

## 2026-04-08

- Add `tests/test_get_concepts.py` — 10 unit tests for `handle_get_concepts` tool (subprocess mocking pattern)
  - Covers: IT/EN description, not-found, subprocess error, non-zero exit, invalid lang, missing concept_id, default lang, fallback to English, invalid JSON output

## 2026-04-05 / 2026-04-06

- Refactor `get_concepts` into two layers:
  - **CLI** `src/istat_mcp_server/cli/get_concepts_cli.py`: standalone command `istat-get-concepts-cli <concept_id>`, JSON output, persistent cache (TTL 1 month)
  - **MCP tool** `src/istat_mcp_server/tools/get_concepts.py`: wraps CLI via `asyncio.create_subprocess_exec`, reads `name_it`/`name_en` from JSON output
- Remove old `cli/get_concepts.py` (printed all schemes, no concept_id filter)
- Register `istat-get-concepts-cli` as console script in `pyproject.toml`
- Cache key `api:conceptschemes:all` shared between CLI and MCP tool

## 2026-04-03

- Refactor `get_data` for token optimization:
  - No longer calls `handle_get_constraints` internally — uses `get_cached_constraints()` directly (no codelist descriptions loaded)
  - New `_extract_dimension_order(ConstraintInfo)` reads Pydantic model directly without JSON roundtrip
  - `_fetch_parse_filter()` caches processed TSV (fetch XML → parse → filter) as a unit — cache hits return ready-to-use TSV
  - Cache TTL for observed data updated: 1 hour → 24 hours (86400 seconds)

## 2026-03-29

- Add `cod_istat`, `den_rip`, `cod_rip` columns to `territorial_subdivisions` DuckDB table
- `cod_istat`: numeric ISTAT code for join with TopoJSON (COD_REG, COD_PROV, PRO_COM_T)
- `den_rip`/`cod_rip`: ripartizione geografica (Nord-ovest, Nord-est, Centro, Sud, Isole)
- Mapping derivato da `resources/geo/unit_territoriali.csv` (NUTS3 2024); match province per nome normalizzato
- 20/20 regioni e 110/110 province matchano con i TopoJSON
- Add `scripts/build_admin_boundaries.sh` to download ISTAT 2026 admin boundaries (comuni, province, regioni) and produce TopoJSON in `resources/geo/`
- Input CRS EPSG:32632; output GeoJSON 4326 singlepart + TopoJSON fedele (no simplification)
- Add `get_territorial_codes` tool (8th tool) with DuckDB backend
- Store territorial data in `resources/istat_lookup.duckdb` (reusable for future lookup tables)
- Include `resources/build_territorial_subdivisions.py` script to rebuild the DB from ISTAT sources
- Add `duckdb` dependency to `pyproject.toml`
- 12 unit tests for territorial codes (level, name, region, province, capoluogo filters)
- Update skill docs with territorial codes workflow note

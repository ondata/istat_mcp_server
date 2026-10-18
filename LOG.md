# Log

## 2026-10-18 (#68 and follow-up)

- #68 (Paolo Valletta): MCP client examples use the venv interpreter (`.venv/bin/python`, `.venv\Scripts\python.exe`), no `--cwd`; copilot guide fixed from `istat_mcp_server.server` (no `__main__`, exits at once) to `istat_mcp_server`; closes #55
- Follow-up to the two Greptile P2 comments on #68, missed before merging: interpreter path quoted in the `claude mcp add` / `gemini mcp add` commands (tested: with a space in the path, unquoted gives `not found`, quoted starts the server); copilot quick start now creates `.venv` (`uv sync`, or `python3 -m venv` + pip) and no longer names `istat-mcp-server`, which is not a console script

## 2026-10-18 (CI rule)

- Ruleset `protect-main` (id 14475862): added required status check `test` (GitHub Actions CI) next to the existing deletion and non-fast-forward rules; no bypass actors, so it applies to admins too and blocks direct pushes to `main`
- Branch does not need to be up to date with `main` before merging (`strict_required_status_checks_policy: false`); Greptile is not required
- Verified: #68 (opened before the CI existed) shows `mergeStateStatus: BLOCKED`

## 2026-10-18 (tests, mcp 2.x)

- `tests/test_http_server.py`: `PERSISTENT_CACHE_DIR` in `tmp_path` too (as in `tests/test_server.py`); before, the 5 HTTP tests touched 3 files in `./cache`, now the full suite touches none
- #70 (mcp 2.x) closed via `@dependabot ignore this major version`; migration tracked in #79

## 2026-10-18 (version)

- `serverInfo.version` was the `mcp` library version (1.30.0): `Server()` now gets `importlib.metadata.version('istat-mcp-server')` (0.1.0), closes #77; test in `tests/test_server.py`, live `initialize` checked

## 2026-10-18 (CI)

- Add `.github/workflows/ci.yml`: `uv sync --all-extras`, `pytest`, `ruff check` on every PR and push to `main`; README/README_IT section on checks before rilascio (= merge into `main`, no versioned releases)

## 2026-10-18 (ruff)

- `ruff check` from 93 errors to 0: `--fix` for 84 (whitespace, import order, unused imports, f-strings, `collections.abc`), the 13 W293 left inside docstrings via `--unsafe-fixes --select W293`, removed unused `error` in `server.py` `call_tool`
- Cause: ruff configured in `pyproject.toml` but never run (no pre-commit, no CI); 88 tests pass

## 2026-10-18

- Bump dependency floors in one change (replaces dependabot #69, #71-#73): pydantic>=2.14.1, python-dotenv>=1.2.4, starlette>=1.8.0, ruff>=0.17.1; lock: starlette 1.9.0, ruff 0.17.1
- Verified: 88 tests pass; `ruff check` reports 93 errors, same count with ruff 0.15.8 (pre-existing)
- Not merged #70 (mcp>=2.3.0,<3): `server.py:100` fails at import, `'Server' object has no attribute 'list_tools'`; needs a dedicated migration

## 2026-10-11

- Merge dependabot #62-#66: lxml>=6.1.3, pydantic>=2.14.0, pytest>=9.1.1, pytest-mock>=3.16.0, build setuptools>=84.0.0
- Dependabot PRs leave `uv.lock` stale: regenerated (lxml 6.1.3, pydantic 2.14.0, pytest-mock 3.16.0); 88 tests pass, `uv build` ok

## 2026-10-10

- Docs (#60): rate limit is 4 calls/min (as in `ApiClient` since f649958) in README, README_IT, SKILL.md, GUIDA_RAPIDA, copilot instructions; `old/` and `PROJECT_STATUS.md` left as they are
- Rewrite `GUIDA_RAPIDA.md`: 8 tools, `get_data` returns TSV, cache TTLs from `server.py`, `uv sync`, generic paths instead of personal ones
- Open: `.env.example` sets `OBSERVED_DATA_CACHE_TTL_SECONDS=3600`, code default is 86400; README_IT does not mention `istat-get-constraints-cli`
- Add `istat-get-constraints-cli <dataflow_id> [--dimension DIM]` (#58, closes #53): same JSON as `get_constraints` on stdout, so long code lists stay out of the LLM context; shared logic in `build_constraints_output`
- Add streamable-HTTP host (`istat-mcp-http`, `http` extra), Dockerfile and Helm chart (#57, closes #56)
  - bearer token compared with `hmac.compare_digest`; chart defaults to 1 replica because ISTAT rate-limits by IP and limiter/cache are per process
  - not verified locally: `helm lint`, `docker build`
- Bump dependency floors in one change (replaces dependabot #48-#52): pydantic>=2.12.5, diskcache>=5.6.3, httpx>=0.28.1, pytest>=9.0.3, mcp>=1.27.0,<2
- `mcp` capped below 2: unbounded `>=1.27.0` resolves to mcp 2.3.0 (major); lock now mcp 1.30.0, pytest 9.1.1
- Verified: 76 tests pass; stdio smoke test (initialize, list_tools, live `get_constraints`/`get_data` on `151_914`)

## 2026-04-11

- Add Astro site in `site/` — single page EN (`/`) and IT (`/it`), design system from `DESIGN.md`
- Add GitHub Actions workflow `deploy-site.yml` (trigger on `site/**`, uses `withastro/action@v3`)
- Local build verified: 2 pages generated

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

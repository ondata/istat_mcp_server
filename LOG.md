# Log

## 2026-03-29

- Add `scripts/build_admin_boundaries.sh` to download ISTAT 2026 admin boundaries (comuni, province, regioni) and produce TopoJSON in `resources/geo/`
- Input CRS EPSG:32632; output GeoJSON 4326 singlepart + TopoJSON fedele (no simplification)
- Add `get_territorial_codes` tool (8th tool) with DuckDB backend
- Store territorial data in `resources/istat_lookup.duckdb` (reusable for future lookup tables)
- Include `resources/build_territorial_subdivisions.py` script to rebuild the DB from ISTAT sources
- Add `duckdb` dependency to `pyproject.toml`
- 12 unit tests for territorial codes (level, name, region, province, capoluogo filters)
- Update skill docs with territorial codes workflow note

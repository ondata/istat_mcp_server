# LOG

## 2026-03-25

- Aggiunto tool MCP `get_territorial_codes`: restituisce codici REF_AREA per livello o nome luogo (anche comuni)
- Creato `resources/territorial_subdivisions.parquet` (115 KB, zstd) — gerarchia completa CL_ITTER107
  - 1 nazione, 5 ripartizioni, 21 regioni, 113 province, 9002 comuni
  - Schema: `code`, `name_it`, `level`, `nuts_level`, `parent_code`
  - Gerarchia navigabile: comune → provincia → regione → ripartizione → italia
  - Creato `resources/build_territorial_subdivisions.py` per ricostruire il file

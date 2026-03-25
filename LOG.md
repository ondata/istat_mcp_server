# LOG

## 2026-03-25

- feat: `territorial_subdivisions.parquet` — aggiunti campi `capoluogo_provincia` e `capoluogo_regione` (bool) per i comuni; fonte: `situas-servizi.istat.it/publish/reportspooljson?pfun=61`; `get_territorial_codes` ora li espone nella risposta
- fix: `client.py` — HTTP 404 con body "NoRecordsFound" ora restituisce messaggio chiaro invece di "API error 404" generico; ISTAT usa 404 per "nessun record trovato", non solo per endpoint mancanti
- fix: `get_data` ignorava tutti i `dimension_filters` — `_extract_constraints_info` leggeva chiave `'constraints'` invece di `'dimensions'` nel JSON di `get_constraints`; l'URL produceva sempre `ALL`
- docs: aggiunta nota in skill `istat-mcp`: `search_constraint_values` mostra codici disponibili nell'intero dataflow, non per combinazioni specifiche — un codice può restituire 0 record se combinato con certi valori di altre dimensioni

## 2026-03-25

- `get_data` ora restituisce in coda url sdmx, curl per CSV e spiegazione dei filtri applicati
- Nuovo tool MCP `search_constraint_values`: cerca valori di una dimensione dalla cache, con filtro substring opzionale
- `get_constraints` ora restituisce sommario compatto (dimension, codelist, value_count) invece dei valori completi
  - Risolve l'errore "result exceeds maximum allowed tokens" su dataflow con molti valori (es. 8127 comuni)
  - I dati completi restano in cache, interrogabili via `search_constraint_values`
- Aggiunti modelli Pydantic: `DimensionConstraintSummary`, `ConstraintsSummaryOutput`, `SearchConstraintValuesInput`

- Aggiunto tool MCP `get_territorial_codes`: restituisce codici REF_AREA per livello o nome luogo (anche comuni)
- Creato `resources/territorial_subdivisions.parquet` (115 KB, zstd) — gerarchia completa CL_ITTER107
  - 1 nazione, 5 ripartizioni, 21 regioni, 113 province, 9002 comuni
  - Schema: `code`, `name_it`, `level`, `nuts_level`, `parent_code`
  - Gerarchia navigabile: comune → provincia → regione → ripartizione → italia
  - Creato `resources/build_territorial_subdivisions.py` per ricostruire il file

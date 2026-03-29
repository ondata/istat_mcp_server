# LOG

## 2026-03-29

- `get_constraints` ora restituisce output compatto (~200 token vs ~14k): solo dimensione, codelist, conteggio valori
- Nuovo tool `search_constraint_values`: cerca codici per testo in una dimensione specifica
- 6 nuovi test per `search_constraint_values`, suite completa 59 test OK
- Issue #31
- Fix `_determine_default_periods`: se EndPeriod >= anno corrente, fallback a anno_corrente - 1 (evita 404)
- Aggiunto campo `type` (`enumerated`/`range`) ai modelli output di `get_constraints` per parsing uniforme
- 5 nuovi test per `_determine_default_periods`, suite completa 53 test OK
- PR #34

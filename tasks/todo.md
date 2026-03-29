# Issue #31: get_constraints compatto + search_constraint_values

## Fase 1: Rendere `get_constraints` compatto

Modifica l'output per restituire solo un riepilogo (dimensione, codelist, conteggio valori) invece di tutti i valori con descrizioni.

- [ ] Aggiungere modelli `CompactDimensionConstraint` e `CompactConstraintsOutput` in `models.py`
- [ ] Modificare `handle_get_constraints` in `get_constraints.py` per restituire output compatto (ma continuare a fare cache completa dei codelist internamente)
- [ ] Aggiornare descrizione tool in `server.py`
- [ ] Aggiornare test in `test_get_constraints.py`

## Fase 2: Nuovo tool `search_constraint_values`

Nuovo tool che cerca valori in una dimensione specifica di un dataflow, filtrando per testo.

- [ ] Aggiungere modello `SearchConstraintValuesInput` in `models.py`
- [ ] Creare `tools/search_constraint_values.py` con handler
- [ ] Registrare tool in `server.py` (schema + handler)
- [ ] Esportare in `tools/__init__.py`
- [ ] Scrivere test in `tests/test_search_constraint_values.py`

## Fase 3: Test e PR

- [ ] Eseguire test completa
- [ ] Branch + PR con riferimento a issue #31

## Domande

- Nessuna

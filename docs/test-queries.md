# Test Queries

Reference queries for debugging and testing the MCP server tools.

## Tasso di disoccupazione - Piemonte (minimale)

Dataflow `151_914` — "Tasso di disoccupazione", dato annuale, una sola regione.

```json
{
  "id_dataflow": "151_914",
  "dimension_filters": {
    "FREQ": ["A"],
    "REF_AREA": ["ITC1"],
    "DATA_TYPE": ["UNEM_R"],
    "SEX": ["9"],
    "AGE": ["Y15-74"],
    "EDU_LEV_HIGHEST": ["99"],
    "CITIZENSHIP": ["TOTAL"],
    "DURATION_UNEMPLOYMENT": ["TOTAL"]
  }
}
```

- **Risultato atteso**: 1 riga, ultimo anno disponibile
- **CSV URL**: `https://esploradati.istat.it/SDMXWS/rest/data/151_914/A.ITC1.UNEM_R.9.Y15-74.99.TOTAL.TOTAL/ALL/?detail=full&startPeriod=2025&endPeriod=2025&format=csv`
- **Utile per**: verificare output base, formato URL CSV/SDMX, filtri dimensionali

## Tasso di disoccupazione - tutte le regioni, ultimi 5 anni

Dataflow `151_914` — serie storica regionale.

```json
{
  "id_dataflow": "151_914",
  "dimension_filters": {
    "FREQ": ["A"],
    "REF_AREA": ["ITC1", "ITC2", "ITC3", "ITC4", "ITD1", "ITD2", "ITD3", "ITD4", "ITD5", "ITDA", "ITE1", "ITE2", "ITE3", "ITE4", "ITF1", "ITF2", "ITF3", "ITF4", "ITF5", "ITF6", "ITG1", "ITG2"],
    "DATA_TYPE": ["UNEM_R"],
    "SEX": ["9"],
    "AGE": ["Y15-74"],
    "EDU_LEV_HIGHEST": ["99"],
    "CITIZENSHIP": ["TOTAL"],
    "DURATION_UNEMPLOYMENT": ["TOTAL"]
  },
  "start_period": "2021",
  "end_period": "2025"
}
```

- **Risultato atteso**: ~110 righe (22 territori x 5 anni)
- **Utile per**: verificare multi-regione, range temporale, dimensione output

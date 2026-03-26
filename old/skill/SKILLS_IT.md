# ISTAT MCP Server - Workflow Skills

## Overview

Questo documento descrive il workflow completo per l'utilizzo efficace del server MCP ISTAT per il recupero e l'analisi dei dati statistici pubblicati da Istat, l'Istituto Nazionale di Statistica.

**7 MCP Tools disponibili**:
1. `discover_dataflows` - Trova dataset tramite keywords (con filtro blacklist)
2. `get_constraints` - Ottiene vincoli + struttura + descrizioni in una chiamata
3. `get_structure` - Ottiene definizioni dimensioni e codelists
4. `get_codelist_description` - Ottiene descrizioni IT/EN per valori codelist
5. `get_concepts` - Ottiene definizioni semantiche concetti SDMX
6. `get_data` - Recupera dati statistici in formato SDMXXML
7. `get_cache_diagnostics` - Tool debug per ispezionare stato cache

## Workflow Completo

### Step 1: Identificare i Dataflow

**Tool**: `discover_dataflows`

Utilizzare questo tool per identificare i dataflow ISTAT che possono contenere i dati cercati.

**Nota**: I dataflow nella blacklist (variabile d'ambiente `DATAFLOW_BLACKLIST`) vengono automaticamente esclusi dai risultati.

**Esempio**:
```json
{
  "keywords": "occupazione,lavoro,impiego"
}
```

**Output**: Lista di dataflow con ID, nomi e descrizioni in italiano e inglese.

---

### Step 2: Ottenere Vincoli e Descrizioni

**Tool**: `get_constraints`

**Approccio consigliato**: Una volta identificato il dataflow, utilizzare questo tool per ottenere in una sola chiamata:
- Le **dimensioni** del dataflow (ordine corretto)
- I **valori validi** per ogni dimensione (solo quelli disponibili per questo dataflow specifico)
- Le **descrizioni** in italiano e inglese per ogni valore
- I **codici delle codelists** associate a ogni dimensione

**Esempio**:
```json
{
  "dataflow_id": "101_1015_DF_DCSP_COLTIVAZIONI_1"
}
```

**Vantaggi**:
- **Workflow automatico**: Internamente chiama `get_structure` + `get_codelist_description` per ogni dimensione
- **Cache intelligente**: Tutto cachato per 1 mese, chiamate successive istantanee
- **Output completo**: Pronto per costruire filtri in `get_data`

**Output tipico**:
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

Per trovare il significato del codice dell'attività di commercio all'ingrosso di prodotti della pesca congelati, surgelati, conservati, secchi:
```json
{
  "codelist_id": "CL_ATECO_2007"
}
```

**Output di get_codelist_description**:
```json
{
  "id_codelist": "CL_ATECO_2007",
  "values": [
    {
      "code": "46382",
      "description_en": "commercio all'ingrosso di prodotti della pesca congelati, surgelati, conservati, secchi",
      "description_it": "commercio all'ingrosso di prodotti della pesca congelati, surgelati, conservati, secchi"
    }
  ]
}
```

---

### Step 3: Comprendere i Concetti SDMX (EVENTUALE)

**Tool**: `get_concepts`

Utilizzare questo tool per identificare la semantica dei concetti del dataflow e comprendere il significato delle dimensioni e degli attributi utilizzati. Può essere chiamato quando si ha necessità di capire la semantica dei concetti su cui si sta lavorando.

**Esempio**:
```json
{"id": "NOTE_INFORM_TECH_LEVEL", 
"name_en": "IT level", 
"name_it": "Informatizzazione"}
```

**Output**: Contiene i concept schemes con tutti i concetti e le loro descrizioni in inglese e italiano.

**Quando usarlo**:
- Per comprendere il significato di una dimensione (es. FREQ = Frequency)
- Per capire i concetti statistici utilizzati nel datawarehouse ISTAT
- Per documentazione e comprensione semantica dei metadati

---

### Step 4: Ottenere i Dati Osservati

**Tool**: `get_data`

Questo tool effettua la chiamata finale all'endpoint ISTAT per richiedere i valori delle osservazioni richieste per costruire la risposta.

#### Comportamento di get_data

**Costruzione automatica della query string**:

Il tool deve accedere all'output costruito con get_constraints. Se è in cache accede direttamente, se non è in cache, chiede a get_constraints di generarlo.

1. **Serie storiche limitate**: Se non viene specificato che è richiesta una serie storica, il tool seleziona **solo l'ultimo anno disponibile** per ridurre le dimensioni della risposta. Le informazioni su startPeriod e endPeriod si trovano associate a "dimension": "TIME_PERIOD"
   - Esempio: `startPeriod=2023&endPeriod=2023`

2. **Ordine delle dimensioni**: L'ordine dei filtri deve rispettare quello della datastructure ottenuta con `get_constraints`.

3. **Filtri del dataflow**: I codici da usare nei filtri sono, per ogni dimensione, quelli dell'output di get_constraints. E' possibile usare più codici per una stessa dimensione concatenandoli con il segno + che sta ad indicare l'operatore logico AND.

4. **Nessun filtro per una singola dimensione**: Se non deve essere utilizzato il filtro per quella dimensione, allora utilizzare il punto da solo . Se è presente un filtro per una dimensione, dovrà essere messo prima del punto. Il numero di punti da utilizzare deve essere pari al numero di dimensioni del dataflow.

#### Esempi di query costruite

**Query 1 - Serie storica mensile della popolazione residente**:
```
Il dataflow 22_315_DF_DCIS_POPORESBIL1_2 viene filtrato su tutte le dimensioni:
FREQ=M (Mensile)
REF_AREA=IT (Italia)
DATA_TYPE=DEROTHREAS (cancellati per altri motivi)
SEX=9 (Totale)

https://esploradati.istat.it/SDMXWS/rest/data/IT1,22_315_DF_DCIS_POPORESBIL1_2/M.IT.DEROTHREAS.9?detail=full&startPeriod=2019-01-01&endPeriod=2025-11-30
```

**Query 2 - Dati trimestrali con serie storica**:
```
Il dataflow 149_577_DF_DCSC_OROS_1_1 viene filtrato sulla dimensione:
FREQ=Q (Trimestrale)
REF_AREA=. (Tutti i valori)
DATA_TYPE=. (Tutti i valori)
ADJUSTMENT=. (Tutti i valori)
ECON_ACTIVITY_NACE_2007=. (Tutti i valori)

https://esploradati.istat.it/SDMXWS/rest/data/IT1,149_577_DF_DCSC_OROS_1_1,1.0/Q..../?detail=full&startPeriod=2020-09-01&endPeriod=2023-12-31
```

**Query 3 - Con dimensionAtObservation**:
```
Il dataflow 149_577_DF_DCSC_OROS_1_1 viene filtrato sulla dimensione:
FREQ=Q (Trimestrale)
REF_AREA=. (Tutti i valori)
DATA_TYPE=. (Tutti i valori)
ADJUSTMENT=. (Tutti i valori)
ECON_ACTIVITY_NACE_2007=0011+0013+0015 (totale servizi (g, h, k, 58 , 61-63, 70-74)+TOTALE SERVIZI DI MERCATO (g-n)+>TOTALE INDUSTRIA E SERVIZI (b-n))

https://esploradati.istat.it/SDMXWS/rest/data/IT1,149_577_DF_DCSC_OROS_1_1,1.0/Q....0011+0013+0015./?detail=full&startPeriod=2020-09-01&endPeriod=2023-12-31
```

#### Input Parameters

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

---

## Caso d'Uso Completo: Analisi Occupazione per Settore

### Scenario
Vogliamo analizzare l'occupazione nei settori manifatturieri italiani dal 2020 al 2023.

### Passo 1: Trovare il dataflow
```json
{
  "tool": "discover_dataflows",
  "input": {"keywords": "occupazione,ore,lavorate"}
}
```

Risultato: Identifichiamo `149_577_DF_DCSC_OROS_1_1` - "Ore lavorate per settore".

### Passo 2: Ottenere vincoli e descrizioni (usando get_constraints)
```json
{
  "tool": "get_constraints",
  "input": {"dataflow_id": "149_577_DF_DCSC_OROS_1_1"}
}
```

**Risultato**: Un'unica chiamata restituisce tutto il necessario:

```json
{
  "id_dataflow": "149_577_DF_DCSC_OROS_1_1",
  "constraints": [
    {
      "dimension": "FREQ",
      "codelist": "CL_FREQ",
      "values": [
        {"code": "Q", "description_en": "quarterly", "description_it": "trimestrale"}
      ]
    },
    {
      "dimension": "REF_AREA",
      "codelist": "CL_ITTER107",
      "values": [
        {"code": "IT", "description_en": "Italy", "description_it": "Italia"}
      ]
    },
    {
      "dimension": "TIME_PERIOD",
      "StartPeriod": "2000-01-01T00:00:00",
      "EndPeriod": "2023-12-31T00:00:00"
    }
  ]
}
```

### Passo 3: Recuperare i dati
```json
{
  "tool": "get_data",
  "input": {
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
}
```

Risultato: Dati pronti per l'analisi.

---

## Best Practices

1. **Cache intelligente**: Tutti i metadati (structure, codelists, concepts) sono cachati per 1 mese, i dataflows per 7 giorni, i dati per 1 ora.
2. **Filtri incrementali**: Iniziare con pochi filtri e aggiungerli progressivamente per evitare dataset vuoti.
3. **Periodi temporali**:
   - Per dati recenti rapidi: omettere start_period/end_period (usa automaticamente ultimo anno)
   - Per serie storiche: specificare range completo
4. **Dimensioni**: Usare sempre `get_constraints` prima di `get_data` per conoscere l'ordine corretto e i valori possibili dei filtri delle dimensioni.
5. **Codelists**: Esplorare sempre le codelists per trovare i codici corretti.
6. **Configurazione ambiente**: usare `DATAFLOWS_CACHE_TTL_SECONDS`, `METADATA_CACHE_TTL_SECONDS`, `OBSERVED_DATA_CACHE_TTL_SECONDS` e `AVAILABLECONSTRAINT_TIMEOUT_SECONDS` per adattare cache e timeout.

---

## Troubleshooting

**Problema**: Dataset troppo grande  
**Soluzione**: Aggiungere più filtri dimensionali o ridurre il range temporale.

**Problema**: Nessun dato restituito  
**Soluzione**: Verificare che i codici dimensionali esistano nella codelist e siano compatibili.

**Problema**: Ordine dimensioni errato  
**Soluzione**: Controllare l'output di `get_constraints` per l'ordine corretto.

**Problema**: Query string malformata (errori 404)  
**Soluzione**: Le dimensioni vuote devono essere rappresentate con `.` nel path. Quando vengono valorizzate con un filtro, deve sempre comparire il `.` concatenato al filtro.

**Problema**: Server non si carica in Claude Desktop  
**Soluzione**: Vedere sezione "Configurazione Claude Desktop" sotto.

---

## Configurazione Claude Desktop

### Problema Noto: File di Configurazione Riscritto

Claude Desktop **riscrive il file** `%APPDATA%\Claude\claude_desktop_config.json` all'avvio, rimuovendo potenzialmente la sezione `mcpServers`. Questo è un comportamento noto della versione attuale.

### Script Disponibili

Il progetto include script PowerShell per gestire la configurazione:

**1. `setup_claude_config.ps1`** - Configura il file prima di avviare Claude Desktop
```powershell
.\setup_claude_config.ps1
```

**2. `verify_claude_config.ps1`** - Verifica la configurazione dopo l'avvio
```powershell
.\verify_claude_config.ps1
```

### Configurazione Corretta

Il file `claude_desktop_config.json` deve contenere:
```json
{
  "mcpServers": {
    "istat": {
      "command": "C:\\Users\\patru\\Dropbox\\mcp\\istat_mcp_server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "C:\\Users\\patru\\Dropbox\\mcp\\istat_mcp_server"
    }
  },
  "preferences": {
    "coworkWebSearchEnabled": true,
    "coworkScheduledTasksEnabled": true,
    "ccdScheduledTasksEnabled": true
  }
}
```

### Test Manuale del Server

Per verificare che il server funzioni indipendentemente da Claude Desktop:
```powershell
cd C:\Users\patru\Dropbox\mcp\istat_mcp_server
.venv\Scripts\python.exe -m istat_mcp_server
```

Il server dovrebbe mostrare:
```text
Starting ISTAT MCP Server on stdio
MCP server configured with 7 tools
```

### Documentazione Aggiuntiva

- **CONFIGURAZIONE_CLAUDE.md** - Guida completa agli script setup/verify
- **TROUBLESHOOTING_CLAUDE.md** - Analisi dettagliata e soluzioni alternative
- **LOGGING_FORMAT.md** - Formato del logging avanzato implementato

---

## Riferimenti API

- **Base URL**: `https://esploradati.istat.it/SDMXWS/rest`
- **Formato**: SDMX 2.1 XML
- **Rate Limit**: 3 chiamate/minuto (gestito automaticamente)
- **Cache**: Sistema multi-layer automatico
- **Formato Query**: `/data/{dataflow_id}/{dim1.dim2.dim3...}/ALL/?params`
  - Dimensioni vuote: rappresentate con `.` tra separatori
  - Dimensioni multiple: separate con `+` (es. `IT+FR`)
  - Tutte le dimensioni: devono essere presenti (ordine da `get_structure`)

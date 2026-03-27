# ISTAT MCP Server

Server MCP per accedere ai dati statistici italiani tramite API SDMX di ISTAT.

## Panoramica

Questo server Model Context Protocol (MCP) fornisce a Claude Desktop accesso ai dati statistici italiani di ISTAT (Istituto Nazionale di Statistica) tramite API SDMX REST. Implementa un meccanismo di cache a due livelli per ridurre le chiamate API e mette a disposizione sette tool per scoprire, interrogare e recuperare dati statistici.

## Funzionalita

- **9 tool MCP** per scoperta e recupero dati:
  - `discover_dataflows` - Trova dataset disponibili tramite keyword (con filtro blacklist)
  - `get_structure` - Ottiene definizioni delle dimensioni e codelist per un ID di datastructure
  - `get_constraints` - Ottiene valori di vincolo disponibili per ogni dimensione con descrizioni (combina struttura + vincoli + descrizioni codelist)
  - `get_codelist_description` - Ottiene descrizioni in italiano/inglese per valori delle codelist
  - `get_concepts` - Ottiene definizioni semantiche dei concetti SDMX
  - `get_data` - Recupera dati statistici in formato SDMXXML (con validazione blacklist)
  - `get_cache_diagnostics` - Tool di debug per ispezionare stato cache
  - `search_constraint_values` - Cerca codici per una dimensione specifica (con filtro per nome opzionale)
  - `get_territorial_codes` - Ottiene codici territoriali ISTAT per livello (comune, provincia, regione, ripartizione)

- **Workflow consigliato** (semplice ed efficiente):
  1. **Scopri**: usa `discover_dataflows` per trovare il dataflow di interesse
  2. **Ottieni metadati completi**: usa `get_constraints` per vedere tutte le dimensioni con valori validi E descrizioni in una sola chiamata
     - Questo e l'approccio **CONSIGLIATO**: una chiamata invece di molte
     - Combina internamente `get_structure` + `get_codelist_description` per tutte le dimensioni
     - Tutti i dati sono in cache per 1 mese, quindi le chiamate successive sono immediate
     - Restituisce informazioni complete pronte per costruire i filtri in `get_data`
  3. **Recupera dati**: usa `get_data` con i filtri dimensionali appropriati per ottenere i dati osservati

  **Workflow alternativo** (manuale):
  - Usa `get_structure` con un ID di datastructure per vedere dimensioni e codelist associate
  - Poi chiama `get_codelist_description` manualmente per ogni codelist necessaria
  - Usa `get_concepts` se hai bisogno di definizioni semantiche di dimensioni/attributi

- **Progressive Discovery**: Le risposte ai metadati SDMX possono essere grandi — dataflow con molte dimensioni e codelist ampie possono superare i 100KB, saturando il context window degli LLM. Usa un approccio a strati per mantenere ogni passo leggero:

  | Passo | Tool | Cosa ottieni | Dimensione indicativa |
  |-------|------|--------------|----------------------|
  | 1 | `discover_dataflows` | ID + nomi che corrispondono alle keyword | 1–5 KB |
  | 2a | `get_constraints` *(senza filtro)* | Tutte le dimensioni + valori validi + descrizioni | 5–50 KB |
  | 2b | `get_constraints` *(con `dimensions`)* | Solo le dimensioni specificate | 0.5–5 KB |
  | 3 | `search_constraint_values` | Codici filtrati in una sola dimensione | ~1 KB |
  | 4 | `get_data` | Tabella dati osservati | variabile |

  Quando ti servono una o due dimensioni, usa il parametro `dimensions` per tenere le risposte piccole:

  ```
  get_constraints(dataflow_id="101_1015_DF_DCSP_COLTIVAZIONI_1", dimensions=["REF_AREA"])
  ```

  Tutti i risultati sono in cache per 1 mese, quindi una chiamata mirata ora non costa nulla alla prossima query completa.

- **Cache a due livelli**:
  - Cache in memoria (cachetools) per accesso rapido durante la sessione
  - Cache persistente su disco (diskcache) che sopravvive ai riavvii

- **Rate limiting**: massimo 3 chiamate API al minuto con accodamento automatico

- **Retry logic**: backoff esponenziale su errori transitori

- **Blacklist dataflow**: filtra dataflow specifici da tutte le query

## Installazione

1. Clona il repository:
```bash
git clone <repository-url>
cd istat_mcp_server
```

2. Crea un virtual environment e installa le dipendenze (richiesto Python >=3.11):

**Con uv (consigliato):**
```bash
uv sync
```
`uv sync` crea automaticamente una directory `.venv` e installa tutte le dipendenze al suo interno. Per eseguire comandi manualmente, attivalo prima:
```bash
source .venv/bin/activate  # Su Windows: .venv\Scripts\activate
```

**Con pip:**
```bash
python -m venv .venv
source .venv/bin/activate  # Su Windows: .venv\Scripts\activate
pip install -e .
```

3. Crea un file `.env` (opzionale, usa i default se assente):
```bash
cp .env.example .env
```

Opzionale: per risposte lente dell'endpoint `availableconstraint` usato da `get_constraints`, imposta:
```bash
AVAILABLECONSTRAINT_TIMEOUT_SECONDS=180
```

## Configurazione client MCP

Questo server funziona con qualsiasi client compatibile con MCP. Le sezioni seguenti coprono i più comuni.

[Claude Desktop](#claude-desktop) | [Claude Code](#claude-code) | [Gemini CLI](#gemini-cli) | [VS Code](#vs-code) | [Codex CLI](#codex-cli) | [Claude Desktop su Windows con Python su WSL2](#claude-desktop-su-windows-con-python-su-wsl2)

> In tutti gli esempi, sostituisci `/path/to/istat_mcp_server` con il percorso reale di questa directory, e `python` con `python3` se necessario sul tuo sistema.

### Claude Desktop

Aggiungi al file di configurazione di Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

### Claude Code

**Aggiungi globalmente** (disponibile in tutti i tuoi progetti):

```bash
claude mcp add -s user istat -- python -m istat_mcp_server --cwd /path/to/istat_mcp_server
```

**Aggiungi solo per il progetto corrente** (crea o aggiorna `.mcp.json` nella cartella del progetto):

```bash
claude mcp add istat -- python -m istat_mcp_server --cwd /path/to/istat_mcp_server
```

Oppure aggiungi manualmente a `.mcp.json` nella root del tuo progetto:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

> `-s user` rende il server disponibile globalmente in tutti i tuoi progetti. Senza questa opzione, il server è limitato al progetto corrente.

### Gemini CLI

**Aggiungi globalmente:**

```bash
gemini mcp add -s user istat -- python -m istat_mcp_server --cwd /path/to/istat_mcp_server
```

Oppure aggiungi manualmente a `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

### VS Code

Aggiungi alle impostazioni utente o a `.vscode/settings.json`:

```json
{
  "mcpServers": {
    "istat": {
      "command": "python",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "/path/to/istat_mcp_server"
    }
  }
}
```

Sostituisci `/path/to/istat_mcp_server` con il percorso reale di questa directory.

### Codex CLI

Aggiungi a `~/.codex/config.toml`:

```toml
[mcp_servers.istat]
command = "python"
args = ["-m", "istat_mcp_server"]
cwd = "/path/to/istat_mcp_server"
```

### Claude Desktop su Windows con Python su WSL2

Se usi Claude Desktop su Windows ma hai Python e questo server installati dentro WSL2, usa `wsl.exe -e` per collegare i due ambienti. Punta all'eseguibile Python dentro il tuo virtual environment:

```json
{
  "mcpServers": {
    "istat": {
      "command": "wsl.exe",
      "args": [
        "-e",
        "/home/<tuo-utente>/path/to/istat_mcp_server/.venv/bin/python",
        "-m", "istat_mcp_server"
      ]
    }
  }
}
```

Sostituisci `/home/<tuo-utente>/path/to/istat_mcp_server` con il percorso WSL reale di questa directory.

> **Nota:** Claude Code gira nativamente dentro WSL2 e usa la configurazione standard descritta sopra. Il wrapper `wsl.exe` è necessario solo per Claude Desktop che gira sul lato Windows.

## Configurazione blacklist dataflow

Puoi escludere dataflow specifici da tutte le query tramite variabili d'ambiente. Utile per filtrare dataset problematici o non desiderati.

### Configurazione tramite file .env

Aggiungi la variabile `DATAFLOW_BLACKLIST` al tuo file `.env`:

```bash
# Escludi dataflow specifici (lista separata da virgole)
DATAFLOW_BLACKLIST=149_577_DF_DCSC_OROS_1_1,22_315_DF_DCIS_POPORESBIL1_2
```

### Comportamento

- **discover_dataflows**: i dataflow in blacklist vengono filtrati automaticamente dai risultati
- **get_data**: i tentativi di lettura da dataflow in blacklist restituiscono un messaggio di errore

### Casi d'uso

- Escludere dataflow deprecati
- Filtrare dataset problematici che causano errori
- Nascondere dataflow interni o di test

## Esempi d'uso

Una volta configurato, puoi chiedere a Claude per esempio:

**Step 1: Scopri i dataflow**
- "Mostrami tutti i dataflow disponibili sulla popolazione"
- "Trova dataflow relativi all'agricoltura"

**Step 2: Ottieni informazioni complete sui vincoli (CONSIGLIATO)**
- "Get constraints for dataflow 101_1015_DF_DCSP_COLTIVAZIONI_1"
  - Restituisce tutte le dimensioni con valori validi E descrizioni IT/EN
  - Una chiamata invece di piu chiamate `get_structure` + `get_codelist_description`
  - Tutto in cache per 1 mese

**Step 2 alternativo: esplora struttura e codelist manualmente**
- "Mostrami la struttura della datastructure DCSP_COLTIVAZIONI"
- "Dammi le descrizioni della codelist CL_ITTER107 per trovare le regioni italiane"
- "Mostrami tutti i valori della codelist CL_AGRI_MADRE per i tipi di coltura"

**Step 3: Recupera dati con filtri**
- "Fetch population data for Italy from 2020 to 2023"
- "Get agricultural data for dataflow 101_1015_DF_DCSP_COLTIVAZIONI_1 filtered by REF_AREA=IT and TYPE_OF_CROP=APPLE"

## Sviluppo

Esegui i test:
```bash
pytest
```

Formatta il codice:
```bash
ruff format .
```

Controlla il codice:
```bash
ruff check .
```

## Struttura progetto

```
.
├── src/
│   └── istat_mcp_server/
│       ├── __init__.py
│       ├── __main__.py        # Entry point per `python -m istat_mcp_server`
│       ├── server.py          # Inizializzazione server MCP
│       ├── api/               # Client API e modelli
│       │   ├── client.py      # Client HTTP con rate limiting
│       │   └── models.py      # Modelli Pydantic
│       ├── cache/             # Sistema cache a due livelli
│       │   ├── manager.py     # Facade cache
│       │   ├── memory.py      # Cache in memoria
│       │   └── persistent.py  # Cache su disco
│       ├── tools/             # Handler tool MCP
│       │   ├── discover_dataflows.py
│       │   ├── get_structure.py
│       │   ├── get_constraints.py
│       │   ├── get_codelist_description.py
│       │   ├── get_concepts.py
│       │   ├── get_data.py
│       │   └── get_cache_diagnostics.py
│       └── utils/             # Utility
│           ├── logging.py
│           ├── validators.py
│           └── blacklist.py
├── tests/                     # Suite test
├── cache/                     # Cache runtime (ignorata da git)
├── log/                       # File log (ignorati da git)
├── .env.example
├── pyproject.toml
└── README.md
```

## Configurazione cache

Il server usa una strategia di caching a due livelli:

- **Memory cache**: cache in-process veloce con TTL di 5 minuti
- **Persistent cache**: cache su disco con TTL configurabili:
  - Dataflow: 7 giorni
  - Strutture/Codelist: 1 mese
  - Dati: 1 ora

Variabili `.env` rilevanti:
- `MEMORY_CACHE_TTL_SECONDS=300`
- `DATAFLOWS_CACHE_TTL_SECONDS=604800`
- `METADATA_CACHE_TTL_SECONDS=2592000`
- `OBSERVED_DATA_CACHE_TTL_SECONDS=3600`
- `AVAILABLECONSTRAINT_TIMEOUT_SECONDS=180`

La cache viene salvata per default nella directory `./cache`.

## Logging e debug

Il server crea automaticamente file di log nella directory `./log` con queste caratteristiche:

- **Rotazione automatica**: i file vengono ruotati a 10MB
- **Retention**: vengono mantenuti gli ultimi 5 file log
- **Doppio output**: log su file e su stderr (per i log di Claude Desktop)

### Livelli log

Controlla la verbosita tramite variabile `LOG_LEVEL` in `.env`:

```bash
LOG_LEVEL=DEBUG   # Massimo dettaglio per debug
LOG_LEVEL=INFO    # Default, operazioni standard
LOG_LEVEL=WARNING # Solo warning ed errori
LOG_LEVEL=ERROR   # Solo errori
```

### Dove trovare i log

- **Server logs**: `./log/istat_mcp_server.log`
- **Claude Desktop logs**:
  - Windows: `%APPDATA%\Claude\logs\`
  - macOS: `~/Library/Logs/Claude/`

### Debug problemi cache

Il file log mostra:
- Percorso directory cache all'avvio
- Operazioni cache (a livello DEBUG)
- Chiamate API e retry
- Invocazioni tool

Usa il tool `get_cache_diagnostics` in Claude Desktop per ispezionare lo stato cache in tempo reale.

## API rate limiting

La API SDMX di ISTAT e limitata a 3 chiamate al minuto. Il server gestisce automaticamente questo vincolo mettendo in coda le richieste quando il limite e raggiunto.

## Licenza

Licenza MIT

## Contribuire

I contributi sono benvenuti. Apri una issue o una pull request.

## Autore

- Vincenzo Patruno: https://www.linkedin.com/in/vincenzopatruno/

## Riferimenti

- ISTAT SDMX API: https://esploradati.istat.it/SDMXWS/rest/
- Model Context Protocol: https://modelcontextprotocol.io/

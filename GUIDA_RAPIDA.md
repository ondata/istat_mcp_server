# Guida Rapida - MCP Server ISTAT per Claude Desktop

Guida rapida per usare il server su Windows con Claude Desktop. Il server funziona con qualsiasi client MCP: per gli altri client (Claude Code, Gemini CLI, VS Code, Codex CLI) e per l'installazione completa vedi [README_IT.md](README_IT.md).

Negli esempi, sostituisci `C:\percorso\istat_mcp_server` con la cartella in cui hai clonato il repository.

## 📦 Installazione

```powershell
cd C:\percorso\istat_mcp_server
uv sync
```

`uv sync` crea la cartella `.venv` e installa le dipendenze.

In alternativa, senza `uv`: `python -m venv .venv`, poi `.\.venv\Scripts\Activate.ps1` e `pip install -e .`

## 📋 Configurazione per Claude Desktop

### Passo 1: Copiare la Configurazione

1. Apri il file di configurazione di Claude Desktop:
   - Premi `Win+R`
   - Digita: `%APPDATA%\Claude\claude_desktop_config.json`
   - Premi Invio

2. Se il file non esiste, crealo con questo contenuto:
```json
{
  "mcpServers": {
    "istat": {
      "command": "C:\\percorso\\istat_mcp_server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "C:\\percorso\\istat_mcp_server"
    }
  }
}
```

3. Se il file esiste già, aggiungi la sezione "istat" dentro "mcpServers".

### Passo 2: Riavviare Claude Desktop

Chiudi completamente Claude Desktop e riaprilo.

## 🚀 Utilizzo

Una volta configurato, puoi chiedere a Claude:

### Esempi di Domande

1. **Scoprire dataset disponibili:**
   - "Quali dataset ISTAT sono disponibili sulla popolazione?"
   - "Mostra i dataflow ISTAT sull'occupazione"

2. **Ottenere informazioni su un dataset:**
   - "Qual è la struttura del dataset sulle coltivazioni?"
   - "Quali valori può assumere il territorio nel dataset sulla disoccupazione?"

3. **Ottenere dati:**
   - "Scarica i dati sulla popolazione italiana dal 2020 al 2023"
   - "Mostra il tasso di disoccupazione per regione"

## 🛠️ Strumenti Disponibili

Il server fornisce 8 strumenti MCP:

1. **discover_dataflows** - Scopri i dataset disponibili, con filtro per parole chiave
2. **get_structure** - Ottieni la struttura di un dataset (dimensioni e codelist)
3. **get_constraints** - Ottieni i valori ammessi per ogni dimensione, con descrizioni
4. **get_codelist_description** - Ottieni le descrizioni in italiano/inglese dei valori di una codelist
5. **get_concepts** - Ottieni la descrizione di un concetto SDMX
6. **get_data** - Scarica i dati in formato tabellare TSV, con l'URL per riprodurre la query
7. **get_cache_diagnostics** - Diagnostica lo stato della cache
8. **get_territorial_codes** - Cerca i codici territoriali ISTAT (regioni, province, comuni)

Ci sono anche due comandi da terminale che scrivono JSON su stdout, utili per non riversare liste lunghe nella conversazione: `istat-get-concepts-cli` e `istat-get-constraints-cli` (vedi [README.md](README.md) e, per `istat-get-constraints-cli`, la skill in [skills/istat-mcp/SKILL.md](skills/istat-mcp/SKILL.md)).

## 📊 Sistema di Cache

Il server usa una cache a due livelli:

- **Cache in memoria**: 5 minuti, massimo 512 elementi (veloce, per la sessione corrente)
- **Cache persistente su disco** (`diskcache`, su SQLite):
  - Liste di dataflow: 7 giorni
  - Strutture/vincoli/codelist: 1 mese
  - Dati: 1 giorno

Le durate si possono cambiare nel file `.env` (vedi `.env.example`).

### Come Funziona

1. **Primo accesso**: I dati vengono scaricati dall'API ISTAT e salvati in entrambe le cache
2. **Accessi successivi**: I dati vengono letti dalla cache (prima memoria, poi disco)

### Dove Trovarli

La cache è salvata nella cartella `cache` del repository (`C:\percorso\istat_mcp_server\cache`), oppure nella cartella indicata da `PERSISTENT_CACHE_DIR`.

## 🔧 Risoluzione Problemi

### Errore "PermissionError: [WinError 5] Accesso negato: 'cache'"

Il server non riesce a creare la directory cache. Soluzioni:

**Soluzione 1 - Creare la directory manualmente:**
```powershell
cd C:\percorso\istat_mcp_server
New-Item -ItemType Directory -Path "cache" -Force
```

**Soluzione 2 - Usare la directory temporanea:**
Il server usa automaticamente `%TEMP%\istat_mcp_cache` se non riesce a creare la directory cache principale.

**Soluzione 3 - Cambiare la directory cache:**
Crea un file `.env` con:
```env
PERSISTENT_CACHE_DIR=C:\Users\<utente>\AppData\Local\istat_mcp_cache
```

### Il server non si connette

1. Verifica che il path in `claude_desktop_config.json` sia corretto
2. Controlla i log di Claude Desktop in: `%APPDATA%\Claude\logs\`
3. Testa il server manualmente:
```powershell
cd C:\percorso\istat_mcp_server
.\.venv\Scripts\Activate.ps1
python -m istat_mcp_server
```

### Errori di dipendenze

Reinstalla le dipendenze:
```powershell
cd C:\percorso\istat_mcp_server
uv sync
```

Senza `uv`: attiva `.venv` con `.\.venv\Scripts\Activate.ps1` e lancia `pip install -e .`

## 📚 Documentazione

- **README_IT.md** / **README.md** - Documentazione completa del progetto
- **CLAUDE_DESKTOP_CONFIG.md** - Guida dettagliata alla configurazione
- **skills/istat-mcp/** - Skill che guida il modello nel flusso di lavoro corretto (consigliata)
- **.env.example** - Variabili di ambiente configurabili
- **API ISTAT**: https://esploradati.istat.it/SDMXWS/rest/

## ✨ Funzionalità

- ✅ 8 strumenti MCP
- ✅ Cache a due livelli (memoria + disco)
- ✅ Rate limiting (4 chiamate/minuto)
- ✅ Retry automatico con backoff esponenziale
- ✅ Parsing XML SDMX 2.1
- ✅ Validazione input con Pydantic
- ✅ Logging configurabile
- ✅ Test automatici

## 🎯 Prossimi Passi

1. Apri Claude Desktop
2. Inizia una nuova conversazione
3. Chiedi: "Quali dataset ISTAT hai a disposizione?"
4. Esplora i dati statistici italiani con Claude!

---

**Versione**: 0.1.0  
**Python**: 3.11+  
**Licenza**: MIT

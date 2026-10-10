# Guida Rapida - MCP Server ISTAT per Claude Desktop

## ✅ Installazione Completata

Il server MCP per accedere ai dati ISTAT è stato installato con successo!

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
      "command": "C:\\Users\\patru\\Dropbox\\mcp\\istat_mcp_server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "istat_mcp_server"],
      "cwd": "C:\\Users\\patru\\Dropbox\\mcp\\istat_mcp_server"
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
   - "Qual è la struttura del dataflow DCSP_COLTIVAZIONI?"
   - "Quali dimensioni ha il dataset sulla popolazione?"

3. **Ottenere dati:**
   - "Scarica i dati sulla popolazione italiana dal 2020 al 2023"
   - "Mostra i dati ISTAT sull'occupazione per regione"

## 🛠️ Strumenti Disponibili

Il server fornisce 5 strumenti MCP:

1. **discover_dataflows** - Scopri i dataset disponibili
2. **get_structure** - Ottieni la struttura di un dataset
3. **get_codelist_description** - Ottieni descrizioni in italiano/inglese
4. **get_data** - Scarica i dati reali in formato SDMX-XML
5. **get_cache_diagnostics** - Diagnostica lo stato della cache

## 📊 Sistema di Cache

Il server usa un sistema di cache a due livelli che **serializza automaticamente** i dati:

- **Cache in memoria**: 5 minuti, massimo 512 elementi (veloce, per la sessione corrente)
- **Cache persistente su disco**: Salva i dati in formato JSON per persistenza
  - Liste di dataflow: 24 ore
  - Strutture/vincoli/codelist: 1 mese
  - Dati: 1 ora

### Come Funziona

1. **Primo accesso**: I dati vengono scaricati dall'API ISTAT e salvati in entrambe le cache
2. **Accessi successivi**: I dati vengono letti dalla cache (prima memoria, poi disco)
3. **Serializzazione automatica**: Gli oggetti Python vengono convertiti in JSON per il salvataggio

### Dove Trovarli

La cache è salvata in: `C:\Users\patru\Dropbox\mcp\istat_mcp_server\cache`

**Nota**: I dati nella cache sono in formato JSON (dict/list), non oggetti Python, per garantire la compatibilità con il sistema di caching persistente.

## 🔧 Risoluzione Problemi

### Errore "PermissionError: [WinError 5] Accesso negato: 'cache'"

Il server non riesce a creare la directory cache. Soluzioni:

**Soluzione 1 - Creare la directory manualmente:**
```powershell
cd C:\Users\patru\Dropbox\mcp\istat_mcp_server
New-Item -ItemType Directory -Path "cache" -Force
```

**Soluzione 2 - Usare la directory temporanea:**
Il server ora usa automaticamente `%TEMP%\istat_mcp_cache` se non riesce a creare la directory cache principale.

**Soluzione 3 - Cambiare la directory cache:**
Crea un file `.env` con:
```env
PERSISTENT_CACHE_DIR=C:\Users\patru\AppData\Local\istat_mcp_cache
```

### Il server non si connette

1. Verifica che il path in `claude_desktop_config.json` sia corretto
2. Controlla i log di Claude Desktop in: `%APPDATA%\Claude\logs\`
3. Testa il server manualmente:
```powershell
cd C:\Users\patru\Dropbox\mcp\istat_mcp_server
.\.venv\Scripts\Activate.ps1
python -m istat_mcp_server
```

### Errori di dipendenze

Reinstalla le dipendenze:
```powershell
cd C:\Users\patru\Dropbox\mcp\istat_mcp_server
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 📚 Documentazione

- **README.md** - Documentazione completa del progetto
- **CLAUDE_DESKTOP_CONFIG.md** - Guida dettagliata alla configurazione
- **.env.example** - Variabili di ambiente configurabili
- **API ISTAT**: https://esploradati.istat.it/SDMXWS/rest/

## ✨ Funzionalità

- ✅ 6 strumenti MCP completamente funzionali
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

# Troubleshooting: Server ISTAT MCP non si avvia

## Analisi della Situazione

### ✅ Cosa funziona
- Il server ISTAT MCP è stato **usato con successo ieri sera** (12 marzo 2026 21:50)
- Il server si avvia correttamente da command line, con l'interprete dell'ambiente virtuale: `.venv\Scripts\python.exe -m istat_mcp_server`
- Il codice è corretto e tutti i test passano

### ❌ Problema attuale
- Oggi (13 marzo 2026) Claude Desktop **non carica più** il server ISTAT
- Il file `claude_desktop_config.json` viene **riscritto** da Claude Desktop all'avvio
- La sezione `mcpServers` viene rimossa dal file di configurazione

### 🔍 Evidenze dai Log

**Log del server ISTAT** (`%APPDATA%\Claude\logs\mcp-server-istat.log`):
- Dimensione: 5.2 MB
- Ultima modifica: 12/03/2026 21:50:01
- Ultime righe mostrano il server funzionante con chiamate a:
  - `discover_dataflows`
  - `get_data`
  - `get_structure`
  - `get_codelist_description`

**Log MCP generale** (`%APPDATA%\Claude\logs\mcp.log`):
```
2026-03-12T20:44:22.325Z [info] [istat] Server started and connected successfully
```

## 🎯 Soluzioni da Provare

### Soluzione 1: Controllare l'Interfaccia Grafica di Claude Desktop

Claude Desktop potrebbe avere un'interfaccia grafica per gestire i server MCP. Cerca in:

1. **Apri Claude Desktop**
2. **Cerca Settings/Preferences**: Cerca nelle impostazioni
3. **Cerca una di queste sezioni**:
   - "MCP Servers"
   - "Plugins"
   - "Extensions"
   - "Integrations"
   - "Developer Settings"

4. **Se trovi il server "istat"**:
   - Controlla se è disabilitato
   - Verifica i percorsi:
     - Command: `C:\Users\patru\Dropbox\mcp\istat_mcp_server\.venv\Scripts\python.exe`
     - Args: `-m istat_mcp_server`
     - Cwd: `C:\Users\patru\Dropbox\mcp\istat_mcp_server`

### Soluzione 2: Verificare Database Interno di Claude

Claude Desktop potrebbe usare un database interno per le configurazioni:

```powershell
# Cerca file database
Get-ChildItem "$env:APPDATA\Claude" -Recurse -Filter "*.db" -ErrorAction SilentlyContinue
Get-ChildItem "$env:APPDATA\Claude" -Recurse -Filter "*.sqlite" -ErrorAction SilentlyContinue

# Files da controllare:
# - DIPS (36 KB)
# - DIPS-wal (4.1 MB) - Write-Ahead Log di SQLite
```

Se trovi file SQLite, puoi ispezionarli con:
```powershell
# Installa DB Browser for SQLite
choco install db-browser-sqlite
# Oppure scarica da: https://sqlitebrowser.org/
```

### Soluzione 3: Controllare il Registro di Windows

Claude Desktop potrebbe salvare configurazioni nel registro:

```powershell
# Cerca chiavi relative a MCP o ISTAT
Get-ChildItem "HKCU:\Software\Claude" -Recurse -ErrorAction SilentlyContinue
Get-ChildItem "HKCU:\Software\Anthropic" -Recurse -ErrorAction SilentlyContinue
```

### Soluzione 4: Reinstallare il Server tramite Claude Desktop

Se Claude Desktop ha un marketplace o un sistema di installazione:

1. Cerca "Add Server" o "Install Plugin"
2. Potrebbere essere disponibile un'opzione "Add Local Server" o "Add Custom MCP Server"
3. Inserisci i dettagli del server ISTAT

### Soluzione 5: File di Configurazione Alternativo

Alcuni client MCP usano file separati per i server personalizzati:

```powershell
# Cerca file di configurazione alternativi
Get-ChildItem "$env:APPDATA\Claude" -Recurse -Filter "*server*.json" -ErrorAction SilentlyContinue
Get-ChildItem "$env:APPDATA\Claude" -Recurse -Filter "*mcp*.json" -ErrorAction SilentlyContinue

# Controlla anche in:
# - %LOCALAPPDATA%\Claude\
# - %APPDATA%\Local\Claude\
# - Directory di installazione di Claude Desktop
```

### Soluzione 6: Contattare il Supporto Anthropic

Se nessuna delle soluzioni precedenti funziona:

1. Documenta il problema:
   - ✅ Server funzionava ieri (log disponibile)
   - ❌ Oggi non si carica più
   - ❌ `claude_desktop_config.json` viene riscritto all'avvio

2. Informazioni da fornire:
   - Versione di Claude Desktop: (controlla in About/Help)
   - Sistema operativo: Windows
   - Log rilevanti: `%APPDATA%\Claude\logs\mcp.log`

3. Canali di supporto:
   - Documentazione MCP: https://modelcontextprotocol.io/
   - Forum/Discord di Anthropic
   - Support email

## 📝 Checklist di Verifica

- [ ] Ho controllato Settings/Preferences in Claude Desktop
- [ ] Ho cercato sezioni MCP/Plugins/Extensions
- [ ] Ho verificato se il server "istat" è elencato ma disabilitato
- [ ] Ho controllato file database SQLite
- [ ] Ho cercato file di configurazione alternativi
- [ ] Ho verificato il registro di Windows
- [ ] Ho controllato la versione di Claude Desktop
- [ ] Ho cercato aggiornamenti disponibili per Claude Desktop

## 🔧 Workaround Temporaneo

Se non riesci a configurare il server tramite Claude Desktop, puoi usare il server manualmente:

```powershell
# Terminale 1: Avvia il server
cd C:\Users\patru\Dropbox\mcp\istat_mcp_server
.venv\Scripts\python.exe -m istat_mcp_server

# Il server accetta comandi JSON via stdin/stdout
# Puoi testarlo con comandi MCP manualicurl
```

## 📊 File da Esaminare

1. **Configurazione**:
   - `%APPDATA%\Claude\claude_desktop_config.json` (viene riscritto)
   - `%APPDATA%\Claude\config.json` (configurazione generale)
   - `%APPDATA%\Claude\Preferences` (preferenze)

2. **Database**:
   - `%APPDATA%\Claude\DIPS` (SQLite database)
   - `%APPDATA%\Claude\DIPS-wal` (Write-Ahead Log)

3. **Log**:
   - `%APPDATA%\Claude\logs\main.log` (log principale)
   - `%APPDATA%\Claude\logs\mcp.log` (log MCP generale)
   - `%APPDATA%\Claude\logs\mcp-server-istat.log` (log server ISTAT)

4. **Altri**:
   - `%APPDATA%\Claude\extensions-blocklist.json`
   - `%LOCALAPPDATA%\Claude\` (se esiste)

## 🆘 Ultima Risorsa: Reverse Engineering

Se proprio non trovi la configurazione, puoi:

1. **Monitorare le modifiche ai file** durante l'aggiunta di un server:
   ```powershell
   # PowerShell con FileSystemWatcher
   $watcher = New-Object System.IO.FileSystemWatcher
   $watcher.Path = "$env:APPDATA\Claude"
   $watcher.IncludeSubdirectories = $true
   $watcher.EnableRaisingEvents = $true
   Register-ObjectEvent $watcher "Created" -Action {
       Write-Host "File created: $($Event.SourceEventArgs.FullPath)"
   }
   ```

2. **Confrontare prima/dopo**:
   - Fai uno snapshot di tutti i file
   - Aggiungi un server tramite Claude Desktop (se possibile)
   - Confronta i file modificati

3. **Analizzare il binario di Claude Desktop**:
   - Decompila l'applicazione Electron
   - Esegui strings sul binario per trovare riferimenti ai percorsi di configurazione

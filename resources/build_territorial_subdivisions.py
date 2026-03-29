"""Build resources/istat_lookup.duckdb (table territorial_subdivisions) from CL_ITTER107 and ISTAT data.

Sources:
- CL_ITTER107: fetched via mcp__istat__get_codelist_description (cached in cache/cache.db)
- ISTAT municipalities CSV: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
- ISTAT capoluogo JSON: https://situas-servizi.istat.it/publish/reportspooljson?pfun=61&pdata=01/01/2048

Output columns (table: territorial_subdivisions):
- code: ISTAT territorial code (CL_ITTER107 for all levels; 6-digit numeric for comuni)
- name_it: Italian name
- level: italia | ripartizione | regione | provincia | comune
- nuts_level: 0 | 1 | 2 | 3 | 4
- parent_code: code of the parent territorial unit (NULL for Italia)
- capoluogo_provincia: True if the comune is a provincial/UTS capital (NULL for non-comuni)
- capoluogo_regione: True if the comune is a regional capital (NULL for non-comuni)
- cod_istat: numeric ISTAT code as string (COD_RIP for ripartizioni, COD_REG for regioni,
             COD_PROV_STORICO for province, PRO_COM_T for comuni; NULL for italia)

Usage:
    python3 resources/build_territorial_subdivisions.py <itter107_json> [comuni_csv]
"""

import csv
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

import duckdb

# NUTS 2021 codes that DON'T follow simple ITH->ITD / ITI->ITE substitution
# Maps NUTS2021 NUTS3 code -> CL_ITTER107 code
NUTS2021_TO_ITTER_OVERRIDE = {
    'ITC4C': 'ITC45',  # Metro Milano -> Milano
    'ITC4D': 'IT108',  # Monza e della Brianza
    'ITI35': 'IT109',  # Fermo (must be before ITI->ITE rule)
    'ITF46': 'ITF41',  # Foggia
    'ITF47': 'ITF42',  # Bari / Citta Metropolitana
    'ITF48': 'IT110',  # Barletta-Andria-Trani
    'ITG2D': 'ITG25',  # Sassari
    'ITG2E': 'ITG26',  # Nuoro
    'ITG2F': 'ITG27',  # Cagliari
    'ITG2G': 'ITG28',  # Oristano
    'ITG2H': 'IT111',  # Sud Sardegna
}

# Special IT1XX province codes -> parent NUTS2 region code
IT1XX_PARENTS = {
    'IT108': 'ITC4',  # Monza e della Brianza -> Lombardia
    'IT109': 'ITE3',  # Fermo -> Marche
    'IT110': 'ITF4',  # Barletta-Andria-Trani -> Puglia
    'IT111': 'ITG2',  # Sud Sardegna -> Sardegna
    'IT113': 'ITG2',  # Gallura Nord-Est Sardegna -> Sardegna
    'IT119': 'ITG2',  # Sulcis Iglesiente -> Sardegna
}

COMUNI_CSV_URL = 'https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv'
ISTAT_DATA_URL = 'https://situas-servizi.istat.it/publish/reportspooljson?pfun=61&pdata=01/01/2048'

# NUTS1 code → COD_RIP numeric string
NUTS1_TO_COD_RIP = {'ITC': '1', 'ITD': '2', 'ITE': '3', 'ITF': '4', 'ITG': '5'}

# NUTS1 code → denominazione ripartizione geografica
NUTS1_TO_DEN_RIP = {
    'ITC': 'Nord-ovest',
    'ITD': 'Nord-est',
    'ITE': 'Centro',
    'ITF': 'Sud',
    'ITG': 'Isole',
}

# Sardegna: dopo la riforma del 2016 i codici comuni cambiano (090xxx → 112xxx ecc.)
# Il JSON situas-servizi usa i nuovi codici, il CSV ISTAT quelli vecchi → nessun match automatico.
# Mapping manuale NUTS3 → COD_PROV_STORICO per le province attualmente codificate nel JSON.
# ITG29 (Olbia-Tempio), ITG2C (Carbonia-Iglesias), IT111 (Sud Sardegna) non presenti nel JSON → NULL.
SARDINIA_NUTS3_TO_COD_PROV = {
    'ITG25': '112',  # Sassari
    'ITG26': '114',  # Nuoro
    'ITG27': '118',  # Cagliari
    'ITG28': '115',  # Oristano
    'ITG2A': '116',  # Ogliastra
    'ITG2B': '117',  # Medio Campidano
    'IT113': '113',  # Gallura Nord-Est Sardegna
    'IT119': '119',  # Sulcis Iglesiente
}

OUTPUT_PATH = Path(__file__).parent.parent / 'src' / 'istat_mcp_server' / 'resources' / 'istat_lookup.duckdb'


def nuts2021_to_itter(code: str) -> str:
    """Convert NUTS 2021 NUTS3 code to CL_ITTER107 equivalent."""
    if code in NUTS2021_TO_ITTER_OVERRIDE:
        return NUTS2021_TO_ITTER_OVERRIDE[code]
    if code.startswith('ITH'):
        return 'ITD' + code[3:]
    if code.startswith('ITI'):
        return 'ITE' + code[3:]
    return code


def load_itter107(path: str) -> dict[str, str]:
    """Load CL_ITTER107 codelist from a JSON file (MCP tool result format)."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    text = data[0]['text']
    entries = re.findall(r'\{[^{}]+\}', text)
    codes = {}
    for e in entries:
        cm = re.search(r'"code":\s*"([^"]+)"', e)
        di = re.search(r'"description_it":\s*"([^"]+)"', e)
        if cm and di:
            codes[cm.group(1)] = di.group(1)
    return codes


def download_comuni_csv() -> str:
    """Download ISTAT municipalities CSV to a temp file, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix='_comuni_istat.csv', delete=False)
    print(f'Downloading {COMUNI_CSV_URL}...')
    urllib.request.urlretrieve(COMUNI_CSV_URL, tmp.name)
    utf8_path = tmp.name + '_utf8.csv'
    with open(tmp.name, encoding='latin1') as f:
        content = f.read()
    with open(utf8_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return utf8_path


def download_istat_data() -> dict[str, dict]:
    """Download ISTAT comuni data from JSON endpoint.

    Returns:
        Dict mapping 6-digit comune code -> {
            'cap_prov': bool,
            'cap_reg': bool,
            'cod_reg': str,       # e.g. '19' for Sicilia
            'cod_prov': str,      # e.g. '82' (int of COD_PROV_STORICO)
            'cod_rip': str,       # e.g. '5'
        }
    """
    print(f'Downloading {ISTAT_DATA_URL}...')
    with urllib.request.urlopen(ISTAT_DATA_URL) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    result = {}
    for rec in data.get('resultset', []):
        code = str(rec.get('PRO_COM_T', '')).strip().zfill(6)
        if code:
            result[code] = {
                'cap_prov': bool(rec.get('CC_UTS', 0)),
                'cap_reg': bool(rec.get('CC_REG', 0)),
                'cod_reg': str(int(rec['COD_REG'])),
                'cod_prov': str(int(rec['COD_PROV_STORICO'])),
                'cod_rip': str(rec['COD_RIP']),
            }
    print(f'  Loaded ISTAT data for {len(result)} comuni')
    return result


def build_comuni_mappings(csv_path: str) -> tuple[dict, dict]:
    """Build comune_code->ITTER_nuts3 and storico->ITTER_nuts3 mappings."""
    comune_to_nuts3 = {}
    storico_to_nuts3 = {}
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)
        for row in reader:
            cod6 = row[15].strip().zfill(6)
            storico = row[2].strip().zfill(3)
            nuts3_2021 = row[22].strip()
            if nuts3_2021:
                itter = nuts2021_to_itter(nuts3_2021)
                if cod6:
                    comune_to_nuts3[cod6] = itter
                if storico:
                    storico_to_nuts3[storico] = itter
    return comune_to_nuts3, storico_to_nuts3


def build_duckdb(codes: dict, comune_to_nuts3: dict, storico_to_nuts3: dict, istat_data: dict) -> None:
    """Build and write the DuckDB database."""
    # Province: standard NUTS3 + letter-suffix + IT1XX
    nuts3_codes = {k: v for k, v in codes.items() if re.match(r'^IT[A-Z][0-9]{2}$', k)}
    letter_suffix = {k: v for k, v in codes.items() if re.match(r'^IT[A-Z][0-9][A-Z]$', k)}
    it1xx = {k: v for k, v in codes.items() if re.match(r'^IT1[0-9]{2}$', k)}
    all_province_codes = {**nuts3_codes, **letter_suffix, **it1xx}

    # Build nuts3 → cod_istat_prov and nuts2 → cod_istat_reg from comuni data
    nuts3_to_cod_prov: dict[str, str] = {}
    nuts2_to_cod_reg: dict[str, str] = {}
    for cod6, rec in istat_data.items():
        nuts3 = comune_to_nuts3.get(cod6) or storico_to_nuts3.get(cod6[:3])
        if nuts3:
            nuts3_to_cod_prov[nuts3] = rec['cod_prov']
            nuts2_to_cod_reg[nuts3[:4]] = rec['cod_reg']

    # Fallback Sardegna: riforma 2016 cambia i codici comuni (090xxx → 112xxx)
    # il CSV usa i vecchi codici, il JSON i nuovi → nessun match automatico
    for nuts3, cod_prov in SARDINIA_NUTS3_TO_COD_PROV.items():
        nuts3_to_cod_prov.setdefault(nuts3, cod_prov)
    nuts2_to_cod_reg.setdefault('ITG2', '20')  # Sardegna = COD_REG 20

    # Helper: NUTS1 code → den_rip
    def den_rip(nuts1: str | None) -> str | None:
        return NUTS1_TO_DEN_RIP.get(nuts1) if nuts1 else None

    rows = []

    rows.append(('IT', 'Italia', 'italia', 0, None, None, None, None, None))

    for k, v in {'ITC': 'Nord-ovest', 'ITD': 'Nord-est', 'ITE': 'Centro', 'ITF': 'Sud', 'ITG': 'Isole'}.items():
        rows.append((k, v, 'ripartizione', 1, 'IT', None, None, NUTS1_TO_COD_RIP.get(k), den_rip(k)))

    for k, v in codes.items():
        if re.match(r'^IT[A-Z][0-9]$', k):
            rows.append((k, v, 'regione', 2, k[:3], None, None, nuts2_to_cod_reg.get(k), den_rip(k[:3])))

    for k, v in all_province_codes.items():
        parent = IT1XX_PARENTS.get(k, k[:4])
        nuts1 = IT1XX_PARENTS.get(k, k)[:3]
        rows.append((k, v, 'provincia', 3, parent, None, None, nuts3_to_cod_prov.get(k), den_rip(nuts1)))

    no_parent = 0
    for k, v in codes.items():
        if re.match(r'^[0-9]{6}$', k):
            parent = comune_to_nuts3.get(k) or storico_to_nuts3.get(k[:3])
            if not parent:
                no_parent += 1
            rec = istat_data.get(k, {})
            cap_prov = rec.get('cap_prov', False)
            cap_reg = rec.get('cap_reg', False)
            nuts1 = parent[:3] if parent else None
            # IT1XX province parent: es. IT108 → ITC4 → nuts1=ITC
            if parent and re.match(r'^IT1', parent):
                nuts1 = IT1XX_PARENTS.get(parent, parent)[:3]
            rows.append((k, v, 'comune', 4, parent, cap_prov, cap_reg, k, den_rip(nuts1)))

    # Remove existing db if present
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    conn = duckdb.connect(str(OUTPUT_PATH))
    conn.execute('''
        CREATE TABLE territorial_subdivisions (
            code VARCHAR NOT NULL,
            name_it VARCHAR NOT NULL,
            level VARCHAR NOT NULL,
            nuts_level TINYINT,
            parent_code VARCHAR,
            capoluogo_provincia BOOLEAN,
            capoluogo_regione BOOLEAN,
            cod_istat VARCHAR,
            den_rip VARCHAR
        )
    ''')
    conn.executemany(
        'INSERT INTO territorial_subdivisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rows,
    )
    conn.execute('CREATE INDEX idx_level ON territorial_subdivisions(level)')
    conn.execute('CREATE INDEX idx_parent ON territorial_subdivisions(parent_code)')
    conn.execute('CREATE INDEX idx_code ON territorial_subdivisions(code)')
    conn.close()

    size = OUTPUT_PATH.stat().st_size
    print(f'Written: {OUTPUT_PATH}')
    print(f'Rows: {len(rows)} | Size: {size:,} bytes ({size // 1024} KB)')
    print(f'Province: {len(all_province_codes)} | Comuni senza parent: {no_parent}')


if __name__ == '__main__':
    itter107_path = sys.argv[1] if len(sys.argv) > 1 else None
    comuni_csv_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not itter107_path:
        print('Usage: python3 build_territorial_subdivisions.py <itter107_json> [comuni_csv]')
        print('  itter107_json: MCP tool result JSON for CL_ITTER107 codelist')
        print('  comuni_csv: ISTAT municipalities CSV (latin1); downloaded if omitted')
        sys.exit(1)

    print('Loading CL_ITTER107...')
    codes = load_itter107(itter107_path)
    print(f'  Loaded {len(codes)} codes')

    if comuni_csv_path:
        utf8_path = comuni_csv_path + '_utf8.csv'
        with open(comuni_csv_path, encoding='latin1') as f:
            content = f.read()
        with open(utf8_path, 'w', encoding='utf-8') as f:
            f.write(content)
        comuni_csv_path = utf8_path
    else:
        comuni_csv_path = download_comuni_csv()

    print('Building comuni mappings...')
    comune_to_nuts3, storico_to_nuts3 = build_comuni_mappings(comuni_csv_path)
    print(f'  comuni: {len(comune_to_nuts3)} | storico: {len(storico_to_nuts3)}')

    print('Downloading ISTAT data...')
    istat_data = download_istat_data()

    print('Building DuckDB...')
    build_duckdb(codes, comune_to_nuts3, storico_to_nuts3, istat_data)

"""Build resources/territorial_subdivisions.parquet from CL_ITTER107 and ISTAT municipalities CSV.

Sources:
- CL_ITTER107: fetched via mcp__istat__get_codelist_description (cached in cache/cache.db)
- ISTAT municipalities CSV: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
- ISTAT capoluogo JSON: https://situas-servizi.istat.it/publish/reportspooljson?pfun=61&pdata=01/01/2048

Output columns:
- code: ISTAT territorial code (CL_ITTER107 for all levels; 6-digit numeric for comuni)
- name_it: Italian name
- level: italia | ripartizione | regione | provincia | comune
- nuts_level: 0 | 1 | 2 | 3 | 4
- parent_code: code of the parent territorial unit (NULL for Italia)
- capoluogo_provincia: True if the comune is a provincial/UTS capital (NULL for non-comuni)
- capoluogo_regione: True if the comune is a regional capital (NULL for non-comuni)

Usage:
    python3 resources/build_territorial_subdivisions.py [path_to_itter107_json] [path_to_comuni_csv]
"""

import csv
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# NUTS 2021 codes that DON'T follow simple ITH->ITD / ITI->ITE substitution
# Maps NUTS2021 NUTS3 code -> CL_ITTER107 code
NUTS2021_TO_ITTER_OVERRIDE = {
    'ITC4C': 'ITC45',  # Metro Milano → Milano
    'ITC4D': 'IT108',  # Monza e della Brianza
    'ITI35': 'IT109',  # Fermo (must be before ITI->ITE rule)
    'ITF46': 'ITF41',  # Foggia
    'ITF47': 'ITF42',  # Bari / Città Metropolitana
    'ITF48': 'IT110',  # Barletta-Andria-Trani
    'ITG2D': 'ITG25',  # Sassari
    'ITG2E': 'ITG26',  # Nuoro
    'ITG2F': 'ITG27',  # Cagliari
    'ITG2G': 'ITG28',  # Oristano
    'ITG2H': 'IT111',  # Sud Sardegna
}

# Special IT1XX province codes -> parent NUTS2 region code
IT1XX_PARENTS = {
    'IT108': 'ITC4',  # Monza e della Brianza → Lombardia
    'IT109': 'ITE3',  # Fermo → Marche
    'IT110': 'ITF4',  # Barletta-Andria-Trani → Puglia
    'IT111': 'ITG2',  # Sud Sardegna → Sardegna
    'IT113': 'ITG2',  # Gallura Nord-Est Sardegna → Sardegna
    'IT119': 'ITG2',  # Sulcis Iglesiente → Sardegna
}

COMUNI_CSV_URL = 'https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv'
CAPOLUOGO_JSON_URL = 'https://situas-servizi.istat.it/publish/reportspooljson?pfun=61&pdata=01/01/2048'

OUTPUT_PATH = Path(__file__).parent / 'territorial_subdivisions.parquet'


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
    # Convert to UTF-8
    utf8_path = tmp.name + '_utf8.csv'
    with open(tmp.name, encoding='latin1') as f:
        content = f.read()
    with open(utf8_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return utf8_path


def download_capoluogo_json() -> dict[str, tuple[bool, bool]]:
    """Download capoluogo flags from ISTAT JSON endpoint.

    Returns:
        Dict mapping 6-digit comune code -> (capoluogo_provincia, capoluogo_regione)
    """
    print(f'Downloading {CAPOLUOGO_JSON_URL}...')
    with urllib.request.urlopen(CAPOLUOGO_JSON_URL) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    result = {}
    for rec in data.get('resultset', []):
        code = str(rec.get('PRO_COM_T', '')).strip().zfill(6)
        if code:
            result[code] = (bool(rec.get('CC_UTS', 0)), bool(rec.get('CC_REG', 0)))
    print(f'  Loaded capoluogo flags for {len(result)} comuni')
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


def build_parquet(codes: dict, comune_to_nuts3: dict, storico_to_nuts3: dict, capoluogo: dict[str, tuple[bool, bool]] | None = None) -> None:
    """Build and write the Parquet file."""
    # Province: standard NUTS3 + letter-suffix + IT1XX
    nuts3_codes = {k: v for k, v in codes.items() if re.match(r'^IT[A-Z][0-9]{2}$', k)}
    letter_suffix = {k: v for k, v in codes.items() if re.match(r'^IT[A-Z][0-9][A-Z]$', k)}
    it1xx = {k: v for k, v in codes.items() if re.match(r'^IT1[0-9]{2}$', k)}
    all_province_codes = {**nuts3_codes, **letter_suffix, **it1xx}

    rows = []

    rows.append(('IT', 'Italia', 'italia', 0, None, None, None))

    for k, v in {'ITC': 'Nord-ovest', 'ITD': 'Nord-est', 'ITE': 'Centro', 'ITF': 'Sud', 'ITG': 'Isole'}.items():
        rows.append((k, v, 'ripartizione', 1, 'IT', None, None))

    for k, v in codes.items():
        if re.match(r'^IT[A-Z][0-9]$', k):
            rows.append((k, v, 'regione', 2, k[:3], None, None))

    for k, v in all_province_codes.items():
        parent = IT1XX_PARENTS.get(k, k[:4])
        rows.append((k, v, 'provincia', 3, parent, None, None))

    no_parent = 0
    for k, v in codes.items():
        if re.match(r'^[0-9]{6}$', k):
            parent = comune_to_nuts3.get(k) or storico_to_nuts3.get(k[:3])
            if not parent:
                no_parent += 1
            cap_prov, cap_reg = capoluogo.get(k, (False, False)) if capoluogo else (False, False)
            rows.append((k, v, 'comune', 4, parent, cap_prov, cap_reg))

    codes_col, names_col, levels_col, nuts_col, parent_col, cap_prov_col, cap_reg_col = zip(*rows)
    table = pa.table({
        'code': pa.array(codes_col, type=pa.string()),
        'name_it': pa.array(names_col, type=pa.string()),
        'level': pa.array(levels_col, type=pa.string()),
        'nuts_level': pa.array(nuts_col, type=pa.int8()),
        'parent_code': pa.array(parent_col, type=pa.string()),
        'capoluogo_provincia': pa.array(cap_prov_col, type=pa.bool_()),
        'capoluogo_regione': pa.array(cap_reg_col, type=pa.bool_()),
    })
    pq.write_table(table, str(OUTPUT_PATH), compression='zstd')

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
        # Convert to UTF-8 if needed
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

    print('Downloading capoluogo flags...')
    capoluogo = download_capoluogo_json()

    print('Building Parquet...')
    build_parquet(codes, comune_to_nuts3, storico_to_nuts3, capoluogo)

"""
ANZSCO 2022 data pipeline.

Sources:
  Structure/titles: https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations/2022
  Descriptions:     ABS unit group web pages (one page per unit group, contains all occupation descriptions)

Update-checking:
  Every run computes SHA-256 of each source (Excel files + each scraped page).
  Hashes are stored in data/raw/checksums.json.
  On re-run, changed sources are flagged in data/raw/change_log.json.
  Documents derived from changed sources are marked needs_review=True in the processed output.
  Nothing is silently overwritten — a human must validate flagged entries before they go live.
"""

import hashlib
import json
import time
import re
import pathlib
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (research bot; contact lizanpeter@gmail.com)'}
BASE_URL = 'https://www.abs.gov.au'
ABS_BASE = '/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations/2022'

DATA_RAW  = pathlib.Path('data/raw')
DATA_PROC = pathlib.Path('data/processed')
DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROC.mkdir(parents=True, exist_ok=True)

CHECKSUM_FILE  = DATA_RAW / 'checksums.json'
CHANGE_LOG     = DATA_RAW / 'change_log.json'
EXCEL_URLS = {
    'anzsco_structure.xlsx': f'{ABS_BASE}/anzsco%202022%20structure%20062023.xlsx',
    'anzsco_index.xlsx':     f'{ABS_BASE}/anzsco%202022%20index%20of%20principal%20titles%2C%20alternative%20titles%20and%20specialisations%20062023.xlsx',
}


# ---------------------------------------------------------------------------
# Checksum helpers
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_checksums() -> dict:
    if CHECKSUM_FILE.exists():
        return json.loads(CHECKSUM_FILE.read_text())
    return {}

def save_checksums(cs: dict):
    CHECKSUM_FILE.write_text(json.dumps(cs, indent=2))

def record_change(key: str, old_hash: str, new_hash: str, notes: str = ''):
    log = []
    if CHANGE_LOG.exists():
        log = json.loads(CHANGE_LOG.read_text())
    log.append({
        'detected_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'key': key,
        'old_hash': old_hash,
        'new_hash': new_hash,
        'notes': notes,
        'reviewed': False,
    })
    CHANGE_LOG.write_text(json.dumps(log, indent=2))
    print(f'  [CHANGE DETECTED] {key} — flagged for review')


# ---------------------------------------------------------------------------
# Excel downloads
# ---------------------------------------------------------------------------

def download_excel_files(force=False) -> dict:
    """Download Excel files, check for changes. Returns {filename: changed}."""
    checksums = load_checksums()
    changed = {}

    for fname, path in EXCEL_URLS.items():
        url = BASE_URL + path
        out = DATA_RAW / fname
        print(f'Fetching {fname}...')
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()

        new_hash = sha256_bytes(r.content)
        old_hash = checksums.get(fname)

        if old_hash and old_hash != new_hash:
            record_change(fname, old_hash, new_hash, 'Excel file changed on ABS — re-validate affected documents')
            changed[fname] = True
        elif not old_hash:
            changed[fname] = True  # first download
        else:
            changed[fname] = False
            print(f'  Unchanged (hash match)')

        out.write_bytes(r.content)
        checksums[fname] = new_hash
        save_checksums(checksums)

    return changed


# ---------------------------------------------------------------------------
# Parse Excel files for taxonomy + enrichment
# ---------------------------------------------------------------------------

def parse_structure() -> pd.DataFrame:
    """Return flat DataFrame of all occupations with hierarchy info."""
    xl = pd.ExcelFile(DATA_RAW / 'anzsco_structure.xlsx')
    raw = xl.parse('Table 5', header=None, skiprows=10)
    raw.columns = ['major', 'sub_major', 'minor', 'unit', 'occupation', '_', 'skill_level']

    # Forward-fill hierarchy columns
    current = {'major': None, 'sub_major': None, 'minor': None, 'unit': None,
                'major_title': None, 'sub_major_title': None, 'minor_title': None, 'unit_title': None}
    rows = []

    for _, r in raw.iterrows():
        major_val    = str(r['major']).strip() if pd.notna(r['major']) else None
        sub_val      = str(r['sub_major']).strip() if pd.notna(r['sub_major']) else None
        minor_val    = str(r['minor']).strip() if pd.notna(r['minor']) else None
        unit_val     = str(r['unit']).strip() if pd.notna(r['unit']) else None
        occ_val      = str(r['occupation']).strip() if pd.notna(r['occupation']) else None

        if major_val and re.match(r'^\d{1}$', major_val):
            current['major'] = major_val
            current['major_title'] = sub_val  # title is in sub_major column on same row
        elif sub_val and re.match(r'^\d{2}$', sub_val):
            current['sub_major'] = sub_val
            current['sub_major_title'] = minor_val  # title is in minor column
        elif minor_val and re.match(r'^\d{3}$', minor_val):
            current['minor'] = minor_val
            current['minor_title'] = unit_val  # title in unit column
        elif unit_val and re.match(r'^\d{4}$', unit_val):
            current['unit'] = unit_val
            current['unit_title'] = occ_val  # title in occupation column
        elif occ_val and re.match(r'^\d{6}$', occ_val):
            sl = str(r['skill_level']).strip() if pd.notna(r['skill_level']) else None
            rows.append({
                'code':            occ_val,
                'title':           r['_'] if pd.notna(r['_']) else occ_val,
                'skill_level':     sl,
                'unit_code':       current['unit'],
                'unit_title':      current['unit_title'],
                'minor_code':      current['minor'],
                'minor_title':     current['minor_title'],
                'sub_major_code':  current['sub_major'],
                'sub_major_title': current['sub_major_title'],
                'major_code':      current['major'],
                'major_title':     current['major_title'],
            })

    return pd.DataFrame(rows)


def parse_index() -> dict:
    """Return {code: {alt_titles: [...], specialisations: [...]}}."""
    xl = pd.ExcelFile(DATA_RAW / 'anzsco_index.xlsx')
    df = xl.parse('Table 2', header=None, skiprows=5)
    df.columns = ['code', 'description', 'category']
    df = df.dropna(subset=['code'])
    df['code'] = df['code'].astype(str).str.strip().str.zfill(6)

    enrichment = {}
    for _, r in df.iterrows():
        code = r['code']
        if not re.match(r'^\d{6}$', code):
            continue
        if code not in enrichment:
            enrichment[code] = {'alt_titles': [], 'specialisations': []}
        cat = str(r['category']).strip()
        desc = str(r['description']).strip()
        if cat == 'Alternative Title':
            enrichment[code]['alt_titles'].append(desc)
        elif cat == 'Specialisation':
            enrichment[code]['specialisations'].append(desc)

    return enrichment


# ---------------------------------------------------------------------------
# Web scraping: unit group pages
# ---------------------------------------------------------------------------

def build_unit_group_url(unit_code: str, major: str, sub_major: str, minor: str) -> str:
    return f'{BASE_URL}{ABS_BASE}/browse-classification/{major}/{sub_major}/{minor}/{unit_code}'


def parse_unit_group_page(html: str, unit_code: str) -> dict:
    """Extract unit group description, tasks, and per-occupation descriptions."""
    soup = BeautifulSoup(html, 'lxml')
    main = soup.find('main') or soup.body
    text_lines = [l.strip() for l in main.get_text(separator='\n').split('\n') if l.strip()]

    result = {
        'unit_code':        unit_code,
        'unit_description': '',
        'tasks':            [],
        'occupations':      {},
    }

    # The page renders unit group content TWICE (once in sidebar nav, once in body).
    # Find the LAST occurrence of the "{unit_code} Title" pattern — that is the body.
    start_idx = None
    for i, line in enumerate(text_lines):
        if line.startswith(unit_code + ' ') and len(line) > len(unit_code) + 1:
            start_idx = i  # keep overwriting — we want the last one

    if start_idx is None:
        return result

    lines = text_lines[start_idx:]
    i = 1  # skip the title line itself

    # Lines to skip wholesale
    SKIP_LINES = {
        'APA', 'Copy', 'Detail', 'Cite', 'Citation', 'Close', 'Print',
        'Print current page', 'Print all pages', 'Print this section only',
        'On this page', 'Sections', 'This is not the latest release',
        'View the latest release', 'Indicative Skill Level:',
        'In Australia and New Zealand:', 'Reference period', 'Released',
        'View all releases', 'How search works', 'Group', 'Unit Group',
        'Tasks Include:', 'Occupations:',
        'Alternative Title:', 'Alternative Titles:',
        'Specialisation:', 'Specialisations:',
        'Registration or licensing is required.',
        'Registration or licensing may be required.',
        'Occupations in this group include:',
        'No occupations have currently been identified for this residual category.',
    }

    # Unit group description: first long sentence (>40 chars) after the title line
    while i < len(lines):
        line = lines[i]
        if line in SKIP_LINES or line.startswith('Released at') or line.startswith('22/11') or line == '2022':
            i += 1
            continue
        if len(line) > 40 and ' ' in line and not line[0].isdigit():
            result['unit_description'] = line
            i += 1
            break
        i += 1

    # Tasks, then occupation descriptions
    in_tasks = False
    in_occ_body = False     # True once we've passed the occupation's alt-titles
    current_occ_code = None
    current_occ_desc = ''

    def flush_occ():
        if current_occ_code and current_occ_desc:
            result['occupations'][current_occ_code] = current_occ_desc.strip()

    while i < len(lines):
        line = lines[i]
        i += 1

        if line == 'Tasks Include:':
            in_tasks = True
            continue
        if line == 'Occupations:':
            in_tasks = False
            continue

        if in_tasks:
            if line and line[0].islower():
                result['tasks'].append(line)
            continue

        # Stop at page footer
        if line.startswith('Book traversal') or line.startswith('Previous page') or line == 'ANZSCO Search':
            flush_occ()
            break

        # New occupation entry
        m = re.match(r'^(\d{6})\s+(.+)$', line)
        if m and m.group(1).startswith(unit_code[:4]):
            flush_occ()
            current_occ_code = m.group(1)
            current_occ_desc = ''
            in_occ_body = False
            continue

        if current_occ_code is None:
            continue

        # Within an occupation entry
        if line in SKIP_LINES or re.match(r'^Skill Level: \d$', line):
            # Once we hit a metadata label, alt-title phase is over
            in_occ_body = True
            continue

        # A long sentence with punctuation is the description
        if len(line) > 40 and (' ' in line) and not line[0].isdigit():
            if not current_occ_desc:
                current_occ_desc = line
            in_occ_body = True
        elif not in_occ_body:
            # Short line before description = alt title or specialisation label — skip
            pass

    flush_occ()
    return result


def scrape_unit_groups(unit_groups: list[dict], delay: float = 1.5) -> dict:
    """
    Scrape all unit group pages. Checks hashes — skips unchanged pages.
    Returns {unit_code: parsed_data}.
    """
    checksums = load_checksums()
    html_cache = DATA_RAW / 'unit_group_pages'
    html_cache.mkdir(exist_ok=True)

    results = {}
    total = len(unit_groups)

    for idx, ug in enumerate(unit_groups):
        code = ug['unit_code']
        url  = build_unit_group_url(code, ug['major'], ug['sub_major'], ug['minor'])
        cache_file = html_cache / f'{code}.html'
        ck_key = f'page_{code}'

        print(f'  [{idx+1:3d}/{total}] {code} {ug["unit_title"][:40]:40s}', end=' ')

        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f'HTTP {r.status_code} — skipping')
            time.sleep(delay)
            continue

        new_hash = sha256_bytes(r.content)
        old_hash = checksums.get(ck_key)

        if old_hash and old_hash == new_hash and cache_file.exists():
            print('(unchanged)')
            html = cache_file.read_text(encoding='utf-8')
        else:
            if old_hash and old_hash != new_hash:
                record_change(ck_key, old_hash, new_hash, f'Unit group {code} page changed on ABS')
            cache_file.write_text(r.text, encoding='utf-8')
            checksums[ck_key] = new_hash
            save_checksums(checksums)
            html = r.text
            print('scraped')
            time.sleep(delay)

        results[code] = parse_unit_group_page(html, code)

    return results


# ---------------------------------------------------------------------------
# Build composite documents
# ---------------------------------------------------------------------------

def build_composite_documents(structure: pd.DataFrame, index_enrichment: dict,
                               scraped: dict, changed_keys: set) -> list[dict]:
    """
    One document per 6-digit occupation code.
    Combines: unit group description + task list + occupation description + alt titles + specialisations.
    Marks needs_review=True if any source data changed since last run.
    """
    docs = []

    for _, row in structure.iterrows():
        code      = row['code']
        unit_code = row['unit_code']
        unit_data = scraped.get(unit_code, {})
        enrichment = index_enrichment.get(code, {})

        # Build the text blob that gets embedded.
        # Titles are repeated at top and bottom so they anchor the embedding
        # even when the shared unit-group task list dominates the middle.
        title = row['title']
        alt_titles = enrichment.get('alt_titles', [])
        specs = enrichment.get('specialisations', [])
        all_titles = [title] + alt_titles + specs

        parts = []

        # 1. Title block — repeated for emphasis (sentence-transformers pools tokens,
        #    so more occurrences of the title shift the centroid toward it)
        title_line = 'Occupation: ' + ' / '.join(all_titles)
        parts.append(title_line)
        parts.append(title_line)  # intentional repeat

        # 2. Hierarchy context
        parts.append(f"Field: {row['major_title']} > {row['sub_major_title']} > {row['minor_title']}")

        # 3. Occupation-specific description (before tasks — most differentiating signal)
        occ_desc = unit_data.get('occupations', {}).get(code, '')
        if occ_desc:
            parts.append('Description: ' + occ_desc)

        # 4. Unit group overview (real sentence only — APA/nav artifacts filtered in parser)
        unit_desc = unit_data.get('unit_description', '')
        if unit_desc and len(unit_desc) > 30:
            parts.append('Group overview: ' + unit_desc)

        # 5. Task list
        tasks = unit_data.get('tasks', [])
        if tasks:
            parts.append('Tasks include: ' + '; '.join(tasks))

        # 6. Title anchor at end
        parts.append(title_line)

        embedding_text = '\n'.join(parts)

        # Determine if this document needs human review
        source_keys = {f'page_{unit_code}', 'anzsco_structure.xlsx', 'anzsco_index.xlsx'}
        needs_review = bool(source_keys & changed_keys)

        docs.append({
            'code':            code,
            'title':           title,
            'unit_code':       unit_code,
            'unit_title':      row['unit_title'],
            'minor_title':     row['minor_title'],
            'sub_major_title': row['sub_major_title'],
            'major_title':     row['major_title'],
            'skill_level':     row['skill_level'],
            'alt_titles':      alt_titles,
            'specialisations': specs,
            'embedding_text':  embedding_text,
            'needs_review':    needs_review,
            'last_updated':    datetime.datetime.utcnow().isoformat() + 'Z',
        })

    return docs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_pipeline(force_scrape: bool = False):
    print('\n=== ANZSCO Data Pipeline ===')
    print(f'Started: {datetime.datetime.utcnow().isoformat()}Z\n')

    # 1. Download Excel files
    print('--- Step 1: Excel files ---')
    excel_changed = download_excel_files()
    changed_keys = {k for k, v in excel_changed.items() if v}

    # 2. Parse structure and index
    print('\n--- Step 2: Parse taxonomy ---')
    structure = parse_structure()
    print(f'Occupations loaded: {len(structure)}')
    index_enrichment = parse_index()
    print(f'Index enrichment entries: {sum(len(v["alt_titles"]) + len(v["specialisations"]) for v in index_enrichment.values())}')

    # 3. Build unit group list for scraping
    unit_groups = (structure[['unit_code', 'unit_title', 'major_code', 'sub_major_code', 'minor_code']]
                   .drop_duplicates('unit_code')
                   .rename(columns={'major_code': 'major', 'sub_major_code': 'sub_major', 'minor_code': 'minor'})
                   .to_dict('records'))
    print(f'Unit groups to check: {len(unit_groups)}')

    # 4. Scrape unit group pages
    print('\n--- Step 3: Scrape unit group pages ---')
    scraped = scrape_unit_groups(unit_groups)
    changed_keys |= {k for k in load_checksums() if k.startswith('page_') and
                     k not in {f'page_{ug["unit_code"]}' for ug in unit_groups}}

    # 5. Build composite documents
    print('\n--- Step 4: Build composite documents ---')
    docs = build_composite_documents(structure, index_enrichment, scraped, changed_keys)
    needs_review = [d for d in docs if d['needs_review']]

    out_file = DATA_PROC / 'anzsco_documents.json'
    out_file.write_text(json.dumps(docs, indent=2))
    print(f'Documents written: {len(docs)} -> {out_file}')
    if needs_review:
        print(f'NEEDS REVIEW: {len(needs_review)} documents flagged (source data changed)')
        review_file = DATA_PROC / 'needs_review.json'
        review_file.write_text(json.dumps([d['code'] for d in needs_review], indent=2))
        print(f'Review list -> {review_file}')
    else:
        print('All documents up to date — no review needed')

    print(f'\nDone: {datetime.datetime.utcnow().isoformat()}Z')
    return docs


if __name__ == '__main__':
    docs = run_pipeline()

import pandas as pd

xl = pd.ExcelFile('data/raw/anzsco_structure.xlsx')
df = xl.parse('Table 5', header=None, skiprows=10)
df.columns = ['major', 'sub_major', 'minor', 'unit', 'occupation', 'col5', 'skill_level']

major_codes = df['major'].dropna().astype(str).str.strip()
major_codes = major_codes[major_codes.str.match(r'^\d{1}$')]
sub_codes   = df['sub_major'].dropna().astype(str).str.strip()
sub_codes   = sub_codes[sub_codes.str.match(r'^\d{2}$')]
minor_codes = df['minor'].dropna().astype(str).str.strip()
minor_codes = minor_codes[minor_codes.str.match(r'^\d{3}$')]
unit_codes  = df['unit'].dropna().astype(str).str.strip()
unit_codes  = unit_codes[unit_codes.str.match(r'^\d{4}$')]
occ_codes   = df['occupation'].dropna().astype(str).str.strip()
occ_codes   = occ_codes[occ_codes.str.match(r'^\d{6}$')]

print("ANZSCO Hierarchy Counts:")
print(f"  Major groups:     {len(major_codes):>5}")
print(f"  Sub-major groups: {len(sub_codes):>5}")
print(f"  Minor groups:     {len(minor_codes):>5}")
print(f"  Unit groups:      {len(unit_codes):>5}   <- primary retrieval target")
print(f"  Occupations:      {len(occ_codes):>5}   <- final code returned to user")

xl2 = pd.ExcelFile('data/raw/anzsco_index.xlsx')
df2 = xl2.parse('Table 2', header=None, skiprows=5)
df2.columns = ['code', 'description', 'category']
df2 = df2.dropna(subset=['code'])
df2['code'] = df2['code'].astype(str).str.strip().str.zfill(6)

alt_titles = df2[df2['category'] == 'Alternative Title']
specs = df2[df2['category'] == 'Specialisation']
print(f"\nIndex enrichment:")
print(f"  Alternative job titles: {len(alt_titles)}")
print(f"  Specialisations:        {len(specs)}")

n_unit = len(unit_codes)
n_occ = len(occ_codes)
print(f"\nScraping plan:")
print(f"  Unit group pages: {n_unit} pages (~{n_unit*1.5/60:.0f} min at 1.5s/page)")
print(f"  Occupation pages: {n_occ} pages (~{n_occ*1.5/60:.0f} min at 1.5s/page)")

xl3 = pd.ExcelFile('data/raw/anzsco_correspondence.xlsx')
print(f"\nCorrespondence file sheets: {xl3.sheet_names}")

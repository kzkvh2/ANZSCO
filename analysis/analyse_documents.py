import json, pathlib
import pandas as pd
import statistics

docs = json.loads(pathlib.Path('data/processed/anzsco_documents.json').read_text())
df = pd.DataFrame(docs)

print(f"=== ANZSCO Document Analysis ===")
print(f"Total documents: {len(df)}")
print(f"Needs review:    {df['needs_review'].sum()}")
print()

# Embedding text length
df['text_len'] = df['embedding_text'].str.len()
df['word_count'] = df['embedding_text'].str.split().str.len()

print(f"=== Embedding text richness ===")
print(f"  Median chars:   {df['text_len'].median():.0f}")
print(f"  Mean chars:     {df['text_len'].mean():.0f}")
print(f"  Min chars:      {df['text_len'].min()}")
print(f"  Max chars:      {df['text_len'].max()}")
print(f"  Median words:   {df['word_count'].median():.0f}")
print()

# How many have actual descriptions scraped?
df['has_occ_desc'] = df['embedding_text'].str.contains('Description: ')
df['has_tasks']    = df['embedding_text'].str.contains('Tasks: ')
df['has_alt']      = df['alt_titles'].apply(lambda x: len(x) > 0)
df['has_spec']     = df['specialisations'].apply(lambda x: len(x) > 0)

print(f"=== Content coverage ===")
print(f"  Has unit group task list:       {df['has_tasks'].sum():>5} / {len(df)} ({df['has_tasks'].mean()*100:.0f}%)")
print(f"  Has occupation description:     {df['has_occ_desc'].sum():>5} / {len(df)} ({df['has_occ_desc'].mean()*100:.0f}%)")
print(f"  Has alternative job titles:     {df['has_alt'].sum():>5} / {len(df)} ({df['has_alt'].mean()*100:.0f}%)")
print(f"  Has specialisations:            {df['has_spec'].sum():>5} / {len(df)} ({df['has_spec'].mean()*100:.0f}%)")
print()

# Thin documents (potential problem cases)
thin = df[df['word_count'] < 30]
print(f"=== Thin documents (< 30 words) ===")
print(f"  Count: {len(thin)}")
if len(thin) > 0:
    for _, r in thin.head(10).iterrows():
        print(f"  {r['code']} {r['title'][:50]:50s} | {r['word_count']} words")
print()

# Distribution by major group
print(f"=== Documents by major group ===")
by_major = df.groupby('major_title')['code'].count().sort_values(ascending=False)
for group, count in by_major.items():
    avg_words = df[df['major_title'] == group]['word_count'].mean()
    print(f"  {str(group)[:45]:45s}: {count:>4} occupations | avg {avg_words:.0f} words/doc")
print()

# Sample documents — best and worst
print(f"=== Sample: richest document ===")
best = df.loc[df['word_count'].idxmax()]
print(f"  {best['code']} {best['title']} ({best['word_count']} words)")
print(best['embedding_text'][:600])
print()
print(f"=== Sample: thinnest non-zero document ===")
non_zero = df[df['word_count'] > 5]
worst = non_zero.loc[non_zero['word_count'].idxmin()]
print(f"  {worst['code']} {worst['title']} ({worst['word_count']} words)")
print(worst['embedding_text'])

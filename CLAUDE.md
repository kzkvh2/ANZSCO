# CLAUDE.md — ANZSCO Code Finder

Read `current_state.md` first every session. It is the single source of truth for project status, roadmap, tech stack, and decisions.

## Project in one sentence
AI tool that reads a CV and returns the top 5 matching ANZSCO occupation codes for Australian skilled migration visas.

## Live products
- Landing page: https://kzkvh2.github.io/ANZSCO/
- Streamlit app: https://anzsco.streamlit.app/
- GitHub repo: https://github.com/kzkvh2/ANZSCO

## Quick start (local dev)
```bash
cd ~/projects/anzsco
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/streamlit run app/streamlit_app.py
```

## Run tests
```bash
# Original 10 synthetic CVs (already passed 100% top-5 / 80% top-1)
ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. .venv/bin/python3 tests/acceptance/acceptance_test.py

# Diverse 10 CVs (trades, health, ICT, social — run to validate)
ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. .venv/bin/python3 tests/acceptance/diverse_cv_test.py
```

## Key constraints
- Regulatory: information tool only, not migration advice. Disclaimers are mandatory.
- Data: ANZSCO 2022 (ABS). Update via checksum mechanism in src/scraper/.
- OSCA replaces ANZSCO for ABS statistics in 2027 — but Home Affairs still uses ANZSCO for visa purposes. Monitor annually.
- Embeddings file (`data/processed/anzsco_embeddings.npy`) is gitignored; auto-rebuilt on cold start.

## Models in use
- Profile extraction: claude-sonnet-4-6
- Re-ranking: claude-haiku-4-5-20251001
- Embeddings: all-MiniLM-L6-v2 (local, sentence-transformers)

## What NOT to do
- Do not add the Streamlit app link to the landing page until validation is complete (waitlist-only strategy)
- Do not remove the disclaimer
- Do not commit anzsco_embeddings.npy (gitignored intentionally)
- Do not add assessing body links to results (decided: confusing, premature for monetisation)

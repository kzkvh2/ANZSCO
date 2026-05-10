# Project: ANZSCO Code Finder — Current State
_Last updated: 2026-05-10_

## Project Overview
**ANZSCO Code Finder** — A tool for skilled migrants to identify the correct ANZSCO occupation code for Australian visa applications, without paying a migration agent.

**Who it's for**: Foreign skilled workers applying for Australian visas.
**Core problem**: Getting the wrong ANZSCO code = visa refusal, failed skills assessment ($500–$1,500 in fees), years of delay.
**Regulatory position**: Information tool, not migration advice. Strong disclaimers required.

---

## Live Products

| Product | URL | Status |
|---|---|---|
| Landing page | https://kzkvh2.github.io/ANZSCO/ | Live — waitlist, Brevo email capture |
| Streamlit app | https://kzkvh2-anzsco.hf.space | Live on HuggingFace Spaces |
| GitHub repo | https://github.com/kzkvh2/ANZSCO | Up to date |

**NOTE: anzsco.streamlit.app is dead** — crashed and unrecoverable. HF Spaces is the active deployment.

---

## Phased Plan

### Phase 0 — Data Pipeline ✅ COMPLETE
- Scraped 364 ANZSCO unit group pages from ABS (2022 edition)
- Built 1,076 composite documents (one per 6-digit occupation code)
- Each document: occupation title + alt titles + specialisations + unit group overview + task list + occupation description
- Median 167 words/document; 87% have task lists; 100% have occupation descriptions
- Update-check mechanism: SHA-256 checksums per source; changed sources flag `needs_review=True` on affected documents

### Phase 1 — Matching Engine ✅ COMPLETE
- Embeddings: all-MiniLM-L6-v2, shape (1076, 384), stored in `data/processed/anzsco_embeddings.npy` (gitignored, auto-rebuilt on cold start)
- CV parser: pdfminer.six (PDF) + python-docx (Word)
- Pipeline: Claude Haiku extracts structured profile (incl. name) → cosine similarity top 20 → Claude Sonnet re-ranks to top 5 with explanations
- Rerank prompt has calibrated score anchors (90–100 near-perfect / 70–89 strong / 50–69 partial / <40 omit). Model returns 1–5 results; Python post-filters at ≥35.

### Phase 2 — Demo App ✅ DEPLOYED
- Streamlit app at `app/streamlit_app.py`, live at https://kzkvh2-anzsco.hf.space
- Auto-matches on CV upload — result cached by MD5 hash of file bytes
- Greets user by first name if extracted from CV
- Shows parsability score with tier-specific guidance
- Shows top matches with score/100, confidence icon (🟢🟡🔴), 1-sentence explanation
- Per-card links: `Search: LinkedIn · SEEK · Indeed` + `Assessing body: [Name](url)` (hardcoded mapping for ~40 unit codes; fallback to skilled occupation list)
- "What to do next" — 4-step guidance
- Privacy notice: CV not stored, processed in memory only
- Live job listings: auto-triggered on results load, Adzuna API, 6 results in 2-column grid, ~1-2s
- Feedback: 👍/👎 → Brevo transactional email → lizanpeter@gmail.com (above jobs section)

### Phase 3 — Acceptance Test ✅ PASSED (2026-05-07)
- Top-5 accuracy: **10/10 (100%)** on synthetic CVs; **8/10 (80%)** on diverse CVs
- Top-1 accuracy: **8/10 (80%)** on synthetic; **7/10 (70%)** on diverse (likely higher — 2 misses were test spec errors)

### Phase 4 — Landing Page ✅ COMPLETE
- Live at https://kzkvh2.github.io/ANZSCO/ (GitHub Pages, /docs)
- Waitlist → Brevo email capture; app link shown immediately after signup

### Phase 5 — Agent Extension (Later)

---

## Known Issues / Backlog

| Issue | Severity | Notes |
|---|---|---|
| No production accuracy data | High | Add logging; review first 20 real runs |
| Seniority/tenure ignored in matching | High | Add experience-level signal to re-rank prompt |
| No email nurture sequence | Med | Set up 2-email Brevo sequence for waitlist |
| No usage analytics | Med | Add basic logging or Plausible |
| Mobile UX poor on Streamlit | Med | Long-term: replace with Next.js/FastAPI app |
| No monetisation gate | Low (now) | Freemium after validation |
| Assessing body map incomplete | Low | ~40 unit codes hardcoded; expand from Home Affairs SMOL spreadsheet |

---

## Tech Stack

| Component | Tool |
|---|---|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM extract profile | claude-haiku-4-5-20251001 |
| LLM re-rank | claude-sonnet-4-6 |
| Live job search | Adzuna API (free 1,000/month) — replaced Apify 2026-05-10 |
| Feedback email | Brevo transactional API |
| CV parsing | pdfminer.six + python-docx |
| Demo app | Streamlit on HuggingFace Spaces |
| Landing page | HTML + Tailwind CSS (GitHub Pages) |
| Email capture | Brevo (landing page) |

---

## Secrets (all gitignored / set via HF Spaces)
- `ANTHROPIC_API_KEY` — Claude API
- `ADZUNA_APP_ID` = `d0f8559f`
- `ADZUNA_APP_KEY` = `42d87c5f95929313f4e24363d0749a6e`

---

## Environment
- Python 3.12.3 (WSL Ubuntu), project at `~/projects/anzsco`
- Venv: `~/projects/anzsco/.venv`
- Deploy to HF Spaces: see `memory/project_state.md` for full script

## Project Structure
```
anzsco/
├── current_state.md
├── requirements.txt
├── .streamlit/config.toml
├── .venv/
├── data/
│   ├── raw/
│   │   ├── anzsco_structure.xlsx
│   │   ├── anzsco_index.xlsx
│   │   └── unit_group_pages/     (gitignored)
│   └── processed/
│       ├── anzsco_documents.json
│       ├── anzsco_metadata.json
│       ├── embeddings_hash.txt
│       └── anzsco_embeddings.npy (gitignored, auto-rebuilt)
├── src/
│   ├── jobs.py                   ← Adzuna job search
│   └── rag/
│       ├── cv_parser.py
│       ├── embedder.py
│       └── matcher.py
├── tests/acceptance/
├── docs/                         ← Landing page (GitHub Pages)
└── app/
    └── streamlit_app.py
```

---

## Session Findings Log

### 2026-05-10 (Session 3 — assessing bodies, Adzuna, UX polish)
- Added hardcoded `ASSESSING_BODIES` dict (40 unit codes → body name + URL) in streamlit_app.py
- Per-card links changed to: `Search: LinkedIn · SEEK · Indeed` + assessing body link
- Job search auto-triggers on results load (no button); feedback moved above jobs section
- Switched job search from Apify (credits exhausted) to Adzuna API
  - Adzuna: ~1-2s, 1,000 free/month, single call aggregates SEEK + Indeed + others
  - `_render_jobs` simplified to 2-column grid of 6 Adzuna results + fallback search links
  - Secrets set via HfApi.add_space_secret() (not committed to git)

### 2026-05-10 (Session 2 — UX overhaul + job search + HF Spaces migration)
- Streamlit Cloud died → migrated to HuggingFace Spaces
- Auto-match on upload, name greeting, score labels, privacy notice, debug hidden
- Haiku for extraction (cost); Sonnet for rerank (quality — Haiku caused score inflation)
- Web3Forms blocks server-side POST → switched to Brevo
- JSA and LMI occupation profile URLs return 404 — removed

### 2026-05-10 (Session 1 — diverse CV test + feedback)
- Top-5: 8/10, Top-1: 7/10 on diverse CVs (true accuracy likely 9-10/10)
- Feedback button added (👍/👎 → Brevo)

### 2026-05-07 (Phase 0–4 complete)
- All MVP phases shipped

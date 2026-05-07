# Project: mate1 — Current State
_Last updated: 2026-05-07_

## Project Overview
**ANZSCO Code Finder** — A tool for skilled migrants to identify the correct ANZSCO occupation code for Australian visa applications, without paying a migration agent.

**Who it's for**: Foreign skilled workers applying for Australian visas.
**Core problem**: Getting the wrong ANZSCO code = visa refusal, failed skills assessment ($500–$1,500 in fees), years of delay.
**Current team**: Peter + Máté (validation). No investor demo planned.
**Regulatory position**: Information tool, not migration advice. Strong disclaimers required.

---

## Live Products

| Product | URL | Status |
|---|---|---|
| Landing page | https://kzkvh2.github.io/ANZSCO/ | Live — waitlist, Web3Forms email capture working |
| Streamlit app | https://anzsco.streamlit.app/ | Live — full CV matching, public |
| GitHub repo | https://github.com/kzkvh2/ANZSCO | Public |

---

## Phased Plan

### Phase 0 — Data Pipeline ✅ COMPLETE
- Scraped 364 ANZSCO unit group pages from ABS (2022 edition)
- Built 1,076 composite documents (one per 6-digit occupation code)
- Each document: occupation title + alt titles + specialisations + unit group overview + task list + occupation description
- Median 167 words/document; 87% have task lists; 100% have occupation descriptions
- Update-check mechanism: SHA-256 checksums per source; changed sources flag `needs_review=True` on affected documents; human review required before going live

### Phase 1 — Matching Engine ✅ COMPLETE
- Embeddings: all-MiniLM-L6-v2, shape (1076, 384), stored in `data/processed/anzsco_embeddings.npy` (gitignored, auto-rebuilt on cold start)
- CV parser: pdfminer.six (PDF) + python-docx (Word)
- Pipeline: Claude Sonnet extracts structured profile → cosine similarity top 20 → Claude Haiku re-ranks to top 5 with explanations
- Match quality score: 0–100 per result, confidence: high/medium/low
- Parsability score: composite of word count + encoding quality + structure + CV signal keywords

### Phase 2 — Demo App ✅ DEPLOYED
- Streamlit app at `app/streamlit_app.py`, live at https://anzsco.streamlit.app/
- st.cache_resource preloads model + embeddings at startup (avoids per-request rebuild)
- First cold start ~1 min (model download + embedding rebuild on Streamlit Cloud)
- Shows parsability score with tier-specific actionable guidance (≥70/50-70/<50)
- Shows top 5 matches with match score bar, confidence indicator, and 1-sentence explanation
- Timing breakdown shown
- Disclaimer and Home Affairs link shown
- Run locally: `ANTHROPIC_API_KEY=sk-ant-... .venv/bin/streamlit run app/streamlit_app.py`

### Phase 3 — Acceptance Test ✅ PASSED (2026-05-07)
- Top-5 accuracy: **10/10 (100%)** — target was ≥8/10
- Top-1 accuracy: **8/10 (80%)** — target was ≥5/10
- Avg time: 10.4s/CV (cold model load amortised after first call)
- Two misses on #1: Marketing Manager (got Sales & Marketing Manager — acceptable), HR Manager (got 132311 vs 132111 — one digit off, same level)
- Full results: `tests/acceptance/last_run.json`
- **Caveat**: All 10 CVs are synthetic, mid-career, written by us. Real-world accuracy unvalidated.

### Phase 4 — Landing Page ✅ COMPLETE
- Live at https://kzkvh2.github.io/ANZSCO/ (GitHub Pages, served from /docs)
- Waitlist-only — tool not linked from landing page
- Web3Forms email capture working (access key in HTML); emails forward to lizanpeter@gmail.com
- SEO meta tags, OG tags, canonical URL set
- Deployed via GitHub Pages on main branch /docs folder

### Phase 5 — Agent Extension (Later)
- Bulk CV upload
- PDF report output
- API for migration agent platforms
- Visa pathway overlay, assessing body guidance

---

## Strategic Backlog / Known Issues

### Critical (before scaling traffic)
- **No analytics**: Don't know if anyone is using the app, what accuracy looks like in production
- **No feedback mechanism**: No way for users to signal whether results were helpful or wrong
- **Disconnected products**: Landing page (waitlist) and app are not linked. Users who sign up don't get app access. App is public but unadvertised.
- **Cold start UX**: ~1 min first load on Streamlit Cloud after inactivity. Users will think it's broken.
- **Acceptance test validity**: 10 synthetic CVs written by us. Not a real-world accuracy benchmark.

### Matching Quality
- **Seniority & tenure not considered**: A candidate with 20 years IT management experience may match ICT Support Technician (junior code). Profile extraction captures seniority but re-ranker doesn't use it. Fix: add seniority/skill-level signal to re-rank prompt.

### Product/Strategic
- **Monetisation path undefined**: Tool is free and unlinked. No freemium gate, no conversion funnel.
- **Mobile UX**: Streamlit is desktop-first. Target audience (Indian, Filipino, Nepali applicants) is mobile-heavy.
- **Streamlit is not a long-term platform**: Generic look, no custom branding, poor mobile, no session persistence.
- **Real user validation needed**: 10 real users with real CVs, not synthetic test cases.

---

## MVP Specification

### Input
- CV upload (PDF or Word), English only
- ATS/parsability score displayed alongside results

### Output
- Top 5 ANZSCO matches, ranked
- Each: 6-digit code + title + 1-sentence match explanation + match quality score (0–100)

### Data — CRITICAL
- Source: ANZSCO 2022 (ABS). Must always be current.
- Update mechanism: checksum-based change detection → human review before live
- Re-run scraper a few times per year or on ABS release

---

## Tech Stack (MVP)

| Component | Tool | Why |
|---|---|---|
| Data pipeline | Custom scraper (requests + BeautifulSoup) | Direct ABS source, versioned |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Fast, local, no API cost for indexing |
| Vector search | numpy cosine similarity | 1,076 items — no DB needed |
| LLM (re-rank + explain) | Claude API (claude-haiku-4-5 + claude-sonnet-4-6) | Best reasoning, prompt caching |
| CV parsing | pdfminer.six + python-docx | Handles PDF and Word |
| ATS score | textstat + word count heuristics | Simple parsability signal |
| Demo app | Streamlit (anzsco.streamlit.app) | Fast to build; not a long-term platform |
| Landing page | HTML + Tailwind CSS (GitHub Pages) | Zero hosting cost |
| Email capture | Web3Forms (free) | Zero setup, no backend |

---

## Environment
- Python 3.12.3 (WSL Ubuntu)
- Venv: `~/projects/mate1/.venv`
- Jupyter kernel: `mate1`
- Notebook: `analysis/anzsco_research.ipynb`

## Project Structure
```
mate1/
├── current_state.md              ← read this first each session
├── requirements.txt              ← pip dependencies for Streamlit Cloud
├── .streamlit/config.toml        ← brand colours, upload limit
├── .venv/                        ← Python 3.12 virtual environment
├── analysis/
│   └── anzsco_research.ipynb     ← data exploration notebook
├── data/
│   ├── raw/
│   │   ├── anzsco_structure.xlsx
│   │   ├── anzsco_index.xlsx
│   │   ├── checksums.json
│   │   ├── change_log.json
│   │   └── unit_group_pages/     ← 364 cached HTML pages (gitignored)
│   └── processed/
│       ├── anzsco_documents.json ← 1,076 composite documents (committed)
│       ├── anzsco_metadata.json  ← code/title index (committed)
│       ├── embeddings_hash.txt   ← SHA-256 of documents (committed)
│       └── anzsco_embeddings.npy ← embedding vectors (gitignored, auto-rebuilt)
├── src/
│   ├── scraper/anzsco_scraper.py
│   └── rag/
│       ├── cv_parser.py
│       ├── embedder.py
│       └── matcher.py            ← preload() + match_cv()
├── tests/acceptance/
│   ├── acceptance_test.py
│   ├── smoke_test.py
│   └── last_run.json             ← gitignored
├── docs/                         ← Landing page (GitHub Pages)
│   └── index.html
└── app/
    └── streamlit_app.py          ← Demo app (Streamlit Cloud)
```

## Context Management Convention
- This file is the single source of truth. Read it at the start of every session.
- Update it at the end of each session or after a significant milestone.

---

## Data Findings

### Findings — 2026-05-07 (Phase 4 complete, all MVP phases done)
- Landing page live with working email capture (Web3Forms confirmed working end-to-end)
- Streamlit app deployed at anzsco.streamlit.app (Streamlit Community Cloud)
- Assessing body links removed from results — confusing, premature for monetisation
- Key deployment detail: anzsco_embeddings.npy is gitignored; Streamlit Cloud auto-rebuilds via build_embeddings() on cold start; st.cache_resource prevents rebuild per re-run

### Findings — 2026-05-07 (Phase 3 complete)
- Top-5 accuracy: 10/10 (100%) — target was ≥8/10
- Top-1 accuracy: 8/10 (80%) — target was ≥5/10
- Avg time: 10.4s/CV

### Findings — 2026-05-07 (Phase 1 complete)
- Embeddings built: 1,076 docs × 384 dimensions, 33s on CPU
- Full pipeline: CV text → Claude profile extraction → cosine similarity (top 20) → Claude re-rank → top 5
- Two Claude calls per CV: extract profile (Sonnet) + re-rank (Haiku). Both use prompt caching.

### Findings — 2026-05-07 (Phase 0 complete)
- ABS provides direct Excel downloads — no fragile web scraping needed for structure data
- 1,076 six-digit occupation codes across 364 unit groups
- 467 alternative job titles + 1,408 specialisations in index file
- Composite documents: median 167 words, 87% have task lists, 100% have occupation descriptions
- Checksum-based update mechanism operational: tracks 366 sources

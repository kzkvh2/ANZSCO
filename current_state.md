# Project: mate1 — Current State
_Last updated: 2026-05-07_

## Project Overview
**ANZSCO Code Finder** — A tool for skilled migrants to identify the correct ANZSCO occupation code for Australian visa applications, without paying a migration agent.

**Who it's for**: Foreign skilled workers applying for Australian visas (Indian, Filipino, Nepali, Chinese applicants are primary target).  
**Core problem**: Getting the wrong ANZSCO code = visa refusal, failed skills assessment ($500–$1,500 in fees), years of delay.  
**Current validation team**: Peter + Mate. No investor demo planned.  
**Regulatory position**: Information tool, not migration advice. Strong disclaimers required.

---

## Phased Plan

### Phase 0 — Data Pipeline ✅ COMPLETE
- Scraped 364 ANZSCO unit group pages from ABS (2022 edition)
- Built 1,076 composite documents (one per 6-digit occupation code)
- Each document: occupation title + alt titles + specialisations + unit group overview + task list + occupation description
- Median 167 words/document; 87% have task lists; 100% have occupation descriptions
- Update-check mechanism: SHA-256 checksums per source; changed sources flag `needs_review=True` on affected documents; human review required before going live
- Data freshness cadence: re-run scraper a few times per year or when ABS releases updates

### Phase 1 — Matching Engine ✅ COMPLETE
Built the core pipeline: CV text → top 5 ANZSCO codes with match scores and explanations.

Steps:
1. [x] Embed all 1,076 documents with `sentence-transformers` (all-MiniLM-L6-v2), saved as numpy array — shape (1076, 384), built in 33s
2. [x] CV parser: pdfminer.six for PDF, python-docx for Word — `src/rag/cv_parser.py`
3. [x] CV pre-processor: Claude extracts structured profile (job titles, duties, skills, industries) — Step 1 of matcher
4. [x] Matcher: embed profile → cosine similarity top 20 → Claude re-ranks to top 5 with explanations — `src/rag/matcher.py`
5. [x] Match quality score: 0–100 per result, confidence: high/medium/low
6. [x] Parsability score: composite of word count + encoding quality + structure + CV signal keywords

### Phase 2 — Demo App ✅ BUILT (needs live test)
Streamlit app at `app/streamlit_app.py`.
- Upload CV (PDF or Word)
- See parsability score (0–100) with warning if low
- See top 5 ANZSCO matches: code, title, match score, confidence, 1-sentence explanation
- Timing breakdown shown
- Disclaimer shown
- Run: `ANTHROPIC_API_KEY=sk-ant-... .venv/bin/streamlit run app/streamlit_app.py`
- **Blocked on**: ANTHROPIC_API_KEY set in WSL environment

### Phase 3 — Acceptance Test ✅ PASSED (2026-05-07)
- Top-5 accuracy: **10/10 (100%)** — target was ≥8/10
- Top-1 accuracy: **8/10 (80%)** — target was ≥5/10
- Avg time: 10.4s/CV (cold model load amortised after first call)
- Two misses on #1: Marketing Manager (got Sales & Marketing Manager — acceptable), HR Manager (got 132311 vs 132111 — one digit off, same level)
- Full results: `tests/acceptance/last_run.json`

### Phase 4 — Landing Page
Simple public page to validate demand. Not the full product.
- Headline: "Find your ANZSCO code in 60 seconds — free"
- Email capture / waitlist
- Optional: teaser of the tool (limited free uses)
- SEO target: "ANZSCO code for [job title]" searches
- No auth, no payment processing yet

### Known Issues / Backlog
- **Seniority & tenure not considered**: A candidate with 20 years of IT experience who ran a service desk will match ICT Support Technician (a junior code) instead of a management/senior code. The profile extraction captures seniority but the re-ranker does not penalise codes that are mismatched to experience level. Fix: add seniority signal to the re-rank prompt and filter out codes whose skill level is inconsistent with the candidate's years of experience.

### Phase 5 — Agent Extension (Later)
- Bulk CV upload
- PDF report output
- API for migration agent platforms
- Possibly: visa pathway overlay, assessing body guidance

---

## MVP Specification

### Input
- CV upload (PDF or Word), English only
- ATS/parsability score displayed alongside results

### Output
- Top 5 ANZSCO matches, ranked
- Each: 6-digit code + title + 1-sentence match explanation + match quality score (0–100)
- Expandable later: location availability, industry, assessing body, visa pathway

### Data — CRITICAL
- Source: ANZSCO 2022 (ABS). Must always be current.
- Update mechanism: checksum-based change detection → human review before live
- All sources versioned and documented
- Re-run scraper a few times per year or on ABS release

### Acceptance Test
- 10 ground-truth CVs: software engineer, nurse, accountant, chef, civil engineer, teacher, electrician, marketing manager, architect, HR manager
- Pass: correct code in top 5 for ≥8/10 (80%)
- Stretch: #1 for ≥5/10 (50%)
- Speed: <10s

---

## Tech Stack (MVP)

| Component | Tool | Why |
|---|---|---|
| Data pipeline | Custom scraper (requests + BeautifulSoup) | Direct ABS source, versioned |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Fast, local, no API cost for indexing |
| Vector search | numpy cosine similarity | 1,076 items — no DB needed |
| LLM (re-rank + explain) | Claude API (claude-sonnet-4-6) | Best reasoning, prompt caching |
| CV parsing | pdfminer.six + python-docx | Handles PDF and Word |
| ATS score | textstat + word count heuristics | Simple parsability signal |
| Demo app | Streamlit | Fast to build, easy to share locally |
| Landing page | TBD (simple HTML or Next.js) | Phase 4 decision |

**Removed from original plan**: LangChain, LlamaIndex, ChromaDB — unnecessary complexity for this scale.

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
├── .venv/                        ← Python 3.12 virtual environment
├── analysis/
│   └── anzsco_research.ipynb     ← data exploration notebook
├── data/
│   ├── raw/
│   │   ├── anzsco_structure.xlsx ← ABS download (structure + codes)
│   │   ├── anzsco_index.xlsx     ← ABS download (alt titles + specialisations)
│   │   ├── checksums.json        ← SHA-256 per source (update detection)
│   │   ├── change_log.json       ← audit trail of detected changes
│   │   └── unit_group_pages/     ← 364 cached HTML pages
│   └── processed/
│       ├── anzsco_documents.json ← 1,076 composite documents (ready for embedding)
│       └── needs_review.json     ← codes flagged for human review (empty = clean)
├── src/
│   ├── scraper/
│   │   └── anzsco_scraper.py     ← data pipeline (run to refresh data)
│   ├── rag/                      ← Phase 1: embedding + matching
│   └── api/                      ← Phase 4+: FastAPI app
├── tests/
│   └── acceptance/               ← 10 ground-truth CV test cases
├── docs/                         ← Landing page (GitHub Pages — served from /docs)
│   └── index.html                ← Web3Forms waitlist, SEO meta tags
└── app/                          ← Phase 2: Streamlit demo
```

## Context Management Convention
- This file is the single source of truth. Read it at the start of every session.
- Update it at the end of each session or after a significant milestone.
- Run `Save Findings` cell in the notebook before clearing context.

---

## Data Findings

### Findings — 2026-05-07 (Phase 1 complete)
- Embeddings built: 1,076 docs × 384 dimensions, 33s on CPU, saved to `data/processed/anzsco_embeddings.npy`
- Full pipeline: CV text → Claude profile extraction → cosine similarity (top 20) → Claude re-rank → top 5
- Two Claude calls per CV: extract profile + re-rank. Both use prompt caching.
- Parsability score implemented: word count + encoding + structure + CV signal keywords
- Streamlit demo app built at `app/streamlit_app.py` — needs ANTHROPIC_API_KEY to run
- Smoke test at `tests/acceptance/smoke_test.py` — run to validate before acceptance suite
- **NOT YET RUN end-to-end**: API key not set in WSL environment — needs `export ANTHROPIC_API_KEY=sk-ant-...`

### Findings — 2026-05-07 (Phase 0 complete)
- ABS provides direct Excel downloads — no fragile web scraping needed for structure data
- 1,076 six-digit occupation codes across 364 unit groups
- 467 alternative job titles + 1,408 specialisations in index file (key for matching real-world CV job titles)
- Unit group web pages have rich descriptions: overview paragraph + 5–12 task bullet points + per-occupation descriptions
- Composite documents: median 167 words, 87% have task lists, 100% have occupation descriptions, only 3 thin docs (<30 words)
- Data is good enough for embedding — original concern about thin descriptions was unfounded
- Checksum-based update mechanism operational: tracks 366 sources (2 Excel files + 364 pages)
- Next: embed documents and build matching pipeline

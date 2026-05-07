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

---

## Roadmap & Strategy

### Where we are
Two live products (landing page + Streamlit demo) with a working matching engine (100% top-5 / 80% top-1 on synthetic test cases). Waitlist collecting emails. No real users validated. No funnel between the two products. Tool is publicly accessible but not advertised.

### Where we want to be (6 months)
A validated, monetisable product with real user accuracy data, a growing organic user base, and a clear conversion path from free → paid. The Streamlit demo is replaced by a purpose-built, mobile-friendly web app.

### How we get there

| # | Initiative | Type | Priority | Impact | Effort | Timeline | Cost | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | **Funnel fix** — show app link after signup | GTM | 🔴 Critical | High | Done | ✅ Done | Free | — |
| 2 | **Real user test** — 10 real CVs from real people | Validation | 🔴 Critical | High | Low | This week | Free | App live |
| 3 | **Feedback button** — thumbs up/down on results | Product | 🔴 Critical | High | Low | This week | Free | App live |
| 4 | **Cold start UX** — explain the ~1 min wait | Product | 🟠 High | Med | Low | This week | Free | — |
| 5 | **Outreach phase 1** — Reddit/Whirlpool/Facebook seeding | GTM | 🟠 High | High | Med | This week | Free | Funnel fix |
| 6 | **Testimonials** — 2–3 real users, quote + occupation | GTM | 🟠 High | High | Low | 2 weeks | Free | Real users |
| 7 | **SEO content** — blog/FAQ targeting "ANZSCO code for [job]" | GTM | 🟠 High | High | Med | 2–4 weeks | Free | Landing page |
| 8 | **Email nurture** — 2-step sequence for waitlist | GTM | 🟠 High | Med | Low | 2 weeks | Free | Email tool |
| 9 | **Seniority fix** — add experience-level signal to re-ranker | Tech | 🟡 Medium | Med | Med | 1 month | Free | — |
| 10 | **Freemium gate** — email required after 3 free uses | Product | 🟡 Medium | High | High | 1 month | Free | Auth/session |
| 11 | **Analytics** — usage tracking, accuracy in production | Tech | 🟡 Medium | Med | Low | 1 month | Free | — |
| 12 | **Purpose-built web app** — replace Streamlit (mobile-first) | Tech | 🟡 Medium | High | High | 2–3 months | Low | Funding/time |
| 13 | **B2B pitch** — migration agents, RTOs, education providers | GTM | 🟡 Medium | Very High | High | 2–3 months | Low | Validation |
| 14 | **PDF report output** — downloadable results | Product | 🟢 Low | Med | Med | 3+ months | Free | — |
| 15 | **API** — for integration with agent platforms | Tech | 🟢 Low | High | High | 6+ months | — | B2B validated |
| 16 | **Visa pathway overlay** — which visa each code qualifies for | Product | 🟢 Low | High | High | 6+ months | — | Legal review |

### Strategic decisions to make (not yet decided)
- **Monetisation model**: Freemium individual (3 free → paid) vs B2B (sell to agents/RTOs) vs both. B2B has higher ACV and no payment friction for individual migrants; but longer sales cycle.
- **Platform**: Streamlit → purpose-built Next.js/FastAPI app. Trigger: when you have validated users and are ready to invest in product.
- **Email infrastructure**: Web3Forms is fine for the waitlist. Need Brevo/Mailchimp free tier for nurture sequences (Web3Forms doesn't send to submitters).

### Outreach plan (Phase 1 — this week)
Target: grow waitlist to 100 signups. All organic, free, no ads.

**Where to post:**
| Channel | Specific targets | Message angle |
|---|---|---|
| Reddit | r/AusVisa, r/australia, r/ImmigrationAustralia | Answer existing ANZSCO questions, link tool |
| Whirlpool.net.au | Visa & immigration forum | Same approach — answer first, share link |
| Facebook groups | "Australia PR/Visa", "Indians in Australia", "Filipinos in Australia" | Post as helpful resource, not an ad |
| LinkedIn | Personal post as founder | "I built this because..." story format |
| YouTube | Comments on ANZSCO explainer videos | Answer question, mention free tool |

**Rules for every post:**
1. Answer the question genuinely first. Add the link second.
2. Never post the same message twice (spam filters + community bans)
3. Disclose you built it when sharing
4. Target posts where someone is actively confused about their ANZSCO code

**Message template (adapt per channel):**
> "Finding your ANZSCO code is genuinely confusing — there are 1,076 of them and the descriptions are written in bureaucratic language. I built a free tool that reads your CV and matches it to the right code. Early days but it's worked well so far: [link]. No account, no cost."

---

## Known Issues / Backlog

| Issue | Severity | Fix |
|---|---|---|
| Seniority/tenure ignored in matching | High | Add experience-level signal to re-rank prompt |
| Acceptance test uses synthetic CVs only | High | Run 10 real user CVs, update pass/fail criteria |
| No user feedback mechanism | High | Add thumbs up/down to Streamlit app |
| Cold start ~1 min on Streamlit Cloud | High | Explain in UI; long-term: replace platform |
| No production accuracy data | High | Add logging; review first 20 real runs |
| No email nurture sequence | Med | Set up Brevo free tier, 2-email sequence |
| Mobile UX poor on Streamlit | Med | Long-term: replace with purpose-built app |
| No usage analytics | Med | Add basic logging or Streamlit analytics |
| Streamlit is not a long-term platform | Med | Plan Next.js/FastAPI app for v2 |
| No monetisation gate | Low (now) | Freemium after validation |

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

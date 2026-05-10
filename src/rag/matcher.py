"""
Core matching pipeline.

Flow:
  1. Claude extracts structured profile from raw CV text
     (job titles, duties, skills — strips noise like dates/addresses)
  2. Embed the structured profile with sentence-transformers
  3. Cosine similarity against 1,076 ANZSCO document embeddings → top 20
  4. Claude re-ranks top 20 → returns top 5 with explanations + scores
  5. Return ranked list with match quality score (0–100)

The two Claude calls use prompt caching on the ANZSCO context so the
system prompt is only billed once per cache TTL (5 min).
"""

import json
import os
import re
import numpy as np
import anthropic
from sentence_transformers import SentenceTransformer

from src.rag.embedder import build_embeddings, embed_query, MODEL_NAME

MODEL_EXTRACT = 'claude-haiku-4-5-20251001'  # structured extraction — Haiku is accurate and ~4x cheaper than Sonnet
MODEL_RERANK  = 'claude-haiku-4-5-20251001'  # re-ranking — classification task, speed matters
_st_model: SentenceTransformer | None = None
_embeddings: np.ndarray | None = None
_metadata: list[dict] | None = None


def _get_st_model() -> SentenceTransformer:
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer(MODEL_NAME)
    return _st_model


def _get_index() -> tuple[np.ndarray, list[dict]]:
    global _embeddings, _metadata
    if _embeddings is None:
        _embeddings, _metadata = build_embeddings()
    return _embeddings, _metadata


def preload() -> None:
    """Warm the module-level model and index cache. Call once at app startup."""
    _get_st_model()
    _get_index()


def _claude_client() -> anthropic.Anthropic:
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise EnvironmentError(
            'ANTHROPIC_API_KEY not set. '
            'Run: export ANTHROPIC_API_KEY=sk-ant-...'
        )
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# Step 1: Extract structured profile from raw CV text
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM = """You are a CV analyst. Extract the core professional profile from a CV.
Return ONLY a JSON object with these fields:
- name: full name of the person as it appears at the top of the CV (string, or null if not clearly present)
- job_titles: list of job titles the person has held (most recent first)
- duties: list of key duties and responsibilities (bullet point style, max 15)
- skills: list of technical and professional skills
- industries: list of industries worked in
- seniority: estimated seniority level (junior/mid/senior/lead/manager/executive)

Be specific. Use the exact language from the CV. Do not invent or infer beyond what is written."""

def extract_cv_profile(raw_text: str, client: anthropic.Anthropic) -> dict:
    """Use Claude to extract structured profile from raw CV text."""
    response = client.messages.create(
        model=MODEL_EXTRACT,
        max_tokens=1024,
        system=EXTRACT_SYSTEM,
        messages=[{
            'role': 'user',
            'content': f'Extract the professional profile from this CV:\n\n{raw_text[:6000]}'
        }]
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: return raw text as duties list
        return {'job_titles': [], 'duties': [raw_text[:500]], 'skills': [], 'industries': [], 'seniority': ''}


def profile_to_query(profile: dict) -> str:
    """Convert structured profile to a single embedding query string."""
    parts = []
    if profile.get('job_titles'):
        parts.append('Job titles: ' + ', '.join(profile['job_titles'][:5]))
    if profile.get('duties'):
        parts.append('Duties: ' + '; '.join(profile['duties'][:10]))
    if profile.get('skills'):
        parts.append('Skills: ' + ', '.join(profile['skills'][:15]))
    if profile.get('industries'):
        parts.append('Industries: ' + ', '.join(profile['industries'][:3]))
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Step 2+3: Embed + cosine similarity retrieval
# ---------------------------------------------------------------------------

MIN_COSINE_SCORE = 0.50  # discard anything below this — likely irrelevant

def retrieve_candidates(query_text: str, top_k: int = 20) -> list[dict]:
    """Embed query, compute cosine similarity, return top_k candidates above threshold."""
    model      = _get_st_model()
    embeddings, metadata = _get_index()

    query_vec  = embed_query(query_text, model)
    scores     = embeddings @ query_vec          # cosine sim (embeddings are normalized)

    ranked = np.argsort(scores)[::-1]
    candidates = []
    for i in ranked:
        if len(candidates) >= top_k:
            break
        if scores[i] < MIN_COSINE_SCORE:
            break  # sorted descending — everything below is worse
        meta = metadata[i]
        candidates.append({
            'code':            meta['code'],
            'title':           meta['title'],
            'unit_title':      meta['unit_title'],
            'minor_title':     meta['minor_title'],
            'sub_major_title': meta['sub_major_title'],
            'major_title':     meta['major_title'],
            'skill_level':     meta['skill_level'],
            'alt_titles':      meta['alt_titles'],
            'specialisations': meta['specialisations'],
            'embedding_text':  meta['embedding_text'],
            'cosine_score':    float(scores[i]),
        })

    # If fewer than 5 passed the threshold, lower the floor and fill up to 5
    # so Claude always has something to work with
    if len(candidates) < 5:
        for i in ranked[len(candidates):]:
            if len(candidates) >= 5:
                break
            meta = metadata[i]
            candidates.append({
                'code':            meta['code'],
                'title':           meta['title'],
                'unit_title':      meta['unit_title'],
                'minor_title':     meta['minor_title'],
                'sub_major_title': meta['sub_major_title'],
                'major_title':     meta['major_title'],
                'skill_level':     meta['skill_level'],
                'alt_titles':      meta['alt_titles'],
                'specialisations': meta['specialisations'],
                'embedding_text':  meta['embedding_text'],
                'cosine_score':    float(scores[i]),
            })

    return candidates


# ---------------------------------------------------------------------------
# Step 4: Claude re-ranks top 20 → top 5 with explanations
# ---------------------------------------------------------------------------

RERANK_SYSTEM = """You are an ANZSCO occupation classification expert.
Your job is to select the 5 best-matching ANZSCO occupation codes for a given candidate profile.

STRICT RULES:
- Use ONLY codes and titles from the provided candidate list. Never invent codes or titles.
- Copy the "code" and "title" fields EXACTLY as they appear in the candidate list.

For each of your top 5 selections return:
- code: the 6-digit ANZSCO code (copy exactly from candidate list)
- title: the occupation title (copy exactly from candidate list — do NOT paraphrase or substitute)
- match_score: integer 0-100 (how well this code fits this person)
- explanation: one sentence explaining why this code fits, referencing specific duties or skills from the CV
- confidence: "high" | "medium" | "low"

Return ONLY a JSON array of 5 objects. No other text."""

def rerank_with_claude(profile: dict, candidates: list[dict],
                       client: anthropic.Anthropic) -> list[dict]:
    """Claude re-ranks the top 20 embedding candidates → top 5 with explanations."""

    profile_text = json.dumps(profile, indent=2)
    candidates_text = json.dumps([{
        'code': c['code'],
        'title': c['title'],
        'field': f"{c['major_title']} > {c['sub_major_title']}",
        'description': c['embedding_text'][:400],
        'cosine_score': round(c['cosine_score'], 3),
    } for c in candidates], indent=2)

    response = client.messages.create(
        model=MODEL_RERANK,
        max_tokens=2048,
        system=[{
            'type': 'text',
            'text': RERANK_SYSTEM,
            'cache_control': {'type': 'ephemeral'},
        }],
        messages=[{
            'role': 'user',
            'content': (
                f'Candidate profile:\n{profile_text}\n\n'
                f'Top 20 ANZSCO candidates from semantic search:\n{candidates_text}\n\n'
                'Select and rank the best 5 matches.'
            )
        }]
    )

    text = response.content[0].text.strip()
    text = re.sub(r'^```(?:json)?\n?', '', text)
    text = re.sub(r'\n?```.*$', '', text, flags=re.DOTALL)
    # Extract just the JSON array in case the model added trailing commentary
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_cv(raw_cv_text: str, top_k_candidates: int = 20) -> dict:
    """
    Full pipeline: raw CV text → top 5 ANZSCO matches.

    Returns:
    {
        profile:    dict,        # extracted structured profile
        results:    list[dict],  # top 5 matches with scores + explanations
        timing:     dict,        # ms per stage
    }
    """
    import time
    timings = {}
    client = _claude_client()

    t0 = time.perf_counter()
    profile = extract_cv_profile(raw_cv_text, client)
    timings['extract_profile_ms'] = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    query_text = profile_to_query(profile)
    candidates = retrieve_candidates(query_text, top_k=top_k_candidates)
    timings['retrieval_ms'] = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    results = rerank_with_claude(profile, candidates, client)
    timings['rerank_ms'] = int((time.perf_counter() - t0) * 1000)

    timings['total_ms'] = sum(timings.values())

    return {
        'profile':  profile,
        'results':  results,
        'timing':   timings,
    }

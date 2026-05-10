"""
ANZSCO Code Finder — Demo App
Upload a CV (PDF or Word) and get top ANZSCO matches.

Run:
  cd ~/projects/mate1
  ANTHROPIC_API_KEY=sk-ant-... .venv/bin/streamlit run app/streamlit_app.py
"""

import sys, pathlib, hashlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import os
import urllib.parse
import requests
import streamlit as st
from src.rag.cv_parser import extract_text, parsability_score
from src.rag.matcher import match_cv, preload
from src.jobs import fetch_jobs_for_codes, seek_search_url, indeed_search_url, linkedin_search_url

WEB3FORMS_KEY = '7fdb3ee2-ba92-4fed-bcd8-ecc37e4e39a3'

# Wire Apify token from Streamlit secrets into env so src/jobs.py can read it.
try:
    if 'APIFY_TOKEN' in st.secrets:
        os.environ['APIFY_TOKEN'] = st.secrets['APIFY_TOKEN']
except Exception:
    pass


def _score_label(score: int) -> str:
    if score >= 90: return 'Excellent match'
    if score >= 70: return 'Strong match'
    return 'Partial match'


def _render_jobs(jobs: dict, title: str) -> None:
    seek_jobs   = jobs.get('seek', [])
    li_jobs     = jobs.get('linkedin', [])
    indeed_jobs = jobs.get('indeed', [])

    col_seek, col_li, col_indeed = st.columns(3)

    with col_seek:
        st.markdown('**SEEK**')
        if seek_jobs:
            for j in seek_jobs:
                st.markdown(
                    f'[{j["title"]}]({j["url"]})\n\n'
                    f'<small>{j["company"]} · {j["location"]}'
                    + (f' · {j["salary"]}' if j.get('salary') else '')
                    + '</small>',
                    unsafe_allow_html=True,
                )
                st.write('')
        else:
            st.markdown(f'[Search all SEEK listings →]({seek_search_url(title)})')

    with col_li:
        st.markdown('**LinkedIn**')
        if li_jobs:
            for j in li_jobs:
                st.markdown(
                    f'[{j["title"]}]({j["url"]})\n\n'
                    f'<small>{j["company"]} · {j["location"]}</small>',
                    unsafe_allow_html=True,
                )
                st.write('')
        else:
            st.markdown(f'[Search all LinkedIn listings →]({linkedin_search_url(title)})')

    with col_indeed:
        st.markdown('**Indeed**')
        if indeed_jobs:
            for j in indeed_jobs:
                st.markdown(
                    f'[{j["title"]}]({j["url"]})\n\n'
                    f'<small>{j["company"]} · {j["location"]}'
                    + (f' · {j["salary"]}' if j.get('salary') else '')
                    + '</small>',
                    unsafe_allow_html=True,
                )
                st.write('')
        else:
            st.markdown(f'[Search all Indeed listings →]({indeed_search_url(title)})')


def _send_feedback(thumbs_up: bool, results: list[dict]) -> None:
    top = results[0] if results else {}
    all_codes = ', '.join(f"{r['code']} {r['title']}" for r in results)
    try:
        requests.post(
            'https://api.web3forms.com/submit',
            data={
                'access_key': WEB3FORMS_KEY,
                'subject': f'ANZSCO Finder — {"👍" if thumbs_up else "👎"} feedback',
                'top_result': f"{top.get('code')} {top.get('title')} ({top.get('match_score')}/100)",
                'all_results': all_codes,
                'feedback': 'Helpful' if thumbs_up else 'Not helpful',
            },
            timeout=5,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit command
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title='ANZSCO Code Finder',
    page_icon='🎯',
    layout='centered',
)


@st.cache_resource(show_spinner="Loading ANZSCO knowledge base — first launch takes ~1 min...")
def _preload():
    preload()

_preload()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title('ANZSCO Code Finder')
st.markdown(
    'Upload your CV to find your ANZSCO occupation code — required for Australian skilled migration visa applications. '
    'We match your experience against all 1,076 ANZSCO codes.'
)
st.caption(
    '_Guidance only — not migration advice. Always verify your code against the '
    '[Home Affairs skilled occupation list](https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list) '
    'before submitting a visa application._'
)

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
st.markdown('---')
st.markdown('**Upload your CV** — PDF or Word document, English only.')
uploaded = st.file_uploader(
    'Upload CV',
    type=['pdf', 'docx', 'doc'],
    label_visibility='collapsed',
)

if not uploaded:
    st.stop()

file_bytes = uploaded.getvalue()
file_hash  = hashlib.md5(file_bytes).hexdigest()

# ---------------------------------------------------------------------------
# Step 1 — Parse CV (cached per file)
# ---------------------------------------------------------------------------
parse_key = f'parse_{file_hash}'
if parse_key not in st.session_state:
    with st.spinner('Reading your CV — typically under 10 seconds...'):
        try:
            raw_text = extract_text(file_bytes, uploaded.name)
        except Exception as e:
            st.error(f'Could not read file: {e}')
            st.stop()
        parse_result = parsability_score(raw_text)
    st.session_state[parse_key] = {'raw_text': raw_text, 'parse_result': parse_result}

cached       = st.session_state[parse_key]
raw_text     = cached['raw_text']
parse_result = cached['parse_result']
readability  = parse_result['overall']

col1, col2 = st.columns([1, 3])
with col1:
    st.metric('CV Readability', f'{readability}/100')
with col2:
    if readability >= 70:
        st.success(f'Read cleanly — {parse_result["word_count"]} words extracted.')
    elif readability >= 40:
        st.warning(
            f'Partially readable — {parse_result["word_count"]} words extracted. '
            'Results may be less accurate. Try re-saving as a plain Word .docx if matches look off.'
        )
    else:
        st.error(
            f'Could not read clearly — only {parse_result["word_count"]} words extracted. '
            'For best results: open your CV, select all, paste into a new blank Word document, and re-upload.'
        )

# ---------------------------------------------------------------------------
# Step 2 — Match (auto, cached per file)
# ---------------------------------------------------------------------------
match_key = f'match_{file_hash}'
if match_key not in st.session_state:
    with st.spinner('Matching to 1,076 ANZSCO codes — typically 15 seconds...'):
        try:
            result = match_cv(raw_text)
        except EnvironmentError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f'Matching failed: {e}')
            raise
    st.session_state[match_key] = result

result  = st.session_state[match_key]
profile = result['profile']
results = result['results']

st.markdown('---')

if not results:
    st.warning(
        'No strong ANZSCO matches found. '
        'This usually means the CV text could not be extracted cleanly — '
        'try re-uploading as a plain Word .docx.'
    )
    st.stop()

# ---------------------------------------------------------------------------
# Name greeting
# ---------------------------------------------------------------------------
first_name = None
raw_name = (profile.get('name') or '').strip()
if len(raw_name) > 1:
    first_name = raw_name.split()[0]

if first_name:
    st.subheader(f'Hi {first_name} — here are your ANZSCO matches')
else:
    st.subheader('Your ANZSCO matches')

st.caption(
    'Confidence: 🟢 High  🟡 Medium  🔴 Low — '
    'reflects how well your CV aligns with the ANZSCO occupation definition'
)

# ---------------------------------------------------------------------------
# Results cards
# ---------------------------------------------------------------------------
CONFIDENCE_COLOUR = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}

for i, match in enumerate(results, 1):
    conf_icon = CONFIDENCE_COLOUR.get(match.get('confidence', 'low'), '🔴')
    label     = _score_label(match['match_score'])
    is_top    = (i == 1)

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            header = f'**#{i} — {match["code"]}  {match["title"]}**'
            if is_top:
                header += '  ⭐'
            st.markdown(header)
            st.caption(match.get('explanation', ''))
            st.markdown(f'[Search jobs on SEEK →]({seek_search_url(match["title"])})')
        with c2:
            st.markdown(f'**{match["match_score"]}/100** {conf_icon}')
            st.caption(label)

with st.expander('Debug — extracted profile & timing'):
    timing = result['timing']
    st.caption(
        f'Total: {timing["total_ms"]}ms  '
        f'(extract {timing["extract_profile_ms"]}ms · '
        f'retrieve {timing["retrieval_ms"]}ms · '
        f'rank {timing["rerank_ms"]}ms)'
    )
    if profile.get('job_titles'):
        st.write('**Job titles:**', ', '.join(profile['job_titles']))
    if profile.get('skills'):
        st.write('**Skills:**', ', '.join(profile['skills'][:15]))
    if profile.get('industries'):
        st.write('**Industries:**', ', '.join(profile['industries']))

# ---------------------------------------------------------------------------
# What to do next
# ---------------------------------------------------------------------------
st.markdown('---')
st.subheader('What to do next')
st.markdown(
    '1. **Note your top ANZSCO code** — this is what you will submit in your skills assessment application.\n'
    '2. **Verify your visa pathway** — confirm your code appears on the '
    '[Home Affairs skilled occupation list](https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list).\n'
    '3. **Find your assessing body** — each occupation is assessed by a specific authority; '
    'check the [skills assessment page](https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189/points-tested) '
    'to find yours.\n'
    '4. **Explore the job market** — use the job search below to gauge demand before you apply.'
)

# ---------------------------------------------------------------------------
# Live jobs — button-triggered
# ---------------------------------------------------------------------------
st.markdown('---')
qualifying = [m for m in results if m.get('match_score', 0) > 70]

if qualifying:
    person = f"{first_name}'s" if first_name else 'Your'
    st.subheader(f'Live job listings — {person} top matches')
    st.caption(
        f'{len(qualifying)} occupation{"s" if len(qualifying) > 1 else ""} scored above 70. '
        'Searches SEEK, LinkedIn, and Indeed simultaneously (~45 seconds).'
    )

    jobs_key = 'jobs_' + '_'.join(m['code'] for m in qualifying)

    if jobs_key not in st.session_state:
        n = len(qualifying)
        if st.button(
            f'Search live job boards for {n} occupation{"s" if n > 1 else ""}',
            key='search_jobs',
            type='primary',
        ):
            if not os.environ.get('APIFY_TOKEN'):
                st.session_state[jobs_key] = {m['code']: {} for m in qualifying}
            else:
                with st.spinner('Searching SEEK, LinkedIn, and Indeed...'):
                    try:
                        titles_by_code = {m['code']: m['title'] for m in qualifying}
                        st.session_state[jobs_key] = fetch_jobs_for_codes(titles_by_code, n=3)
                    except Exception:
                        st.session_state[jobs_key] = {m['code']: {} for m in qualifying}
            st.rerun()
    else:
        all_jobs = st.session_state[jobs_key]
        if len(qualifying) == 1:
            m = qualifying[0]
            _render_jobs(all_jobs.get(m['code'], {}), m['title'])
        else:
            tabs = st.tabs([f'{m["code"]} {m["title"]}' for m in qualifying])
            for tab, m in zip(tabs, qualifying):
                with tab:
                    _render_jobs(all_jobs.get(m['code'], {}), m['title'])

# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
st.markdown('---')
st.markdown('**Were these results helpful?**')
feedback_key = f'feedback_{file_hash}'
if st.session_state.get(feedback_key):
    st.success('Thanks for your feedback — it helps us improve the tool.')
else:
    col_up, col_down, _ = st.columns([1, 1, 6])
    with col_up:
        if st.button('👍  Yes', key='fb_up'):
            _send_feedback(True, results)
            st.session_state[feedback_key] = True
            st.rerun()
    with col_down:
        if st.button('👎  No', key='fb_down'):
            _send_feedback(False, results)
            st.session_state[feedback_key] = True
            st.rerun()

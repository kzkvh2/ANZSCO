"""
ANZSCO Code Finder — Demo App
Upload a CV (PDF or Word) and get top 5 ANZSCO matches.

Run:
  cd ~/projects/mate1
  ANTHROPIC_API_KEY=sk-ant-... .venv/bin/streamlit run app/streamlit_app.py
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import re
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


def _render_jobs(jobs: dict, title: str, code: str) -> None:
    """Render job results from SEEK, LinkedIn, and Indeed in three columns."""
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
            st.markdown(f'[Search all SEEK listings]({seek_search_url(title)})')

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
            st.markdown(f'[Search all LinkedIn listings]({linkedin_search_url(title)})')

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
            st.markdown(f'[Search all Indeed listings]({indeed_search_url(title)})')


def _send_feedback(thumbs_up: bool, top_results: list[dict]) -> None:
    top = top_results[0] if top_results else {}
    all_codes = ', '.join(f"{r['code']} {r['title']}" for r in top_results)
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

st.title('ANZSCO Code Finder')
st.caption('Upload your CV and get your top 5 ANZSCO occupation codes for Australian skilled migration visas.')

st.info(
    '**Disclaimer**: This tool provides information only and does not constitute migration advice. '
    'For a binding skills assessment, consult a registered MARA agent.',
    icon='ℹ️',
)

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
st.markdown('**Upload your CV** — PDF or Word document, English only.')
uploaded = st.file_uploader(
    'Upload CV',
    type=['pdf', 'docx', 'doc'],
    label_visibility='collapsed',
)

if uploaded:
    with st.spinner('Reading your CV...'):
        file_bytes = uploaded.read()
        try:
            raw_text = extract_text(file_bytes, uploaded.name)
        except Exception as e:
            st.error(f'Could not read file: {e}')
            st.stop()

    parse_result = parsability_score(raw_text)
    score = parse_result['overall']

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric('CV Readability', f'{score}/100')
    with col2:
        if score >= 70:
            st.success(f'CV read cleanly ({parse_result["word_count"]} words extracted). Good to go.')
        elif score >= 50:
            st.warning(
                f'CV partially readable ({parse_result["word_count"]} words extracted). '
                'Results may be less accurate — try re-saving as a plain Word .docx if matches look off.'
            )
        else:
            st.error(
                f'CV could not be read clearly (score {score}/100, {parse_result["word_count"]} words). '
                'For best results: open your CV, select all, paste into a new Word document, and re-upload.'
            )

    with st.expander('View extracted CV text'):
        st.text(raw_text[:2000] + ('...' if len(raw_text) > 2000 else ''))

    st.divider()

    if st.button('Find my ANZSCO codes', type='primary'):
        with st.spinner('Analysing your CV and matching ANZSCO codes... (~10 seconds)'):
            try:
                result = match_cv(raw_text)
            except EnvironmentError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(f'Matching failed: {e}')
                raise

        st.session_state['match_result'] = result

    if 'match_result' not in st.session_state:
        st.stop()

    result  = st.session_state['match_result']
    profile = result['profile']

    # Personalised greeting using extracted name
    first_name = None
    raw_name = profile.get('name') or ''
    if raw_name and len(raw_name.strip()) > 1:
        first_name = raw_name.strip().split()[0]

    if first_name:
        st.subheader(f'Hi {first_name} — here are your top ANZSCO matches')
    else:
        st.subheader('Your top 5 ANZSCO matches')

    with st.expander('What we extracted from your CV'):
        if profile.get('job_titles'):
            st.write('**Job titles:**', ', '.join(profile['job_titles']))
        if profile.get('skills'):
            st.write('**Skills:**', ', '.join(profile['skills'][:12]))
        if profile.get('industries'):
            st.write('**Industries:**', ', '.join(profile['industries']))

    CONFIDENCE_COLOUR = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}

    for i, match in enumerate(result['results'], 1):
        conf_icon = CONFIDENCE_COLOUR.get(match.get('confidence', 'low'), '🔴')
        score_bar = '█' * (match['match_score'] // 10) + '░' * (10 - match['match_score'] // 10)

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f'**#{i} — {match["code"]} {match["title"]}**')
                st.caption(match.get('explanation', ''))
                st.markdown(f'[Search jobs on SEEK]({seek_search_url(match["title"])})')
            with c2:
                st.markdown(f'**{match["match_score"]}/100** {conf_icon}')
                st.caption(f'`{score_bar}`')

    timing = result['timing']
    st.caption(
        f'Total: {timing["total_ms"]}ms '
        f'(extract {timing["extract_profile_ms"]}ms · '
        f'retrieve {timing["retrieval_ms"]}ms · '
        f'rank {timing["rerank_ms"]}ms)'
    )

    st.warning(
        'These codes are a guide only. Verify your final selection against the '
        '[Home Affairs skilled occupation list](https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list) '
        'before submitting a visa application.',
        icon='⚠️',
    )

    # -----------------------------------------------------------------------
    # Live jobs — auto-load for all matches scoring > 70
    # -----------------------------------------------------------------------
    qualifying = [m for m in result['results'] if m.get('match_score', 0) > 70]

    if qualifying:
        st.divider()
        person = f'{first_name}\'s' if first_name else 'Your'
        st.subheader(f'Jobs available now — {person} top matches')
        st.caption(
            f'Live listings from SEEK, LinkedIn, and Indeed for your '
            f'{len(qualifying)} occupation{"s" if len(qualifying) > 1 else ""} scoring above 70. '
            'Results update in real time from live job boards.'
        )

        jobs_cache_key = 'jobs_' + '_'.join(m['code'] for m in qualifying)

        if jobs_cache_key not in st.session_state:
            if not os.environ.get('APIFY_TOKEN'):
                # No token — pre-populate with empty so search links show immediately
                st.session_state[jobs_cache_key] = {m['code']: {} for m in qualifying}
            else:
                with st.spinner('Searching SEEK, LinkedIn, and Indeed... (~45 seconds)'):
                    titles_by_code = {m['code']: m['title'] for m in qualifying}
                    try:
                        st.session_state[jobs_cache_key] = fetch_jobs_for_codes(titles_by_code, n=3)
                    except Exception:
                        st.session_state[jobs_cache_key] = {m['code']: {} for m in qualifying}
                st.rerun()

        all_jobs = st.session_state[jobs_cache_key]

        if len(qualifying) == 1:
            m = qualifying[0]
            _render_jobs(all_jobs.get(m['code'], {}), m['title'], m['code'])
        else:
            tabs = st.tabs([f"{m['code']} {m['title']}" for m in qualifying])
            for tab, m in zip(tabs, qualifying):
                with tab:
                    _render_jobs(all_jobs.get(m['code'], {}), m['title'], m['code'])

    st.divider()

    st.markdown('**Were these results helpful?**')
    feedback_key = f'feedback_sent_{id(result)}'
    if st.session_state.get(feedback_key):
        st.success('Thanks for your feedback — it helps us improve the tool.')
    else:
        col_up, col_down, _ = st.columns([1, 1, 6])
        with col_up:
            if st.button('👍  Yes', key='fb_up'):
                _send_feedback(True, result['results'])
                st.session_state[feedback_key] = True
                st.rerun()
        with col_down:
            if st.button('👎  No', key='fb_down'):
                _send_feedback(False, result['results'])
                st.session_state[feedback_key] = True
                st.rerun()

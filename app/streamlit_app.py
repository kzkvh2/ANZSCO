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
from src.jobs import fetch_all_jobs, seek_search_url, indeed_search_url, linkedin_search_url

WEB3FORMS_KEY = '7fdb3ee2-ba92-4fed-bcd8-ecc37e4e39a3'

# Wire Apify token from Streamlit secrets into env so src/jobs.py can read it
if 'APIFY_TOKEN' in st.secrets:
    os.environ['APIFY_TOKEN'] = st.secrets['APIFY_TOKEN']


def _seek_url(title: str) -> str:
    return f'https://www.seek.com.au/jobs?keywords={urllib.parse.quote_plus(title)}&where=All+Australia'


def _lmi_url(code: str, title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return f'https://labourmarketinsights.gov.au/occupation-profile/{slug}?occupationCode={code}'


def _render_jobs(jobs: dict, title: str, code: str) -> None:
    """Render job results from SEEK, LinkedIn, and search links for Indeed + LMI."""
    seek_jobs = jobs.get('seek', [])
    li_jobs   = jobs.get('linkedin', [])

    col_seek, col_li = st.columns(2)

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

    col_indeed, col_lmi = st.columns(2)
    with col_indeed:
        st.markdown(f'**Indeed** — [Search all listings]({indeed_search_url(title)})')
    with col_lmi:
        st.markdown(f'**Labour market outlook** — [View occupation profile]({_lmi_url(code, title)})')


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
        pass  # feedback is best-effort; don't surface errors to user


@st.cache_resource(show_spinner="Loading ANZSCO knowledge base — first launch takes ~1 min...")
def _preload():
    preload()

_preload()


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title='ANZSCO Code Finder',
    page_icon='🎯',
    layout='centered',
)

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

    # Parsability score with actionable guidance
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

        profile = result['profile']
        with st.expander('What we extracted from your CV'):
            if profile.get('job_titles'):
                st.write('**Job titles:**', ', '.join(profile['job_titles']))
            if profile.get('skills'):
                st.write('**Skills:**', ', '.join(profile['skills'][:12]))
            if profile.get('industries'):
                st.write('**Industries:**', ', '.join(profile['industries']))

        st.subheader('Your top 5 ANZSCO matches')

        CONFIDENCE_COLOUR = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}

        for i, match in enumerate(result['results'], 1):
            conf_icon = CONFIDENCE_COLOUR.get(match.get('confidence', 'low'), '🔴')
            score_bar = '█' * (match['match_score'] // 10) + '░' * (10 - match['match_score'] // 10)

            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f'**#{i} — {match["code"]} {match["title"]}**')
                    st.caption(match.get('explanation', ''))
                    st.markdown(
                        f'[Search jobs on SEEK]({_seek_url(match["title"])}) · '
                        f'[Labour market outlook]({_lmi_url(match["code"], match["title"])})',
                    )
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
        # Live jobs section — top match only
        # -----------------------------------------------------------------------
        st.divider()
        top = result['results'][0]
        top_title = top['title']
        top_code  = top['code']

        st.subheader(f'Jobs available now — {top_code} {top_title}')
        st.caption('Live listings from SEEK and LinkedIn for your top-matched occupation. Results update in real time from live job boards.')

        jobs_cache_key = f'jobs_{top_code}'

        if jobs_cache_key not in st.session_state:
            if st.button('Search live job boards (SEEK + LinkedIn)', key='find_jobs'):
                with st.spinner('Searching SEEK and LinkedIn... (~45 seconds)'):
                    st.session_state[jobs_cache_key] = fetch_all_jobs(top_title, n=3)
                st.rerun()
        else:
            jobs = st.session_state[jobs_cache_key]
            _render_jobs(jobs, top_title, top_code)

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

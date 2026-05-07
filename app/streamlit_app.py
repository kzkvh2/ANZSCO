"""
ANZSCO Code Finder — Demo App
Upload a CV (PDF or Word) and get top 5 ANZSCO matches.

Run:
  cd ~/projects/mate1
  ANTHROPIC_API_KEY=sk-ant-... .venv/bin/streamlit run app/streamlit_app.py
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
from src.rag.cv_parser import extract_text, parsability_score
from src.rag.matcher import match_cv, preload


@st.cache_resource(show_spinner="Loading ANZSCO knowledge base — first launch takes ~1 min...")
def _preload():
    preload()

_preload()

# ---------------------------------------------------------------------------
# Assessing body lookup — keyed on ANZSCO major group prefix
# Used to generate the "What next?" one-liner per result
# ---------------------------------------------------------------------------
ASSESSING_BODY = {
    '1': ('VETASSESS', 'https://www.vetassess.com.au'),                    # Managers
    '21': ('VETASSESS', 'https://www.vetassess.com.au'),                   # Arts/Social science professionals
    '22': ('VETASSESS', 'https://www.vetassess.com.au'),                   # Business professionals
    '223': ('VETASSESS', 'https://www.vetassess.com.au'),                  # HR/Marketing
    '232': ('VETASSESS', 'https://www.vetassess.com.au'),                  # Design/Architecture
    '241': ('AITSL', 'https://www.aitsl.edu.au'),                          # School teachers
    '242': ('AITSL', 'https://www.aitsl.edu.au'),                          # Early childhood teachers
    '25': ('AHPRA', 'https://www.ahpra.gov.au'),                           # Health professionals (nurses, midwives, etc.)
    '26': ('ACS', 'https://www.acs.org.au/msa'),                           # ICT professionals
    '27': ('Engineers Australia', 'https://www.engineersaustralia.org.au/skills-assessment'),  # Engineers (code 27x)
    '233': ('Engineers Australia', 'https://www.engineersaustralia.org.au/skills-assessment'), # Engineers
    '234': ('Engineers Australia', 'https://www.engineersaustralia.org.au/skills-assessment'), # Science & building professionals
    '3': ('TRA', 'https://www.tradesrecognitionaustralia.gov.au'),          # Technicians & trades
    '4': ('VETASSESS', 'https://www.vetassess.com.au'),                    # Community & personal service
    '5': ('VETASSESS', 'https://www.vetassess.com.au'),                    # Clerical & admin
    '6': ('VETASSESS', 'https://www.vetassess.com.au'),                    # Sales workers
    '7': ('TRA', 'https://www.tradesrecognitionaustralia.gov.au'),         # Machinery operators
    '8': ('VETASSESS', 'https://www.vetassess.com.au'),                    # Labourers
}

def get_assessing_body(code: str) -> tuple[str, str] | None:
    """Return (body_name, url) for a 6-digit ANZSCO code, longest-prefix match."""
    for prefix in ('242', '241', '234', '233', '232', '27', '26', '25', '23', '22', '21',
                   '1', '3', '4', '5', '6', '7', '8'):
        if code.startswith(prefix):
            return ASSESSING_BODY.get(prefix)
    return None


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
            body_info = get_assessing_body(match['code'])

            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f'**#{i} — {match["code"]} {match["title"]}**')
                    st.caption(match.get('explanation', ''))
                    if body_info:
                        body_name, body_url = body_info
                        st.markdown(
                            f'**What next?** Skills assessment via [{body_name}]({body_url})',
                            help='This is the typical assessing body for this occupation. Confirm on the Home Affairs website before applying.'
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
            'These codes are a guide only. Verify your code with the relevant assessing body '
            'and the [Home Affairs occupation list](https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list) '
            'before submitting a visa application.',
            icon='⚠️',
        )

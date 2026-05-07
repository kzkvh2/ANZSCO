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
from src.rag.matcher import match_cv

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title='ANZSCO Code Finder',
    page_icon='🇦🇺',
    layout='centered',
)

st.title('🇦🇺 ANZSCO Code Finder')
st.caption('Upload your CV and we\'ll identify your top 5 ANZSCO occupation codes for Australian visa applications.')

st.info(
    '**Disclaimer**: This tool provides information only and does not constitute migration advice. '
    'For a binding skills assessment, consult a registered MARA agent.',
    icon='ℹ️',
)

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
uploaded = st.file_uploader(
    'Upload your CV',
    type=['pdf', 'docx', 'doc'],
    help='PDF or Word document, English only.',
)

if uploaded:
    with st.spinner('Reading your CV...'):
        file_bytes = uploaded.read()
        try:
            raw_text = extract_text(file_bytes, uploaded.name)
        except Exception as e:
            st.error(f'Could not read file: {e}')
            st.stop()

    # Parsability score
    parse_result = parsability_score(raw_text)
    score = parse_result['overall']
    col1, col2 = st.columns([1, 3])
    with col1:
        colour = 'green' if score >= 70 else ('orange' if score >= 50 else 'red')
        st.metric('CV Readability', f'{score}/100')
    with col2:
        if parse_result['warning']:
            st.warning(parse_result['warning_message'])
        else:
            st.success(f'CV parsed cleanly ({parse_result["word_count"]} words extracted).')

    # Show extracted text preview
    with st.expander('View extracted CV text'):
        st.text(raw_text[:2000] + ('...' if len(raw_text) > 2000 else ''))

    st.divider()

    # Run matching
    if st.button('Find my ANZSCO codes', type='primary'):
        with st.spinner('Analysing your CV and matching ANZSCO codes... (this takes ~10 seconds)'):
            try:
                result = match_cv(raw_text)
            except EnvironmentError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(f'Matching failed: {e}')
                raise

        # Show extracted profile
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
                with c2:
                    st.markdown(f'**{match["match_score"]}/100** {conf_icon}')
                    st.caption(f'`{score_bar}`')

        timing = result['timing']
        st.caption(
            f'Total time: {timing["total_ms"]}ms '
            f'(extract: {timing["extract_profile_ms"]}ms, '
            f'retrieve: {timing["retrieval_ms"]}ms, '
            f'rank: {timing["rerank_ms"]}ms)'
        )

        st.info(
            'These codes are a guide only. Before submitting a visa application, '
            'verify your code with the relevant assessing body (e.g. ACS, Engineers Australia, VETASSESS).',
            icon='⚠️',
        )

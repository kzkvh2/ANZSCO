"""
CV text extraction.

Handles PDF (via pdfminer) and Word documents (via python-docx).
Returns raw text plus a parsability score (0–100) indicating how
cleanly the text was extracted — low scores warn the user that
their CV format may reduce match quality.
"""

import io
import pathlib
import re
import textstat


def parse_pdf(file_bytes: bytes) -> str:
    from pdfminer.high_level import extract_text_to_fp
    from pdfminer.layout import LAParams

    output = io.StringIO()
    extract_text_to_fp(
        io.BytesIO(file_bytes),
        output,
        laparams=LAParams(),
        output_type='text',
        codec='utf-8',
    )
    return output.getvalue()


def parse_docx(file_bytes: bytes) -> str:
    import docx
    doc = docx.Document(io.BytesIO(file_bytes))
    return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from a PDF or Word file."""
    ext = pathlib.Path(filename).suffix.lower()
    if ext == '.pdf':
        return parse_pdf(file_bytes)
    elif ext in ('.docx', '.doc'):
        return parse_docx(file_bytes)
    else:
        raise ValueError(f'Unsupported file type: {ext}. Upload a PDF or Word document.')


def parsability_score(text: str) -> dict:
    """
    Score how cleanly a CV was extracted (0–100).
    Not a quality-of-writing score — purely a signal of how well
    the parser could read the file. Low score = warn the user.
    """
    scores = {}
    words = text.split()
    word_count = len(words)

    # 1. Word count (a real CV should have 200–1500 words)
    if word_count >= 300:
        scores['word_count'] = 100
    elif word_count >= 150:
        scores['word_count'] = 70
    elif word_count >= 50:
        scores['word_count'] = 40
    else:
        scores['word_count'] = 10

    # 2. Garbled character ratio (OCR/encoding issues produce junk chars)
    printable = sum(1 for c in text if c.isprintable() or c in '\n\t ')
    garbled_ratio = 1 - (printable / max(len(text), 1))
    scores['encoding'] = max(0, int(100 - garbled_ratio * 500))

    # 3. Line structure — parseable CVs have multiple short lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    scores['structure'] = min(100, len(lines) * 3)

    # 4. Contains recognisable CV signals
    cv_signals = ['experience', 'education', 'skills', 'employment', 'work', 'qualification',
                  'responsibilities', 'university', 'degree', 'certificate', 'managed', 'developed']
    text_lower = text.lower()
    signal_hits = sum(1 for s in cv_signals if s in text_lower)
    scores['cv_signals'] = min(100, signal_hits * 12)

    overall = int(
        scores['word_count'] * 0.35 +
        scores['encoding']   * 0.30 +
        scores['structure']  * 0.20 +
        scores['cv_signals'] * 0.15
    )

    return {
        'overall': overall,
        'word_count': word_count,
        'breakdown': scores,
        'warning': overall < 50,
        'warning_message': (
            'Your CV may not have been read clearly (score: {}). '
            'Try uploading a plain Word document for best results.'.format(overall)
        ) if overall < 50 else None,
    }

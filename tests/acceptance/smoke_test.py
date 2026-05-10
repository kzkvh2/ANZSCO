"""
Smoke test: run a single synthetic CV through the full pipeline.
Use this to validate the matching engine before running the full acceptance suite.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  cd ~/projects/anzsco
  PYTHONPATH=. .venv/bin/python3 tests/acceptance/smoke_test.py
"""

import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from src.rag.matcher import match_cv

SAMPLE_CV = """
Jane Smith
Senior Software Engineer | Sydney, NSW | jane.smith@email.com

EXPERIENCE

Senior Software Engineer — Atlassian (2020–present)
- Designed and developed scalable backend services using Python and Go
- Led migration of monolithic application to microservices architecture
- Implemented CI/CD pipelines using Jenkins and GitHub Actions
- Mentored junior developers and conducted code reviews
- Built RESTful APIs consumed by mobile and web clients

Software Developer — Canva (2017–2020)
- Developed features for image processing pipeline in Python
- Optimised database queries reducing response time by 40%
- Collaborated with product team to deliver features on schedule

EDUCATION
Bachelor of Computer Science — University of Sydney (2017)

SKILLS
Python, Go, Java, PostgreSQL, Redis, AWS, Docker, Kubernetes, REST APIs, microservices
"""

# Both are valid: CV shows DevOps-heavy work (CI/CD, Docker, K8s) AND software development
EXPECTED_CODES = {'261313', '261316'}  # Software Engineer OR DevOps Engineer

if __name__ == '__main__':
    print('Running smoke test...')
    print('CV: Senior Software Engineer at Atlassian')
    print(f'Expected ANZSCO codes: {EXPECTED_CODES}')
    print()

    result = match_cv(SAMPLE_CV)

    print('=== Extracted Profile ===')
    print(json.dumps(result['profile'], indent=2))
    print()

    print('=== Top 5 Matches ===')
    codes = []
    for i, r in enumerate(result['results'], 1):
        codes.append(r['code'])
        marker = ' <-- EXPECTED' if r['code'] in EXPECTED_CODES else ''
        print(f"  {i}. [{r['code']}] {r['title']}")
        print(f"     Score: {r['match_score']}/100 | Confidence: {r['confidence']}{marker}")
        print(f"     {r['explanation']}")
        print()

    print('=== Timing ===')
    for k, v in result['timing'].items():
        print(f'  {k}: {v}ms')

    print()
    in_top5  = bool(EXPECTED_CODES & set(codes))
    is_top1  = codes[0] in EXPECTED_CODES if codes else False
    total_ms = result['timing']['total_ms']

    print('=== Result ===')
    print(f"  Expected code in top 5: {'PASS' if in_top5 else 'FAIL'}")
    print(f"  Expected code is #1:    {'PASS' if is_top1 else 'FAIL'}")
    print(f"  Total time:             {total_ms}ms ({'PASS' if total_ms < 10000 else 'SLOW'})")

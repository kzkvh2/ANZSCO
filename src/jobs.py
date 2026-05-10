"""
Live job search for a given occupation title.

Sources:
  - SEEK   : parseforge/seek-scraper Apify actor   (~4s)
  - LinkedIn: curious_coder/linkedin-jobs-scraper   (~44s)
  - Indeed  : no reliable scraper; caller should show a search link

Requires env var: APIFY_TOKEN
"""

import concurrent.futures
import os
import urllib.parse
import requests


def _apify_token() -> str:
    return os.environ.get('APIFY_TOKEN', '')


def _run_actor_sync(actor: str, payload: dict, timeout_secs: int = 120) -> list[dict]:
    token = _apify_token()
    if not token:
        return []
    url = f'https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items'
    try:
        r = requests.post(
            url,
            json=payload,
            params={'token': token, 'waitForFinish': timeout_secs},
            timeout=timeout_secs + 15,
        )
        if r.ok:
            return r.json() or []
    except Exception:
        pass
    return []


def fetch_seek_jobs(title: str, n: int = 3) -> list[dict]:
    items = _run_actor_sync(
        'parseforge~seek-scraper',
        {'keywords': title, 'maxItems': n},
        timeout_secs=30,
    )
    return [
        {
            'title': j.get('title', ''),
            'company': j.get('companyName', ''),
            'location': j.get('location', ''),
            'url': j.get('url', ''),
            'salary': j.get('salaryLabel', ''),
            'source': 'SEEK',
        }
        for j in items[:n]
        if j.get('url')
    ]


def fetch_linkedin_jobs(title: str, n: int = 3) -> list[dict]:
    search_url = (
        'https://www.linkedin.com/jobs/search/'
        f'?keywords={urllib.parse.quote_plus(title)}'
        '&location=Australia&f_TPR=r604800'
    )
    items = _run_actor_sync(
        'curious_coder~linkedin-jobs-scraper',
        {'urls': [search_url], 'maxJobListings': n},
        timeout_secs=120,
    )
    return [
        {
            'title': j.get('title', ''),
            'company': j.get('companyName', ''),
            'location': j.get('location', ''),
            'url': j.get('link', ''),
            'salary': '',
            'source': 'LinkedIn',
        }
        for j in items[:n]
        if j.get('link')
    ]


def fetch_all_jobs(title: str, n: int = 3) -> dict:
    """Run SEEK and LinkedIn in parallel. Returns {'seek': [...], 'linkedin': [...]}."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        seek_f = ex.submit(fetch_seek_jobs, title, n)
        li_f = ex.submit(fetch_linkedin_jobs, title, n)
    return {
        'seek': seek_f.result(),
        'linkedin': li_f.result(),
    }


def seek_search_url(title: str) -> str:
    return f'https://www.seek.com.au/jobs?keywords={urllib.parse.quote_plus(title)}&where=All+Australia'


def indeed_search_url(title: str) -> str:
    return f'https://au.indeed.com/jobs?q={urllib.parse.quote_plus(title)}&l=Australia'


def linkedin_search_url(title: str) -> str:
    return (
        f'https://www.linkedin.com/jobs/search/'
        f'?keywords={urllib.parse.quote_plus(title)}&location=Australia'
    )

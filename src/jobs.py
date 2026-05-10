"""
Live job search for a given occupation title.

Source: Adzuna Jobs API (https://developer.adzuna.com/)
  - Free tier: 1,000 requests/month
  - Single call replaces the previous SEEK + LinkedIn + Indeed Apify scrapers
  - Response time: ~1-2 seconds

Requires env vars: ADZUNA_APP_ID, ADZUNA_APP_KEY
"""

import os
import urllib.parse
import requests


def fetch_adzuna_jobs(title: str, n: int = 6) -> list[dict]:
    app_id  = os.environ.get('ADZUNA_APP_ID', '')
    app_key = os.environ.get('ADZUNA_APP_KEY', '')
    if not app_id or not app_key:
        return []
    try:
        r = requests.get(
            'https://api.adzuna.com/v1/api/jobs/au/search/1',
            params={
                'app_id': app_id,
                'app_key': app_key,
                'results_per_page': n,
                'what': title,
                'where': 'Australia',
                'content-type': 'application/json',
            },
            timeout=10,
        )
        if not r.ok:
            return []
        items = r.json().get('results', [])
        results = []
        for j in items[:n]:
            url = j.get('redirect_url', '')
            if not url:
                continue
            sal_min = j.get('salary_min')
            sal_max = j.get('salary_max')
            if sal_min and sal_max:
                salary = f'${sal_min:,.0f}–${sal_max:,.0f}'
            elif sal_min:
                salary = f'${sal_min:,.0f}+'
            else:
                salary = ''
            results.append({
                'title':    j.get('title', ''),
                'company':  j.get('company', {}).get('display_name', ''),
                'location': j.get('location', {}).get('display_name', ''),
                'url':      url,
                'salary':   salary,
            })
        return results
    except Exception:
        return []


def fetch_jobs_for_codes(titles_by_code: dict[str, str], n: int = 6) -> dict[str, list]:
    """Fetch Adzuna jobs for multiple ANZSCO codes. Returns {code: [job, ...]}."""
    return {code: fetch_adzuna_jobs(title, n) for code, title in titles_by_code.items()}


def seek_search_url(title: str) -> str:
    return f'https://www.seek.com.au/jobs?keywords={urllib.parse.quote_plus(title)}&where=All+Australia'


def indeed_search_url(title: str) -> str:
    return f'https://au.indeed.com/jobs?q={urllib.parse.quote_plus(title)}&l=Australia'


def linkedin_search_url(title: str) -> str:
    return (
        f'https://www.linkedin.com/jobs/search/'
        f'?keywords={urllib.parse.quote_plus(title)}&location=Australia'
    )

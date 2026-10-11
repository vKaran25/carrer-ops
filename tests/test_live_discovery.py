"""Opt-in real Tavily discovery. Read-only; never seeds the user's database."""
import asyncio
import os

import httpx
import pytest

from app.config import get_settings
from app.discovery import web_jobs


@pytest.mark.skipif(os.getenv('RUN_LIVE_SEARCH_TESTS') != '1', reason='Opt-in real Tavily discovery requires a search key')
def test_real_web_discovery_returns_original_jobs_or_explicit_unscored_leads():
    assert get_settings().tavily_api_key, 'Add TAVILY_API_KEY to .env before running this live check'
    async def run():
        async with httpx.AsyncClient(headers={'User-Agent': 'CareerOps/0.1 (personal career research)'}) as active:
            return await web_jobs({'hard_filters': {'locations': ['India']}}, ['Python software engineer'], active)
    result = asyncio.run(run())
    assert result['queries'] and not result['warnings'], result['warnings']
    assert result['jobs'] or result['external_links'], 'No jobs or indexed leads retrieved; inspect current search coverage'
    for job in result['jobs']:
        assert job['description'].strip() and job['company'] != 'Not specified'
        assert job['url'].startswith('https://')
    for lead in result['external_links']:
        assert 'fit_score' not in lead and lead['url'].startswith('https://')

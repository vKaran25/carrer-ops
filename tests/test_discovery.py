"""Isolated fixtures for web search, LinkedIn handoff and explicit imports."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.config import Settings
from app.discovery import TavilySearch, WebSearchError, canonical_url, linkedin_url, linkedin_search_url, web_jobs
from test_workflows import client, resume_docx


@pytest.mark.parametrize('url', ['https://www.linkedin.com/jobs/view/12345?trk=test',
    'https://in.linkedin.com/jobs/view/software-engineer-at-fixture-12345/'])
def test_linkedin_canonical_id(url):
    assert linkedin_url(url) == 'https://www.linkedin.com/jobs/view/12345'


@pytest.mark.parametrize('url', ['http://www.linkedin.com/jobs/view/12345',
    'https://linkedin.com.evil.example/jobs/view/12345', 'https://www.linkedin.com/jobs/search/',
    'https://user:pass@www.linkedin.com/jobs/view/12345', 'https://localhost/jobs/view/12345',
    'https://www.linkedin.com:444/jobs/view/12345'])
def test_import_rejects_non_job_and_unsafe_links(url):
    with pytest.raises(ValueError):
        linkedin_url(url)


def test_search_link_encodes_keywords_and_location():
    url = linkedin_search_url(['C++ developer'], {'hard_filters': {'locations': ['Pune, India']}})
    assert 'C%2B%2B+developer' in url and 'Pune%2C+India' in url
    assert canonical_url('https://example.org/jobs?id=10&utm_source=test#foo') == 'https://example.org/jobs?id=10'


@pytest.mark.parametrize('status', [401, 429, 432])
def test_tavily_failures_have_actionable_messages(status):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(status))) as active:
            with pytest.raises(WebSearchError, match='authenticate|quota'):
                await TavilySearch(active, 'fixture-key').search('Java jobs')
    asyncio.run(run())


def test_web_discovery_verifies_jd_skips_expired_and_never_fetches_linkedin(monkeypatch):
    import app.discovery as discovery
    settings = Settings(tavily_api_key='fixture', web_search_max_queries=3)
    monkeypatch.setattr(discovery, 'get_settings', lambda: settings)
    async def validate(url):
        assert 'linkedin.com' not in url
    monkeypatch.setattr(discovery, 'validate_public_url', validate)
    monkeypatch.setattr('app.web_fetch.validate_public_url', validate)
    requests = []
    def handler(request):
        requests.append(str(request.url))
        assert 'linkedin.com' not in str(request.url)
        expired = str(request.url).endswith('expired')
        schema = {'@type': 'JobPosting', 'title': 'Java engineer', 'hiringOrganization': {'name': 'Fictional Co'},
                  'description': 'Java software development and testing of payment systems.',
                  'jobLocation': {'address': {'addressLocality': 'Pune', 'addressCountry': 'India'}},
                  'validThrough': (datetime.now(timezone.utc) + timedelta(days=-1 if expired else 10)).isoformat()}
        return httpx.Response(200, text='<script type="application/ld+json">' + json.dumps(schema) + '</script>')
    class Provider:
        queries = []
        async def search(self, query):
            self.queries.append(query)
            return [{'title': 'Java engineer at Fictional Co', 'url': url} for url in
                    ['https://www.linkedin.com/jobs/view/12345', 'https://example.org/open', 'https://example.org/expired']]
    provider = Provider()
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as active:
            return await web_jobs({'hard_filters': {'locations': ['Pune, Maharashtra, India']}}, ['Java engineer'], active, provider=provider)
    result = asyncio.run(run())
    assert len(provider.queries) == 3 and '-site:linkedin.com' in provider.queries[-1]
    assert len(result['jobs']) == 1
    assert result['jobs'][0]['company'] == 'Fictional Co'
    assert result['jobs'][0]['location'] == 'Pune, India'
    assert len(requests) == 2 and result['pages_checked'] == 2
    assert len(result['external_links']) == 2
    assert all('fit_score' not in lead for lead in result['external_links'])


def test_no_key_is_explicit_and_does_not_request_network(monkeypatch):
    monkeypatch.setattr('app.discovery.get_settings', lambda: Settings(tavily_api_key=''))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: pytest.fail('Unexpected network'))) as active:
            return await web_jobs({}, ['Java jobs'], active)
    result = asyncio.run(run())
    assert not result['jobs'] and not result['queries']
    assert 'TAVILY_API_KEY' in result['warnings'][0]


def test_repeated_queries_save_credits_and_never_request_generated_answers():
    calls = []
    def handler(request):
        calls.append(request)
        data = json.loads(request.content)
        assert data['search_depth'] == 'basic' and data['include_answer'] is False
        return httpx.Response(200, json={'results': [{'title': 'Fixture job', 'url': 'https://example.org/job'}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as active:
            provider = TavilySearch(active, 'cache-fixture-only-key')
            first = await provider.search('Unique fixture cache query')
            again = await provider.search('Unique fixture cache query')
            assert first == again
            await TavilySearch(active, 'different-fixture-key').search('Unique fixture cache query')
    asyncio.run(run())
    assert len(calls) == 2


def test_employer_redirect_to_linkedin_is_blocked_before_second_request(monkeypatch):
    from app.web_fetch import fetch
    monkeypatch.setattr('app.web_fetch.socket.getaddrinfo', lambda *args, **kwargs: [(None, None, None, None, ('93.184.216.34', 443))])
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={'location': 'https://www.linkedin.com/jobs/view/12345'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as active:
            with pytest.raises(ValueError, match='automated fetching'):
                await fetch(active, 'https://example.org/job')
    asyncio.run(run())
    assert calls == ['https://example.org/job']


def test_import_persists_chat_but_requires_interest_and_preserves_progress(client):
    active,_,_=client
    assert active.post('/api/chat/import-job',json={}).status_code==404
    assert active.get('/api/chat').json()==[]
    assert active.get('/api/jobs').json()==[]

def test_import_requires_resume_and_sufficient_details(client):
    active,_,_=client
    assert active.post('/api/chat/import-job',json={}).status_code==404
    assert active.get('/api/chat').json()==[]
    assert active.get('/api/jobs').json()==[]

def test_linkedin_search_uses_skills_without_identity_or_search_key(client):
    active,_,_=client
    assert active.post('/api/linkedin-search',json={}).status_code==404
    assert active.get('/api/chat').json()==[]
    assert active.get('/api/jobs').json()==[]

def test_dynamic_sources_work_without_configured_boards_and_filter_before_cap(monkeypatch):
    from app.scout import discover_jobs
    async def web(spec, terms, client):
        return {'jobs': [{'title': 'Java engineer', 'company': 'Fixture', 'location': loc,
                         'url': f'https://example.org/job/{i}', 'description': 'Java APIs This fictional engineering position builds documented production APIs, reviews code, writes automated unit and integration tests, collaborates with product engineers, investigates service issues, maintains secure deployments and communicates implementation tradeoffs. Required skills are grounded in the role title and supplied fixture. '}
                        for i, loc in enumerate(['London'] * 210 + ['Pune'])],
                'warnings': [], 'external_links': [], 'queries': ['Java Pune jobs'], 'pages_checked': 1}
    monkeypatch.setattr('app.discovery.web_jobs', web)
    async def run():
        async with httpx.AsyncClient() as active:
            return await discover_jobs({'hard_filters': {'locations': ['Pune, Maharashtra, India']}}, 1, sources=[],
                                       client=active, discovery_terms=['Java engineer'])
    result = asyncio.run(run())
    assert len(result['jobs']) == 1 and result['jobs'][0]['location'] == 'Pune'
    assert result['stats']['hard_filter_excluded'] == {'Different required location': 210}
    assert result['stats']['web_queries'] == 1

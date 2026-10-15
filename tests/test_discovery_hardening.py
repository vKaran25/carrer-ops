"""Source-boundary regressions: malformed data and listing cards cannot become JDs."""
import asyncio
import json

import httpx
import pytest

from app.discovery import TavilySearch, canonical_url, web_jobs
from app.scout import discover_jobs, parse_static
from app.sources import JobSource, known_ats


@pytest.mark.parametrize('payload', [None, [], 'invalid', {'results': None}])
def test_malformed_provider_root_is_reported_as_validation_failure(payload):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) as active:
            with pytest.raises(ValueError, match='invalid response'):
                await TavilySearch(active, 'malformed-fixture').search('malformed provider fixture')
    asyncio.run(run())


@pytest.mark.parametrize('host', ['notgreenhouse.io', 'evilgreenhouse.io', 'notlever.co', 'evilmyworkdayjobs.com'])
def test_provider_detection_requires_a_real_domain_boundary(host):
    assert known_ats(JobSource(company='Fixture', url=f'https://{host}/fixture')) is None


def test_jsonld_bad_optional_fields_do_not_hide_a_valid_sibling():
    document = json.dumps([
        {'@type': 'JobPosting', 'title': 'Broken engineer', 'description': {}, 'jobLocation': None},
        {'@type': 'JobPosting', 'title': 'Python engineer', 'description': 'Build Python APIs.',
         'url': '/jobs/valid', 'jobLocation': [None, {'address': {'addressLocality': 'Pune',
             'addressCountry': {'@type': 'Country', 'name': 'India'}}}]},
    ])
    source = JobSource(company='Fixture', url='https://example.org/careers')
    jobs, _ = parse_static(source, '<script type="application/ld+json">' + document + '</script>', source.url)
    valid = next(job for job in jobs if job['title'] == 'Python engineer')
    assert valid['location'] == 'Pune, India'
    assert valid['description'] == 'Build Python APIs.'


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'https://user:secret@example.org/jobs/1', 'https://example.org:444/jobs/1'])
def test_canonical_job_urls_reject_unsafe_links(url):
    with pytest.raises(ValueError):
        canonical_url(url)


def test_listing_cards_and_missing_descriptions_stay_unscored(monkeypatch):
    source = JobSource(company='Fixture', url='https://example.org/careers')
    cards, _ = parse_static(source, '<div class="job-card"><h2>Python engineer</h2>'
        '<a href="/jobs/card">Read more</a><span class="location">Pune</span></div>', source.url)
    async def crawl(*args):
        return cards + [{'title': 'Java engineer', 'company': 'Fixture', 'url': 'https://example.org/jobs/empty',
                         'description': '', 'location': 'Pune'}], []
    monkeypatch.setattr('app.scout.crawl_source', crawl)
    async def run():
        async with httpx.AsyncClient() as active:
            return await discover_jobs({}, sources=[source], client=active)
    result = asyncio.run(run())
    assert result['jobs'] == []
    assert len(result['external_links']) == 2
    assert all('fit_score' not in lead for lead in result['external_links'])
    assert result['stats']['description_unavailable'] == 2
    assert any('description' in warning.lower() for warning in result['warnings'])
    from app.search_feedback import empty_search_message
    assert 'unscored' in empty_search_message({**result, 'search_stats': result['stats']})


def test_full_jd_later_in_crawl_replaces_listing_without_duplicate_lead(monkeypatch):
    source = JobSource(company='Fixture', url='https://example.org/careers')
    card = {'title': 'Python engineer', 'company': 'Fixture', 'url': 'https://example.org/jobs/one',
            'description': 'Read more', 'metadata': {'description_kind': 'listing'}}
    detail = {**card, 'description': 'Build Python APIs and write unit tests.', 'metadata': {'structured_job': True}}
    async def crawl(*args):
        return [card, card, detail], []
    monkeypatch.setattr('app.scout.crawl_source', crawl)
    async def run():
        async with httpx.AsyncClient() as active:
            return await discover_jobs({}, sources=[source], client=active)
    result = asyncio.run(run())
    assert [job['description'] for job in result['jobs']] == [detail['description']]
    assert result['external_links'] == [] and result['stats']['description_unavailable'] == 0
    assert result['stats']['tech_jobs'] == 1


def test_malformed_ats_root_falls_back_without_discarding_other_sources(monkeypatch):
    async def validate(url):
        pass
    monkeypatch.setattr('app.web_fetch.validate_public_url', validate)
    async def no_browser(source):
        return []
    monkeypatch.setattr('app.scout.browser_jobs', no_browser)
    sources = [JobSource(company='Bad fixture', url='https://job-boards.greenhouse.io/bad'),
               JobSource(company='Good fixture', url='https://job-boards.greenhouse.io/good')]
    def handler(request):
        if 'boards-api' in request.url.host:
            if '/bad/' in request.url.path:
                return httpx.Response(200, json=[])
            return httpx.Response(200, json={'jobs': [None, {'id': 1, 'title': 'Python engineer',
                'absolute_url': 'https://example.org/jobs/good', 'content': 'Build Python APIs.', 'location': None}]})
        return httpx.Response(200, text='<html></html>')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as active:
            return await discover_jobs({}, sources=sources, client=active)
    result = asyncio.run(run())
    assert len(result['jobs']) == 1 and result['jobs'][0]['company'] == 'Good fixture'
    assert any('Bad fixture' in warning for warning in result['warnings'])


def test_discovered_greenhouse_api_job_selects_only_its_requisition(monkeypatch):
    async def validate(url):
        pass
    monkeypatch.setattr('app.discovery.validate_public_url', validate)
    monkeypatch.setattr('app.web_fetch.validate_public_url', validate)
    observed = []
    def handler(request):
        observed.append(str(request.url))
        assert '/boards/fixture/jobs' in str(request.url)
        return httpx.Response(200, json={'jobs': [
            {'id': number, 'title': 'Python engineer', 'absolute_url': f'https://job-boards.greenhouse.io/fixture/jobs/{number}',
             'content': 'Build Python APIs.', 'location': {'name': 'Pune'}} for number in [100, 200]]})
    class Provider:
        async def search(self, query):
            return [{'url': 'https://boards-api.greenhouse.io/v1/boards/fixture/jobs/100', 'title': 'Python engineer'}]
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as active:
            return await web_jobs({}, ['Python engineer'], active, provider=Provider())
    result = asyncio.run(run())
    assert len(result['jobs']) == 1 and result['jobs'][0]['url'].endswith('/100')
    assert len(observed) == 1

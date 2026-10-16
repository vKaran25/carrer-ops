"""Fictional city index: no network, real resume, production DB or model calls."""
import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.geography import Gazetteer, GeographyError, distance_km
from app.query_parser import LocationScope, QueryParserError, QuerySpec, parse_query
from app.scoring import rank_jobs
from scripts.setup_geography import build_index


@pytest.fixture
def geo(tmp_path, monkeypatch):
    def row(id, name, lon, country='FX', aliases=''):
        return '\t'.join(map(str, [id, name, name, aliases, 0, lon, 'P', 'PPL', country, '', 'A1', '', '', '', 1000, '', '', '', '2026-01-01']))
    path = tmp_path / 'geography.sqlite'
    countries = ['FX\tFIX\t000\t\tFixtureland', 'OX\tOTH\t001\t\tOtherland']
    admins = ['FX.A1\tFixture State\tFixture State\t1', 'OX.A1\tOther State\tOther State\t2']
    build_index([row(1, 'Anchor', 0, aliases='Ankhor'), row(2, 'Nearby', .1), row(3, 'Farther', 1),
                 row(4, 'Foreign', .01, 'OX'), row(5, 'Duplicate', 2), row(6, 'Duplicate', 3, 'OX')], countries, admins, path)
    lookup = Gazetteer(path)
    monkeypatch.setattr('app.geography.gazetteer', lambda *args: lookup)
    return lookup


def scope(mode='preferred', radius=50.):
    return LocationScope(place='Anchor, Fixtureland', radius_km=radius, mode=mode, evidence='around Anchor, Fixtureland')


def job(location, id='test'):
    return {'job_id': id, 'title': 'Python engineer', 'company': 'Fictional employer', 'description': 'Python APIs and mentorship This fictional engineering position builds documented production APIs, reviews code, writes automated unit and integration tests, collaborates with product engineers, investigates service issues, maintains secure deployments and communicates implementation tradeoffs. Required skills are grounded in the role title and supplied fixture. ', 'location': location}


def test_index_alias_qualifiers_ambiguity_and_missing_data(geo, tmp_path):
    assert geo.resolve('Ankhor, Fixture State, FX')['id'] == 1
    assert geo.resolve('Duplicate, Otherland')['id'] == 6
    with pytest.raises(GeographyError, match='ambiguous'):
        geo.resolve('Duplicate')
    with pytest.raises(GeographyError, match='Could not resolve'):
        geo.resolve('Unlisted')
    with pytest.raises(GeographyError, match='setup_geography'):
        Gazetteer(tmp_path / 'missing.sqlite').resolve('Anchor')
    assert 110 < distance_km(geo.resolve('Anchor'), geo.resolve('Farther')) < 112


def test_preferred_radius_country_boundary_unknown_distance_and_actual_points(geo):
    spec = QuerySpec(hard_filters={}, soft_preferences=[], location_scope=scope())
    result = rank_jobs(spec, [job('Nearby, Fixtureland', 'near'), job('Farther, Fixtureland', 'far'),
                             job('Remote, Fixtureland', 'unknown'), job('Foreign, Otherland', 'foreign'), job('Remote', 'missing')],
                       {'facts': ['Built Python APIs.']}, semantic=lambda *_: .6)
    assert [j['job_id'] for j in result['jobs']] == ['near', 'far', 'unknown']
    near, far, unknown = result['jobs']
    assert near['fit_score'] == 68.
    assert 56 < far['fit_score'] < 58
    assert unknown['fit_score'] == 48.
    assert not far['score_breakdown']['location']['within_radius']
    assert unknown['score_breakdown']['location']['distance_km'] is None
    assert result['excluded'] == {'Anchor country is not evidenced by the job location': 2}
    for row in result['jobs']:
        breakdown = row['score_breakdown']
        assert sum(c['points'] for c in breakdown['components']) + breakdown['rounding_and_cap'] == pytest.approx(row['fit_score'])
        assert sum(c['weight'] for c in breakdown['components']) == pytest.approx(1.)
        assert breakdown['resume_evidence'] == ['Built Python APIs.']
    assert '20%' in result['location_notice']


def test_required_radius_never_relaxes_and_other_hard_filters_survive(geo):
    spec = QuerySpec(hard_filters={'tech_stack_keywords': ['Python']}, soft_preferences=[], location_scope=scope('required', 20.))
    rows = [job('Nearby, Fixtureland', 'near'), job('Farther, Fixtureland', 'far'), job('Fixtureland', 'unknown')]
    assert [j['job_id'] for j in rank_jobs(spec, rows, {}, semantic=lambda *_: .6)['jobs']] == ['near']
    spec.hard_filters.tech_stack_keywords = ['Rust']
    assert not rank_jobs(spec, rows, {})['jobs']


def test_soft_preferences_preserve_eighty_percent_mix_and_legacy_score(geo):
    pref = {'factor': 'career_growth', 'weight': 1., 'evidence': 'mentorship', 'targets': []}
    base = QuerySpec(hard_filters={}, soft_preferences=[pref])
    current = rank_jobs(base, [job('Anchor')], {'facts': ['Built APIs']}, semantic=lambda *_: .6)['jobs'][0]
    base.location_scope = scope()
    nearby = rank_jobs(base, [job('Anchor')], {'facts': ['Built APIs']}, semantic=lambda *_: .6)['jobs'][0]
    assert current['fit_score'] == 56.5  # .65*.6 + .35*.5
    assert nearby['fit_score'] == 65.2  # .8*.565 + .2*1
    assert [c['weight'] for c in nearby['score_breakdown']['components']] == pytest.approx([.52, .28, .2])


@pytest.mark.parametrize('change', [{'evidence': 'invented quote'}, {'place': 'Anchor, Otherland'}, {'radius_km': 25.}])
def test_parser_rejects_ungrounded_location_fields(geo, change):
    data = scope().model_dump() | change
    async def run():
        def transport(request):
            return httpx.Response(200, json={'choices': [{'message': {'tool_calls': [{'function': {'name': 'emit_query_spec', 'arguments': json.dumps({'hard_filters': {}, 'soft_preferences': [], 'location_scope': data})}}]}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            return await parse_query('jobs around Anchor, Fixtureland', settings=Settings(openrouter_api_key='fixture', openrouter_model='fixture:free'), client=client)
    with pytest.raises(QueryParserError):
        asyncio.run(run())


def test_multiple_work_sites_use_nearest_supported_city(geo):
    from app.geography import location_assessment
    result = location_assessment('Farther, Fixtureland; Nearby, Fixtureland', scope())
    assert result['within_radius'] and result['distance_km'] < 12
    assert 'Nearby' in result['evidence']
    assert location_assessment('Nearby - Fixture State - Fixtureland', scope())['within_radius']


def test_nearby_web_queries_include_country_broadening(geo):
    from app.discovery import web_jobs
    class Provider:
        def __init__(self):
            self.queries = []
        async def search(self, query):
            self.queries.append(query)
            return []
    provider = Provider()
    async def run():
        async with httpx.AsyncClient() as client:
            return await web_jobs(QuerySpec(hard_filters={}, soft_preferences=[], location_scope=scope()).model_dump(), ['Python backend'], client, provider=provider)
    asyncio.run(run())
    assert provider.queries[:2] == ['Python backend Anchor Fixtureland jobs careers apply', 'Python backend Fixtureland jobs careers apply']


def test_scout_preserves_scope_and_filters_before_limit(geo, monkeypatch):
    from app.scout import discover_jobs
    from app.sources import JobSource
    async def crawl(*_):
        return [job('Foreign, Otherland', 'foreign') | {'url':'https://example.org/foreign'},
                job('Nearby, Fixtureland', 'near') | {'url':'https://example.org/near'}], []
    monkeypatch.setattr('app.scout.crawl_source', crawl)
    async def run():
        async with httpx.AsyncClient() as client:
            return await discover_jobs(QuerySpec(hard_filters={}, soft_preferences=[], location_scope=scope()).model_dump(), 1,
                                       sources=[JobSource(company='Fixture', url='https://example.org/jobs')], client=client)
    result = asyncio.run(run())
    assert [j['job_id'] for j in result['jobs']] == ['near']
    assert result['stats']['hard_filter_excluded'] == {'Anchor country is not evidenced by the job location': 1}


@pytest.mark.parametrize('query,mode,radius,expected', [
    ('jobs around Anchor, Fixtureland', 'preferred', 50., True),
    ('jobs within 25 km of Anchor, Fixtureland only', 'required', 25., True),
    ('jobs within 25 km of Anchor, Fixtureland only', 'preferred', 25., False),
    ('jobs within 25 km of Anchor, Fixtureland only', 'required', 50., False),
    ('jobs around Anchor, Fixtureland', 'required', 50., False),
])
def test_parser_preserves_requested_radius_and_boundary(geo, query, mode, radius, expected):
    async def run():
        data = {'hard_filters': {}, 'soft_preferences': [], 'location_scope':
                {'place': 'Anchor, Fixtureland', 'radius_km': radius, 'mode': mode, 'evidence': query}}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={
            'choices': [{'message': {'tool_calls': [{'function': {'name': 'emit_query_spec', 'arguments': json.dumps(data)}}]}}]}))) as client:
            return await parse_query(query, settings=Settings(openrouter_api_key='fixture', openrouter_model='fixture:free'), client=client)
    if expected:
        assert asyncio.run(run()).location_scope.mode == mode
    else:
        with pytest.raises(QueryParserError):
            asyncio.run(run())

"""Query-driven web discovery. Search snippets are leads, never scored JDs."""
import asyncio
from hashlib import sha256
import re
from time import monotonic
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.llm import call_tool
from app.web_fetch import fetch, validate_public_url


def linkedin_url(url: str) -> str:
    parts = urlparse(url.strip())
    host = (parts.hostname or '').lower().rstrip('.')
    if parts.scheme != 'https' or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('Paste an HTTPS LinkedIn job URL, such as https://www.linkedin.com/jobs/view/1234567890')
    if host != 'linkedin.com' and not host.endswith('.linkedin.com'):
        raise ValueError('Paste a LinkedIn job URL')
    match = re.fullmatch(r'/jobs/view/(?:[^/]*-)?(\d+)/?', parts.path)
    if not match:
        raise ValueError('Paste a specific LinkedIn job URL from /jobs/view/, rather than a search or profile link')
    return 'https://www.linkedin.com/jobs/view/' + match.group(1)


def is_linkedin(url: str) -> bool:
    host = (urlparse(url).hostname or '').lower().rstrip('.')
    return host == 'linkedin.com' or host.endswith('.linkedin.com')


def canonical_url(url: str) -> str:
    if is_linkedin(url):
        return linkedin_url(url)
    parts = urlparse(url)
    if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password
            or parts.port not in (None, 80, 443)):
        raise ValueError('Job links must be public HTTP(S) URLs without credentials or custom ports')
    # Only tracking parameters are discarded; ATS job IDs in query strings stay.
    from urllib.parse import parse_qsl
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith('utm_') and k.lower() not in ('source', 'ref', 'trk')])
    return urlunparse((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/'), '', query, ''))


class SearchTerms(BaseModel):
    model_config = ConfigDict(extra='forbid')
    keywords: list[str] = Field(min_length=1, max_length=3)


async def search_terms(spec: dict, profile: dict | None = None) -> list[str]:
    hard = spec.get('hard_filters', {})
    explicit = hard.get('role_keywords', []) + hard.get('tech_stack_keywords', [])
    if explicit:
        seniority = [target for p in spec.get('soft_preferences', []) if p.get('factor') == 'seniority'
                     for target in p.get('targets', [])]
        return list(dict.fromkeys([' '.join(seniority + explicit)[:180], ' '.join(explicit)[:180]]))
    # Identity and raw resume content never go to the search provider.
    skills = [f.get('text', '') for f in (profile or {}).get('facts', [])
              if isinstance(f, dict) and f.get('category') == 'skill']
    if not skills:
        return ['technology jobs']
    result = await call_tool(SearchTerms, system='Choose up to three short job-search role/skill keyword phrases supported by the supplied skills. No employer names, personal information, location, experience duration, or invented skills. These are retrieval queries, not mandatory filters.', data={'skills': skills})
    return [text.strip()[:180] for text in result.keywords if text.strip()] or ['technology jobs']


def linkedin_search_url(terms: list[str], spec: dict) -> str:
    hard = spec.get('hard_filters', {})
    return 'https://www.linkedin.com/jobs/search/?' + urlencode({
        'keywords': ' '.join(([terms[0]] if terms else ['technology jobs']) + hard.get('company_names', [])),
        'location': ', '.join(hard.get('locations', [])),
    })


class WebSearchError(ValueError):
    pass


_SEARCH_CACHE: dict[str, tuple[float, list[dict]]] = {}


class TavilySearch:
    """Replaceable search provider; no generated-answer endpoint is used."""
    def __init__(self, client: httpx.AsyncClient, key: str):
        self.client, self.key = client, key
        self.cache_hits, self.requests = 0, 0

    async def search(self, query: str) -> list[dict]:
        cache_key = sha256(('tavily-basic-v1\0' + self.key + '\0' + query).encode()).hexdigest()
        cached = _SEARCH_CACHE.get(cache_key)
        if cached and monotonic() - cached[0] < 600:
            self.cache_hits += 1
            return [dict(item) for item in cached[1]]
        from app.discovery_cache import read as cached_response, write as cache_response
        persisted = cached_response(cache_key)
        if persisted is not None:
            self.cache_hits += 1
            return persisted
        from app.budgets import reserve
        try:
            reserve('web')
        except HTTPException as exc:
            raise WebSearchError('The daily web discovery safety limit was reached. Configured employer sources were still checked.') from exc
        self.requests += 1
        response = await self.client.post('https://api.tavily.com/search',
            headers={'Authorization': 'Bearer ' + self.key},
            json={'query': query, 'search_depth': 'basic', 'max_results': 10,
                  'include_answer': False, 'include_raw_content': False, 'auto_parameters': False}, timeout=25)
        if response.status_code in (429, 432, 433):
            raise WebSearchError('Web discovery reached its provider quota or rate limit. Configured company boards were still checked.')
        if response.status_code in (401, 403):
            raise WebSearchError('Web discovery could not authenticate. Check TAVILY_API_KEY in .env.')
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError('Web discovery returned an invalid response.') from exc
        if not isinstance(data, dict) or not isinstance(data.get('results'), list):
            raise ValueError('Web discovery returned an invalid response.')
        if not all(isinstance(item, dict) and isinstance(item.get('url'), str) for item in data['results']):
            raise ValueError('Web discovery returned invalid search links.')
        if len(_SEARCH_CACHE) >= 256:
            _SEARCH_CACHE.clear()
        _SEARCH_CACHE[cache_key] = (monotonic(), data['results'])
        cache_response(cache_key, data['results'])
        return data['results']


async def web_jobs(spec: dict, terms: list[str], client: httpx.AsyncClient, *, provider=None) -> dict:
    from app.scout import ats_jobs, parse_static
    from app.sources import JobSource, ats_board_token, known_ats
    settings = get_settings()
    result = {'jobs': [], 'warnings': [], 'external_links': [], 'queries': [], 'pages_checked': 0}
    if provider is None and not settings.tavily_api_key:
        result['warnings'].append('Web discovery is off. Add TAVILY_API_KEY to .env and restart the backend. Configured company boards still work.')
        return result
    provider = provider or TavilySearch(client, settings.tavily_api_key)
    hard = spec.get('hard_filters', {})
    context = ' '.join(hard.get('locations', []) + hard.get('company_names', []) + hard.get('industries', []) + hard.get('work_modes', []))
    if spec.get('location_scope'):
        from app.geography import gazetteer
        anchor = gazetteer().resolve(spec['location_scope']['place'])
        context = ' '.join(filter(None, [context, anchor['name'], anchor['country']]))
    queries = [f'{term} {context} jobs careers apply'.strip() for term in terms[:1]]
    if terms and (spec.get('location_scope') or {}).get('mode') == 'preferred':
        queries.append(f"{terms[0]} {anchor['country']} jobs careers apply")
    # Spend the bounded query budget on retrievable descriptions. Public platform
    # links can still be discovered organically and remain unscored when inaccessible.
    if terms:
        queries.append(f'{terms[0]} {context} (site:greenhouse.io OR site:lever.co OR site:myworkdayjobs.com)')
        queries.append(f'{terms[1] if len(terms)>1 else terms[0]} {context} careers job description -site:linkedin.com')
    leads = {}
    budget = max(1, min(settings.web_search_max_queries, 6))
    index = 0
    while index < min(len(queries), budget):
        query = queries[index]
        result['queries'].append(query)
        try:
            for item in await provider.search(query):
                url = item.get('url', '')
                if urlparse(url).scheme == 'https':
                    leads.setdefault(url, item)
            # Use the remaining query budget to seek an employer copy of an
            # indexed LinkedIn listing. Never fetch LinkedIn itself.
            if index == 1 and budget > 2:
                linkedin_lead = next((i for i in leads.values() if is_linkedin(i.get('url', ''))), None)
                if linkedin_lead:
                    employer_query = str(linkedin_lead.get('title', ''))[:180] + ' careers apply -site:linkedin.com'
                    if len(queries) > 2:
                        queries[2] = employer_query
                    else:
                        queries.append(employer_query)
        except WebSearchError as exc:
            result['warnings'].append(str(exc))
            break
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            result['warnings'].append('Web discovery failed or reached its quota. Check the search key and provider dashboard; company-board results remain available.')
            break
        index += 1
    semaphore = asyncio.Semaphore(3)

    async def read(item):
        url = item['url']
        lead = {'title': str(item.get('title') or 'External listing')[:200], 'url': url,
                'detail': 'Job details unavailable. This link is unscored; check the original listing for details and availability.'}
        if is_linkedin(url):
            try:
                lead['url'] = linkedin_url(url)
            except ValueError:
                return [], None
            return [], lead
        async with semaphore:
            result['pages_checked'] += 1
            try:
                parts = urlparse(url)
                source = JobSource(company='Not specified', url=url)
                ats = known_ats(source)
                if ats in ('greenhouse', 'lever'):
                    paths = [p for p in parts.path.split('/') if p]
                    token = ats_board_token(url, ats)
                    source.company = token
                    found = await ats_jobs(source, client, ats)
                    if ats == 'greenhouse' and 'boards' in paths:
                        remainder = paths[paths.index('boards') + 2:]
                    elif ats == 'lever' and paths[:2] == ['v0', 'postings']:
                        remainder = paths[3:]
                    else:
                        remainder = paths[1:]
                    job_id = (parse_qs(parts.query).get('gh_jid') or [None])[0] if ats == 'greenhouse' else None
                    if remainder and remainder != ['jobs']:
                        job_id = remainder[-1]
                    if job_id:
                        found = [j for j in found if str(j.get('metadata', {}).get('external_id', '')) == job_id
                                 or urlparse(j['url']).path.rstrip('/').split('/')[-1] == job_id]
                else:
                    response = await fetch(client, url)
                    found, _ = parse_static(source, response.text, str(response.url), 'web')
                    found = [j for j in found if j.get('metadata', {}).get('structured_job')]
                found = [j for j in found if j.get('description', '').strip() and j['company'] != 'Not specified']
                for job in found:
                    job['url'] = canonical_url(job['url'])
                    if is_linkedin(job['url']):
                        continue
                    await validate_public_url(job['url'])
                    job.setdefault('metadata', {})['discovered_via'] = url
                found = [job for job in found if not is_linkedin(job['url'])]
                return found, None if found else lead
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                return [], lead

    # Do not let indexed LinkedIn leads consume the employer page-fetch budget.
    linkedin = [item for item in leads.values() if is_linkedin(item['url'])][:10]
    other = [item for item in leads.values() if not is_linkedin(item['url'])][:max(1, min(settings.web_search_max_pages, 20))]
    for jobs, lead in await asyncio.gather(*(read(item) for item in other + linkedin)):
        result['jobs'].extend(jobs)
        if lead:
            result['external_links'].append(lead)
    result['cache_hits'] = getattr(provider, 'cache_hits', 0)
    result['provider_requests'] = getattr(provider, 'requests', 0)
    return result

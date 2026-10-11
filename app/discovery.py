"""Query-driven web discovery. Search snippets are leads, never scored JDs."""
import asyncio
from hashlib import sha256
import re
from time import monotonic
from urllib.parse import urlencode, urlparse, urlunparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.llm import call_tool
from app.web_fetch import fetch, validate_public_url


def linkedin_url(url: str) -> str:
    parts = urlparse(url.strip())
    host = (parts.hostname or '').lower()
    if parts.scheme != 'https' or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('Paste an HTTPS LinkedIn job URL, such as https://www.linkedin.com/jobs/view/1234567890')
    if host != 'linkedin.com' and not host.endswith('.linkedin.com'):
        raise ValueError('Paste a LinkedIn job URL')
    match = re.fullmatch(r'/jobs/view/(?:[^/]*-)?(\d+)/?', parts.path)
    if not match:
        raise ValueError('Paste a specific LinkedIn job URL from /jobs/view/, rather than a search or profile link')
    return 'https://www.linkedin.com/jobs/view/' + match.group(1)


def is_linkedin(url: str) -> bool:
    host = (urlparse(url).hostname or '').lower()
    return host == 'linkedin.com' or host.endswith('.linkedin.com')


def canonical_url(url: str) -> str:
    if is_linkedin(url):
        return linkedin_url(url)
    parts = urlparse(url)
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
        return [' '.join(explicit)[:180]]
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

    async def search(self, query: str) -> list[dict]:
        cache_key = sha256((self.key + '\0' + query).encode()).hexdigest()
        cached = _SEARCH_CACHE.get(cache_key)
        if cached and monotonic() - cached[0] < 600:
            return [dict(item) for item in cached[1]]
        response = await self.client.post('https://api.tavily.com/search',
            headers={'Authorization': 'Bearer ' + self.key},
            json={'query': query, 'search_depth': 'basic', 'max_results': 10,
                  'include_answer': False, 'include_raw_content': False, 'auto_parameters': False}, timeout=25)
        if response.status_code in (429, 432, 433):
            raise WebSearchError('Web discovery reached its provider quota or rate limit. Configured company boards were still checked.')
        if response.status_code in (401, 403):
            raise WebSearchError('Web discovery could not authenticate. Check TAVILY_API_KEY in .env.')
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get('results'), list):
            raise ValueError('Web discovery returned an invalid response.')
        if not all(isinstance(item, dict) and isinstance(item.get('url'), str) for item in data['results']):
            raise ValueError('Web discovery returned invalid search links.')
        if len(_SEARCH_CACHE) >= 256:
            _SEARCH_CACHE.clear()
        _SEARCH_CACHE[cache_key] = (monotonic(), data['results'])
        return data['results']


async def web_jobs(spec: dict, terms: list[str], client: httpx.AsyncClient, *, provider=None) -> dict:
    from app.scout import ats_jobs, parse_static
    from app.sources import JobSource, known_ats
    settings = get_settings()
    result = {'jobs': [], 'warnings': [], 'external_links': [], 'queries': [], 'pages_checked': 0}
    if provider is None and not settings.tavily_api_key:
        result['warnings'].append('Web discovery is off. Add TAVILY_API_KEY to .env and restart the backend. Configured company boards still work.')
        return result
    provider = provider or TavilySearch(client, settings.tavily_api_key)
    hard = spec.get('hard_filters', {})
    context = ' '.join(hard.get('locations', []) + hard.get('company_names', []))
    queries = [f'{term} {context} jobs careers apply'.strip() for term in terms[:1]]
    # Include LinkedIn as a discovery source, without fetching or automating it.
    if terms:
        queries.append(f'site:linkedin.com/jobs/view/ {terms[0]} {context}')
    if len(terms) > 1:
        queries.append(f'{terms[1]} {context} jobs careers apply'.strip())
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
                'detail': 'Job details unavailable. Open the listing, or paste its LinkedIn URL and JD into chat.'}
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
                    if not paths:
                        return [], lead
                    source.url = f'{parts.scheme}://{parts.netloc}/{paths[0]}'
                    source.company = paths[0]
                    found = await ats_jobs(source, client, ats)
                    if len(paths) > 1 or parts.query:
                        found = [j for j in found if canonical_url(j['url']) == canonical_url(url)]
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
    return result

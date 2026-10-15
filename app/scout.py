"""ATS APIs, bounded static crawler, then logged Playwright fallback."""

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
import html
import json
import logging
import re
from itertools import zip_longest
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from app.sources import JobSource, ats_board_token, known_ats, load_sources
from app.web_fetch import fetch, validate_public_url

logger = logging.getLogger(__name__)
TECH_ROLE = re.compile(r"\b(engineer|developer|software|data|scientist|security|devops|sre|technical|technology|IT|programmer|QA|machine learning|AI|ML|analytics|product design|UX)\b", re.I)


def text_from_html(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True)


def parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def posting(source: JobSource, *, title: str, url: str, description="", location="", posted_at=None, path="ats", **metadata):
    if not isinstance(title, str) or not title.strip() or not isinstance(url, str) or not url:
        return None
    metadata = {**metadata, "source_url": source.url}
    if source.industry:
        metadata.update(industry=source.industry, industry_evidence="User-configured source metadata")
    if source.company_tier:
        metadata.update(company_tier=source.company_tier, tier_evidence="User-configured source metadata")
    description = description if isinstance(description, str) else ''
    location = location if isinstance(location, str) else ''
    return {"title": title.strip(), "company": source.company, "location": location or "Not specified",
            "url": urljoin(source.url, url), "description": description,
            "description_snippet": description[:450], "posted_at": posted_at,
            "source": path, "metadata": metadata}


async def ats_jobs(source: JobSource, client: httpx.AsyncClient, provider: str) -> list[dict]:
    parts = urlparse(source.url)
    path = [p for p in parts.path.split("/") if p]
    jobs = []
    if provider == "greenhouse":
        token = ats_board_token(source.url, provider)
        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        data = (await fetch(client, endpoint)).json()
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            raise ValueError('Greenhouse returned invalid job data')
        for item in data.get("jobs", []):
            if not isinstance(item, dict):
                continue
            location = item.get('location')
            jobs.append(posting(source, title=item.get("title"), url=item.get("absolute_url"),
                description=text_from_html(item.get("content", "")), location=location.get('name', '') if isinstance(location, dict) else '',
                # updated_at is NOT publication time; never use it for recency.
                posted_at=parse_date(item.get("first_published")), endpoint=endpoint, external_id=str(item.get("id", ''))))
    elif provider == "lever":
        token = ats_board_token(source.url, provider)
        api_host = "api.eu.lever.co" if (parts.hostname or "").startswith("jobs.eu.") else "api.lever.co"
        endpoint = f"https://{api_host}/v0/postings/{token}?mode=json"
        data = (await fetch(client, endpoint)).json()
        if not isinstance(data, list):
            raise ValueError('Lever returned invalid job data')
        for item in data:
            if not isinstance(item, dict):
                continue
            description = text_from_html(item.get("descriptionPlain") or item.get("description", ""))
            sections = item.get('lists')
            if isinstance(sections, list):
                description += " " + " ".join(text_from_html(section.get("content", ""))
                                               for section in sections if isinstance(section, dict))
            categories = item.get('categories')
            jobs.append(posting(source, title=item.get("text"), url=item.get("hostedUrl"), description=description.strip(),
                location=categories.get('location', '') if isinstance(categories, dict) else '',
                posted_at=parse_date(item.get("createdAt")), endpoint=endpoint, external_id=str(item.get('id', ''))))
    elif provider == "workday":
        if not path or ".myworkdayjobs.com" not in (parts.hostname or ""):
            raise ValueError("Workday source needs a public myworkdayjobs.com site URL")
        tenant = parts.hostname.split(".")[0]
        site = next((p for p in path if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)), path[-1])
        endpoint = f"{parts.scheme}://{parts.netloc}/wday/cxs/{tenant}/{site}/jobs"
        for offset in range(0, 100, 20):
            data = (await fetch(client, endpoint, method="POST", json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""})).json()
            for item in data.get("jobPostings", []):
                posted = item.get("postedOn", "")
                match = re.search(r"(\d+)\s+Days?", posted, re.I)
                date = datetime.now(timezone.utc) - timedelta(days=int(match.group(1))) if match else None
                if "today" in posted.casefold():
                    date = datetime.now(timezone.utc)
                external_path = item.get("externalPath", "")
                detail_endpoint = endpoint.removesuffix("/jobs") + external_path
                detail = (await fetch(client, detail_endpoint)).json().get("jobPostingInfo", {}) if external_path else {}
                jobs.append(posting(source, title=item["title"], url=source.url.rstrip("/") + external_path,
                    location=item.get("locationsText", ""), description=text_from_html(detail.get("jobDescription", "")),
                    posted_at=parse_date(detail.get("startDate")) or date, endpoint=detail_endpoint))
            if offset + 20 >= data.get("total", 0):
                break
    return [j for j in jobs if j]


def parse_static(source: JobSource, document: str, page_url: str, path="bs4") -> tuple[list[dict], list[str]]:
    soup = BeautifulSoup(document, "html.parser")
    jobs = []
    def visit(value):
        if isinstance(value, list):
            for entry in value:
                visit(entry)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            if isinstance(types, str):
                types = [types]
            if not isinstance(types, list):
                types = []
            if "JobPosting" in types:
                expires = parse_date(value.get("validThrough"))
                if expires and expires < datetime.now(timezone.utc):
                    return
                locations = value.get("jobLocation", [])
                if isinstance(locations, dict):
                    locations = [locations]
                if not isinstance(locations, list):
                    locations = []
                labels = []
                for loc in locations:
                    address = loc.get("address", {}) if isinstance(loc, dict) else {}
                    if isinstance(address, dict):
                        components = []
                        for key in ('addressLocality', 'addressRegion', 'addressCountry'):
                            component = address.get(key)
                            if isinstance(component, dict):
                                component = component.get('name')
                            if isinstance(component, str) and component.strip():
                                components.append(component.strip())
                        if components:
                            labels.append(', '.join(components))
                if value.get("jobLocationType") == "TELECOMMUTE":
                    labels.insert(0, "Remote")
                job_url = value.get('url') or page_url
                if not isinstance(job_url, str):
                    return
                job = posting(source, title=value.get("title", ""), url=urljoin(page_url, job_url),
                    description=text_from_html(value.get("description", "")), location=" / ".join(labels),
                    posted_at=parse_date(value.get("datePosted")), path=path, structured_job=True)
                organization = value.get("hiringOrganization", {})
                if job and isinstance(organization, dict) and isinstance(organization.get("name"), str):
                    job["company"] = organization['name'].strip() or source.company
                jobs.append(job)
            else:
                for child in value.values():
                    if isinstance(child, (dict, list)):
                        visit(child)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            visit(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError):
            logger.info("Invalid JSON-LD on %s", page_url)
    for card in soup.select("[data-job-title], .job-card, .job-listing, .job-posting"):
        link = card.select_one("a[href]")
        heading = card.select_one("h2, h3, [data-job-title]")
        title = card.get("data-job-title") or (heading.get_text(" ", strip=True) if heading else link.get_text(" ", strip=True) if link else "")
        if link and title:
            jobs.append(posting(source, title=title, url=urljoin(page_url, link["href"]), description=card.get_text(" ", strip=True),
                location=(card.select_one(".location").get_text(" ", strip=True) if card.select_one(".location") else ""),
                path=path, description_kind='listing'))
    links = []
    for anchor in soup.select("a[href]"):
        url = urljoin(page_url, anchor["href"]).split("#")[0]
        if urlparse(url).netloc == urlparse(source.url).netloc and re.search(r"(job|career|position|opening)", url, re.I):
            links.append(url)
    return [j for j in jobs if j], list(dict.fromkeys(links))


async def browser_jobs(source: JobSource) -> list[dict]:
    logger.warning("Playwright fallback: no usable ATS/static data for %s", source.url)
    from playwright.async_api import async_playwright
    await validate_public_url(source.url)
    async with async_playwright() as runtime:
        browser = await runtime.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            async def route(request_route):
                try:
                    await validate_public_url(request_route.request.url)
                    await request_route.continue_()
                except ValueError:
                    await request_route.abort()
            await page.route("**/*", route)
            await page.goto(source.url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1500)
            jobs, _ = parse_static(source, await page.content(), page.url, "playwright")
            return jobs
        finally:
            await browser.close()


async def crawl_source(source: JobSource, client: httpx.AsyncClient) -> tuple[list[dict], list[str]]:
    warnings = []
    provider = known_ats(source)
    if provider:
        try:
            jobs = await ats_jobs(source, client, provider)
            if jobs:
                return jobs, warnings
            warnings.append(f"{source.company}: ATS returned no usable jobs; trying static pages")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("ATS failed for %s (%s)", source.company, type(exc).__name__)
            warnings.append(f"{source.company}: ATS fetch failed; trying static pages")
    queue, seen, jobs = deque([(source.url, 0)]), set(), []
    while queue and len(seen) < 8:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            response = await fetch(client, url)
            found, links = parse_static(source, response.text, url)
            jobs.extend(found)
            if depth < 1:
                queue.extend((link, depth + 1) for link in links[:8])
        except (httpx.HTTPError, ValueError):
            warnings.append(f"{source.company}: unable to fetch a career page")
    if not jobs:
        try:
            jobs = await browser_jobs(source)
        except Exception as exc:
            logger.warning("Browser fallback failed for %s (%s)", source.company, type(exc).__name__)
            warnings.append(f"{source.company}: browser fallback unavailable or no accessible postings")
    return jobs, warnings


async def discover_jobs(query_spec: dict, limit: int = 10, *, sources: list[JobSource] | None = None,
                        tracked_urls: set[str] | None = None, client: httpx.AsyncClient | None = None,
                        discovery_terms: list[str] | None = None) -> dict:
    if not 1 <= limit <= 200:
        raise ValueError("Job limit must be between 1 and 200")
    active_sources = [s for s in (sources if sources is not None else load_sources()) if s.enabled]
    company_names = query_spec.get("hard_filters", {}).get("company_names", [])
    if company_names:
        active_sources = [s for s in active_sources if s.company.casefold() in {n.casefold() for n in company_names}]
    if not active_sources and discovery_terms is None:
        return {"jobs": [], "warnings": ["No configured source matches this search. Add a company career URL in Settings."],
                "stats": {"sources_searched": 0, "retrieved": 0, "tech_jobs": 0, "already_tracked": 0,
                          "hard_filter_excluded": {}, "eligible": 0, "returned": 0}}
    semaphore = asyncio.Semaphore(4)
    async def collect(source, active):
        async with semaphore:
            return await crawl_source(source, active)
    async def run(active):
        from app.query_parser import QuerySpec
        from app.scoring import eligible
        spec = QuerySpec(hard_filters=query_spec.get("hard_filters", {}), soft_preferences=[],
                         location_scope=query_spec.get('location_scope'))
        from app.discovery import canonical_url
        tracked = set()
        for url in tracked_urls or set():
            try:
                tracked.add(canonical_url(url))
            except ValueError:
                tracked.add(url)
        as_of = datetime.now(timezone.utc)
        collected = await asyncio.gather(*(collect(s, active) for s in active_sources))
        web = {"jobs": [], "warnings": [], "external_links": [], "queries": [], "pages_checked": 0}
        if discovery_terms is not None:
            from app.discovery import web_jobs
            web = await web_jobs(query_spec, discovery_terms, active)
            collected.append((web['jobs'], web['warnings']))
        jobs, warnings, seen = [], [], set()
        tech_seen, incomplete = set(), {}
        stats = {"sources_searched": len(active_sources), "retrieved": sum(len(found) for found, _ in collected),
                 "tech_jobs": 0, "already_tracked": 0, "hard_filter_excluded": {}, "eligible": 0, "returned": 0}
        stats.update(web_queries=len(web['queries']), web_pages_checked=web['pages_checked'])
        stats['description_unavailable'] = 0
        external_links = list(web['external_links'])
        matching_sources = []
        for found, notes in collected:
            warnings.extend(notes)
            matches = []
            for job in found:
                try:
                    job['url'] = canonical_url(job['url'])
                except ValueError:
                    continue
                if job["url"] not in seen and TECH_ROLE.search(job["title"]):
                    if job['url'] not in tech_seen:
                        tech_seen.add(job['url'])
                        stats["tech_jobs"] += 1
                    if job["url"] in tracked:
                        seen.add(job['url'])
                        stats["already_tracked"] += 1
                        continue
                    if not job.get('description', '').strip() or job.get('metadata', {}).get('description_kind') == 'listing':
                        incomplete.setdefault(job['url'], {'title': job['title'], 'url': job['url'],
                            'detail': 'Full job description unavailable. This lead is unscored; required filters and availability are unverified.'})
                        continue
                    seen.add(job['url'])
                    incomplete.pop(job['url'], None)
                    accepted, reason = eligible(job, spec, as_of)
                    if not accepted:
                        exclusions = stats["hard_filter_excluded"]
                        exclusions[reason] = exclusions.get(reason, 0) + 1
                        continue
                    matches.append(job)
            matching_sources.append(matches)
        stats['description_unavailable'] = len(incomplete)
        external_links = list({lead['url']: lead for lead in external_links + list(incomplete.values())
                               if lead['url'] not in seen}.values())
        stats['unscored_leads'] = len(external_links)
        if stats['description_unavailable']:
            warnings.append(f"{stats['description_unavailable']} listings had no verified job description and were left unscored.")
        # Apply mandatory filters to every source before capping, then interleave
        # sources so a large first company cannot consume the whole candidate pool.
        for group in zip_longest(*matching_sources):
            jobs.extend(job for job in group if job is not None)
        stats["eligible"], stats["returned"] = len(jobs), min(len(jobs), limit)
        return {"jobs": jobs[:limit], "warnings": warnings, "stats": stats,
                "external_links": external_links, "web_queries": web['queries']}
    if client is not None:
        return await run(client)
    async with httpx.AsyncClient(headers={"User-Agent": "CareerOps/0.1 (personal career research)"}) as active:
        return await run(active)


async def search_jobs(query_spec: dict, limit: int = 10) -> list[dict]:
    """Stable public scout contract; deduplicates against the local tracker."""
    from sqlmodel import Session, select
    from app.db import engine, init_db
    from app.models import Application, JobPosting
    init_db()
    with Session(engine) as session:
        tracked = set(session.exec(select(JobPosting.url).join(Application).where(
            JobPosting.user_id == 1, Application.status != "dismissed"
        )).all())
    return (await discover_jobs(query_spec, limit, tracked_urls=tracked))["jobs"]

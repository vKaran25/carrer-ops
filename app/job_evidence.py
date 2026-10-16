"""Conservative source checks; no LLM invents missing JD or location details."""
import re


def usable_description(job: dict) -> bool:
    description = job.get('description', '').strip()
    metadata = job.get('metadata') or job.get('source_metadata') or {}
    # A minimum content guard catches one-line structured summaries. It does not
    # certify completeness; original source and uncertainty remain visible.
    return len(description) >= 300 and metadata.get('description_kind') != 'listing'


def stated_work_location(job: dict) -> str | None:
    text = job.get('description', '')
    match = re.search(r'\b(?:work\s+location|job\s+location|place\s+of\s+work)\s*:\s*'
                      r'([^\n\r;]{2,160}?)(?=\n|\r|;|\b(?:experience|qualifications|responsibilities|employment\s+type|job\s+type|function)\s*:|$)', text, re.I)
    return match.group(1).strip(' .') if match else None


def location_evidence(job: dict) -> tuple[str, bool]:
    """Combine country evidence from the same posting; never choose a conflicting city."""
    base = job.get('location', '')
    stated = stated_work_location(job)
    if not stated:
        return base, False
    from app.geography import gazetteer
    geo = gazetteer()
    base_cities, base_countries = geo.job_places(base)
    cities, countries = geo.job_places(stated)
    selected = stated
    if not countries and len(base_countries) == 1:
        code = next(iter(base_countries))
        country = next(c['name'] for c in geo.countries() if c['code'] == code)
        selected = ' / '.join(chunk.strip() + ', ' + country for chunk in re.split(r'[;|/]|\s+or\s+', stated, flags=re.I) if chunk.strip())
        cities, countries = geo.job_places(selected)
    city_conflict = bool(base_cities and cities and not {c['id'] for c in base_cities}.intersection(c['id'] for c in cities))
    country_conflict = bool(base_countries and countries and base_countries.isdisjoint(countries))
    return selected, city_conflict or country_conflict

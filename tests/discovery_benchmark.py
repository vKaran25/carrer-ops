"""Opt-in live discovery capture and independent review; never opens the workspace DB."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic_core import to_jsonable_python
from app.config import get_settings
from app.discovery import canonical_url, search_terms
from app.query_parser import parse_query
from app.scoring import rank_jobs
from app.scout import discover_jobs
from app.sources import JobSource

MANIFEST = ROOT / 'tests/discovery_benchmark.json'


def employer_key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def assess(report, manifest):
    """Unreviewed evidence never passes. Fit scores are not relevance labels."""
    gates = manifest['gates']
    expected = {case['id']: case for case in manifest['cases']}
    rows = report.get('cases', [])
    if len(rows) != len(expected) or {row['id'] for row in rows} != set(expected):
        raise ValueError('Review must contain exactly the 12 fixed benchmark cases')
    pending, failures, covered, non_seed = [], [], 0, set()
    reviewed, relevant, indian_counts, international_counts = 0, 0, {}, {}
    seeds = {employer_key(name) for name in report['seed_employers']}
    for row in rows:
        case = expected[row['id']]
        if row.get('error'):
            failures.append(row['id'] + ': capture failed')
        jobs = row.get('jobs', [])
        if len(jobs) > 10:
            raise ValueError('Only the captured top 10 may be reviewed')
        usable, seen_urls = 0, set()
        for job in jobs:
            try:
                url = canonical_url(job.get('url', ''))
            except ValueError:
                failures.append(row['id'] + ': invalid captured job URL')
                continue
            if url in seen_urls:
                failures.append(row['id'] + ': duplicate captured job URL')
                continue
            seen_urls.add(url)
            if not job.get('description', '').strip() or job.get('metadata', {}).get('description_kind') == 'listing':
                failures.append(row['id'] + ': missing usable job description')
                continue
            review = job.get('review', {})
            fields = ('relevant', 'mandatory_filters_satisfied', 'source_evidence_supported')
            if any(type(review.get(field)) is not bool for field in fields):
                pending.append(row['id'] + ': job needs independent review')
                continue
            reviewed += 1
            relevant += review['relevant']
            if not review['mandatory_filters_satisfied'] or not review['source_evidence_supported']:
                failures.append(row['id'] + ': mandatory-filter or source-evidence failure')
            if all(review[field] for field in fields):
                usable += 1
                if case['region'] == 'India':
                    identity = review.get('verified_employer_name')
                    if not isinstance(identity, str) or not identity.strip():
                        pending.append(row['id'] + ': employer identity needs verification')
                    elif employer_key(identity) not in seeds:
                        non_seed.add(employer_key(identity))
        if row.get('effective_filters_reviewed') is False:
            failures.append(row['id'] + ': parsed filters contradict the requested search')
        elif row.get('effective_filters_reviewed') is not True:
            pending.append(row['id'] + ': parsed filters need independent review')
        if case['region'] == 'India':
            indian_counts[row['id']] = usable
            verified = row.get('eligible_openings_verified')
            if type(verified) is not bool:
                pending.append(row['id'] + ': eligible-opening availability needs independent review')
            elif verified and not row.get('reference_openings'):
                pending.append(row['id'] + ': independent reference openings missing')
            elif verified and usable >= gates['minimum_jobs_per_indian_case']:
                covered += 1
        else:
            international_counts[row['id']] = usable
    relevance = relevant / reviewed if reviewed else 0
    if relevance < gates['minimum_relevance']:
        failures.append('Reviewed relevance below 70%')
    if covered < gates['minimum_covered_indian_cases']:
        failures.append('Fewer than 6 Indian cases have 3 relevant, evidenced eligible jobs')
    if len(non_seed) < gates['minimum_non_seed_indian_employers']:
        failures.append('Fewer than 5 verified non-seed Indian employers')
    return {'status': 'pending' if pending else 'failed' if failures else 'passed',
            'reviewed_jobs': reviewed, 'relevance': relevance, 'covered_indian_cases': covered,
            'non_seed_indian_employers': len(non_seed), 'indian_usable_counts': indian_counts,
            'international_usable_counts': international_counts, 'pending': pending, 'failures': failures,
            'notice': 'A passed discovery benchmark is not full P4 acceptance. Review international gaps and actual provider credits separately.'}


async def capture(manifest):
    settings = get_settings()
    if not settings.tavily_api_key or not settings.openrouter_configured or not settings.free_model_selected:
        raise ValueError('Configure TAVILY_API_KEY and a free tool-capable OpenRouter model before live capture')
    sources = [JobSource.model_validate(item) for item in json.loads((ROOT / 'app/default_sources.json').read_text())]
    report = {'benchmark_version': manifest['version'], 'captured_at': datetime.now(timezone.utc).isoformat(),
              'seed_employers': [source.company for source in sources], 'cases': [],
              'credits_note': 'queries are attempts, not charged credits; cache hits may reduce usage. Record dashboard credits before/after.',
              'provider_credits_before': None, 'provider_credits_after': None}
    for case in manifest['cases']:
        row = {'id': case['id'], 'query': case['query'], 'jobs': [], 'effective_filters_reviewed': None}
        if case['region'] == 'India':
            row.update(eligible_openings_verified=None, reference_openings=[])
        profile = {'facts': [{'id': 'fixture-skill', 'category': 'skill', 'text': case['skills']},
                             {'id': 'fixture-project', 'category': 'project', 'text': case['project']}]}
        try:
            spec = await parse_query(case['query'])
            terms = await search_terms(spec.model_dump(), profile)
            found = await discover_jobs(spec.model_dump(), limit=200, sources=sources,
                                        tracked_urls=set(), discovery_terms=terms)
            ranked = await asyncio.to_thread(rank_jobs, spec, found['jobs'], profile)
            row.update(query_spec=spec.model_dump(), search_stats=found['stats'],
                       warnings=found['warnings'], web_queries=found.get('web_queries', []),
                       external_links=found.get('external_links', []))
            for job in ranked['jobs'][:10]:
                row['jobs'].append({**job, 'review': {'relevant': None, 'mandatory_filters_satisfied': None,
                    'source_evidence_supported': None, 'verified_employer_name': None, 'notes': ''}})
        except Exception as exc:
            # Never persist provider payloads, credentials or a personal resume.
            row['error'] = type(exc).__name__
        report['cases'].append(to_jsonable_python(row))
        print(case['id'] + ': ' + (row.get('error') or f"{len(row['jobs'])} scored jobs captured; review pending"), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--capture', action='store_true', help='Uses real provider calls only when explicitly selected')
    action.add_argument('--review', type=Path, help='Assess a manually completed capture without network calls')
    parser.add_argument('--output', type=Path, help='New local capture file; existing files are never overwritten')
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    try:
        if args.capture:
            if args.output is None or args.output.exists():
                raise ValueError('--capture needs --output pointing to a new file')
            report = asyncio.run(capture(manifest))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
            return 1 if any(row.get('error') for row in report['cases']) else 0
        result = assess(json.loads(args.review.read_text(encoding='utf-8')), manifest)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'passed' else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Benchmark setup/review error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

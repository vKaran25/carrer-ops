"""Review cannot certify unlabelled output or use fit scores as relevance truth."""
from copy import deepcopy
import json

import pytest

from discovery_benchmark import MANIFEST, assess, capture


def report():
    manifest = json.loads(MANIFEST.read_text())
    rows = []
    for case in manifest['cases']:
        rows.append({'id': case['id'], 'effective_filters_reviewed': True,
            'eligible_openings_verified': True, 'reference_openings': ['https://example.org/reference'],
            'jobs': [{'url': f'https://example.org/{case["id"]}/{index}', 'description': 'A fictional complete job description.',
                'fit_score': 100, 'review': {'relevant': True, 'mandatory_filters_satisfied': True,
                'source_evidence_supported': True, 'verified_employer_name': 'Fictional employer ' + case['id']}} for index in range(3)]})
    return {'seed_employers': ['Fictional seed'], 'cases': rows}, manifest


def test_review_gate_rejects_unreviewed_high_fit_scores_and_missing_cases():
    data, manifest = report()
    data['cases'][0]['jobs'][0]['review']['relevant'] = None
    assert assess(data, manifest)['status'] == 'pending'
    with pytest.raises(ValueError, match='12 fixed'):
        assess({**data, 'cases': data['cases'][:-1]}, manifest)


def test_coverage_counts_real_reviewed_eligible_jobs_and_distinct_employers():
    data, manifest = report()
    assert assess(data, manifest)['status'] == 'passed'
    wrong = deepcopy(data)
    wrong['cases'][0]['jobs'][0]['review']['mandatory_filters_satisfied'] = False
    assert assess(wrong, manifest)['status'] == 'failed'
    same_employer = deepcopy(data)
    for case in same_employer['cases']:
        for job in case['jobs']:
            job['review']['verified_employer_name'] = 'One fictional employer'
    assert assess(same_employer, manifest)['non_seed_indian_employers'] == 1
    assert assess(same_employer, manifest)['status'] == 'failed'
    duplicates = deepcopy(data)
    duplicates['cases'][0]['jobs'][1] = deepcopy(duplicates['cases'][0]['jobs'][0])
    assert assess(duplicates, manifest)['status'] == 'failed'
    incorrect_parse = deepcopy(data)
    incorrect_parse['cases'][0]['effective_filters_reviewed'] = False
    assert assess(incorrect_parse, manifest)['status'] == 'failed'


def test_missing_key_fails_before_any_live_call(monkeypatch):
    import asyncio
    from app.config import Settings
    monkeypatch.setattr('discovery_benchmark.get_settings', lambda: Settings(tavily_api_key=''))
    with pytest.raises(ValueError, match='Configure TAVILY_API_KEY'):
        asyncio.run(capture(json.loads(MANIFEST.read_text())))

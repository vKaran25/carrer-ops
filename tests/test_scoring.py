from datetime import datetime, timezone
import pytest

from app.query_parser import QuerySpec
from app.scoring import contains, rank_jobs

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)
PROFILE = {"facts": [{"id": "p1", "category": "project", "text": "Built Java payment APIs."}]}
JOBS = [
    {"job_id": "weak", "title": "Java backend engineer", "company": "Fictional A", "description": "Java backend payments", "industry": "fintech", "company_tier": "high", "age_days": 2, "location": "Remote"},
    {"job_id": "strong", "title": "Java backend intern", "company": "Fictional B", "description": "Java backend payments", "industry": "fintech", "company_tier": "mid", "age_days": 3, "location": "India"},
    {"job_id": "old", "title": "Java backend intern", "company": "Fictional C", "description": "Java backend payments", "industry": "fintech", "company_tier": "mid", "age_days": 30},
    {"job_id": "wrong-stack", "title": "Javascript backend engineer", "company": "Fictional D", "description": "Javascript backend analytics", "industry": "analytics", "age_days": 2},
]


def spec(hard=None, soft=None):
    return QuerySpec(hard_filters=hard or {}, soft_preferences=soft or [])


def test_adversarial_soft_preferences_never_exclude_eligible_jobs():
    query = spec({"tech_stack_keywords": ["java"], "industries": ["fintech"], "recency_days": 7},
        [{"factor": "company_tier", "targets": ["low"], "weight": 1.0, "evidence": "only obscure startups"},
         {"factor": "seniority", "targets": ["intern"], "weight": 1.0, "evidence": "intern"}])
    result = rank_jobs(query, JOBS, PROFILE, as_of=NOW, semantic=lambda *_: 0.6)
    assert {j["job_id"] for j in result["jobs"]} == {"weak", "strong"}
    assert result["jobs"][0]["job_id"] == "strong"
    assert result["jobs"][1]["fit_score"] < result["jobs"][0]["fit_score"]
    assert "lower fit scores" in result["relaxation_note"]
    assert all("company_tier" in j["weak_preferences"] for j in result["jobs"])


@pytest.mark.parametrize("hard", [
    {"tech_stack_keywords": ["rust"]}, {"company_names": ["Nonexistent"]},
    {"industries": ["aerospace"]}, {"locations": ["Mars"]}, {"recency_days": 1},
])
def test_impossible_hard_filters_are_preserved(hard):
    result = rank_jobs(spec(hard), JOBS, PROFILE, as_of=NOW, semantic=lambda *_: 1)
    assert result["jobs"] == []
    assert "Hard filters were preserved" in result["relaxation_note"]


def test_unknown_publication_date_is_not_treated_as_recent():
    job = {"title": "Java engineer", "company": "Fixture", "description": "Java", "updated_at": NOW.isoformat()}
    result = rank_jobs(spec({"recency_days": 7}), [job], PROFILE, as_of=NOW)
    assert result["jobs"] == [] and result["excluded"]["Publication date unavailable"] == 1


def test_keyword_matching_does_not_confuse_java_with_javascript():
    assert not contains("Javascript development", "java")
    assert contains("Java, Python and C++", "java")
    assert contains("C++ development", "c++")


def test_resume_optional_search_discloses_missing_profile():
    result = rank_jobs(spec(), JOBS[:1], {}, as_of=NOW)
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["fit_score"] == 0
    assert "No resume on file" in result["jobs"][0]["explanation"]


def test_unknown_company_tier_is_not_invented():
    query = spec(soft=[{"factor": "company_tier", "targets": ["mid"], "weight": 1.0, "evidence": "mid"}])
    result = rank_jobs(query, [{"title": "Java engineer", "company": "Unknown", "description": "Java"}], PROFILE, semantic=lambda *_: .5)
    assert result["jobs"][0]["factors"][0]["value"] == 0
    assert "tier unknown" in result["jobs"][0]["explanation"]

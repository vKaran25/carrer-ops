import asyncio
import json
import os

import httpx
import pytest

from app.config import Settings
from app.query_parser import QueryParserError, QuerySpec, parse_query


QUERIES = [
    "find me jobs acc to my resume that is posted within this week",
    "find me jobs posted within a week or two that are not high-level companies, since as an intern I have a higher chance at mid-to-low-level companies",
    "find me jobs that best suit my stack of projects — e.g. if I built something similar to what a company builds, my interest and eligibility align better",
    "find me java backend jobs specifically from fintech companies",
    "find me jobs from companies already in my resume where I have a better chance of progressing career-wise",
]


def preference(factor, evidence, targets=None, weight=1.0):
    return dict(factor=factor, weight=weight, targets=targets or [], evidence=evidence)


# Representative tool outputs for deterministic contract tests. Actual extraction
# is tested separately by the opt-in live OpenRouter test below.
OUTPUTS = [
    dict(hard_filters={"recency_days": 7}, soft_preferences=[
        preference("resume_match", "acc to my resume"),
    ]),
    dict(hard_filters={"recency_days": 14}, soft_preferences=[
        preference("company_tier", "mid-to-low-level companies", ["mid", "low"]),
        preference("seniority", "as an intern", ["intern"], 0.5),
    ]),
    dict(hard_filters={}, soft_preferences=[
        preference("project_domain_similarity", "best suit my stack of projects"),
    ]),
    dict(hard_filters={"tech_stack_keywords": ["java"], "role_keywords": ["backend"],
                       "industries": ["fintech"]}, soft_preferences=[]),
    dict(hard_filters={}, soft_preferences=[
        preference("resume_company_affinity", "companies already in my resume"),
        preference("career_growth", "progressing career-wise"),
    ]),
]
SETTINGS = Settings(openrouter_api_key="test-key", openrouter_model="test/tool-model")


def assert_extraction(index, spec):
    hard = spec.hard_filters
    prefs = {p.factor: p for p in spec.soft_preferences}
    if index == 0:
        assert hard.recency_days == 7
        assert "resume_match" in prefs
    elif index == 1:
        assert hard.recency_days == 14
        assert "company_tier" in prefs
        assert set(prefs["company_tier"].targets) == {"mid", "low"}
    elif index == 2:
        assert "project_domain_similarity" in prefs
    elif index == 3:
        assert hard.tech_stack_keywords == ["java"]
        assert hard.role_keywords == ["backend"]
        assert hard.industries == ["fintech"]
        assert not prefs
    elif index == 4:
        assert {"resume_company_affinity", "career_growth"} <= prefs.keys()
    if index != 3:
        assert not hard.tech_stack_keywords
        assert not hard.role_keywords
        assert not hard.industries
    assert not hard.company_names
    if index > 1:
        assert hard.recency_days is None
    assert all(0 < p.weight <= 1 and p.evidence in QUERIES[index]
               for p in spec.soft_preferences)


def tool_response(output):
    return {"choices": [{"message": {"tool_calls": [{
        "type": "function", "function": {
            "name": "emit_query_spec", "arguments": json.dumps(output),
        },
    }]}}]}


@pytest.mark.parametrize("index", range(5))
def test_example_contract(index):
    requests = []

    def handler(request):
        requests.append(request)
        payload = json.loads(request.content)
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert payload["messages"][1] == {"role": "user", "content": QUERIES[index]}
        assert payload["tool_choice"]["function"]["name"] == "emit_query_spec"
        assert payload["provider"]["require_parameters"] is True
        assert payload["provider"]["data_collection"] == "deny"
        schema = payload["tools"][0]["function"]["parameters"]
        assert "hard_filters" in schema["properties"]
        assert "soft_preferences" in schema["properties"]
        return httpx.Response(200, json=tool_response(OUTPUTS[index]))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await parse_query(QUERIES[index], settings=SETTINGS, client=client)

    assert_extraction(index, asyncio.run(run()))
    assert len(requests) == 1


def test_example_specs_are_distinct():
    assert len({QuerySpec.model_validate(o).model_dump_json() for o in OUTPUTS}) == 5


@pytest.mark.parametrize("output", [
    {"hard_filters": {"company_tier": "low"}, "soft_preferences": []},
    {"hard_filters": {"recency_days": 0}, "soft_preferences": []},
    {"hard_filters": {}, "soft_preferences": [preference("resume_match", "invented")]},
    {"hard_filters": {}, "soft_preferences": [preference("resume_match", "resume", weight=0)]},
    {"hard_filters": {}, "soft_preferences": [preference("unknown", "resume")]},
    {"hard_filters": {}, "soft_preferences": [preference("resume_match", "resume")] * 2},
])
def test_invalid_specs_fail_without_retry(output):
    check_failure(httpx.Response(200, json=tool_response(output)))


@pytest.mark.parametrize("response", [
    httpx.Response(503),
    httpx.Response(200, json={"choices": [{"message": {"content": "not a tool call"}}]}),
    httpx.Response(200, content="not json"),
    httpx.Response(200, json={"choices": []}),
])
def test_upstream_failures(response):
    check_failure(response)


def check_failure(response):
    requests = []

    def handler(request):
        requests.append(request)
        return response

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(QueryParserError):
                await parse_query("my resume", settings=SETTINGS, client=client)

    asyncio.run(run())
    assert len(requests) == 1


def test_blank_and_unconfigured():
    with pytest.raises(ValueError):
        asyncio.run(parse_query("  ", settings=SETTINGS))
    with pytest.raises(QueryParserError, match="Configure"):
        asyncio.run(parse_query("jobs", settings=Settings(openrouter_api_key="", openrouter_model="")))


@pytest.mark.skipif(os.getenv("RUN_LIVE_QUERY_TESTS") != "1", reason="Opt-in live OpenRouter test")
def test_live_five_examples():
    async def run():
        specs = []
        for index, query in enumerate(QUERIES):
            spec = await parse_query(query)
            assert_extraction(index, spec)
            specs.append(spec.model_dump_json())
        assert len(set(specs)) == 5

    asyncio.run(run())

"""Regressions for location scope, source starvation and misleading empty results."""
import asyncio

import httpx
import pytest

from app.locations import location_matches, query_locations
from app.scout import discover_jobs
from app.search_feedback import empty_search_message
from app.sources import JobSource


def test_unqualified_city_and_unsupported_region_request_clarification():
    from app.geography import GeographyError
    with pytest.raises(GeographyError, match='ambiguous'):
        location_matches('Noida, India', 'Delhi')
    with pytest.raises(GeographyError):
        location_matches('Bengaluru, India', 'delhi ncr')


def test_exact_city_and_context_do_not_silently_expand():
    assert query_locations('find jobs in Pune', ['Pune, Maharashtra, India']) == ['Pune, Maharashtra, India']
    assert location_matches('Pune, India', 'Pune, Maharashtra, India')
    assert not location_matches('Bengaluru, India', 'Pune, Maharashtra, India')
    assert query_locations('I live near Delhi but want jobs in Bengaluru', ['bengaluru']) == ['bengaluru']
    assert location_matches('Gurugram, India', 'Gurgaon, Haryana, India')


def job(index, location="Remote", title="Software engineer"):
    return {"title": title, "company": "Fictional Test Co", "location": location,
            "url": f"https://example.org/job/{index}", "description": 'Java API development This fictional engineering position builds documented production APIs, reviews code, writes automated unit and integration tests, collaborates with product engineers, investigates service issues, maintains secure deployments and communicates implementation tradeoffs. Required skills are grounded in the role title and supplied fixture. '}


def test_location_filters_run_before_cap_and_late_sources_are_searched(monkeypatch):
    sources = [JobSource(company="Large fixture", url="https://example.org/large"),
               JobSource(company="Regional fixture", url="https://example.org/regional")]
    async def crawl(source, client):
        if source.company == "Large fixture":
            return [job(i) for i in range(300)], []
        return [job("regional", "Pune, India", "AI/ML Intern")], []
    monkeypatch.setattr("app.scout.crawl_source", crawl)
    async def run():
        async with httpx.AsyncClient() as client:
            return await discover_jobs({"hard_filters": {"locations": ["Pune, Maharashtra, India"]}}, 1,
                                       sources=sources, client=client)
    result = asyncio.run(run())
    assert [j["url"] for j in result["jobs"]] == ["https://example.org/job/regional"]
    assert result["stats"]["retrieved"] == 301
    assert result["stats"]["hard_filter_excluded"] == {"Different required location": 300}
    assert result["stats"]["eligible"] == 1


def test_result_cap_interleaves_matching_sources_and_preserves_tracking(monkeypatch):
    sources = [JobSource(company=name, url=f"https://example.org/{name}") for name in ("one", "two")]
    async def crawl(source, client):
        return [job(f"{source.company}-{i}", "Pune, India") for i in range(5)], []
    monkeypatch.setattr("app.scout.crawl_source", crawl)
    async def run():
        async with httpx.AsyncClient() as client:
            return await discover_jobs({"hard_filters": {"locations": ["Pune, Maharashtra, India"]}}, 2, sources=sources,
                                       client=client, tracked_urls={"https://example.org/job/one-0"})
    result = asyncio.run(run())
    assert [j["url"] for j in result["jobs"]] == ["https://example.org/job/one-1", "https://example.org/job/two-0"]
    assert result["stats"]["already_tracked"] == 1 and result["stats"]["eligible"] == 9


def test_empty_message_reports_location_without_claiming_tracker_exclusion():
    result = {"jobs": [], "query_spec": {"hard_filters": {"locations": ["Pune, Maharashtra, India"]}},
              "excluded": {"Different required location": 200}}
    message = empty_search_message(result)
    assert "Pune" in message and "checked company sources" in message
    assert "tracker" not in message
    assert "retrieved" in empty_search_message({"jobs": [], "search_stats": {"sources_searched": 2, "retrieved": 0}})
    assert "already in your tracker" in empty_search_message({
        "jobs": [], "search_stats": {"sources_searched": 1, "retrieved": 5, "already_tracked": 5, "tech_jobs": 5}
    })

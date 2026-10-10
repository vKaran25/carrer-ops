import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest

from app.scout import ats_jobs, discover_jobs, parse_static
from app.sources import JobSource, known_ats


@pytest.fixture(autouse=True)
def no_dns(monkeypatch):
    async def validate(url): pass
    monkeypatch.setattr("app.web_fetch.validate_public_url",validate)


def test_static_jsonld_crawl_contract_and_location():
    source=JobSource(company="Fictional Co",url="https://example.org/careers",provider="static")
    payload={"@type":"JobPosting","title":"Java backend engineer","description":"Build Java APIs","url":"/job/1","datePosted":"2026-10-08","jobLocation":{"address":{"addressLocality":"Bengaluru","addressCountry":"India"}}}
    jobs,links=parse_static(source,'<script type="application/ld+json">'+json.dumps(payload)+'</script><a href="/jobs/more">More</a>',source.url)
    assert jobs[0]["location"]=="Bengaluru, India" and jobs[0]["source"]=="bs4"
    assert jobs[0]["url"]=="https://example.org/job/1" and links==["https://example.org/jobs/more"]


@pytest.mark.parametrize("query",["Java backend","Python engineer","Frontend developer"])
def test_three_varied_searches_are_capped_deduplicated_and_tech_only(query,monkeypatch):
    import app.scout as scout
    source=JobSource(company="Fixture",url="https://example.org/careers")
    async def crawl(s,c):
        return ([{"title":title,"company":"Fixture","url":f"https://example.org/job/{i}","location":"Remote","description_snippet":query} for i,title in enumerate(["Java backend","Python engineer","Frontend developer","Finance accountant"])],[])
    monkeypatch.setattr(scout,"crawl_source",crawl)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
            return await discover_jobs({},limit=2,sources=[source],tracked_urls={"https://example.org/job/0"},client=client)
    result=asyncio.run(run())
    assert len(result["jobs"])==2
    assert all(j["url"]!="https://example.org/job/0" for j in result["jobs"])


def test_greenhouse_uses_json_api_and_publication_time_not_updated_time():
    source=JobSource(company="Fixture",url="https://job-boards.greenhouse.io/fixture")
    requests=[]
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200,json={"jobs":[{"id":1,"title":"Software engineer","absolute_url":"https://example.org/job/1","location":{"name":"Remote"},"content":"<p>Java APIs</p>","updated_at":"2026-10-09"}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await ats_jobs(source,client,known_ats(source))
    jobs=asyncio.run(run())
    assert requests==["https://boards-api.greenhouse.io/v1/boards/fixture/jobs?content=true"]
    assert jobs[0]["posted_at"] is None and jobs[0]["description"]=="Java APIs"


def test_lever_and_workday_api_contracts():
    def handler(request):
        url=str(request.url)
        if 'lever.co' in url:
            return httpx.Response(200,json=[{"text":"Backend engineer","hostedUrl":"https://jobs.lever.co/fixture/1","categories":{"location":"Remote"},"descriptionPlain":"Python APIs","createdAt":1791504000000}])
        if url.endswith('/jobs'):
            assert request.method=='POST' and json.loads(request.content)["limit"]==20
            return httpx.Response(200,json={"total":1,"jobPostings":[{"title":"Software engineer","externalPath":"/job/Test/R1","locationsText":"India","postedOn":"Posted 3 Days Ago"}]})
        return httpx.Response(200,json={"jobPostingInfo":{"jobDescription":"<p>Java backend</p>","startDate":"2026-10-06"}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            lever=await ats_jobs(JobSource(company="Fixture",url="https://jobs.lever.co/fixture"),client,"lever")
            workday=await ats_jobs(JobSource(company="Fixture",url="https://fixture.wd5.myworkdayjobs.com/en-US/Tech"),client,"workday")
            return lever,workday
    lever,workday=asyncio.run(run())
    assert lever[0]["posted_at"] and workday[0]["description"]=='Java backend'


def test_playwright_fallback_is_logged_and_used_only_after_empty_static(monkeypatch,caplog):
    import app.scout as scout
    source=JobSource(company="Fixture",url="https://example.org/careers",provider="static")
    calls=[]
    async def browser(s):
        calls.append(s.company)
        scout.logger.warning("Playwright fallback for %s",s.company)
        return [{"title":"Software engineer","company":"Fixture","url":"https://example.org/job/1","source":"playwright"}]
    monkeypatch.setattr(scout,"browser_jobs",browser)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,text='<div id="app"></div>'))) as client:
            return await scout.crawl_source(source,client)
    jobs,notes=asyncio.run(run())
    assert calls==["Fixture"] and jobs[0]["source"]=='playwright' and 'Playwright fallback' in caplog.text

"""Opt-in public ATS checks. No LLM calls or application submissions."""
import asyncio
import os
import httpx
import pytest

from app.scout import ats_jobs
from app.sources import JobSource

pytestmark=pytest.mark.skipif(os.getenv('RUN_LIVE_SOURCE_TESTS')!='1',reason='Opt-in public network acceptance checks')


@pytest.mark.parametrize('company,token',[('Canonical','canonical'),('Vercel','vercel'),('Cloudflare','cloudflare')])
def test_real_greenhouse_returns_real_tech_postings(company,token):
    async def run():
        async with httpx.AsyncClient() as client:
            return await ats_jobs(JobSource(company=company,url=f'https://job-boards.greenhouse.io/{token}'),client,'greenhouse')
    jobs=asyncio.run(run())
    assert jobs and all(j['source']=='ats' and j['url'].startswith('https://') for j in jobs)
    assert any(j['description'] and j['posted_at'] for j in jobs)


def test_real_workday_json_adapter():
    async def run():
        async with httpx.AsyncClient() as client:
            return await ats_jobs(JobSource(company='NVIDIA',url='https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite'),client,'workday')
    jobs=asyncio.run(run())
    assert jobs and any(j['description'] and j['source']=='ats' for j in jobs)


def test_real_lever_json_adapter():
    async def run():
        async with httpx.AsyncClient() as client:
            return await ats_jobs(JobSource(company='Spotify',url='https://jobs.lever.co/spotify'),client,'lever')
    jobs=asyncio.run(run())
    assert jobs and all(j['source']=='ats' for j in jobs)
    assert any(j['description'] and j['url'].startswith('https://jobs.lever.co/spotify/') for j in jobs)

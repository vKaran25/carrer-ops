"""Real Chromium JS rendering, with network routes replaced by explicit fixtures."""
import asyncio
import json
import pytest
from app.scout import browser_jobs
from app.sources import JobSource


def test_actual_browser_renders_javascript_created_job(monkeypatch,caplog):
    import playwright.async_api as playwright_api
    original=playwright_api.Page.goto
    async def validate(url): pass
    monkeypatch.setattr('app.scout.validate_public_url',validate)
    # The page is a public-looking URL routed to a local fixture, not fetched live.
    async def goto(page,url,**kwargs):
        await page.unroute('**/*')
        payload={'@type':'JobPosting','title':'Software engineer','description':'Fictional JS fixture','url':'https://example.org/js-role'}
        html='<html><body><div id="app"></div><script>setTimeout(()=>{const s=document.createElement("script");s.type="application/ld+json";s.textContent='+json.dumps(json.dumps(payload))+';document.body.appendChild(s);},50)</script></body></html>'
        await page.route('**/*',lambda route:route.fulfill(status=200,content_type='text/html',body=html))
        return await original(page,url,**kwargs)
    monkeypatch.setattr(playwright_api.Page,'goto',goto)
    try:
        jobs=asyncio.run(browser_jobs(JobSource(company='Fictional Fixture',url='https://example.org/careers')))
    except Exception as exc:
        if 'Executable doesn' in str(exc):pytest.skip('Install Chromium with python -m playwright install chromium')
        raise
    assert jobs[0]['title']=='Software engineer' and jobs[0]['source']=='playwright'
    assert 'Playwright fallback' in caplog.text

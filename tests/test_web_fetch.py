import asyncio
import gzip
import httpx
import pytest
from app.web_fetch import fetch, validate_public_url


def test_compressed_public_responses_are_decoded_once(monkeypatch):
    async def validate(url): pass
    monkeypatch.setattr('app.web_fetch.validate_public_url',validate)
    def handler(request):
        return httpx.Response(200,content=gzip.compress(b'{"jobs":[]}'),headers={'content-encoding':'gzip','content-type':'application/json'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch(client,'https://example.org/jobs')
    assert asyncio.run(run()).json()=={'jobs':[]}


@pytest.mark.parametrize('url',['http://localhost/test','http://127.0.0.1/test','http://10.0.0.1/test','file:///etc/passwd','https://example.org:8000/test'])
def test_private_urls_and_nonstandard_ports_are_rejected(url):
    with pytest.raises(ValueError):asyncio.run(validate_public_url(url))

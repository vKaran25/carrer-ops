"""Public-page fetching with bounded redirects and blocked local-network URLs."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx


async def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
        raise ValueError("Only public HTTP(S) URLs are supported")
    if parsed.port not in (None, 80, 443):
        raise ValueError("Only standard public web ports are supported")
    host = parsed.hostname
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("Local URLs are not allowed")
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Source host cannot be resolved") from exc
    if any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("Private-network URLs are not allowed")


async def fetch(client: httpx.AsyncClient, url: str, *, method="GET", json=None) -> httpx.Response:
    for _ in range(5):
        await validate_public_url(url)
        async with client.stream(method, url, json=json, follow_redirects=False, timeout=25) as response:
            if response.is_redirect:
                url = str(response.url.join(response.headers["location"]))
                method, json = "GET", None
                continue
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 12_000_000:
                    raise ValueError("Source response exceeds the size limit")
            headers = dict(response.headers)
            # aiter_bytes already decompresses the wire body; do not decode it twice.
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, headers=headers, content=bytes(body), request=response.request)
    raise ValueError("Source redirected too many times")

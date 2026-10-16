"""Drive a queued request deterministically in isolated API regression fixtures."""
import asyncio
import httpx
from fastapi import HTTPException
from sqlmodel import Session
from app.models import SearchRun
from app.search_queue import execute


def complete_search(client, engine, **kwargs):
    response = client.post('/api/search', **kwargs)
    if response.status_code != 202:
        return response
    run_id = response.json()['id']
    with Session(engine) as session:
        row = session.get(SearchRun, run_id)
        row.status, row.worker_id = 'running', 'fixture-worker'
        attempt = row.attempt
        session.add(row); session.commit()
    try:
        asyncio.run(execute(engine, run_id, 'fixture-worker', attempt))
    except Exception as exc:
        with Session(engine) as session:
            row = session.get(SearchRun, run_id)
            row.status = 'failed'; session.add(row); session.commit()
        status = exc.status_code if isinstance(exc, HTTPException) else 422 if isinstance(exc, (ValueError, LookupError)) else 503
        return httpx.Response(status, json={'detail':str(exc)}, request=response.request)
    with Session(engine) as session:
        turn_id = session.get(SearchRun, run_id).result['turn_id']
    turn = next(t for t in client.get('/api/chat').json() if t['id'] == turn_id)
    return httpx.Response(200, json={**turn['result'], 'turn_id':turn_id}, request=response.request)

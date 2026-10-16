"""Persistent search tickets and one globally leased worker; no automatic replay."""
import asyncio
from hashlib import blake2b
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlmodel import Session, select

from app.budgets import account_context, reserve
from app.chat import resume_digest
from app.config import get_settings
from app.db import get_profile
from app.models import SearchContext, SearchRun, User, WorkerHeartbeat, utcnow
from app.workspace import user_id

ACTIVE = ('queued', 'running', 'cancelling')
TERMINAL = ('succeeded', 'failed', 'cancelled', 'interrupted', 'needs_input')


def heartbeat(session: Session, worker: str):
    row = session.get(WorkerHeartbeat, 1) or WorkerHeartbeat(worker_id=worker)
    row.worker_id, row.updated_at = worker, utcnow()
    session.add(row)


def owned_run(session: Session, run_id: str, *, lock=False) -> SearchRun:
    statement = select(SearchRun).where(SearchRun.id == run_id, SearchRun.user_id == user_id(session))
    row = session.exec(statement.with_for_update() if lock else statement).first()
    if row is None:
        raise LookupError('Search not found in this workspace.')
    return row


def ticket(row: SearchRun) -> dict:
    return {'id': row.id, 'request_key': row.request_key, 'query': row.request.get('query', ''), 'status': row.status,
            'phase': row.phase, 'attempt': row.attempt, 'created_at': row.created_at,
            'updated_at': row.updated_at, 'error': row.error,
            'turn_id': (row.result or {}).get('turn_id')}


def enqueue(session: Session, request: dict, request_key: str) -> SearchRun:
    actor = user_id(session)
    # Serialize admission for an account, including concurrent duplicate requests.
    session.exec(select(User).where(User.id == actor).with_for_update()).one()
    prior = session.exec(select(SearchRun).where(SearchRun.user_id == actor,
                                               SearchRun.request_key == request_key)).first()
    payload = {k: request[k] for k in ('query', 'mode', 'limit')}
    if prior:
        if {k: prior.request[k] for k in payload} != payload:
            raise HTTPException(409, 'This request key belongs to a different search.')
        return prior
    if session.exec(select(SearchRun).where(SearchRun.user_id == actor, SearchRun.status.in_(ACTIVE))).first():
        raise HTTPException(409, 'A search is already queued or running. Wait for it or cancel it first.')
    profile = get_profile(session)
    if not profile or not profile.structured_facts.get('facts'):
        raise ValueError('Add a resume before finding jobs.')
    context = session.exec(select(SearchContext).where(SearchContext.user_id == actor)).first()
    if context is None:
        context = SearchContext(user_id=actor)
        session.add(context)
    payload['context_revision'] = context.revision if context else 0
    reserve('search', session=session, user_id=actor)
    row = SearchRun(id=uuid4().hex, user_id=actor, request_key=request_key, request=payload,
                    resume_digest=resume_digest(profile))
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def cancel(session: Session, run_id: str) -> SearchRun:
    row = owned_run(session, run_id, lock=True)
    if row.status in ACTIVE:
        row.cancel_requested = True
        row.status = 'cancelled' if row.status == 'queued' else 'cancelling'
        row.phase = row.status
        row.updated_at = utcnow()
        session.add(row)
        session.commit()
    return row


def retry(session: Session, run_id: str) -> SearchRun:
    actor = user_id(session)
    session.exec(select(User).where(User.id == actor).with_for_update()).one()
    row = owned_run(session, run_id, lock=True)
    if row.status not in ('failed', 'interrupted'):
        raise HTTPException(409, 'Only a failed or interrupted search can be retried.')
    if session.exec(select(SearchRun).where(SearchRun.user_id == actor, SearchRun.status.in_(ACTIVE))).first():
        raise HTTPException(409, 'Finish or cancel the current search first.')
    if row.resume_digest != resume_digest(get_profile(session)):
        raise HTTPException(409, 'Your resume changed. Start a new search with the current resume.')
    reserve('search', session=session, user_id=actor)
    context = session.exec(select(SearchContext).where(SearchContext.user_id == actor)).first()
    row.request = {**row.request, 'context_revision': context.revision if context else 0}
    row.status, row.phase, row.error = 'queued', 'queued', None
    row.attempt += 1
    row.cancel_requested, row.worker_id, row.heartbeat_at = False, None, None
    row.updated_at = utcnow()
    session.add(row)
    session.commit()
    return row


class SearchInterrupted(Exception):
    pass


def checkpoint(session: Session, phase: str):
    marker = session.info.get('search_run')
    if marker is None:
        return
    run_id, worker, attempt = marker
    with Session(session.get_bind()) as active:
        row = active.get(SearchRun, run_id)
        if not row or row.worker_id != worker or row.attempt != attempt or row.status != 'running' or row.cancel_requested:
            raise SearchInterrupted()
        row.phase, row.heartbeat_at, row.updated_at = phase, utcnow(), utcnow()
        active.add(row)
        active.commit()


def finish_lock(session: Session):
    """Lock the ticket before persisting any result; cancellation cannot race commit."""
    marker = session.info.get('search_run')
    if marker is None:
        return
    from app.auth import recheck_access
    recheck_access(session)
    session.exec(select(User).where(User.id == user_id(session)).with_for_update()).one()
    run_id, worker, attempt = marker
    row = session.exec(select(SearchRun).where(SearchRun.id == run_id).with_for_update()
                       .execution_options(populate_existing=True)).first()
    if not row or row.worker_id != worker or row.attempt != attempt or row.status != 'running' or row.cancel_requested:
        raise SearchInterrupted()
    if row.resume_digest != resume_digest(get_profile(session)):
        raise ValueError('Your resume changed during this search. Start a new search.')


async def execute(engine, run_id: str, worker: str, attempt: int):
    from app.orchestrator import run
    with Session(engine) as session:
        row = session.get(SearchRun, run_id)
        actor, payload, digest = row.user_id, row.request, row.resume_digest
        session.info.update(user_id=actor, defer_commit=True, search_run=(run_id, worker, attempt))
        if get_settings().auth_mode == 'supabase':
            from app.models import AuthIdentity
            identity = session.exec(select(AuthIdentity).where(AuthIdentity.user_id == actor)).first()
            user = session.get(User, actor)
            if not identity or not user:
                raise SearchInterrupted()
            session.info.update(auth_subject=identity.subject, email=user.email)
        if digest != resume_digest(get_profile(session)):
            raise ValueError('Your resume changed while queued. Start a new search.')
        context = session.exec(select(SearchContext).where(SearchContext.user_id == actor)).first()
        if (context.revision if context else 0) != payload.get('context_revision', 0):
            raise ValueError('Search context changed while queued. Start a new search using current preferences.')
        with account_context(actor, engine):
            result = await run({'action': 'search', **{k: payload[k] for k in ('query', 'mode', 'limit')}}, session)
        # ranking has locked the ticket and flushed chat/context/jobs without committing.
        row = session.get(SearchRun, run_id)
        row.status, row.phase, row.result = 'succeeded', 'complete', {'turn_id': result['turn_id']}
        row.updated_at, row.heartbeat_at = utcnow(), utcnow()
        session.add(row)
        session.commit()


async def monitor(engine, row: SearchRun, worker: str):
    task = asyncio.create_task(execute(engine, row.id, worker, row.attempt))
    try:
        async with asyncio.timeout(get_settings().search_timeout_seconds):
            while not task.done():
                await asyncio.sleep(1)
                with Session(engine) as session:
                    current = session.get(SearchRun, row.id)
                    if not current or current.cancel_requested or current.worker_id != worker or current.attempt != row.attempt:
                        task.cancel()
                        break
                    if current.status == 'running':
                        current.heartbeat_at = utcnow()
                        heartbeat(session, worker)
                        session.add(current)
                        session.commit()
            await task
    finally:
        if not task.done():
            task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def recover(engine):
    with Session(engine) as session:
        for row in session.exec(select(SearchRun).where(SearchRun.status.in_(('running', 'cancelling')))).all():
            row.status = 'cancelled' if row.cancel_requested else 'interrupted'
            row.phase = row.status
            row.error = 'The server stopped before completion. Retry explicitly to search again.' if row.status == 'interrupted' else None
            row.worker_id, row.updated_at = None, utcnow()
            session.add(row)
        session.commit()


async def worker_loop(engine):
    worker = uuid4().hex
    while True:
        # Session pooler pins this connection while the advisory lock is held.
        lease = None
        lease_key = None
        try:
            if engine.dialect.name == 'postgresql':
                lease = engine.connect()
                namespace = lease.execute(text('SELECT current_schema()')).scalar()
                lease_key = int.from_bytes(blake2b(('career-ops-worker:' + namespace).encode(), digest_size=8).digest(), signed=True)
                acquired = lease.execute(text('SELECT pg_try_advisory_lock(:key)'), {'key': lease_key}).scalar()
                lease.commit()
                if not acquired:
                    lease.close(); lease = None
                    await asyncio.sleep(3)
                    continue
            recover(engine)
            while True:
                with Session(engine) as session:
                    heartbeat(session, worker)
                    row = session.exec(select(SearchRun).where(SearchRun.status == 'queued')
                                       .order_by(SearchRun.created_at).with_for_update(skip_locked=True)).first()
                    if row:
                        row.status, row.phase, row.worker_id = 'running', 'starting', worker
                        row.heartbeat_at, row.updated_at = utcnow(), utcnow()
                        session.add(row); session.commit(); session.refresh(row)
                        session.expunge(row)
                    else:
                        session.commit()
                if row is None:
                    from app.accounts import process_deletions
                    await process_deletions(engine)
                    await asyncio.sleep(1)
                    if lease is not None:
                        lease.execute(text('SELECT 1')); lease.commit()
                    continue
                failure = None
                try:
                    await monitor(engine, row, worker)
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():
                        raise
                    failure = ('cancelled', None)
                except SearchInterrupted:
                    failure = ('cancelled', None)
                except TimeoutError:
                    failure = ('failed', 'This search exceeded the execution time limit. Retry explicitly.')
                except HTTPException as exc:
                    failure = ('failed', exc.detail if isinstance(exc.detail, str) else 'Service temporarily unavailable.')
                except (ValueError, LookupError) as exc:
                    failure = ('needs_input', str(exc))
                except Exception:
                    failure = ('failed', 'Search could not complete. Your previous search context is preserved. Retry explicitly.')
                if failure:
                    with Session(engine) as session:
                        current = session.get(SearchRun, row.id)
                        if current and current.worker_id == worker and current.attempt == row.attempt and current.status in ('running', 'cancelling'):
                            current.status, current.error = failure
                            current.phase, current.updated_at = current.status, utcnow()
                            session.add(current); session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Never include provider payloads, keys, queries or resumes in worker logs.
            import logging
            logging.getLogger(__name__).error('Search worker paused after a database/service failure.')
            await asyncio.sleep(3)
        finally:
            if lease is not None:
                try:
                    lease.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': lease_key}); lease.commit()
                finally:
                    lease.close()


@asynccontextmanager
async def worker_lifespan(engine):
    task = asyncio.create_task(worker_loop(engine))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

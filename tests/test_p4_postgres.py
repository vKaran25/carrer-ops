"""Opt-in real PostgreSQL checks in a disposable private schema; no live accounts."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import HTTPException
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlmodel import Session, select

from app.config import get_settings
from app.db import make_engine
from app.models import (Application, AuthIdentity, ChatTurn, DailyUsage, DeletionRequest,
    DiscoveryCache, Invitation, JobPosting, ResumeProfile, SearchContext, SearchRun, User, UserAction, utcnow)

pytestmark = pytest.mark.skipif(os.getenv('RUN_POSTGRES_TESTS') != '1', reason='Opt-in isolated PostgreSQL schema')


@pytest.fixture(scope='module')
def pg():
    settings=get_settings()
    assert settings.supabase_database_url, 'Configure staged Supabase pooler URI'
    patch=pytest.MonkeyPatch()
    schema='career_ops_test_'+uuid4().hex[:12]
    patch.setattr(settings,'database_schema',schema)
    patch.setattr(settings,'database_url',settings.supabase_database_url)
    patch.setattr(settings,'auth_mode','supabase')
    config=Config('alembic.ini')
    command.upgrade(config,'head')
    engine=make_engine(settings.supabase_database_url)
    try:
        yield engine
    finally:
        # Exact schema created above; never a user-configured or production schema.
        assert schema.startswith('career_ops_test_') and len(schema)==28
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose();patch.undo()


def account(engine):
    from app.auth import bind_workspace, Principal
    subject,email=str(uuid4()),uuid4().hex+'@example.invalid'
    with Session(engine) as session:
        session.add(Invitation(email=email));session.commit()
        bind_workspace(session,Principal(subject,email))
        actor=session.info['user_id']
        session.add(ResumeProfile(user_id=actor,filename='fictional.docx',raw_resume_text='Python APIs',
            structured_facts={'facts':[{'category':'skill','text':'Python APIs','evidence':'Python APIs'}]}))
        session.commit()
    return actor,subject,email


def owned(engine, identity):
    session=Session(engine)
    actor,subject,email=identity
    session.info.update(user_id=actor,auth_subject=subject,email=email)
    return session


def test_private_schema_rls_and_version(pg):
    with pg.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar()=='0001_core'
        rows=connection.execute(text("SELECT c.relname,c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND c.relkind='r' AND c.relname!='alembic_version'" )).all()
        assert len(rows)>=15 and all(row[1] for row in rows)
        assert connection.execute(text("SELECT has_schema_privilege('anon',current_schema(),'USAGE')")).scalar() is False
        assert connection.execute(text("SELECT has_schema_privilege('authenticated',current_schema(),'USAGE')")).scalar() is False


def test_verified_mapping_and_revocation(pg):
    from app.auth import Principal, bind_workspace, recheck_access
    identity=account(pg)
    with owned(pg,identity) as session:
        bind_workspace(session,Principal(identity[1],identity[2]));assert session.info['user_id']==identity[0]
        invite=session.get(Invitation,identity[2]);invite.enabled=False;session.add(invite);session.commit()
        with pytest.raises(HTTPException) as exc: recheck_access(session)
        assert exc.value.status_code==403
    with Session(pg) as session:
        with pytest.raises(HTTPException): bind_workspace(session,Principal(str(uuid4()),'uninvited@example.invalid'))


def test_direct_cross_account_access_and_deferred_api(pg,monkeypatch):
    from fastapi.testclient import TestClient
    from app.db import get_session
    import app.main as main
    a,b=account(pg),account(pg)
    from app.tracker import save_jobs
    with owned(pg,a) as session:
        job=save_jobs(session,[{'title':'Fictional engineer','company':'Fixture','url':'https://example.invalid/'+uuid4().hex}])[0];job_id=job.id
    def sessions():
        with owned(pg,b) as session: yield session
    main.app.dependency_overrides[get_session]=sessions
    try:
        with TestClient(main.app) as client:
            for path in (f'/api/jobs/{job_id}',): assert client.get(path).status_code==404
            assert client.post(f'/api/jobs/{job_id}/mark-applied',json={'explicit_action':True}).status_code==404
            for action in ('tailor','curate','research'): assert client.post(f'/api/jobs/{job_id}/{action}').status_code==404
            assert client.get('/api/jobs').json()==[]
            assert client.get('/api/chat').json()==[]
            assert client.get('/api/resume').json()['filename']=='fictional.docx'
    finally: main.app.dependency_overrides.clear()


def test_applied_audit_and_later_stage_idempotence(pg):
    from app.tracker import save_jobs, approval_gate, update_status
    a,b=account(pg),account(pg)
    with owned(pg,a) as session:
        job=save_jobs(session,[{'title':'Fictional engineer','company':'Fixture','url':'https://example.invalid/'+uuid4().hex}])[0]
        application=session.exec(select(Application).where(Application.job_id==job.id)).one()
        application.status='applied';application.applied_at=utcnow();session.add(application)
        with pytest.raises(DBAPIError, match='same-transaction'):session.commit()
        session.rollback()
        application=session.exec(select(Application).where(Application.job_id==job.id)).one()
        session.add(UserAction(user_id=b[0],application_id=application.id,action='mark_applied',previous_status='interested',new_status='applied'))
        with pytest.raises(DBAPIError, match='actor must own'):session.commit()
        session.rollback()
        with pytest.raises(ValueError):approval_gate(session,job.id,explicit_action=False)
        result=approval_gate(session,job.id,explicit_action=True);stamp=result.applied_at
        update_status(session,job.id,'interviewing')
        result=approval_gate(session,job.id,explicit_action=True)
        assert result.status=='interviewing' and result.applied_at==stamp
        assert len(session.exec(select(UserAction).where(UserAction.application_id==result.id,UserAction.action=='mark_applied')).all())==1


def test_queue_idempotency_admission_cancel_retry_and_recovery(pg):
    from app.search_queue import enqueue,cancel,retry,recover,owned_run
    a,b=account(pg),account(pg)
    request={'query':'Python jobs','mode':'resume','limit':3}
    with owned(pg,a) as session:
        row=enqueue(session,request,'same');run_id=row.id
        assert enqueue(session,request,'same').id==run_id
        with pytest.raises(HTTPException):enqueue(session,request,'other')
        session.rollback()
        assert cancel(session,run_id).status=='cancelled'
        row=enqueue(session,request,'new');row.status='running';row.worker_id='dead';session.add(row);session.commit()
        pending=row.id
    with owned(pg,b) as session:
        with pytest.raises(LookupError):owned_run(session,pending)
    recover(pg)
    with owned(pg,a) as session:
        assert owned_run(session,pending).status=='interrupted'
        assert retry(session,pending).attempt==2
        cancel(session,pending)


def test_15_account_concurrent_admission_and_duplicate_protection(pg):
    from app.search_queue import enqueue,cancel
    accounts=[account(pg) for _ in range(15)]
    request={'query':'fixture','mode':'resume','limit':1}
    # Isolate quota day from earlier tests; no provider requests are made.
    with Session(pg) as session:session.exec(text('DELETE FROM dailyusage'));session.commit()
    def submit(identity):
        with owned(pg,identity) as session:return enqueue(session,request,'concurrent').id
    with ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(submit,accounts))
    assert len(set(results))==15
    with ThreadPoolExecutor(max_workers=5) as pool: duplicates=list(pool.map(submit,accounts))
    assert duplicates==results
    for identity,run_id in zip(accounts,results):
        with owned(pg,identity) as session:cancel(session,run_id)


def test_atomic_operational_budget_and_cache_privacy(pg,monkeypatch):
    from app.budgets import account_context,reserve
    from app.discovery_cache import write,read
    identity=account(pg)
    monkeypatch.setattr(get_settings(),'model_daily_global_limit',3)
    def attempt(_):
        try:
            with account_context(identity[0],pg):reserve('model')
            return True
        except HTTPException:return False
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(attempt,range(15)))
    assert sum(results)==3
    key=uuid4().hex*2
    assert read(key) is None
    with account_context(identity[0],pg):
        write(key,[{'url':'https://example.invalid/job','title':'Public role','content':'Public snippet','private_resume':'must not persist'}])
        assert set(read(key)[0])=={'url','title','content'}
        with Session(pg) as session:
            cache=session.get(DiscoveryCache,key);cache.expires_at=utcnow()-timedelta(seconds=1);session.add(cache);session.commit()
        assert read(key) is None


def test_active_deletion_retains_only_retry_marker(pg,monkeypatch):
    import app.accounts as accounts
    identity=account(pg)
    async def unavailable(subject):return False
    monkeypatch.setattr(accounts,'delete_auth_identity',unavailable)
    with owned(pg,identity) as session:
        result=asyncio.run(accounts.delete_account(session))
        assert result['deleted'] and result['auth_cleanup']=='pending'
    with Session(pg) as session:
        assert session.get(User,identity[0]) is None
        assert not session.exec(select(ResumeProfile).where(ResumeProfile.user_id==identity[0])).all()
        assert not session.get(Invitation,identity[2]).enabled
        assert session.get(DeletionRequest,identity[1])
    async def recovered(subject):return True
    monkeypatch.setattr(accounts,'delete_auth_identity',recovered)
    asyncio.run(accounts.process_deletions(pg))
    with Session(pg) as session:assert session.get(DeletionRequest,identity[1]) is None


def test_worker_search_commits_chat_context_ticket_atomically(pg,monkeypatch):
    import app.orchestrator as graph
    from app.query_parser import QuerySpec
    from app.search_queue import worker_loop,enqueue
    identity=account(pg)
    with Session(pg) as session:session.exec(text('DELETE FROM dailyusage'));session.commit()
    monkeypatch.setattr(get_settings(),'tavily_api_key','')
    async def discover(*args,**kwargs):
        return {'jobs':[{'title':'Python engineer','company':'Fixture','location':'Remote','url':'https://example.invalid/'+uuid4().hex,'description':'Python APIs'}],'warnings':[]}
    monkeypatch.setattr(graph,'discover_jobs',discover)
    async def cycle():
        with owned(pg,identity) as session:run_id=enqueue(session,{'query':'','mode':'resume','limit':3},'worker').id
        task=asyncio.create_task(worker_loop(pg))
        try:
            for _ in range(100):
                await asyncio.sleep(.2)
                with Session(pg) as session:
                    row=session.get(SearchRun,run_id)
                    if row.status in ('succeeded','failed','needs_input'):break
            assert row.status=='succeeded',row.error
            with Session(pg) as session:
                assert session.get(ChatTurn,row.result['turn_id']).user_id==identity[0]
                assert session.exec(select(SearchContext).where(SearchContext.user_id==identity[0])).one().last_turn_id==row.result['turn_id']
                assert not session.exec(select(Application).join(JobPosting).where(JobPosting.user_id==identity[0])).all()
        finally:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
    asyncio.run(cycle())


@pytest.mark.parametrize('mutation',['cancel','resume'])
def test_inflight_cancellation_or_resume_change_cannot_persist_results(pg,monkeypatch,mutation):
    import app.orchestrator as graph
    from app.search_queue import worker_loop,enqueue,cancel
    identity=account(pg)
    with Session(pg) as session:session.exec(text('DELETE FROM dailyusage'));session.commit()
    monkeypatch.setattr(get_settings(),'tavily_api_key','')
    async def cycle():
        entered,release=asyncio.Event(),asyncio.Event()
        async def discover(*args,**kwargs):
            entered.set();await release.wait()
            return {'jobs':[{'title':'Python engineer','company':'Fixture','location':'Remote','url':'https://example.invalid/'+uuid4().hex,'description':'Python APIs'}],'warnings':[]}
        monkeypatch.setattr(graph,'discover_jobs',discover)
        with owned(pg,identity) as session:run_id=enqueue(session,{'query':'','mode':'resume','limit':3},mutation).id
        task=asyncio.create_task(worker_loop(pg))
        try:
            await asyncio.wait_for(entered.wait(),20)
            with owned(pg,identity) as session:
                if mutation=='cancel':cancel(session,run_id)
                else:
                    profile=session.exec(select(ResumeProfile).where(ResumeProfile.user_id==identity[0])).one()
                    profile.raw_resume_text='Changed fictional source';session.add(profile);session.commit()
            release.set()
            for _ in range(100):
                await asyncio.sleep(.2)
                with Session(pg) as session:
                    row=session.get(SearchRun,run_id)
                    if row.status in ('cancelled','needs_input','failed','succeeded'):break
            assert row.status==('cancelled' if mutation=='cancel' else 'needs_input'),row.error
            with Session(pg) as session:
                assert not session.exec(select(ChatTurn).where(ChatTurn.user_id==identity[0])).all()
                assert not session.exec(select(JobPosting).where(JobPosting.user_id==identity[0])).all()
                assert session.exec(select(SearchContext).where(SearchContext.user_id==identity[0])).one().intent is None
        finally:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
    asyncio.run(cycle())


def test_two_workers_do_not_recover_or_execute_each_others_live_ticket(pg,monkeypatch):
    import app.orchestrator as graph
    from app.search_queue import worker_loop,enqueue
    identity=account(pg)
    with Session(pg) as session:session.exec(text('DELETE FROM dailyusage'));session.commit()
    monkeypatch.setattr(get_settings(),'tavily_api_key','')
    async def cycle():
        entered,release=asyncio.Event(),asyncio.Event();calls=[]
        async def discover(*args,**kwargs):
            calls.append('discovery');entered.set();await release.wait()
            return {'jobs':[],'warnings':[],'stats':{'sources_searched':1,'retrieved':0}}
        monkeypatch.setattr(graph,'discover_jobs',discover)
        with owned(pg,identity) as session:run_id=enqueue(session,{'query':'','mode':'resume','limit':3},'lease').id
        first=asyncio.create_task(worker_loop(pg));second=None
        try:
            await asyncio.wait_for(entered.wait(),20)
            second=asyncio.create_task(worker_loop(pg));await asyncio.sleep(2)
            with Session(pg) as session:assert session.get(SearchRun,run_id).status=='running'
            assert len(calls)==1
            release.set()
            for _ in range(100):
                await asyncio.sleep(.2)
                with Session(pg) as session:
                    row=session.get(SearchRun,run_id)
                    if row.status in ('succeeded','failed'):break
            assert row.status=='succeeded',row.error
            assert len(calls)==1
        finally:
            for task in (first,second):
                if task:task.cancel()
            for task in (first,second):
                if task:
                    try:await task
                    except asyncio.CancelledError:pass
    asyncio.run(cycle())

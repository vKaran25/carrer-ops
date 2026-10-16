from app.workspace import user_id as workspace_user_id
from app.features import unavailable, core_features
from contextlib import asynccontextmanager
from pathlib import Path
import re
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlmodel import Session, select

from app.config import get_settings
from app.chat import history, interest
from app.chat import resume_digest
from app.search_context import view as context_view, reset as reset_context, save_preferences
from app.curator import layout_advisory
from app.db import get_profile, get_session, init_db, engine
from app.llm import LLMError
from app.memory import consolidate
from app.models import Application, JobPosting, MemoryFact
from app.orchestrator import run
from app.personalization import recalibrate, set_consent
from app.query_parser import QueryParserError
from app.query_parser import QuerySpec, parse_query
from app.discovery import linkedin_url, search_terms, linkedin_search_url
from app.resumes import extract_profile, read_upload, save_profile
from app.sources import JobSource, load_sources, save_sources
from app.tracker import STATUSES, get_application, remove_interest

settings = get_settings()

@asynccontextmanager
async def lifespan(app):
    settings.validate_runtime()
    if get_session in app.dependency_overrides:
        # An isolated dependency override must never start a worker on the real DB.
        yield
        return
    init_db()
    from app.search_queue import worker_lifespan
    async with worker_lifespan(engine):
        yield

app = FastAPI(title="Career Ops Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # Never expose the key itself, only whether it is configured.
    return {"status": "ok", "openrouter_configured": settings.openrouter_configured}


@app.get('/ready')
def readiness():
    from sqlalchemy import text
    database = False
    try:
        with engine.connect() as connection:
            database = connection.execute(text('SELECT 1')).scalar() == 1
    except Exception:
        pass
    checks = {'database': database, 'geography': Path(settings.geonames_db).is_file(),
              'model': settings.openrouter_configured and settings.free_model_selected,
              'web_discovery': bool(settings.tavily_api_key),
              'authentication': settings.auth_mode == 'supabase' or settings.environment == 'development',
              'auth_deletion': bool(settings.supabase_secret_key) or settings.auth_mode == 'local'}
    try:
        from datetime import timezone
        from app.models import WorkerHeartbeat, utcnow
        with Session(engine) as session:
            beat = session.get(WorkerHeartbeat, 1)
            when = beat.updated_at.replace(tzinfo=timezone.utc) if beat and beat.updated_at.tzinfo is None else beat.updated_at if beat else None
            checks['search_worker'] = bool(when and (utcnow()-when).total_seconds() < 60)
    except Exception:
        checks['search_worker'] = False
    return JSONResponse({'status': 'ready' if all(checks.values()) else 'not_ready', 'checks': checks},
                        status_code=200 if all(checks.values()) else 503)


@app.middleware('http')
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.exception_handler(ValueError)
async def invalid_request(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(LookupError)
async def missing_record(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(LLMError)
@app.exception_handler(QueryParserError)
async def model_failure(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc), "action": "Configure a free tool-calling model in .env. Provider failures are reported explicitly."})

@app.get("/api/bootstrap")
def bootstrap(session: Session = Depends(get_session)):
    applications = session.exec(select(Application).join(JobPosting).where(JobPosting.user_id == workspace_user_id(session))).all()
    profile = get_profile(session)
    return {"model_configured": settings.openrouter_configured and settings.free_model_selected,
            "features": core_features(), "free_models_only": True,
            "auth_mode": settings.auth_mode, "account_email": session.info.get("email"),
            'account_subject': session.info.get('auth_subject'),
            "web_search_configured": bool(get_settings().tavily_api_key),
            "resume": {"filename": profile.filename, "fact_count": len(profile.structured_facts.get("facts", []))} if profile else None,
            "counts": {s: sum(a.status == s for a in applications) for s in STATUSES},
            "source_count": sum(s.enabled for s in load_sources()), "pdf_compiler_available": bool(shutil.which("tectonic"))}

class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(default="", max_length=2000)
    mode: str = "resume"
    request_key: str | None = Field(default=None, min_length=16, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    limit: int = Field(default=10, ge=1, le=50)


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirm: StrictBool


@app.delete('/api/account')
async def remove_account(request: DeleteAccountRequest, session: Session = Depends(get_session)):
    if request.confirm is not True:
        raise ValueError('Confirm account deletion explicitly.')
    from app.accounts import delete_account
    return await delete_account(session)

@app.post("/api/search", status_code=202)
async def search(request: SearchRequest, session: Session = Depends(get_session)):
    if request.mode not in ("natural", "keyword", "resume"):
        raise ValueError("Choose resume, natural-language or keyword search")
    if request.mode != "resume" and not request.query.strip():
        raise ValueError("Choose natural-language or keyword search and enter a query")
    from uuid import uuid4
    from app.search_queue import enqueue, ticket
    return ticket(enqueue(session, request.model_dump(), request.request_key or uuid4().hex))


@app.get('/api/search/context')
def search_context(session: Session = Depends(get_session)):
    return context_view(session, workspace_user_id(session), resume_digest(get_profile(session)))


@app.get('/api/search/runs')
def search_runs(session: Session = Depends(get_session)):
    from app.models import SearchRun
    from app.search_queue import ticket
    rows = session.exec(select(SearchRun).where(SearchRun.user_id == workspace_user_id(session))
                        .order_by(SearchRun.created_at.desc()).limit(10)).all()
    return [ticket(row) for row in rows]


@app.get('/api/search/runs/{run_id}')
def search_run(run_id: str, session: Session = Depends(get_session)):
    from app.search_queue import owned_run, ticket
    return ticket(owned_run(session, run_id))


@app.post('/api/search/runs/{run_id}/cancel')
def cancel_search(run_id: str, session: Session = Depends(get_session)):
    from app.search_queue import cancel, ticket
    return ticket(cancel(session, run_id))


@app.post('/api/search/runs/{run_id}/retry', status_code=202)
def retry_search(run_id: str, session: Session = Depends(get_session)):
    from app.search_queue import retry, ticket
    return ticket(retry(session, run_id))


@app.get('/api/auth/config')
def auth_configuration():
    return {'enabled': settings.auth_mode == 'supabase',
            'url': settings.supabase_url if settings.auth_mode == 'supabase' else '',
            'publishable_key': settings.supabase_publishable_key if settings.auth_mode == 'supabase' else ''}


@app.delete('/api/search/context')
def new_search(session: Session = Depends(get_session)):
    reset_context(session, workspace_user_id(session))
    return context_view(session, workspace_user_id(session), resume_digest(get_profile(session)))


class PreferencesRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=2000)


@app.put('/api/search/preferences')
async def update_search_preferences(request: PreferencesRequest, session: Session = Depends(get_session)):
    spec = await parse_query(request.query)
    from app.auth import recheck_access
    recheck_access(session)
    save_preferences(session, workspace_user_id(session), request.query, spec)
    return context_view(session, workspace_user_id(session), resume_digest(get_profile(session)))


@app.delete('/api/search/preferences')
def remove_search_preferences(session: Session = Depends(get_session)):
    save_preferences(session, workspace_user_id(session), '', None)
    return context_view(session, workspace_user_id(session), resume_digest(get_profile(session)))

@app.get("/api/jobs")
def jobs(session: Session = Depends(get_session)):
    rows = session.exec(select(JobPosting, Application).join(Application).where(
        JobPosting.user_id == workspace_user_id(session), Application.status.in_(STATUSES)
    ).order_by(JobPosting.found_at.desc())).all()
    return [{**j.model_dump(), "application": a.model_dump(), "status": a.status,
             "fit_score": a.fit_score, "explanation": a.explanation} for j, a in rows]


@app.get("/api/chat")
def chat_history(before_id: int | None = Query(default=None, ge=1), limit: int = Query(default=25, ge=1, le=50),
                 session: Session = Depends(get_session)):
    return history(session, before_id=before_id, limit=limit)


@app.post('/api/linkedin-search', dependencies=[Depends(unavailable)])
async def linkedin_search(request: SearchRequest, session: Session = Depends(get_session)):
    profile = get_profile(session)
    if not profile:
        raise ValueError('Add a resume before preparing a LinkedIn search')
    spec = await parse_query(request.query) if request.query.strip() else QuerySpec(hard_filters={}, soft_preferences=[])
    terms = await search_terms(spec.model_dump(), profile.structured_facts)
    return {'url': linkedin_search_url(terms, spec.model_dump())}


class ImportJobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str = Field(max_length=2000)
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=120)
    location: str = Field(default='', max_length=200)
    description: str = Field(min_length=40, max_length=50000)


@app.post('/api/chat/import-job', dependencies=[Depends(unavailable)])
async def import_job(request: ImportJobRequest, session: Session = Depends(get_session)):
    import asyncio
    from app.chat import record_search
    from app.scoring import rank_jobs
    from app.tracker import save_discovered_jobs
    profile = get_profile(session)
    if not profile:
        raise ValueError('Add a resume before importing a job')
    url = linkedin_url(request.url)
    if not request.title.strip() or not request.company.strip() or len(request.description.strip()) < 40:
        raise ValueError('Enter a title, company and the full job description (at least 40 characters)')
    job = {**request.model_dump(), 'url': url, 'title': request.title.strip(), 'company': request.company.strip(),
           'location': request.location.strip() or 'Not specified', 'source': 'user_import',
           'description_snippet': request.description[:450],
           'metadata': {'evidence': 'User-pasted LinkedIn job details; availability and publication date are unverified'}}
    spec = QuerySpec(hard_filters={}, soft_preferences=[])
    ranked = await asyncio.to_thread(rank_jobs, spec, [job], profile.structured_facts)
    stored = save_discovered_jobs(session, ranked['jobs'])[0]
    application = session.exec(select(Application).where(Application.job_id == stored.id)).first()
    ranked['jobs'][0].update(id=stored.id, status=application.status if application else 'discovered')
    ranked.update(query_spec=spec.model_dump(), warnings=['Imported from details you pasted. Check the original listing to confirm it is still open.'], mode='import',
                  external_links=[], linkedin_search_url='', web_queries=[], trace=['user_import', 'ranking'])
    turn = record_search(session, {'query': 'Import LinkedIn job: ' + request.title.strip(), 'mode': 'import'}, ranked, profile)
    return {**ranked, 'turn_id': turn.id}


class InterestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_id: int = Field(ge=1)


@app.post("/api/jobs/{job_id}/interest")
def interested_job(job_id: int, request: InterestRequest, session: Session = Depends(get_session)):
    return interest(session, job_id, request.turn_id).model_dump()


@app.delete("/api/jobs/{job_id}/interest")
def remove_interested_job(job_id: int, session: Session = Depends(get_session)):
    return {"removed": remove_interest(session, job_id).status == "dismissed"}

@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int, session: Session = Depends(get_session)):
    a = get_application(session, job_id)
    return {**session.get(JobPosting, job_id).model_dump(), "application": a.model_dump(), "status": a.status,
            "fit_score": a.fit_score, "explanation": a.explanation}

@app.post("/api/jobs/{job_id}/tailor", dependencies=[Depends(unavailable)])
async def tailor_job(job_id: int, session: Session = Depends(get_session)):
    return await run({"action": "tailor", "job_id": job_id}, session)

@app.post("/api/jobs/{job_id}/curate", dependencies=[Depends(unavailable)])
async def curate_job(job_id: int, session: Session = Depends(get_session)):
    return await run({"action": "curate", "job_id": job_id}, session)

@app.post("/api/jobs/{job_id}/research", dependencies=[Depends(unavailable)])
async def research_job(job_id: int, session: Session = Depends(get_session)):
    return await run({"action": "research", "job_id": job_id}, session)

class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explicit_action: StrictBool

@app.post("/api/jobs/{job_id}/mark-applied")
async def mark_applied(job_id: int, request: ApprovalRequest, session: Session = Depends(get_session)):
    return await run({"action": "approve", "job_id": job_id, "explicit_action": request.explicit_action}, session)

class StatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    outcome: str | None = None

@app.patch("/api/jobs/{job_id}/status")
async def status_job(job_id: int, request: StatusRequest, session: Session = Depends(get_session)):
    return await run({"action": "status", "job_id": job_id, **request.model_dump()}, session)

@app.delete("/api/jobs/{job_id}/draft", dependencies=[Depends(unavailable)])
def discard_draft(job_id: int, session: Session = Depends(get_session)):
    a = get_application(session, job_id)
    a.draft = a.critique = a.tailored_resume = a.tailored_cover_letter = None
    if a.status == "tailored":
        a.status = "interested"
    session.add(a)
    session.commit()
    return {"discarded": True}

@app.get("/api/resume")
def resume(session: Session = Depends(get_session)):
    profile = get_profile(session)
    return {**profile.model_dump(), "layout_advisory": layout_advisory(profile.latex_source)} if profile else None

def invalidate_drafts(session):
    for a in session.exec(select(Application).join(JobPosting).where(JobPosting.user_id == workspace_user_id(session))).all():
        a.fit_score = None
        a.scoring_signals = {}
        a.explanation = "Resume changed; the previous content-match score has been cleared. New searches use your current facts."
        if a.draft:
            a.critique = {"passed": False, "reason": "Resume changed. Create a fresh draft against current facts", "checks": []}
        a.curated_resume = None
        session.add(a)
    session.commit()

@app.post("/api/resume")
async def upload_resume(file: UploadFile = File(...), session: Session = Depends(get_session)):
    if Path(file.filename or '').suffix.lower() != '.docx':
        raise HTTPException(422, 'Upload a .docx file. Only DOCX resumes are supported for now.')
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Resume exceeds the 5 MB upload limit")
    try:
        text, latex = read_upload(file.filename, content)
    except ValueError as exc:
        raise HTTPException(422, 'Upload a valid .docx file with readable resume text.') from exc
    facts = await extract_profile(text)
    from app.auth import recheck_access
    recheck_access(session)
    profile = save_profile(session, filename=file.filename or "resume.txt", text=text, latex=latex, facts=facts)
    invalidate_drafts(session)
    consolidate(session, workspace_user_id(session))
    return profile.model_dump()

@app.delete("/api/resume")
def remove_resume(session: Session = Depends(get_session)):
    profile = get_profile(session)
    if profile:
        session.delete(profile)
        session.commit()
    invalidate_drafts(session)
    consolidate(session, workspace_user_id(session))
    return {"removed": True}

@app.get("/api/memory")
def memory(session: Session = Depends(get_session)):
    return [f.model_dump() for f in session.exec(select(MemoryFact).where(MemoryFact.user_id == workspace_user_id(session))).all()]

@app.get("/api/personalization", dependencies=[Depends(unavailable)])
def personalization(session: Session = Depends(get_session)):
    return recalibrate(session)

@app.post("/api/personalization/recalibrate", dependencies=[Depends(unavailable)])
def recalibrate_now(session: Session = Depends(get_session)):
    return recalibrate(session, force=True)

class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool

@app.put("/api/personalization/consent", dependencies=[Depends(unavailable)])
def personalization_consent(request: ConsentRequest, session: Session = Depends(get_session)):
    return set_consent(session, request.enabled)

@app.get("/api/sources", dependencies=[Depends(unavailable)])
def sources():
    return [s.model_dump() for s in load_sources()]

@app.put("/api/sources", dependencies=[Depends(unavailable)])
def update_sources(sources: list[JobSource]):
    save_sources(sources)
    return [s.model_dump() for s in sources]

@app.get("/api/free-models", dependencies=[Depends(unavailable)])
async def free_models():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://openrouter.ai/api/v1/models", timeout=20)
            response.raise_for_status()
            models = response.json()["data"]
            return [{"id": m["id"], "name": m["name"]} for m in models
                    if m["id"].endswith(":free") and "tools" in m.get("supported_parameters", [])
                    and float(m.get("pricing", {}).get("prompt", "1")) == 0
                    and float(m.get("pricing", {}).get("completion", "1")) == 0]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise HTTPException(503, "Free model catalog unavailable. Check OpenRouter's current catalog") from exc

@app.get("/api/artifacts/{artifact_id}/{filename}", dependencies=[Depends(unavailable)])
def artifact(artifact_id: str, filename: str):
    if not re.fullmatch(r"[a-f0-9]{32}", artifact_id) or filename not in ("resume.pdf", "resume.tex"):
        raise HTTPException(404, "Artifact not found")
    path = Path(settings.artifact_dir) / artifact_id / filename
    if not path.is_file():
        raise HTTPException(404, "Artifact not found")
    return FileResponse(path, media_type="application/pdf" if filename.endswith("pdf") else "application/x-tex",
                        filename=filename, content_disposition_type="inline" if filename.endswith("pdf") else "attachment")


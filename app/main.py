from contextlib import asynccontextmanager
from pathlib import Path
import re
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlmodel import Session, select

from app.config import get_settings
from app.curator import layout_advisory
from app.db import get_profile, get_session, init_db
from app.llm import LLMError
from app.memory import consolidate
from app.models import Application, JobPosting, MemoryFact
from app.orchestrator import run
from app.personalization import recalibrate, set_consent
from app.query_parser import QueryParserError
from app.resumes import extract_profile, read_upload, save_profile
from app.sources import JobSource, load_sources, save_sources
from app.tracker import get_application

settings = get_settings()

@asynccontextmanager
async def lifespan(app):
    init_db()
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
    applications = session.exec(select(Application).join(JobPosting).where(JobPosting.user_id == 1)).all()
    profile = get_profile(session)
    return {"model_configured": settings.openrouter_configured and settings.free_model_selected,
            "model": settings.openrouter_model or None, "free_models_only": True,
            "resume": {"filename": profile.filename, "fact_count": len(profile.structured_facts.get("facts", []))} if profile else None,
            "counts": {s: sum(a.status == s for a in applications) for s in ("found", "tailored", "applied", "interviewing", "resolved")},
            "source_count": sum(s.enabled for s in load_sources()), "pdf_compiler_available": bool(shutil.which("tectonic"))}

class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    mode: str = "natural"
    limit: int = Field(default=10, ge=1, le=50)

@app.post("/api/search")
async def search(request: SearchRequest, session: Session = Depends(get_session)):
    if request.mode not in ("natural", "keyword") or not request.query.strip():
        raise ValueError("Choose natural-language or keyword search and enter a query")
    return await run({"action": "search", **request.model_dump()}, session)

@app.get("/api/jobs")
def jobs(session: Session = Depends(get_session)):
    rows = session.exec(select(JobPosting, Application).join(Application).where(JobPosting.user_id == 1).order_by(JobPosting.found_at.desc())).all()
    return [{**j.model_dump(), "application": a.model_dump(), "status": a.status,
             "fit_score": a.fit_score, "explanation": a.explanation} for j, a in rows]

@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int, session: Session = Depends(get_session)):
    a = get_application(session, job_id)
    return {**session.get(JobPosting, job_id).model_dump(), "application": a.model_dump(), "status": a.status,
            "fit_score": a.fit_score, "explanation": a.explanation}

@app.post("/api/jobs/{job_id}/tailor")
async def tailor_job(job_id: int, session: Session = Depends(get_session)):
    return await run({"action": "tailor", "job_id": job_id}, session)

@app.post("/api/jobs/{job_id}/curate")
async def curate_job(job_id: int, session: Session = Depends(get_session)):
    return await run({"action": "curate", "job_id": job_id}, session)

@app.post("/api/jobs/{job_id}/research")
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

@app.delete("/api/jobs/{job_id}/draft")
def discard_draft(job_id: int, session: Session = Depends(get_session)):
    a = get_application(session, job_id)
    a.draft = a.critique = a.tailored_resume = a.tailored_cover_letter = None
    if a.status == "tailored":
        a.status = "found"
    session.add(a)
    session.commit()
    return {"discarded": True}

@app.get("/api/resume")
def resume(session: Session = Depends(get_session)):
    profile = get_profile(session)
    return {**profile.model_dump(), "layout_advisory": layout_advisory(profile.latex_source)} if profile else None

def invalidate_drafts(session):
    for a in session.exec(select(Application)).all():
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
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Resume exceeds the 5 MB upload limit")
    text, latex = read_upload(file.filename or "resume.txt", content)
    facts = await extract_profile(text)
    profile = save_profile(session, filename=file.filename or "resume.txt", text=text, latex=latex, facts=facts)
    invalidate_drafts(session)
    consolidate(session)
    return profile.model_dump()

@app.delete("/api/resume")
def remove_resume(session: Session = Depends(get_session)):
    profile = get_profile(session)
    if profile:
        session.delete(profile)
        session.commit()
    invalidate_drafts(session)
    consolidate(session)
    return {"removed": True}

@app.get("/api/memory")
def memory(session: Session = Depends(get_session)):
    return [f.model_dump() for f in session.exec(select(MemoryFact).where(MemoryFact.user_id == 1)).all()]

@app.get("/api/personalization")
def personalization(session: Session = Depends(get_session)):
    return recalibrate(session)

@app.post("/api/personalization/recalibrate")
def recalibrate_now(session: Session = Depends(get_session)):
    return recalibrate(session, force=True)

class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool

@app.put("/api/personalization/consent")
def personalization_consent(request: ConsentRequest, session: Session = Depends(get_session)):
    return set_consent(session, request.enabled)

@app.get("/api/sources")
def sources():
    return [s.model_dump() for s in load_sources()]

@app.put("/api/sources")
def update_sources(sources: list[JobSource]):
    save_sources(sources)
    return [s.model_dump() for s in sources]

@app.get("/api/free-models")
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

@app.get("/api/artifacts/{artifact_id}/{filename}")
def artifact(artifact_id: str, filename: str):
    if not re.fullmatch(r"[a-f0-9]{32}", artifact_id) or filename not in ("resume.pdf", "resume.tex"):
        raise HTTPException(404, "Artifact not found")
    path = Path(settings.artifact_dir) / artifact_id / filename
    if not path.is_file():
        raise HTTPException(404, "Artifact not found")
    return FileResponse(path, media_type="application/pdf" if filename.endswith("pdf") else "application/x-tex",
                        filename=filename, content_disposition_type="inline" if filename.endswith("pdf") else "attachment")


"""One LangGraph routes search, tailoring, critique, curation, research and tracking."""
import asyncio
from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from sqlmodel import select
from app.curator import curate
from app.db import get_profile
from app.embeddings import similarity
from app.memory import consolidate
from app.models import JobPosting, utcnow
from app.personalization import get_weights, recalibrate
from app.query_parser import QuerySpec, parse_query
from app.research import research_company
from app.scoring import contains, rank_jobs
from app.scout import discover_jobs
from app.tailoring import TailoredDraft, critique, render_cover_letter, tailor
from app.tracker import approval_gate, get_application, save_jobs, update_status

class State(TypedDict, total=False):
    action: str
    query: str
    mode: str
    limit: int
    job_id: int
    status: str
    outcome: str | None
    explicit_action: bool
    query_spec: dict
    candidates: list[dict]
    warnings: list[str]
    draft: dict
    result: Any
    trace: list[str]

def session_from(config):
    return config["configurable"]["session"]

def keyword_spec(query: str) -> QuerySpec:
    """Explicit Phase 1 mode, not a silent replacement for the LLM parser."""
    tech = [w for w in ("java", "python", "javascript", "typescript", "rust", "golang", "c++", "c#", "react", "svelte", "kotlin", "swift", "sql") if contains(query, w)]
    roles = [w for w in ("backend", "frontend", "devops", "security", "data", "engineer", "developer") if contains(query, w)]
    return QuerySpec(hard_filters={"tech_stack_keywords": tech, "role_keywords": roles}, soft_preferences=[])

async def parse_node(state, config):
    spec = keyword_spec(state["query"]) if state.get("mode") == "keyword" else await parse_query(state["query"])
    return {"query_spec": spec.model_dump(), "trace": ["keyword_parser" if state.get("mode") == "keyword" else "query_parser"]}

async def scout_node(state, config):
    session = session_from(config)
    tracked = set(session.exec(select(JobPosting.url).where(JobPosting.user_id == 1)).all())
    found = await discover_jobs(state["query_spec"], limit=200, tracked_urls=tracked)
    return {"candidates": found["jobs"], "warnings": found["warnings"], "trace": state["trace"] + ["scout"]}

async def ranking_node(state, config):
    session = session_from(config)
    profile = get_profile(session)
    ranked = await asyncio.to_thread(rank_jobs, QuerySpec.model_validate(state["query_spec"]), state["candidates"],
                                     profile.structured_facts if profile else {}, personalized_weights=get_weights(session))
    selected = ranked["jobs"][:state.get("limit", 10)]
    persisted = save_jobs(session, selected)
    ids = {job.url: job.id for job in persisted}
    results = []
    for job in selected:
        if job["url"] not in ids:
            continue
        application = get_application(session, ids[job["url"]])
        application.fit_score, application.explanation = job["fit_score"], job["explanation"]
        application.scoring_signals = job["scoring_signals"]
        session.add(application)
        results.append({**job, "id": ids[job["url"]], "status": "found"})
    session.commit()
    trace = state["trace"] + ["ranking"]
    return {"result": {**ranked, "jobs": results, "query_spec": state["query_spec"], "warnings": state["warnings"],
                       "mode": state.get("mode", "natural"), "trace": trace}, "trace": trace}

async def tailor_node(state, config):
    session = session_from(config)
    get_application(session, state["job_id"])
    profile = get_profile(session)
    job = session.get(JobPosting, state["job_id"])
    draft = await tailor(job.model_dump(), profile.structured_facts if profile else {})
    return {"draft": draft.model_dump(), "trace": ["tailor"]}

async def critic_node(state, config):
    session = session_from(config)
    profile = get_profile(session)
    draft = TailoredDraft.model_validate(state["draft"])
    checks = await critique(draft, profile.structured_facts)
    application = get_application(session, state["job_id"])
    job = session.get(JobPosting, state["job_id"])
    application.draft, application.critique = draft.model_dump(), checks
    application.tailored_resume = "\n".join(c.text for c in draft.bullets)
    application.tailored_cover_letter = render_cover_letter(draft, job.model_dump())
    signals = dict(application.scoring_signals)
    previous = signals.pop("critic_adjustment", 0.0)
    signals.pop("critic_verified_match", None)
    if application.fit_score is not None:
        application.fit_score = min(100.0, max(0.0, application.fit_score - previous * 100))
    application.explanation = application.explanation.split(" Critic-verified content:")[0]
    if checks["passed"]:
        # Only verified exact claims contribute, and only after user-requested tailoring.
        verified_match = await asyncio.to_thread(similarity, "\n".join(c.text for c in draft.bullets),
                                                 job.title + "\n" + job.description)
        adjustment = .1 * (verified_match - signals.get("resume_match", 0.0))
        if application.fit_score is not None:
            application.fit_score = round(min(100.0, max(0.0, application.fit_score + adjustment * 100)), 1)
        signals.update(critic_verified_match=verified_match, critic_adjustment=adjustment)
        application.explanation += f" Critic-verified content: exact selected facts match this JD at {verified_match:.2f}; fit adjustment {adjustment * 100:+.1f} points."
        checks["content_match"] = {"value": round(verified_match, 4), "adjustment_points": round(adjustment * 100, 1),
                                  "evidence": "Local JD similarity to exact stored facts selected in the critic-verified draft"}
    application.scoring_signals = signals
    if checks["passed"] and application.status in ("found", "tailored"):
        application.status = "tailored"
    application.updated_at = utcnow()
    session.add(application)
    session.commit()
    trace = state["trace"] + ["critic"]
    return {"result": {"draft": draft.model_dump(), "critique": checks, "application": application.model_dump(), "trace": trace}, "trace": trace}

async def gate_node(state, config):
    application = approval_gate(session_from(config), state["job_id"], explicit_action=state.get("explicit_action", False))
    return {"result": application.model_dump(), "trace": ["human_approval_gate"]}

async def tracker_node(state, config):
    session = session_from(config)
    application = update_status(session, state["job_id"], state["status"], state.get("outcome"))
    consolidate(session)
    recalibrate(session)
    return {"result": application.model_dump(), "trace": ["tracker", "memory", "personalization"]}

async def curator_node(state, config):
    session = session_from(config)
    application = get_application(session, state["job_id"])
    result = await curate(session.get(JobPosting, state["job_id"]).model_dump(), get_profile(session))
    application.curated_resume = result
    session.add(application)
    session.commit()
    return {"result": result, "trace": ["resume_curator", "critic"]}

async def research_node(state, config):
    session = session_from(config)
    get_application(session, state["job_id"])
    result = await research_company(session.get(JobPosting, state["job_id"]).company, session)
    return {"result": result, "trace": ["interview_research"]}

builder = StateGraph(State)
for name, function in (("parse", parse_node), ("scout", scout_node), ("ranking", ranking_node), ("tailor", tailor_node),
                       ("critic", critic_node), ("gate", gate_node), ("tracker", tracker_node), ("curator", curator_node), ("research", research_node)):
    builder.add_node(name, function)
builder.add_conditional_edges(START, lambda state: state["action"], {"search": "parse", "tailor": "tailor", "approve": "gate", "status": "tracker", "curate": "curator", "research": "research"})
builder.add_edge("parse", "scout")
builder.add_edge("scout", "ranking")
builder.add_edge("ranking", END)
builder.add_edge("tailor", "critic")
builder.add_edge("critic", END)
for name in ("gate", "tracker", "curator", "research"):
    builder.add_edge(name, END)
graph = builder.compile()

async def run(state: State, session):
    result = await graph.ainvoke(state, config={"configurable": {"session": session}, "recursion_limit": 12})
    return result["result"]

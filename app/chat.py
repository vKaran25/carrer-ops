from app.workspace import commit as commit_workspace
from app.workspace import user_id as workspace_user_id
"""Saved search conversation; only explicit interest creates tracker records."""
from hashlib import sha256
import json

from sqlmodel import Session, select
from pydantic_core import to_jsonable_python

from app.db import get_profile
from app.models import Application, ChatTurn, JobPosting
from app.tracker import track_job
from app.search_feedback import empty_search_message


def resume_digest(profile) -> str | None:
    if profile is None:
        return None
    return sha256(json.dumps([profile.raw_resume_text, profile.structured_facts],
                             sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def record_search(session: Session, state: dict, result: dict, profile) -> ChatTurn:
    turn = ChatTurn(user_id=workspace_user_id(session), query=state.get("query", ""), mode=state.get("mode", "natural"),
                    resume_filename=profile.filename if profile else None,
                    resume_digest=resume_digest(profile), result=to_jsonable_python(result))
    session.add(turn)
    if state.get('context_update'):
        from app.search_context import commit_success
        stats = result.get('search_stats', {})
        # A fully failed/no-source run is a saved diagnostic, not a new intent.
        usable_execution = bool(stats.get('retrieved') or result.get('jobs') or not result.get('warnings'))
        session.flush()
        updated = usable_execution and commit_success(session, workspace_user_id(session), state['context_update'], turn.resume_digest, turn.id)
        info = dict(result.get('context_info') or {})
        info['saved_as_active'] = bool(updated)
        if not updated:
            info['notice'] = 'Previous context was preserved because sources failed or a newer search/reset/preference edit took priority.'
        result['context_info'] = info
        turn.result = to_jsonable_python(result)
    commit_workspace(session)
    session.refresh(turn)
    return turn


def history(session: Session, *, before_id: int | None = None, limit: int = 25) -> list[dict]:
    current_digest = resume_digest(get_profile(session))
    statement = select(ChatTurn).where(ChatTurn.user_id == workspace_user_id(session))
    if before_id is not None:
        statement = statement.where(ChatTurn.id < before_id)
    turns = list(reversed(session.exec(statement.order_by(ChatTurn.id.desc()).limit(limit)).all()))
    job_ids = {job['id'] for turn in turns for job in turn.result.get('jobs', [])}
    applications = {a.job_id: a for a in session.exec(select(Application).join(JobPosting).where(
        JobPosting.user_id == workspace_user_id(session), Application.job_id.in_(job_ids))).all()} if job_ids else {}
    messages = []
    for turn in turns:
        changed = turn.resume_digest != current_digest
        jobs = []
        for snapshot in turn.result.get("jobs", []):
            application = applications.get(snapshot["id"])
            jobs.append({**snapshot, "status": application.status if application else "discovered",
                         "fit_score": None if changed else snapshot.get("fit_score"),
                         "score_breakdown": None if changed else snapshot.get("score_breakdown"),
                         "scoring_signals": {} if changed else snapshot.get("scoring_signals", {}),
                         "factors": [] if changed else snapshot.get("factors", []),
                         "explanation": "Resume changed since this search. Search again for a current fit score."
                                        if changed else snapshot.get("explanation", "")})
        messages.append({"id": turn.id, "query": turn.query, "mode": turn.mode,
                         "resume_filename": turn.resume_filename, "resume_changed": changed,
                         "created_at": turn.created_at, "result": {**turn.result, "jobs": jobs,
                         "empty_message": turn.result.get("empty_message") or empty_search_message(turn.result)}})
    return messages


def interest(session: Session, job_id: int, turn_id: int) -> Application:
    turn = session.get(ChatTurn, turn_id)
    if not turn or turn.user_id != workspace_user_id(session):
        raise LookupError("Search message not found")
    snapshot = next((j for j in turn.result.get("jobs", []) if j["id"] == job_id), None)
    if snapshot is None:
        raise LookupError("This job is not part of the selected search message")
    if turn.resume_digest != resume_digest(get_profile(session)):
        snapshot = {**snapshot, "fit_score": None, "scoring_signals": {},
                    "explanation": "Resume changed since this search. Search again for a current fit score."}
    return track_job(session, job_id, snapshot)

from app.workspace import commit as commit_workspace
from app.workspace import user_id as workspace_user_id
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models import Application, JobPosting, UserAction, utcnow

STATUSES = ("interested", "applied", "interviewing", "resolved")
OUTCOMES = ("interview", "offer", "rejected", "no_response", "withdrawn")


def apply_snapshot(job: JobPosting, snapshot: dict):
    for field in ('title', 'company', 'location', 'description', 'source'):
        if field in snapshot:
            setattr(job, field, snapshot[field])
    if 'description_snippet' in snapshot:
        job.snippet = snapshot['description_snippet']
    if 'metadata' in snapshot or 'source_metadata' in snapshot:
        job.source_metadata = snapshot.get('metadata') or snapshot.get('source_metadata') or {}
    if 'posted_at' in snapshot:
        job.posted_at = publication_date(snapshot['posted_at'])


def get_application(session: Session, job_id: int) -> Application:
    job = session.get(JobPosting, job_id)
    if not job or job.user_id != workspace_user_id(session):
        raise LookupError("Job not found in this workspace")
    application = session.exec(select(Application).where(Application.job_id == job_id).with_for_update()).first()
    if not application:
        raise LookupError("Click Interested in chat before preparing or tracking this job")
    if application.status == "dismissed":
        raise LookupError("Choose Interested in chat to restore this job before preparing it")
    return application


def save_discovered_jobs(session: Session, jobs: list[dict]) -> list[JobPosting]:
    """Persist JD records for chat without creating any tracker applications."""
    results = []
    for item in jobs:
        existing = session.exec(select(JobPosting).where(JobPosting.user_id == workspace_user_id(session), JobPosting.url == item["url"])).first()
        if existing:
            results.append(existing)
            continue
        job = JobPosting(user_id=workspace_user_id(session), title=item["title"], company=item["company"],
                         location=item.get("location") or "Not specified", url=item["url"],
                         snippet=item.get("description_snippet", ""), description=item.get("description", ""),
                         source=item.get("source", "bs4"), posted_at=publication_date(item.get("posted_at")),
                         source_metadata=item.get("metadata", {}))
        session.add(job)
        session.flush()
        results.append(job)
    commit_workspace(session)
    return results


def track_job(session: Session, job_id: int, snapshot: dict) -> Application:
    """Explicit Interested action; repeated clicks never reset pipeline progress."""
    job = session.get(JobPosting, job_id)
    if not job or job.user_id != workspace_user_id(session):
        raise LookupError("Job not found in this workspace")
    existing = session.exec(select(Application).where(Application.job_id == job_id).with_for_update()).first()
    if existing:
        if existing.status == "dismissed":
            apply_snapshot(job, snapshot)
            session.add(job)
            session.add(UserAction(user_id=workspace_user_id(session), application_id=existing.id, action="restore_interest",
                                   previous_status="dismissed", new_status="interested"))
            existing.status = "interested"
            existing.fit_score = snapshot.get("fit_score")
            existing.explanation = snapshot.get("explanation", "")
            existing.scoring_signals = snapshot.get("scoring_signals", {})
            existing.updated_at = utcnow()
            session.add(existing)
            commit_workspace(session)
            session.refresh(existing)
        return existing
    # Keep the tracker JD consistent with the exact card the user selected,
    # even when the same URL appeared in more than one search snapshot.
    apply_snapshot(job, snapshot)
    session.add(job)
    application = Application(job_id=job_id, status="interested",
                              fit_score=snapshot.get("fit_score"),
                              explanation=snapshot.get("explanation", ""),
                              scoring_signals=snapshot.get("scoring_signals", {}))
    session.add(application)
    try:
        session.flush()
    except IntegrityError:
        # A second simultaneous click may have won the unique job constraint.
        session.rollback()
        existing = session.exec(select(Application).where(Application.job_id == job_id).with_for_update()).first()
        if existing:
            return existing
        raise
    session.add(UserAction(user_id=workspace_user_id(session), application_id=application.id, action="mark_interested",
                           previous_status="discovered", new_status="interested"))
    commit_workspace(session)
    session.refresh(application)
    return application


def remove_interest(session: Session, job_id: int) -> Application:
    """Soft-remove a job from Interested without deleting its chat or audit history."""
    job = session.get(JobPosting, job_id)
    if not job or job.user_id != workspace_user_id(session):
        raise LookupError("Job not found in this workspace")
    application = session.exec(select(Application).where(Application.job_id == job_id).with_for_update()).first()
    if not application:
        raise LookupError("This job is not in your tracker")
    if application.status == "dismissed":
        return application
    if application.status != "interested":
        raise ValueError("Only jobs in Interested can be removed")
    session.add(UserAction(user_id=workspace_user_id(session), application_id=application.id, action="remove_interest",
                           previous_status="interested", new_status="dismissed"))
    application.status = "dismissed"
    application.updated_at = utcnow()
    session.add(application)
    commit_workspace(session)
    session.refresh(application)
    return application


def save_jobs(session: Session, jobs: list[dict]) -> list[JobPosting]:
    """Explicit tracker intake helper (also used by isolated fixtures)."""
    selected = [item for item in jobs if not session.exec(select(JobPosting).where(
        JobPosting.user_id == workspace_user_id(session), JobPosting.url == item["url"])).first()]
    records = save_discovered_jobs(session, selected)
    for job, snapshot in zip(records, selected):
        track_job(session, job.id, snapshot)
    return records


def publication_date(value):
    from datetime import datetime
    from app.scout import parse_date
    return value if isinstance(value, datetime) else parse_date(value)


def approval_gate(session: Session, job_id: int, *, explicit_action: bool) -> Application:
    """Called exclusively by the orchestrator approval node after a UI action."""
    if explicit_action is not True:
        raise ValueError("Marking applied requires the explicit Mark as applied action")
    application = get_application(session, job_id)
    if application.applied_at is not None:
        return application
    action = UserAction(user_id=workspace_user_id(session), application_id=application.id, action="mark_applied",
                        previous_status=application.status, new_status="applied")
    session.add(action)
    session.flush()
    application.status = "applied"
    application.applied_at = utcnow()
    application.updated_at = utcnow()
    session.add(application)
    commit_workspace(session)
    session.refresh(application)
    return application


def update_status(session: Session, job_id: int, status: str, outcome: str | None = None):
    if status not in STATUSES or status == "applied":
        raise ValueError("Use Mark as applied for applied status; choose a valid pipeline state")
    application = get_application(session, job_id)
    if status == 'interested' and application.applied_at:
        raise ValueError('An applied application cannot move back to Interested.')
    if status == "interviewing" and not application.applied_at:
        raise ValueError("Mark this application applied before moving to interviewing")
    if outcome is not None and outcome not in OUTCOMES:
        raise ValueError("Unknown outcome")
    if outcome is not None and not application.applied_at:
        raise ValueError("Only explicitly applied applications can have logged outcomes")
    if status == "interviewing" and outcome is None:
        outcome = "interview"
    if status == "resolved" and application.applied_at and outcome is None:
        raise ValueError("Choose an outcome when resolving an applied application")
    if outcome is not None and status not in ("resolved", "interviewing"):
        raise ValueError("Log outcomes in interviewing or resolved states")
    session.add(UserAction(user_id=workspace_user_id(session), application_id=application.id, action="update_status",
                           previous_status=application.status, new_status=status))
    application.status = status
    application.outcome = outcome
    application.outcome_at = utcnow() if outcome else None
    application.updated_at = utcnow()
    session.add(application)
    commit_workspace(session)
    session.refresh(application)
    return application

from sqlmodel import Session, select

from app.models import Application, JobPosting, UserAction, utcnow

STATUSES = ("found", "tailored", "applied", "interviewing", "resolved")
OUTCOMES = ("interview", "offer", "rejected", "no_response", "withdrawn")


def get_application(session: Session, job_id: int) -> Application:
    job = session.get(JobPosting, job_id)
    if not job or job.user_id != 1:
        raise LookupError("Job not found in this workspace")
    application = session.exec(select(Application).where(Application.job_id == job_id)).first()
    if not application:
        raise LookupError("Application not found")
    return application


def save_jobs(session: Session, jobs: list[dict]) -> list[JobPosting]:
    results = []
    for item in jobs:
        existing = session.exec(select(JobPosting).where(JobPosting.user_id == 1, JobPosting.url == item["url"])).first()
        if existing:
            continue
        job = JobPosting(user_id=1, title=item["title"], company=item["company"],
                         location=item.get("location") or "Not specified", url=item["url"],
                         snippet=item.get("description_snippet", ""), description=item.get("description", ""),
                         source=item.get("source", "bs4"), posted_at=publication_date(item.get("posted_at")),
                         source_metadata=item.get("metadata", {}))
        session.add(job)
        session.flush()
        session.add(Application(job_id=job.id))
        results.append(job)
    session.commit()
    return results


def publication_date(value):
    from datetime import datetime
    from app.scout import parse_date
    return value if isinstance(value, datetime) else parse_date(value)


def approval_gate(session: Session, job_id: int, *, explicit_action: bool) -> Application:
    """Called exclusively by the orchestrator approval node after a UI action."""
    if explicit_action is not True:
        raise ValueError("Marking applied requires the explicit Mark as applied action")
    application = get_application(session, job_id)
    if application.critique and not application.critique.get("passed"):
        raise ValueError("The current draft contains unverified claims; fix or discard it before approval")
    if application.applied_at is not None:
        raise ValueError("Application has already been marked applied")
    action = UserAction(user_id=1, application_id=application.id, action="mark_applied",
                        previous_status=application.status, new_status="applied")
    session.add(action)
    session.flush()
    application.status = "applied"
    application.applied_at = utcnow()
    application.updated_at = utcnow()
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def update_status(session: Session, job_id: int, status: str, outcome: str | None = None):
    if status not in STATUSES or status == "applied":
        raise ValueError("Use Mark as applied for applied status; choose a valid pipeline state")
    application = get_application(session, job_id)
    if status == "tailored" and not application.draft:
        raise ValueError("Create a draft before moving to tailored")
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
    session.add(UserAction(user_id=1, application_id=application.id, action="update_status",
                           previous_status=application.status, new_status=status))
    application.status = status
    application.outcome = outcome
    application.outcome_at = utcnow() if outcome else None
    application.updated_at = utcnow()
    session.add(application)
    session.commit()
    session.refresh(application)
    return application

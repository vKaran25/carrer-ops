"""Consolidated local facts: add/update/delete by stable source identity."""

from sqlmodel import Session, select

from app.db import get_profile
from app.models import Application, JobPosting, MemoryFact, utcnow


def consolidate(session: Session, user_id: int = 1) -> dict:
    desired = {}
    profile = get_profile(session, user_id)
    if profile:
        for fact in profile.structured_facts.get("facts", []):
            desired[("resume", fact["id"])] = (fact["text"], fact.get("category", "resume"))
    rows = session.exec(select(Application, JobPosting).join(JobPosting).where(JobPosting.user_id == user_id)).all()
    for application, job in rows:
        if application.applied_at and application.outcome:
            key = ("outcome", str(application.id))
            desired[key] = (f"User logged {application.outcome} for {job.title} at {job.company} ({job.url})", "outcome")
    existing = session.exec(select(MemoryFact).where(MemoryFact.user_id == user_id)).all()
    added = updated = deleted = 0
    for fact in existing:
        key = (fact.source, fact.source_key)
        if key not in desired:
            session.delete(fact)
            deleted += 1
            continue
        text, kind = desired.pop(key)
        if (fact.fact_text, fact.fact_type) != (text, kind):
            fact.fact_text, fact.fact_type, fact.updated_at = text, kind, utcnow()
            session.add(fact)
            updated += 1
    for (source, key), (text, kind) in desired.items():
        session.add(MemoryFact(user_id=user_id, source=source, source_key=key, fact_text=text, fact_type=kind))
        added += 1
    session.commit()
    return {"added": added, "updated": updated, "deleted": deleted}

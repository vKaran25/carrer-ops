import asyncio
from io import BytesIO

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import init_db, make_engine
from app.models import Application, JobPosting, UserAction
from app.resumes import ExtractedFact, ResumeExtraction, grounded_facts, read_upload
from app.tailoring import Claim, TailoredDraft, critique, validate_claims
from app.tracker import approval_gate, save_jobs, update_status


@pytest.fixture
def session(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/test.db")
    init_db(engine)
    with Session(engine) as session:
        yield session


def sample_job(session):
    return save_jobs(session, [{"title": "Java engineer", "company": "Fictional Test Co", "url": "https://example.org/job/1"}])[0]


def test_extract_facts_requires_exact_source_evidence():
    raw = "Built Java APIs. Studied computer science."
    result = grounded_facts(ResumeExtraction(facts=[ExtractedFact(category="project", evidence="Built Java APIs.")]), raw)
    assert result["facts"][0]["text"] == "Built Java APIs."
    with pytest.raises(ValueError, match="exact source"):
        grounded_facts(ResumeExtraction(facts=[ExtractedFact(category="project", evidence="Led a team of 20.")]), raw)


def test_tex_and_word_intake():
    from docx import Document
    source = r"\documentclass{article}\begin{document}\section{Projects}\item Built Java APIs.\end{document}"
    text, original = read_upload("resume.tex", source.encode())
    assert original == source and "Built Java APIs" in text
    doc = Document()
    doc.add_paragraph("Fictional fixture: Built Python dashboards.")
    buffer = BytesIO()
    doc.save(buffer)
    text, original = read_upload("resume.docx", buffer.getvalue())
    assert "Built Python dashboards" in text and original is None
    with pytest.raises(ValueError, match="No readable"):
        read_upload("empty.txt", b"  ")


def test_critic_blocks_planted_fabrication_without_model_call():
    profile = {"facts": [{"id": "f1", "text": "Built Java APIs."}]}
    claim = Claim(text="Led 50 engineers and saved $1 million.", fact_ids=["f1"])
    draft = TailoredDraft(bullets=[claim], cover_letter_claims=[claim])
    result = asyncio.run(critique(draft, profile))
    assert result["passed"] is False
    assert validate_claims([Claim(text="Built Java APIs.", fact_ids=["f1"])], profile) == []


def test_scout_results_are_persisted_and_deduplicated(session):
    job = sample_job(session)
    assert job.id
    assert save_jobs(session, [{"title": "Duplicate", "company": "Fixture", "url": job.url}]) == []
    assert len(session.exec(select(Application)).all()) == 1


def test_approval_requires_explicit_action_and_persists_audit(session):
    job = sample_job(session)
    with pytest.raises(ValueError, match="explicit"):
        approval_gate(session, job.id, explicit_action=False)
    with pytest.raises(ValueError, match="Mark as applied"):
        update_status(session, job.id, "applied")
    approved = approval_gate(session, job.id, explicit_action=True)
    assert approved.status == "applied" and approved.applied_at
    assert session.exec(select(UserAction)).one().action == "mark_applied"
    assert update_status(session, job.id, "interviewing").outcome == "interview"
    assert update_status(session, job.id, "resolved", "offer").outcome == "offer"


def test_database_rejects_unlogged_applied_mutation(session):
    job = sample_job(session)
    application = session.exec(select(Application)).one()
    application.status = "applied"
    session.add(application)
    with pytest.raises(IntegrityError, match="logged user action"):
        session.commit()
    session.rollback()
    assert session.get(Application, application.id).status == "found"


def test_failed_critic_cannot_reach_approval(session):
    job = sample_job(session)
    application = session.exec(select(Application)).one()
    application.critique = {"passed": False}
    session.add(application)
    session.commit()
    with pytest.raises(ValueError, match="unverified"):
        approval_gate(session, job.id, explicit_action=True)


def test_cannot_log_positive_outcome_before_explicit_application(session):
    job = sample_job(session)
    with pytest.raises(ValueError, match="applied"):
        update_status(session, job.id, "interviewing")
    with pytest.raises(ValueError, match="explicitly applied"):
        update_status(session, job.id, "resolved", "offer")

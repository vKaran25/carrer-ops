from sqlmodel import Session, select
from app.db import init_db, make_engine
from app.models import Application, JobPosting, ResumeProfile, User


def test_workspace_records_survive_new_session(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/workspace.db")
    init_db(engine)
    with Session(engine) as session:
        assert session.get(User, 1)
        profile = ResumeProfile(user_id=1, filename="resume.txt", raw_resume_text="Built Java APIs", structured_facts={"facts": [{"id": "f1", "text": "Built Java APIs"}]})
        job = JobPosting(user_id=1, title="Backend", company="Fixture", url="https://example.org/jobs/1", source="bs4")
        session.add(profile)
        session.add(job)
        session.flush()
        session.add(Application(job_id=job.id))
        session.commit()
    with Session(engine) as session:
        assert session.exec(select(ResumeProfile)).one().structured_facts["facts"][0]["text"] == "Built Java APIs"
        assert session.exec(select(Application)).one().status == "found"


def test_local_user_initialization_is_idempotent(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/workspace.db")
    init_db(engine)
    init_db(engine)
    with Session(engine) as session:
        assert len(session.exec(select(User)).all()) == 1

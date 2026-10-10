from sqlmodel import Session, select

from app.db import init_db, make_engine
from app.memory import consolidate
from app.models import Application, JobPosting, MemoryFact, ResumeProfile, ScoringWeights, User, utcnow
from app.personalization import get_weights, recalibrate, set_consent
from app.query_parser import QuerySpec
from app.scoring import rank_jobs
from app.tracker import approval_gate, save_jobs, update_status


def test_memory_consolidates_add_update_delete_without_duplicates(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/db")
    init_db(engine)
    with Session(engine) as session:
        profile = ResumeProfile(user_id=1, filename="fixture.txt", raw_resume_text="Java Python", structured_facts={"facts":[{"id":"f1","text":"Java","category":"skill"},{"id":"f2","text":"Python","category":"skill"}]})
        session.add(profile); session.commit()
        assert consolidate(session) == {"added":2,"updated":0,"deleted":0}
        assert consolidate(session) == {"added":0,"updated":0,"deleted":0}
        profile.structured_facts={"facts":[{"id":"f1","text":"Java APIs","category":"project"}]}
        session.add(profile); session.commit()
        assert consolidate(session) == {"added":0,"updated":1,"deleted":1}
        session.delete(profile); session.commit()
        assert consolidate(session)["deleted"] == 1
        assert session.exec(select(MemoryFact)).all() == []


def add_outcomes(session, count, outcome="offer"):
    set_consent(session, True)
    for i in range(count):
        job = save_jobs(session,[{"title":f"Fixture role {i}","company":"Fictional Test Co","url":f"https://example.org/fixture/{i}"}])[0]
        application = session.exec(select(Application).where(Application.job_id==job.id)).one()
        application.scoring_signals={"tier_mid":1,"tech_overlap":.8,"resume_match":.7}
        session.add(application);session.commit()
        approval_gate(session,job.id,explicit_action=True)
        update_status(session,job.id,"resolved",outcome)


def test_cold_start_and_personalized_rank_change_after_six_positive_outcomes(tmp_path):
    engine=make_engine(f"sqlite:///{tmp_path}/db");init_db(engine)
    with Session(engine) as session:
        add_outcomes(session,6)
        assert recalibrate(session)["active"] is True
        weights=get_weights(session)
        assert weights["tier_mid"]>0
        session.add(User(id=2));session.commit()
        assert get_weights(session,2)=={}
        query=QuerySpec(hard_filters={},soft_preferences=[])
        jobs=[{"job_id":"a-new","title":"Java engineer","company":"Fixture High","description":"Java APIs","company_tier":"high"},
              {"job_id":"z-experienced","title":"Java engineer","company":"Fixture Mid","description":"Java APIs","company_tier":"mid"}]
        profile={"facts":["Built Java APIs"]}
        fresh=rank_jobs(query,jobs,profile,semantic=lambda *_:.7)
        experienced=rank_jobs(query,jobs,profile,semantic=lambda *_:.7,personalized_weights=weights)
        assert fresh["jobs"][0]["job_id"]=="a-new"
        assert experienced["jobs"][0]["job_id"]=="z-experienced"
        assert experienced["personalized"] and not fresh["personalized"]
        assert all(abs(j["personalization_adjustment"])<=15 for j in experienced["jobs"])


def test_cold_start_with_five_outcomes_and_correction_recalibration(tmp_path):
    engine=make_engine(f"sqlite:///{tmp_path}/db");init_db(engine)
    with Session(engine) as session:
        add_outcomes(session,5)
        result=recalibrate(session)
        assert not result["active"] and get_weights(session)=={}
        job=save_jobs(session,[{"title":"Fixture sixth","company":"Fixture","url":"https://example.org/sixth"}])[0]
        application=session.exec(select(Application).where(Application.job_id==job.id)).one()
        application.scoring_signals={"tier_mid":1};session.add(application);session.commit()
        approval_gate(session,job.id,explicit_action=True);update_status(session,job.id,"resolved","offer")
        before=recalibrate(session)
        row=session.exec(select(ScoringWeights)).one();old_digest=row.training_digest
        update_status(session,job.id,"resolved","rejected")
        after=recalibrate(session)
        session.refresh(row)
        assert row.training_digest!=old_digest and before["weights"]!=after["weights"]
        consolidate(session)
        assert len(session.exec(select(MemoryFact).where(MemoryFact.source=="outcome")).all())==6


def test_interview_then_offer_counts_as_one_outcome(tmp_path):
    engine=make_engine(f"sqlite:///{tmp_path}/db");init_db(engine)
    with Session(engine) as session:
        job=save_jobs(session,[{"title":"Fixture","company":"Fixture","url":"https://example.org/one"}])[0]
        approval_gate(session,job.id,explicit_action=True)
        update_status(session,job.id,"interviewing")
        update_status(session,job.id,"resolved","offer")
        assert recalibrate(session)["outcome_count"]==1


def test_learning_requires_opt_in_and_revocation_deletes_weights(tmp_path):
    engine=make_engine(f"sqlite:///{tmp_path}/db");init_db(engine)
    with Session(engine) as session:
        assert not recalibrate(session)["enabled"]
        add_outcomes(session,6)
        assert recalibrate(session)["active"] and get_weights(session)
        result=set_consent(session,False)
        assert not result["enabled"] and not result["active"]
        assert get_weights(session)=={} and not session.exec(select(ScoringWeights)).all()

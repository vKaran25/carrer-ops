import asyncio
from datetime import timedelta

from sqlmodel import Session

from app.db import init_db, make_engine
from app.models import InterviewResearchCache, utcnow
from app.research import Evidence, InterviewRound, ResearchSynthesis, research_company, templates, validate_synthesis

SOURCES = [
    {"title": "Fictional company interview report", "url": "https://example.org/report", "text": "Fictional company uses a phone screen and a coding round. The coding round covers arrays. medium difficulty."},
    {"title": "Another Fictional company report", "url": "https://example.net/report", "text": "Fictional company coding round focuses on arrays."},
]


def synthesis():
    return ResearchSynthesis(sufficient_information=True, rounds=[InterviewRound(name="coding round", type="coding", focus_areas=["arrays"], example_question_types=["arrays"], difficulty="medium", evidence=[Evidence(source_index=0, quote=SOURCES[0]["text"])])], difficulty_note="Not documented", prep_tips=[])


def test_fixed_query_templates():
    queries = templates("Fictional company")
    assert len(queries) == 3 and "site:reddit.com" in queries[1] and "site:leetcode.com/discuss" in queries[2]


def test_synthesis_rejects_fabricated_question_types_or_source_quotes():
    result = synthesis()
    assert validate_synthesis(result, SOURCES)
    result.rounds[0].example_question_types = ["brain surgery"]
    assert not validate_synthesis(result, SOURCES)
    result = synthesis()
    result.rounds[0].evidence[0].quote = "invented source claim"
    assert not validate_synthesis(result, SOURCES)


def test_obscure_company_returns_insufficient_without_llm(monkeypatch, tmp_path):
    import app.research as research
    async def no_sources(company): return []
    async def forbidden_call(*a, **kw): raise AssertionError("No synthesis without evidence")
    monkeypatch.setattr(research, "gather_sources", no_sources)
    monkeypatch.setattr(research, "call_tool", forbidden_call)
    engine = make_engine(f"sqlite:///{tmp_path}/db")
    init_db(engine)
    with Session(engine) as session:
        result = asyncio.run(research_company("Obscure Fictional XYZ", session))
        assert result["sufficient_information"] is False and result["rounds"] == []
        assert "Not enough public information" in result["difficulty_note"]


def test_wrong_company_sources_never_reach_synthesis(monkeypatch, tmp_path):
    import app.research as research
    async def unrelated(company): return SOURCES
    async def forbidden(*a, **kw): raise AssertionError("Unrelated company evidence")
    monkeypatch.setattr(research, "gather_sources", unrelated)
    monkeypatch.setattr(research, "call_tool", forbidden)
    engine = make_engine(f"sqlite:///{tmp_path}/db")
    init_db(engine)
    with Session(engine) as session:
        result = asyncio.run(research_company("Unrelated Obscure XYZ", session))
        assert not result["sufficient_information"] and not result["sources"]


def test_source_backed_structure_single_call_and_shared_cache(monkeypatch, tmp_path):
    import app.research as research
    calls = []
    async def sources(company):
        return [{**s, "text": s["text"] + " " * 150} for s in SOURCES]
    async def tool(*args, **kwargs):
        calls.append(kwargs)
        return synthesis()
    monkeypatch.setattr(research, "gather_sources", sources)
    monkeypatch.setattr(research, "call_tool", tool)
    engine = make_engine(f"sqlite:///{tmp_path}/db")
    init_db(engine)
    with Session(engine) as session:
        result = asyncio.run(research_company("Fictional company", session))
        assert result["sufficient_information"] and len(result["rounds"]) == 1
    with Session(engine) as session:
        result = asyncio.run(research_company("FICTIONAL COMPANY", session))
        assert result["cached"] is True and len(calls) == 1
        from sqlmodel import select
        cache = session.exec(select(InterviewResearchCache)).one()
        cache.researched_at = utcnow() - timedelta(days=61)
        session.add(cache)
        session.commit()
        result = asyncio.run(research_company("Fictional company", session))
        assert result["cached"] is False and len(calls) == 2

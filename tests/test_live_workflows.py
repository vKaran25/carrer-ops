"""Opt-in real free-model acceptance. Never touches the user's workspace database.

Models and public sources can fail/rate-limit; those failures fail these tests.
Default test runs skip them instead of claiming live model quality.
"""
import asyncio
import os
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session

from app.config import Settings, get_settings
from app.db import get_session, init_db, make_engine
from app.models import ResumeProfile
from app.research import research_company
from app.resumes import extract_profile, read_upload

pytestmark = pytest.mark.skipif(os.getenv("RUN_LIVE_LLM_TESTS") != "1", reason="Opt-in real free OpenRouter acceptance")
SOURCE = (Path(__file__).parent / "fixtures/fictional-resume.tex").read_text()


@pytest.fixture
def live_settings(tmp_path):
    current = get_settings()
    assert current.openrouter_configured, "Configure OPENROUTER_API_KEY and OPENROUTER_MODEL in .env"
    assert current.free_model_selected, "Only an actual free tool-calling model may be used"
    return Settings(**{**current.model_dump(), "database_url": f"sqlite:///{tmp_path}/acceptance.db",
                       "artifact_dir": str(tmp_path / "artifacts")})


def test_real_api_graph_search_tailor_critic_and_explicit_gate(live_settings, monkeypatch):
    import app.main as main
    active = make_engine(live_settings.database_url)
    init_db(active)
    def sessions():
        with Session(active) as session:
            yield session
    main.app.dependency_overrides[get_session] = sessions
    monkeypatch.setattr(main, "settings", live_settings)
    monkeypatch.setattr(main, "init_db", lambda: None)
    try:
        with TestClient(main.app) as client:
            response = client.post("/api/search", json={"query": "Find Python technology jobs worldwide", "mode": "natural", "limit": 3})
            assert response.status_code == 200, response.text
            found = response.json()
            assert found["trace"] == ["query_parser", "scout", "ranking"] and 0 < len(found["jobs"]) <= 3
            assert all(j["url"].startswith("https://") and j["status"] == "found" for j in found["jobs"])
            response = client.post("/api/resume", files={"file": ("fictional-resume.tex", SOURCE.encode())})
            assert response.status_code == 200, response.text
            job_id = found["jobs"][0]["id"]
            response = client.post(f"/api/jobs/{job_id}/tailor")
            assert response.status_code == 200, response.text
            assert response.json()["critique"]["passed"], response.json()["critique"]
            assert client.get(f"/api/jobs/{job_id}").json()["status"] == "tailored"
            assert client.post(f"/api/jobs/{job_id}/mark-applied", json={"explicit_action": False}).status_code == 422
            assert client.post(f"/api/jobs/{job_id}/mark-applied", json={"explicit_action": True}).status_code == 200
    finally:
        main.app.dependency_overrides.clear()


def test_real_two_jd_tex_curation_preserves_surrounding_source(live_settings, monkeypatch, tmp_path):
    import app.curator as curator
    from test_curator import masked
    assert shutil.which("tectonic"), "Install Tectonic for the real PDF acceptance test"
    monkeypatch.setattr(curator, "get_settings", lambda: live_settings)
    async def run():
        text, latex = read_upload("fictional-resume.tex", SOURCE.encode())
        facts = await extract_profile(text)
        profile = ResumeProfile(user_id=1, filename="fictional-resume.tex", raw_resume_text=text,
                                latex_source=latex, structured_facts=facts)
        outputs = []
        for index, (title, description) in enumerate([
            ("Fictional Java backend engineer", "Java payments and Spring Boot APIs"),
            ("Fictional Python analytics engineer", "Python analytics dashboards and SQL")
        ]):
            directory = tmp_path / f"curation-{index}"
            result = await curator.curate({"title": title, "company": "Fictional Acceptance Co", "description": description}, profile, directory=directory)
            assert result["original_layout_preserved"] and result["critique"]["passed"]
            assert (directory / "resume.pdf").read_bytes().startswith(b"%PDF")
            output = (directory / "resume.tex").read_text()
            assert masked(output) == masked(SOURCE)
            outputs.append(output)
        assert outputs[0] != outputs[1], "Acceptance requires JD-specific outputs; inspect the model's selected edits"
    asyncio.run(run())


def test_real_well_documented_and_obscure_company_research(live_settings):
    active = make_engine(live_settings.database_url)
    init_db(active)
    async def run():
        with Session(active) as session:
            well = await research_company("Amazon", session, force=True)
            assert well["sufficient_information"] and well["rounds"], "Public research did not produce enough grounded evidence"
            assert all(r["example_question_types"] and r["evidence"] for r in well["rounds"])
            obscure = await research_company("Fictional Nonexistent Acceptance Company 7c842b", session, force=True)
            assert not obscure["sufficient_information"] and not obscure["rounds"]
    asyncio.run(run())

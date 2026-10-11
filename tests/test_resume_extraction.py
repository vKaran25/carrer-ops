"""Resume selection uses source IDs; qualification authenticity is not assessed."""
import asyncio

import pytest
from pydantic import ValidationError

from app.llm import LLMError
from app.resumes import (ResumeExtraction, ResumeExtractionError, SelectedStatement,
                         extract_profile, grounded_facts, resume_statements)


def selected(statement_id, category="experience"):
    return ResumeExtraction(facts=[SelectedStatement(statement_id=statement_id, category=category)])


def test_source_ids_preserve_spacing_punctuation_and_exact_offsets():
    source = "  Built Java APIs — shipped 3 releases.\r\n\n\tSkills:\u00a0Java,  SQL. \n"
    statements = resume_statements(source)
    assert [s["text"] for s in statements] == ["Built Java APIs — shipped 3 releases.", "Skills:\u00a0Java,  SQL."]
    result = grounded_facts(ResumeExtraction(facts=[
        SelectedStatement(statement_id=s["id"], category="project") for s in statements
    ]), source)
    for fact in result["facts"]:
        assert fact["text"] == fact["evidence"] == source[fact["source_start"]:fact["source_end"]]
    assert grounded_facts(ResumeExtraction(facts=[
        SelectedStatement(statement_id="statement-1", category="project"),
        SelectedStatement(statement_id="statement-1", category="experience")
    ]), source)["facts"] == result["facts"][:1]


def test_selection_schema_has_no_generated_resume_text():
    schema = SelectedStatement.model_json_schema()
    assert set(schema["properties"]) == {"category", "statement_id"}
    with pytest.raises(ValidationError):
        SelectedStatement(statement_id="statement-1", category="project", evidence="Rewritten claim")


def test_invalid_id_is_retried_once_then_source_is_copied(monkeypatch):
    calls = []
    async def tool(schema, *, system, data):
        calls.append(data)
        return selected("invented" if len(calls) == 1 else "statement-1")
    monkeypatch.setattr("app.resumes.call_tool", tool)
    result = asyncio.run(extract_profile("Built Java APIs;  3 releases."))
    assert result["facts"][0]["text"] == "Built Java APIs;  3 releases."
    assert len(calls) == 2 and calls[1]["selection_retry"] is True
    assert calls[0]["statements"] == [{"id": "statement-1", "text": "Built Java APIs;  3 releases."}]


def test_repeated_bad_selection_has_nonjudgmental_retry_message(monkeypatch):
    calls = []
    async def tool(*args, **kwargs):
        calls.append(kwargs)
        return selected("invented")
    monkeypatch.setattr("app.resumes.call_tool", tool)
    with pytest.raises(ResumeExtractionError, match="upload the .docx file again to retry") as error:
        asyncio.run(extract_profile("Managed a fictional team of 500 people."))
    assert len(calls) == 2
    assert "claim" not in str(error.value) and "invented" not in str(error.value)


def test_malformed_response_is_retried_but_provider_errors_are_not(monkeypatch):
    calls = []
    async def malformed(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            try:
                ResumeExtraction.model_validate({"facts": [{"category": "project", "evidence": "paraphrase"}]})
            except ValidationError as exc:
                raise LLMError("OpenRouter could not produce a valid structured response") from exc
        return selected("statement-1")
    monkeypatch.setattr("app.resumes.call_tool", malformed)
    assert asyncio.run(extract_profile("Built APIs."))["facts"][0]["text"] == "Built APIs."
    assert len(calls) == 2
    calls.clear()
    async def unavailable(*args, **kwargs):
        calls.append(kwargs)
        raise LLMError("Provider temporarily unavailable")
    monkeypatch.setattr("app.resumes.call_tool", unavailable)
    with pytest.raises(LLMError, match="Provider temporarily unavailable"):
        asyncio.run(extract_profile("Built APIs."))
    assert len(calls) == 1


def test_uploaded_experience_is_accepted_without_authenticity_judgment(monkeypatch):
    source = "Managed a fictional team of 500 people."
    async def tool(*args, **kwargs):
        return selected("statement-1")
    monkeypatch.setattr("app.resumes.call_tool", tool)
    result = asyncio.run(extract_profile(source))
    assert result["facts"][0]["text"] == source
    assert set(result) == {"facts"}


def test_empty_text_does_not_call_a_model(monkeypatch):
    async def unexpected(*args, **kwargs):
        pytest.fail("Empty source text must not be sent to a model")
    monkeypatch.setattr("app.resumes.call_tool", unexpected)
    with pytest.raises(ResumeExtractionError, match="No readable resume text"):
        asyncio.run(extract_profile("  \n\t"))

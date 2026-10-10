import asyncio
from pathlib import Path
import shutil

import pytest
from pypdf import PdfReader

from app.curator import CurationPlan, StatementEdit, compile_pdf, layout_advisory, parse_statements, splice, template
from app.models import ResumeProfile

SOURCE = (Path(__file__).parent / "fixtures/fictional-resume.tex").read_text()
FACTS = {"facts": [
    {"id": "java", "category": "project", "text": "Built Java payment APIs using Spring Boot."},
    {"id": "python", "category": "project", "text": "Built Python analytics dashboards using SQL."},
    {"id": "tests", "category": "experience", "text": "Implemented unit tests for both projects."},
    {"id": "skills", "category": "skill", "text": "Java, Python, SQL."},
]}


def test_statement_ids_and_exact_character_spans_are_stable():
    first, second = parse_statements(SOURCE), parse_statements(SOURCE)
    assert first == second and len(first) == 4
    assert all(SOURCE[s.start:s.end] == s.source for s in first)
    assert first[0].text == FACTS["facts"][0]["text"]


def test_column_advisory_reports_source_structure_without_changing_it():
    assert layout_advisory(SOURCE) is None
    source = SOURCE.replace(r"\begin{document}", r"\begin{document}\begin{multicols}{2}")
    assert "columns or tables" in layout_advisory(source)
    assert "multicols" in source


def masked(source):
    for statement in reversed(parse_statements(source)):
        source = source[:statement.start] + "<statement>" + source[statement.end:]
    return source


def test_two_job_splices_preserve_all_surrounding_formatting():
    statements = parse_statements(SOURCE)
    first = splice(SOURCE, statements, [StatementEdit(statement_id=statements[0].id, text=FACTS["facts"][2]["text"], fact_ids=["tests"])])
    second = splice(SOURCE, statements, [StatementEdit(statement_id=statements[1].id, text=FACTS["facts"][0]["text"], fact_ids=["java"])])
    assert first != second
    assert masked(first) == masked(second) == masked(SOURCE)
    assert statements[1].source in first and statements[0].source in second
    assert r"\newcommand{\resumeItem}[1]{\item #1}" in first


def test_splice_rejects_unknown_ids_and_escapes_tex_commands():
    statements = parse_statements(SOURCE)
    with pytest.raises(ValueError, match="unknown"):
        splice(SOURCE, statements, [StatementEdit(statement_id="invented", text="Injected", fact_ids=["java"])])
    output = splice(SOURCE, statements, [StatementEdit(statement_id=statements[0].id, text=r"100% & \input{secret}", fact_ids=["java"])])
    assert r"100\% \& \textbackslash{}input\{secret\}" in output


def test_fallback_template_contains_only_stored_facts():
    source = template(FACTS)
    assert "Built Java payment APIs" in source
    assert "Employer" not in source
    assert len(parse_statements(source)) == 4


@pytest.mark.skipif(not shutil.which("tectonic"), reason="Tectonic required for real PDF compilation")
def test_real_latex_compile_and_pdf_extraction(tmp_path):
    pdf = compile_pdf(SOURCE, tmp_path / "pdf")
    text = " ".join(p.extract_text() for p in PdfReader(pdf).pages)
    assert "Alex Fixture" in text and "Java payment APIs" in text
    assert len(PdfReader(pdf).pages) == 1


def test_external_file_commands_cannot_compile(tmp_path):
    if not shutil.which("tectonic"):
        pytest.skip("Tectonic not installed")
    with pytest.raises(ValueError, match="self-contained"):
        compile_pdf(SOURCE.replace(r"\begin{document}", r"\begin{document}\input{/etc/passwd}"), tmp_path)


@pytest.mark.skipif(not shutil.which("tectonic"), reason="Tectonic required")
def test_curator_tex_and_new_layout_paths(monkeypatch, tmp_path):
    import app.curator as curator
    async def plan(*args, **kwargs):
        return CurationPlan(edits=[])
    monkeypatch.setattr(curator, "call_tool", plan)
    profile = ResumeProfile(user_id=1, filename="fictional.tex", raw_resume_text="Fixture", latex_source=SOURCE, structured_facts=FACTS)
    first = asyncio.run(curator.curate({"title": "Java"}, profile, directory=tmp_path / "original"))
    assert first["original_layout_preserved"] and first["edit_count"] == 0
    profile.latex_source = None
    second = asyncio.run(curator.curate({"title": "Python"}, profile, directory=tmp_path / "fallback"))
    assert second["original_layout_preserved"] is False
    assert "New clean layout" in second["layout_note"]
    assert (tmp_path / "fallback/resume.pdf").is_file()

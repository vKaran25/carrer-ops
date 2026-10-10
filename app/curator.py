"""Exact-span LaTeX curation, provenance gate, and downloadable PDF artifacts."""

import asyncio
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.llm import call_tool
from app.resumes import latex_text
from app.tailoring import Claim, TailoredDraft, critique


@dataclass(frozen=True)
class Statement:
    id: str
    start: int
    end: int
    source: str
    text: str
    kind: str


def closing_brace(source: str, start: int) -> int:
    depth = 0
    for i in range(start, len(source)):
        if i and source[i - 1] == "\\":
            continue
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("Unbalanced LaTeX statement braces")


def parse_statements(source: str) -> list[Statement]:
    spans = []
    for match in re.finditer(r"(?m)^[ \t]*\\(resumeItem|resumeSummary|summary|skills)\s*\{", source):
        start = match.end()
        end = closing_brace(source, start - 1)
        spans.append((start, end, "bullet" if match.group(1) == "resumeItem" else match.group(1)))
    boundaries = list(re.finditer(r"(?m)^[ \t]*\\(?:item(?:\[[^\]]*\])?|end\{(?:itemize|enumerate)\}|section(?:\*?\{)|resumeItem\s*\{)", source))
    for index, match in enumerate(boundaries):
        if not re.match(r"\s*\\item(?:\[|\s|$)", match.group()):
            continue
        start = match.end()
        end = boundaries[index + 1].start() if index + 1 < len(boundaries) else len(source)
        while start < end and source[start].isspace():
            start += 1
        while end > start and source[end - 1].isspace():
            end -= 1
        if end > start and not any(a <= start < b for a, b, _ in spans):
            spans.append((start, end, "bullet"))
    # Common plain skills/summary lines: preserve labels and line-break macros.
    for match in re.finditer(r"(?m)^[ \t]*\\textbf\{(?:Skills|Languages|Technologies|Summary):?\}\s*:?\s*([^\n]+)", source):
        start, end = match.span(1)
        while end > start and source[end - 1].isspace():
            end -= 1
        if source[max(start, end - 2):end] == "\\\\":
            end -= 2
        if not any(a <= start < b for a, b, _ in spans):
            spans.append((start, end, "skills"))
    statements = []
    for start, end, kind in sorted(spans):
        raw = source[start:end]
        identifier = "stmt-" + sha256(f"{start}:{raw}".encode()).hexdigest()[:16]
        statements.append(Statement(identifier, start, end, raw, latex_text(raw), kind))
    return statements


def escape_latex(text: str) -> str:
    substitutions = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                     "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(substitutions.get(char, char) for char in text)


def layout_advisory(source: str | None) -> str | None:
    if source and (re.search(r"\\begin\{(?:multicols|paracol|tabular|tabularx)\}", source) or len(re.findall(r"\\begin\{minipage\}", source)) > 1):
        return "This source contains columns or tables. Check the PDF's text extraction order before submitting to an ATS. The original layout is preserved."
    return None


class StatementEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement_id: str
    text: str = Field(min_length=1)
    fact_ids: list[str] = Field(min_length=1)


class CurationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edits: list[StatementEdit] = Field(max_length=4)


def splice(source: str, statements: list[Statement], edits: list[StatementEdit]) -> str:
    lookup = {statement.id: statement for statement in statements}
    ids = [edit.statement_id for edit in edits]
    if len(ids) != len(set(ids)) or any(key not in lookup for key in ids):
        raise ValueError("Curation requested duplicate or unknown statement IDs")
    result = source
    for edit in sorted(edits, key=lambda e: lookup[e.statement_id].start, reverse=True):
        statement = lookup[edit.statement_id]
        if source[statement.start:statement.end] != statement.source:
            raise ValueError("Source changed after statement parsing")
        result = result[:statement.start] + escape_latex(edit.text) + result[statement.end:]
    return result


def template(profile: dict) -> str:
    facts = profile.get("facts", [])
    identity = [f for f in facts if f.get("category") == "identity"]
    header = escape_latex(identity[0]["text"]) if identity else "Resume"
    sections = []
    for category, name in (("experience", "Experience"), ("project", "Projects"), ("skill", "Skills"), ("education", "Education")):
        selected = [f for f in facts if f.get("category") == category]
        if selected:
            sections.append(r"\section*{" + name + "}\n" + r"\begin{itemize}" + "\n" + "\n".join(r"\item " + escape_latex(f["text"]) for f in selected) + "\n" + r"\end{itemize}")
    return (r"\documentclass[11pt]{article}" + "\n" + r"\usepackage[margin=0.7in]{geometry}" + "\n" +
            r"\usepackage[T1]{fontenc}" + "\n" + r"\usepackage{lmodern}" + "\n" + r"\pagestyle{empty}" + "\n" +
            r"\begin{document}" + "\n" + r"\begin{center}\Large " + header + r"\end{center}" + "\n" +
            "\n".join(sections) + "\n" + r"\end{document}" + "\n")


def compile_pdf(source: str, directory: Path) -> Path:
    if not shutil.which("tectonic"):
        raise ValueError("PDF compilation requires Tectonic. Install with: brew install tectonic")
    # User-provided sources cannot access local files, invoke programs, or add attachments.
    blocked = r"\\(?:input|include|openin|openout|read|write|write18|catcode|csname|directlua|usepackage\s*\{(?:shellesc|attachfile|pdfpages))\b"
    if re.search(blocked, source, re.I):
        raise ValueError("This LaTeX uses external-file or executable commands; upload a self-contained resume")
    directory.mkdir(parents=True, exist_ok=True)
    tex = directory / "resume.tex"
    tex.write_text(source)
    try:
        process = subprocess.run(["tectonic", "--untrusted", "--outdir", str(directory.resolve()), str(tex.resolve())],
                                 capture_output=True, text=True, timeout=get_settings().latex_compile_timeout_seconds, cwd=directory)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("LaTeX compilation exceeded the time limit") from exc
    output = directory / "resume.pdf"
    if process.returncode or not output.exists():
        # Diagnostics are useful but paths and arbitrary source log output are not shown to users.
        raise ValueError("LaTeX could not compile. Check for unsupported macros/packages or missing external files")
    return output


async def curate(job: dict, profile, *, directory: Path | None = None) -> dict:
    if not profile or not profile.structured_facts.get("facts"):
        raise ValueError("Upload a resume before curating")
    original_layout = profile.latex_source is not None
    source = profile.latex_source or template(profile.structured_facts)
    statements = parse_statements(source)
    if not statements:
        raise ValueError("No editable statements found. Supported: item bullets, resumeItem, summary and skills commands")
    plan = await call_tool(CurationPlan, system=(
        "Choose at most four statement spans for minor JD-relevant curation. The new text must be an "
        "entire cited stored fact's text, or entire cited facts concatenated with '. ' or '; '. Never "
        "paraphrase, infer, invent, or change structure/macros. Select only statements worth changing. "
        "Return an empty edits list if no grounded improvement is justified."
    ), data={"job": job, "statements": [{"id": s.id, "text": s.text, "kind": s.kind} for s in statements],
             "stored_profile": profile.structured_facts})
    checks = {"passed": True, "checks": [], "method": "No edits proposed"}
    if plan.edits:
        claims = [Claim(text=e.text, fact_ids=e.fact_ids) for e in plan.edits]
        checks = await critique(TailoredDraft(bullets=claims, cover_letter_claims=claims), profile.structured_facts)
    if not checks["passed"]:
        raise ValueError("Curation blocked: proposed edits are not grounded in stored resume facts")
    rendered = splice(source, statements, plan.edits)
    artifact_id = uuid.uuid4().hex
    output_dir = directory or Path(get_settings().artifact_dir) / artifact_id
    await asyncio.to_thread(compile_pdf, rendered, output_dir)
    manifest = {"artifact_id": artifact_id, "original_layout_preserved": original_layout,
                "layout_advisory": layout_advisory(profile.latex_source),
                "layout_note": "Original LaTeX layout preserved outside edited statements" if original_layout else "New clean layout from stored facts; original PDF/Word formatting is not preserved",
                "edit_count": len(plan.edits), "edits": [e.model_dump() for e in plan.edits], "critique": checks,
                "pdf_url": f"/api/artifacts/{artifact_id}/resume.pdf", "tex_url": f"/api/artifacts/{artifact_id}/resume.tex"}
    return manifest

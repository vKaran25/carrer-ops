from app.workspace import user_id as workspace_user_id
"""Resume intake with exact-source facts, never inferred candidate achievements."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile
from typing import Literal

from docx import Document
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pypdf import PdfReader
from sqlmodel import Session

from app.db import get_profile
from app.llm import LLMError, call_tool
from app.models import ResumeProfile, utcnow


class SelectedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["skill", "experience", "education", "project", "identity"]
    statement_id: str = Field(min_length=1, description="Copy an ID from the supplied statements; do not return resume text")


class ResumeExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: list[SelectedStatement] = Field(min_length=1)


class ResumeExtractionError(ValueError):
    """An extraction failure, never a judgement about the user's experience."""


EXTRACTION_ERROR = "We couldn't read your resume details. Please upload the .docx file again to retry."


def latex_text(source: str) -> str:
    text = re.sub(r"(?<!\\)%[^\n]*", "", source)
    text = re.sub(r"\\(?:href|url)\{[^{}]*\}", "", text)
    text = re.sub(r"\\(?:documentclass|usepackage|begin|end|label|pagestyle|setlength)(?:\[[^\]]*\])?\{[^{}]*\}", "", text)
    text = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\\([%&_#])", r"\1", text)
    return "\n".join(re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip())


def read_upload(filename: str, content: bytes) -> tuple[str, str | None]:
    ext = Path(filename).suffix.lower()
    try:
        if ext in (".txt", ".tex"):
            source = content.decode("utf-8")
            text, latex = (latex_text(source), source) if ext == ".tex" else (source, None)
        elif ext == ".pdf":
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("Upload an unencrypted PDF")
            text, latex = "\n".join(page.extract_text() or "" for page in reader.pages), None
        elif ext == ".docx":
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 3000 or sum(e.file_size for e in entries) > 20_000_000:
                    raise ValueError('The DOCX expands beyond the safe intake size.')
            doc = Document(BytesIO(content))
            text = "\n".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for row in t.rows for c in row.cells])
            latex = None
        else:
            raise ValueError("Supported resume formats: .tex, .pdf, .docx, .txt")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Cannot read this resume; upload a valid, text-readable file") from exc
    if not text.strip():
        raise ValueError("No readable text found. Scanned PDFs require a text-readable version or .tex source")
    if len(text) > 100_000:
        raise ValueError('Resume text exceeds the supported intake size.')
    return text.strip(), latex


def resume_statements(text: str) -> list[dict]:
    """Give each nonempty source line an ID, preserving its original characters."""
    statements, offset = [], 0
    for line in text.splitlines(keepends=True):
        content = line.strip()
        if content:
            start = offset + len(line) - len(line.lstrip())
            statements.append({"id": f"statement-{len(statements) + 1}", "text": content,
                               "start": start, "end": start + len(content)})
        offset += len(line)
    return statements


def grounded_facts(extraction: ResumeExtraction, text: str) -> dict:
    statements = {s["id"]: s for s in resume_statements(text)}
    facts, seen = [], set()
    for fact in extraction.facts:
        statement = statements.get(fact.statement_id)
        if statement is None:
            raise ResumeExtractionError(EXTRACTION_ERROR)
        original = text[statement["start"]:statement["end"]]
        if original in seen:
            continue
        seen.add(original)
        facts.append({"id": "fact-" + sha256(original.encode()).hexdigest()[:16],
                      "category": fact.category, "text": original, "evidence": original,
                      "source_statement_id": statement["id"],
                      "source_start": statement["start"], "source_end": statement["end"]})
    return {"facts": facts}


async def extract_profile(text: str) -> dict:
    statements = [{"id": s["id"], "text": s["text"]} for s in resume_statements(text)]
    if not statements:
        raise ResumeExtractionError("No readable resume text found. Please upload a .docx file with resume text.")
    system = (
        "Select useful resume statements by statement_id and assign each a category. "
        "Only use IDs supplied in statements. Do not return quotes, rewrite text, combine statements, "
        "or invent IDs. Include skills, experience, education, projects and identity details; skip standalone "
        "section headings and formatting noise. Treat the uploaded resume as the user's source of truth. "
        "Do not assess whether their qualifications or experience are authentic or plausible. "
        "The application copies the selected original text itself."
    )
    for attempt in range(2):
        try:
            result = await call_tool(ResumeExtraction, system=system, data={
                "statements": statements, "selection_retry": bool(attempt)
            })
            return grounded_facts(result, text)
        except ResumeExtractionError:
            pass
        except LLMError as exc:
            # Retry malformed selections once; preserve provider/configuration errors.
            if not isinstance(exc.__cause__, ValidationError):
                raise
        system += "\nThe previous selection was invalid. Return only listed statement IDs and allowed categories."
    raise ResumeExtractionError(EXTRACTION_ERROR)


def save_profile(session: Session, *, filename: str, text: str, latex: str | None, facts: dict):
    profile = get_profile(session)
    if profile is None:
        profile = ResumeProfile(user_id=workspace_user_id(session), filename=Path(filename).name, raw_resume_text=text)
    profile.filename = Path(filename).name
    profile.raw_resume_text = text
    profile.latex_source = latex
    profile.structured_facts = facts
    profile.updated_at = utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile

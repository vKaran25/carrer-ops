"""On-demand drafts composed from exact source facts, with a separate critic."""

import re
from pydantic import BaseModel, ConfigDict, Field

from app.llm import call_tool


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    fact_ids: list[str] = Field(min_length=1)


class TailoredDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bullets: list[Claim] = Field(min_length=1, max_length=8)
    cover_letter_claims: list[Claim] = Field(min_length=1, max_length=6)


class CritiqueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_index: int = Field(ge=0)
    supported: bool
    reason: str


class CriticResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checks: list[CritiqueItem]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".")


def validate_claims(claims: list[Claim], profile: dict) -> list[dict]:
    """Fail closed: each sentence must be an extract from its cited stored facts.

    Grounded rearrangement/selection is useful tailoring. Unconstrained paraphrase
    is deliberately not accepted without a human adding the new fact first.
    """
    facts = {f["id"]: f["text"] for f in profile.get("facts", [])}
    problems = []
    for index, claim in enumerate(claims):
        if any(key not in facts for key in claim.fact_ids):
            problems.append({"claim_index": index, "supported": False, "reason": "Unknown source fact"})
            continue
        cited = [normalize(facts[key]) for key in claim.fact_ids]
        text = normalize(claim.text)
        # Entire claim must be an exact cited statement or concatenation thereof.
        combinations = [". ".join(cited), "; ".join(cited), " ".join(cited)]
        if text not in cited and text not in combinations:
            problems.append({"claim_index": index, "supported": False,
                             "reason": "Claim is not an exact composition of the cited stored facts"})
    return problems


async def tailor(job: dict, profile: dict) -> TailoredDraft:
    if not profile.get("facts"):
        raise ValueError("Upload a resume with verified facts before tailoring")
    return await call_tool(TailoredDraft, system=(
        "Create a draft for this single job by SELECTING and ORDERING the most JD-relevant stored facts. "
        "Each text must equal an entire cited fact's text, or concatenate entire cited texts using '. ' "
        "or '; '. Never paraphrase, expand, infer, or invent claims. Prefer specific relevant project and "
        "experience facts. Use fact_ids as provenance. Different JDs should select different relevant facts. "
        "Cover letter claims follow the same exact-fact rule. If there are no relevant facts, select the "
        "closest real facts; do not claim unrecorded qualifications."
    ), data={"job": job, "stored_profile": profile})


async def critique(draft: TailoredDraft, profile: dict) -> dict:
    claims = draft.bullets + draft.cover_letter_claims
    problems = validate_claims(claims, profile)
    if problems:
        return {"passed": False, "checks": problems, "method": "deterministic provenance gate"}
    response = await call_tool(CriticResponse, system=(
        "Independently fact-check every indexed claim against its cited stored facts. "
        "Mark unsupported claims false, including changed metrics, employers, skills, responsibility or "
        "seniority. Return exactly one check per claim index. Do not assess hiring probability."
    ), data={"claims": [{"index": i, **c.model_dump()} for i, c in enumerate(claims)], "stored_profile": profile})
    indices = [check.claim_index for check in response.checks]
    if sorted(indices) != list(range(len(claims))):
        return {"passed": False, "checks": [], "method": "critic", "reason": "Critic omitted or duplicated claims"}
    return {"passed": all(check.supported for check in response.checks),
            "checks": [c.model_dump() for c in response.checks], "method": "provenance gate and independent critic"}


def render_cover_letter(draft: TailoredDraft, job: dict) -> str:
    opening = f"I am interested in the {job['title']} role at {job['company']}. My recorded experience includes:"
    return opening + "\n\n" + "\n".join(c.text for c in draft.cover_letter_claims)

"""Production Layer 1 ranking. Missing data is disclosed and never invented."""

from datetime import datetime, timedelta, timezone
import re
from typing import Callable

from app.embeddings import similarity
from app.query_parser import QuerySpec
from app.scout import parse_date


def contains(text: str, keyword: str) -> bool:
    pattern = re.escape(keyword.casefold()).replace(r"\ ", r"[\s-]+")
    return bool(re.search(r"(?<![\w])" + pattern + r"(?![\w])", text.casefold()))


def metadata(job: dict) -> dict:
    return job.get("metadata") or job.get("source_metadata") or {}


def published(job: dict, as_of: datetime) -> datetime | None:
    value = job.get("posted_at") or job.get("date_posted")
    if value:
        return value.replace(tzinfo=timezone.utc) if isinstance(value, datetime) and value.tzinfo is None else value if isinstance(value, datetime) else parse_date(value)
    # Benchmark fixtures explicitly provide an age relative to their fixed date.
    if "age_days" in job:
        return as_of - timedelta(days=float(job["age_days"]))
    return None


def eligible(job: dict, spec: QuerySpec, as_of: datetime) -> tuple[bool, str | None]:
    hard = spec.hard_filters
    text = " ".join([job.get("title", ""), job.get("description", ""), job.get("description_snippet", "")])
    stack_text = text + " " + " ".join(job.get("tech_stack", []))
    if hard.recency_days is not None:
        date = published(job, as_of)
        if date is None:
            return False, "Publication date unavailable"
        if date > as_of or date < as_of - timedelta(days=hard.recency_days):
            return False, "Outside required posting window"
    if any(not contains(stack_text, word) for word in hard.tech_stack_keywords):
        return False, "Missing required technology"
    role_text = job.get("title", "") + " " + job.get("role", "") + " " + text
    if any(not contains(role_text, word) for word in hard.role_keywords):
        return False, "Missing required role"
    industry = metadata(job).get("industry") or job.get("industry") or ""
    if hard.industries and not any(contains(industry, word) or contains(text, word) for word in hard.industries):
        return False, "Required industry is not evidenced"
    if hard.company_names and job.get("company", "").casefold() not in {name.casefold() for name in hard.company_names}:
        return False, "Different required company"
    location = job.get("location", "")
    if hard.locations and not any(contains(location, word) for word in hard.locations):
        return False, "Different required location"
    return True, None


def fact_strings(profile: dict) -> list[str]:
    return [fact if isinstance(fact, str) else fact.get("text", "") for fact in profile.get("facts", [])]


def job_signals(job: dict, profile: dict, *, semantic: Callable = similarity,
                as_of: datetime | None = None) -> tuple[dict[str, float], dict[str, str]]:
    facts = fact_strings(profile)
    resume = "\n".join(facts)
    description = job.get("description", "") or job.get("description_snippet", "")
    text = job.get("title", "") + "\n" + description
    signals = {"resume_match": semantic(resume, text) if resume else 0.0}
    notes = {"resume_match": "Local semantic similarity between this JD and stored resume facts" if resume else "No resume on file; profile similarity cannot be assessed"}
    project_facts = [f.get("text", "") for f in profile.get("facts", []) if isinstance(f, dict) and f.get("category") == "project"]
    # Existing golden profile has plain fact strings rather than typed facts.
    if not project_facts:
        project_facts = [f for f in facts if contains(f, "built") or contains(f, "project")]
    signals["project_domain_similarity"] = semantic("\n".join(project_facts), text) if project_facts else 0.0
    notes["project_domain_similarity"] = "JD similarity to recorded project statements" if project_facts else "No stored project evidence available"
    company = job.get("company", "")
    affinity = [f for f in facts if company and contains(f, company)]
    signals["resume_company_affinity"] = float(bool(affinity))
    notes["resume_company_affinity"] = f"Company name appears in stored fact: {affinity[0]}" if affinity else "Company name does not appear in stored resume facts"
    growth_terms = [term for term in ("mentorship", "mentoring", "promotion", "career development", "professional development", "progression") if contains(text, term)]
    signals["career_growth"] = min(1.0, len(growth_terms) / 2)
    notes["career_growth"] = "JD explicitly mentions: " + ", ".join(growth_terms) if growth_terms else "JD contains no explicit career-development evidence; progression is unknown"
    skill_facts = [f.get("text", "") for f in profile.get("facts", []) if isinstance(f, dict) and f.get("category") == "skill"]
    skills = [s for line in skill_facts for s in re.split(r"[,;|]", line) if s.strip()]
    signals["tech_overlap"] = sum(contains(text, s.strip()) for s in skills) / len(skills) if skills else 0.0
    date = published(job, as_of or datetime.now(timezone.utc))
    age = ((as_of or datetime.now(timezone.utc)) - date).total_seconds() / 86400 if date else None
    signals["recency"] = max(0.0, 1 - max(0, age) / 30) if age is not None else 0.0
    tier = metadata(job).get("company_tier") or job.get("company_tier")
    for tier_name in ("high", "mid", "low"):
        signals["tier_" + tier_name] = float(tier == tier_name)
    for seniority in ("intern", "junior"):
        signals["seniority_" + seniority] = float(contains(text, seniority))
    return signals, notes


def rank_jobs(query_spec: QuerySpec, jobs: list[dict], profile: dict, *,
              as_of: str | datetime | None = None, semantic: Callable = similarity,
              personalized_weights: dict[str, float] | None = None) -> dict:
    now = parse_date(as_of) if isinstance(as_of, str) else as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    ranked, excluded = [], {}
    for job in jobs:
        accepted, reason = eligible(job, query_spec, now)
        if not accepted:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        signals, evidence = job_signals(job, profile, semantic=semantic, as_of=now)
        weighted, total_weight, factor_notes, weak = 0.0, 0.0, [], []
        for preference in query_spec.soft_preferences:
            factor = preference.factor
            if factor == "company_tier":
                tier = metadata(job).get("company_tier") or job.get("company_tier")
                value = float(tier in preference.targets) if tier else 0.0
                note = f"Source-recorded company tier: {tier}; requested {', '.join(preference.targets)}" if tier else "Company tier unknown; no tier match claimed"
            elif factor == "seniority":
                seniority = metadata(job).get("seniority") or job.get("seniority")
                matches = [t for t in preference.targets if contains(job.get("title", "") + " " + job.get("description", ""), t)]
                value = float(seniority in preference.targets or bool(matches))
                note = f"Requested seniority evidenced by {seniority or ', '.join(matches)}" if value else "Requested seniority is not evidenced by the posting"
            else:
                value, note = signals[factor], evidence[factor]
            signals[factor] = value
            weighted += preference.weight * value
            total_weight += preference.weight
            factor_notes.append({"factor": factor, "value": round(value, 4), "weight": preference.weight,
                                 "query_evidence": preference.evidence, "evidence": note})
            if value < 0.5:
                weak.append(factor)
        baseline = signals["resume_match"]
        score = (0.65 * baseline + 0.35 * weighted / total_weight) if total_weight else baseline
        adjustment = 0.0
        if personalized_weights:
            adjustment = max(-0.15, min(0.15, sum(personalized_weights.get(k, 0) * v for k, v in signals.items())))
        fit_score = round(100 * max(0.0, min(1.0, score + adjustment)), 1)
        notes = [evidence["resume_match"]] + [n["evidence"] for n in factor_notes]
        if weak:
            notes.append("Included despite weak or unknown soft-preference matches: " + ", ".join(weak) + ". Hard filters remain satisfied.")
        if adjustment:
            notes.append(f"Your logged outcomes adjust the fit score by {adjustment * 100:+.1f} points.")
        ranked.append({**job, "fit_score": fit_score, "layer1_score": round(score * 100, 1),
                       "personalization_adjustment": round(adjustment * 100, 1),
                       "explanation": " ".join(notes), "factors": factor_notes,
                       "scoring_signals": signals, "weak_preferences": weak})
    ranked.sort(key=lambda row: (-row["fit_score"], str(row.get("job_id") or row.get("url") or row.get("id"))))
    relaxed = sorted({factor for row in ranked for factor in row["weak_preferences"]})
    if not ranked:
        note = "No retrieved jobs satisfy every hard filter. Hard filters were preserved; change the query or add sources to search more broadly."
    elif relaxed:
        note = "Some soft preferences have weak or unknown matches. These jobs remain visible with lower fit scores; hard filters were preserved."
    else:
        note = "All results satisfy hard filters and are ranked by evidenced fit."
    return {"jobs": ranked, "relaxation_note": note, "excluded": excluded,
            "personalized": bool(personalized_weights), "score_notice": "Fit scores indicate content match, not interview or offer probability."}


def rank_for_eval(*, query_spec, jobs, profile, as_of):
    return [row["job_id"] for row in rank_jobs(query_spec, jobs, profile, as_of=as_of)["jobs"]]

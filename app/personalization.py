"""Small, deterministic per-user correction learned only from logged outcomes."""

from hashlib import sha256
import json

import numpy as np
from sqlmodel import Session, select

from app.config import get_settings
from app.models import Application, JobPosting, PersonalizationConsent, ScoringWeights, utcnow

FEATURES = ("resume_match", "project_domain_similarity", "resume_company_affinity", "career_growth",
            "tech_overlap", "recency", "tier_high", "tier_mid", "tier_low", "seniority_intern", "seniority_junior")
POSITIVE = {"interview", "offer"}


def consent_enabled(session: Session, user_id: int = 1) -> bool:
    consent = session.exec(select(PersonalizationConsent).where(PersonalizationConsent.user_id == user_id)).first()
    return bool(consent and consent.enabled)


def set_consent(session: Session, enabled: bool, user_id: int = 1) -> dict:
    consent = session.exec(select(PersonalizationConsent).where(PersonalizationConsent.user_id == user_id)).first()
    if consent is None:
        consent = PersonalizationConsent(user_id=user_id)
    consent.enabled, consent.updated_at = enabled, utcnow()
    session.add(consent)
    if not enabled:
        current = session.exec(select(ScoringWeights).where(ScoringWeights.user_id == user_id)).first()
        if current:
            session.delete(current)
    session.commit()
    return recalibrate(session, user_id)


def training_rows(session: Session, user_id: int = 1) -> list[Application]:
    return list(session.exec(select(Application).join(JobPosting).where(
        JobPosting.user_id == user_id, Application.applied_at.is_not(None),
        Application.outcome.in_(["interview", "offer", "rejected", "no_response"])
    ).order_by(Application.id)).all())


def digest(rows):
    return sha256(json.dumps([(r.id, r.outcome, r.scoring_signals) for r in rows], sort_keys=True).encode()).hexdigest()


def recalibrate(session: Session, user_id: int = 1, *, force=False) -> dict:
    rows = training_rows(session, user_id)
    minimum = get_settings().personalization_min_outcomes
    if not consent_enabled(session, user_id):
        return {"active": False, "enabled": False, "outcome_count": len(rows), "minimum_outcomes": minimum,
                "weights": {}, "reason": "Local learning is off. Opt in to train scoring weights from your logged outcomes."}
    current = session.exec(select(ScoringWeights).where(ScoringWeights.user_id == user_id)).first()
    checksum = digest(rows)
    if len(rows) < minimum:
        if current:
            session.delete(current)
            session.commit()
        return {"active": False, "enabled": True, "outcome_count": len(rows), "minimum_outcomes": minimum,
                "weights": {}, "reason": "Cold start: ranking uses Layer 1 only"}
    if current and not force:
        changed_existing = len(rows) < current.outcome_count or digest(rows[:current.outcome_count]) != current.training_digest
        due = len(rows) - current.outcome_count >= get_settings().personalization_recalibrate_every
        if not due and not changed_existing:
            return describe(current, len(rows), minimum)
    x = np.array([[min(1.0, max(0.0, r.scoring_signals.get(name, 0))) for name in FEATURES] for r in rows], dtype=float)
    y = np.array([float(r.outcome in POSITIVE) for r in rows])
    coefficients = np.zeros(len(FEATURES))
    bias = 0.0
    # Regularized batch logistic regression; reproducible, small-data friendly.
    for _ in range(250):
        predictions = 1 / (1 + np.exp(-np.clip(x @ coefficients + bias, -20, 20)))
        error = predictions - y
        coefficients -= .15 * (x.T @ error / len(rows) + .4 * coefficients)
        bias -= .15 * float(error.mean())
    learned = {name: round(float(np.clip(coefficient * .15, -.12, .12)), 6)
               for name, coefficient in zip(FEATURES, coefficients)}
    if current is None:
        current = ScoringWeights(user_id=user_id)
    current.weights, current.outcome_count = learned, len(rows)
    current.training_digest, current.last_recalibrated_at = checksum, utcnow()
    session.add(current)
    session.commit()
    session.refresh(current)
    return describe(current, len(rows), minimum)


def describe(current, count, minimum):
    return {"active": True, "enabled": True, "outcome_count": count, "trained_outcome_count": current.outcome_count,
            "minimum_outcomes": minimum, "weights": current.weights,
            "last_recalibrated_at": current.last_recalibrated_at.isoformat(),
            "reason": "Bounded adjustments from this user's logged outcomes; not a hiring probability"}


def get_weights(session: Session, user_id: int = 1) -> dict:
    if not consent_enabled(session, user_id):
        return {}
    current = session.exec(select(ScoringWeights).where(ScoringWeights.user_id == user_id)).first()
    if len(training_rows(session, user_id)) < get_settings().personalization_min_outcomes:
        return {}
    return current.weights if current else {}

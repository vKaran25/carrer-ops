"""Persistent local workspace. Multi-account authentication belongs to Phase 4."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str | None = None
    auth_provider: str = "local"
    tier: str = "free"
    created_at: datetime = Field(default_factory=utcnow)


class ResumeProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    filename: str
    raw_resume_text: str
    latex_source: str | None = None
    structured_facts: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utcnow)


class JobPosting(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "url"),)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    company: str
    location: str = "Not specified"
    url: str
    snippet: str = ""
    description: str = ""
    source: str
    found_at: datetime = Field(default_factory=utcnow)
    posted_at: datetime | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobposting.id", unique=True)
    status: str = "found"
    tailored_resume: str | None = None
    tailored_cover_letter: str | None = None
    draft: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    critique: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    curated_resume: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    fit_score: float | None = None
    explanation: str = ""
    scoring_signals: dict[str, float] = Field(default_factory=dict, sa_column=Column(JSON))
    applied_at: datetime | None = None
    outcome: str | None = None
    outcome_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utcnow)


class UserAction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    application_id: int = Field(foreign_key="application.id")
    action: str
    previous_status: str
    new_status: str
    created_at: datetime = Field(default_factory=utcnow)


class InterviewResearchCache(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    company: str = Field(unique=True, index=True)
    result: dict[str, Any] = Field(sa_column=Column(JSON))
    researched_at: datetime = Field(default_factory=utcnow)


class MemoryFact(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "source", "source_key"),)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    fact_text: str
    fact_type: str
    source: str
    source_key: str
    updated_at: datetime = Field(default_factory=utcnow)


class ScoringWeights(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    weights: dict[str, float] = Field(default_factory=dict, sa_column=Column(JSON))
    last_recalibrated_at: datetime = Field(default_factory=utcnow)
    outcome_count: int = 0
    training_digest: str = ""


class PersonalizationConsent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    enabled: bool = False
    updated_at: datetime = Field(default_factory=utcnow)


class EvalRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=utcnow)
    test_case_id: str
    score: float
    notes: str

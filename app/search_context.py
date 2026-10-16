from app.workspace import commit as commit_workspace
"""Structured search memory; never turn conversation or JDs into resume facts."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.llm import call_tool, LLMError
from app.models import SearchContext, SearchPreferences, utcnow
from app.query_parser import QuerySpec

ContextField = Literal['recency_days', 'tech_stack_keywords', 'role_keywords', 'industries',
                       'company_names', 'locations', 'work_modes', 'location_scope', 'soft_preferences']


class ClearField(BaseModel):
    model_config = ConfigDict(extra='forbid')
    field: ContextField
    evidence: str = Field(min_length=1)


class IntentResolution(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['new', 'follow_up', 'clarify']
    clear_fields: list[ClearField] = Field(default_factory=list)
    clarification: str | None = None


def empty_spec() -> QuerySpec:
    return QuerySpec(hard_filters={}, soft_preferences=[])


def context_row(session: Session, user_id: int, *, create=False):
    row = session.exec(select(SearchContext).where(SearchContext.user_id == user_id)).first()
    if row is None and create:
        try:
            with session.begin_nested():
                row = SearchContext(user_id=user_id)
                session.add(row)
                session.flush()
            commit_workspace(session)
        except IntegrityError:
            row = session.exec(select(SearchContext).where(SearchContext.user_id == user_id)).one()
    return row


def preferences_row(session: Session, user_id: int):
    return session.exec(select(SearchPreferences).where(SearchPreferences.user_id == user_id)).first()


def merge(base: QuerySpec, patch: QuerySpec, cleared: list[str] = ()) -> QuerySpec:
    data = base.model_dump()
    for field in cleared:
        if field == 'location_scope':
            data[field] = None
        elif field == 'soft_preferences':
            data[field] = []
        else:
            data['hard_filters'][field] = None if field == 'recency_days' else []
    for field, value in patch.hard_filters.model_dump().items():
        if value is not None and value != []:
            data['hard_filters'][field] = value
    if patch.hard_filters.locations:
        data['location_scope'] = None
    if patch.location_scope:
        data['location_scope'] = patch.location_scope.model_dump()
        # A new nearby scope replaces a previous city filter. A separately
        # stated country restriction in this message remains mandatory.
        data['hard_filters']['locations'] = patch.hard_filters.locations
    factors = {p['factor']: p for p in data['soft_preferences']}
    factors.update({p.factor: p.model_dump() for p in patch.soft_preferences})
    data['soft_preferences'] = list(factors.values())
    return QuerySpec.model_validate(data)


def effective_spec(session: Session, user_id: int, intent: dict | None, cleared: list[str]) -> QuerySpec:
    prefs = preferences_row(session, user_id)
    return merge(QuerySpec.model_validate(prefs.spec) if prefs else empty_spec(),
                 QuerySpec.model_validate(intent) if intent else empty_spec(), cleared)


def describe(spec: QuerySpec) -> list[str]:
    labels = []
    for name, value in spec.hard_filters.model_dump().items():
        if value:
            labels.append(f"{name.replace('_', ' ')}: {', '.join(value) if isinstance(value, list) else value}")
    if spec.location_scope:
        s = spec.location_scope
        labels.append(f"{'Prefer near' if s.mode == 'preferred' else 'Require within'} {s.place}: {s.radius_km:g} km")
    labels += [f"Prefer {p.factor.replace('_', ' ')}" + (': ' + ', '.join(p.targets) if p.targets else '') for p in spec.soft_preferences]
    return labels or ['Resume relevance; no additional filters']


def view(session: Session, user_id: int, digest: str | None) -> dict:
    row = context_row(session, user_id)
    prefs = preferences_row(session, user_id)
    spec = effective_spec(session, user_id, row.intent if row else None, row.cleared_fields if row else [])
    return {'active': bool(row and row.intent is not None), 'last_query': row.query if row else '',
            'revision': row.revision if row else 0, 'resume_changed': bool(row and row.intent and row.resume_digest != digest),
            'effective_spec': spec.model_dump(), 'effective_filters': describe(spec),
            'preferences': {'query': prefs.query, 'spec': prefs.spec} if prefs else None}


async def prepare(session: Session, user_id: int, query: str, parse, *, keyword: QuerySpec | None = None) -> dict:
    row = context_row(session, user_id, create=True)
    # Snapshot before awaits: other searches, reset and preference edits can
    # advance the revision. An older run must not overwrite that newer state.
    revision, prior = row.revision, row.intent
    previous_clears = list(row.cleared_fields)
    if keyword is not None or not query.strip():
        resolution = IntentResolution(kind='new')
        patch = keyword or empty_spec()
    else:
        resolution = await call_tool(IntentResolution, system=(
            'Classify a job-search message relative to the last successful explicit intent. '
            'Return new for an independent request; follow_up for same/again/these roles, location/role changes or continuation. '
            'Return clarify for ambiguous references, no prior intent for a follow-up, contradictions or non-search conversation. '
            'Do not guess omitted roles, qualifications, locations or permanent preferences. '
            'clear_fields is only for explicit removal of constraints: e.g. anywhere clears locations AND location_scope, '
            'any posting date clears recency_days; cite the exact current-message text supporting each removal. '
            'Any work arrangement clears work_modes; changing geography alone preserves a required work arrangement. '
            'A changed field is normally handled by the separate parser, not by clearing unrelated constraints. '
            'A follow-up preserves all other constraints. Never weaken a prior hard constraint without explicit user evidence. '
            'Clarification should be one concise question, with no claims about the resume.'),
            data={'message': query, 'previous_explicit_intent': prior})
        if resolution.kind == 'clarify' or (resolution.kind == 'follow_up' and prior is None):
            raise ValueError(resolution.clarification or 'Which previous role or filters should this search use? Enter a complete search or start a new one.')
        if any(c.evidence not in query for c in resolution.clear_fields):
            raise LLMError('Search context contained unsupported removal evidence. Rephrase the requested change.')
        patch = await parse(query)
    clears = list(dict.fromkeys((previous_clears if resolution.kind == 'follow_up' else []) + [c.field for c in resolution.clear_fields]))
    intent = merge(QuerySpec.model_validate(prior) if resolution.kind == 'follow_up' else empty_spec(), patch, [c.field for c in resolution.clear_fields])
    effective = effective_spec(session, user_id, intent.model_dump(), clears)
    return {'query_spec': effective.model_dump(), 'context_update': {'revision': revision,
            'intent': intent.model_dump(), 'cleared_fields': clears, 'query': query},
            'context_info': {'kind': resolution.kind, 'effective_filters': describe(effective),
                             'saved_preferences_applied': bool(preferences_row(session, user_id))}}


def commit_success(session: Session, user_id: int, prepared: dict, digest: str | None, turn_id: int) -> bool:
    """Caller commits this CAS update together with its successful chat turn."""
    result = session.exec(update(SearchContext).where(SearchContext.user_id == user_id,
                          SearchContext.revision == prepared['revision']).values(
        intent=prepared['intent'], cleared_fields=prepared['cleared_fields'], query=prepared['query'],
        resume_digest=digest, last_turn_id=turn_id, revision=prepared['revision']+1, updated_at=utcnow()))
    return result.rowcount == 1


def reset(session: Session, user_id: int):
    context_row(session, user_id, create=True)
    session.exec(update(SearchContext).where(SearchContext.user_id == user_id).values(
        intent=None, query='', cleared_fields=[], last_turn_id=None, resume_digest=None,
        revision=SearchContext.revision + 1, updated_at=utcnow()))
    commit_workspace(session)


def save_preferences(session: Session, user_id: int, query: str, spec: QuerySpec | None):
    context_row(session, user_id, create=True)
    row = preferences_row(session, user_id)
    if spec is None:
        if row:
            session.delete(row)
    else:
        row = row or SearchPreferences(user_id=user_id, query=query, spec=spec.model_dump())
        row.query, row.spec, row.updated_at = query, spec.model_dump(), utcnow()
        session.add(row)
    session.exec(update(SearchContext).where(SearchContext.user_id == user_id).values(
        revision=SearchContext.revision + 1, updated_at=utcnow()))
    commit_workspace(session)

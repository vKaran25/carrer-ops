"""Atomic UTC-day operational caps, independent of any paid/free feature tiers."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session

from app.config import get_settings
from app.models import DailyUsage

owner: ContextVar[int | None] = ContextVar('budget_owner', default=None)
storage: ContextVar[object | None] = ContextVar('budget_storage', default=None)


@contextmanager
def account_context(user_id: int, database_engine=None):
    token = owner.set(user_id)
    binding = storage.set(database_engine)
    try:
        yield
    finally:
        storage.reset(binding)
        owner.reset(token)


def reserve(operation: str, *, session: Session | None = None, user_id: int | None = None):
    settings = get_settings()
    # Standalone offline fixtures/explicit benchmark tools do not consume account caps.
    # Authenticated API requests and workers always bind an owner context.
    actor = user_id if user_id is not None else owner.get()
    if actor is None:
        return
    caps = {'search': settings.search_daily_global_limit, 'model': settings.model_daily_global_limit,
            'web': settings.web_daily_global_limit}
    scopes = [('global', caps[operation])]
    if operation == 'search':
        scopes.append((f'user:{actor}', settings.search_daily_user_limit))
    day = datetime.now(timezone.utc).date().isoformat()
    def allocate(active: Session):
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert = pg_insert if active.bind.dialect.name == 'postgresql' else sqlite_insert
        for scope, limit in scopes:
            statement = insert(DailyUsage).values(scope=scope, day=day, operation=operation, count=1)
            statement = statement.on_conflict_do_update(
                index_elements=['scope', 'day', 'operation'], set_={'count': DailyUsage.count + 1},
                where=DailyUsage.count < limit).returning(DailyUsage.id)
            if limit < 1 or active.execute(statement).scalar() is None:
                raise HTTPException(429, f'The daily {operation} safety limit has been reached. Try again after 00:00 UTC.')
    if session is not None:
        allocate(session)
        return
    from app.db import engine
    with Session(storage.get() or engine) as active:
        allocate(active)
        active.commit()

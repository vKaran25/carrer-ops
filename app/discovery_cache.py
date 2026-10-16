"""A ten-minute PostgreSQL cache of public search responses, not job descriptions."""
from datetime import timedelta
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from app.budgets import owner, storage
from app.config import get_settings
from app.models import DiscoveryCache, utcnow


def enabled():
    # Standalone live benchmark tools must not open the application database.
    return owner.get() is not None and storage.get() is not None and storage.get().dialect.name == 'postgresql'


def read(key: str) -> list[dict] | None:
    if not enabled():
        return None
    with Session(storage.get()) as session:
        row = session.exec(select(DiscoveryCache).where(DiscoveryCache.key == key,
                                                       DiscoveryCache.expires_at > utcnow())).first()
        return [dict(item) for item in row.results] if row else None


def write(key: str, results: list[dict]):
    if not enabled():
        return
    public = [{name: str(item.get(name) or '')[:8000] for name in ('url', 'title', 'content')} for item in results]
    with Session(storage.get()) as session:
        session.exec(delete(DiscoveryCache).where(DiscoveryCache.expires_at <= utcnow()))
        statement = insert(DiscoveryCache).values(key=key, results=public, expires_at=utcnow()+timedelta(minutes=10))
        session.execute(statement.on_conflict_do_update(index_elements=['key'], set_={
            'results': statement.excluded.results, 'expires_at': statement.excluded.expires_at}))
        session.commit()

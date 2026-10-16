"""Request/worker ownership, bound by authentication rather than request bodies."""
from sqlmodel import Session
from app.config import get_settings


def user_id(session: Session) -> int:
    owner = session.info.get('user_id')
    if owner is not None:
        return int(owner)
    settings = get_settings()
    if settings.auth_mode == 'local' and settings.environment == 'development':
        return 1
    raise PermissionError('An authenticated workspace is required.')


def commit(session: Session):
    if session.info.get('defer_commit'):
        session.flush()
    else:
        session.commit()

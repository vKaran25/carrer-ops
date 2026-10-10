from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import get_settings
from app.models import User


def make_engine(url: str):
    if url.startswith("sqlite:/// "):
        raise ValueError("Invalid database URL")
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


engine = make_engine(get_settings().database_url)


def init_db(database_engine=None):
    active = database_engine or engine
    SQLModel.metadata.create_all(active)
    if active.dialect.name == "sqlite":
        with active.begin() as connection:
            connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS prohibit_applied_insert
                BEFORE INSERT ON application WHEN NEW.status = 'applied'
                BEGIN SELECT RAISE(ABORT, 'Applied requires a logged user action'); END""")
            connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS require_applied_action
                BEFORE UPDATE OF status ON application WHEN NEW.status = 'applied' AND OLD.status != 'applied'
                AND NOT EXISTS (SELECT 1 FROM useraction WHERE application_id = NEW.id
                AND action = 'mark_applied' AND new_status = 'applied' AND previous_status = OLD.status)
                BEGIN SELECT RAISE(ABORT, 'Applied requires a logged user action'); END""")
    with Session(active) as session:
        if session.get(User, 1) is None:
            session.add(User(id=1))
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session


def get_profile(session: Session, user_id: int = 1):
    from app.models import ResumeProfile
    return session.exec(select(ResumeProfile).where(ResumeProfile.user_id == user_id)).first()

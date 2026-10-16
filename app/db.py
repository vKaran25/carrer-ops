from pathlib import Path
import re

from sqlalchemy import event
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import get_settings
from app.models import Application, JobPosting, User, UserAction
from app.auth import authenticate, bind_workspace, Principal


def make_engine(url: str):
    if url.startswith("sqlite:/// "):
        raise ValueError("Invalid database URL")
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    if url.startswith(('postgres://', 'postgresql://')):
        url = re.sub(r'^postgres(?:ql)?://', 'postgresql+psycopg://', url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith('postgresql'):
        schema = get_settings().database_schema
        if not re.fullmatch(r'career_ops(?:_[a-z0-9_]+)?', schema):
            raise ValueError('Use a private DATABASE_SCHEMA named career_ops or career_ops_<suffix>.')
        connect_args = {'sslmode': 'require', 'connect_timeout': 10}
        certificate = Path(get_settings().database_ssl_root_cert)
        if certificate.is_file():
            connect_args.update(sslmode='verify-full', sslrootcert=str(certificate.resolve()))
        elif get_settings().environment == 'production':
            raise ValueError('Production PostgreSQL needs the Supabase CA file at DATABASE_SSL_ROOT_CERT.')
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, hide_parameters=True)
    if url.startswith('postgresql'):
        @event.listens_for(engine, 'connect')
        def private_schema(connection, _):
            prior = connection.autocommit
            connection.autocommit = True
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f'SET search_path TO "{schema}"')
                    cursor.execute("SET TIME ZONE 'UTC'")
            finally:
                connection.autocommit = prior
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


engine = make_engine(get_settings().database_url)


def init_db(database_engine=None):
    active = database_engine or engine
    if active.dialect.name != 'sqlite':
        # Production schema changes run through the operator's Alembic command.
        from sqlalchemy import text
        with active.connect() as connection:
            revision = connection.execute(text('SELECT version_num FROM alembic_version')).scalar()
            if revision != '0001_core':
                raise RuntimeError('Database migrations are not current. Run alembic upgrade head.')
        return
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
        # User-approved migration: keep old automatically saved Found jobs in
        # Interested, while preserving every later stage and application audit.
        for application in session.exec(select(Application).join(JobPosting).where(
                Application.status.in_(["found", "tailored"]))).all():
            job = session.get(JobPosting, application.job_id)
            session.add(UserAction(user_id=job.user_id, application_id=application.id,
                                   action=f"migrate_{application.status}_to_interested",
                                   previous_status=application.status, new_status="interested"))
            application.status = "interested"
            session.add(application)
        session.commit()


async def get_session(principal: Principal = Depends(authenticate)):
    with Session(engine) as session:
        bind_workspace(session, principal)
        from app.budgets import account_context
        with account_context(session.info['user_id'], engine):
            yield session


def get_profile(session: Session, user_id: int | None = None):
    from app.models import ResumeProfile
    from app.workspace import user_id as owner
    user_id = owner(session) if user_id is None else user_id
    return session.exec(select(ResumeProfile).where(ResumeProfile.user_id == user_id)
                        .execution_options(populate_existing=True)).first()

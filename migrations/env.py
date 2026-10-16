"""Explicit schema deployment; no URL or credential is written into Alembic config."""
from alembic import context
from sqlalchemy import text
from app.config import get_settings
from app.db import make_engine


def run_migrations():
    settings = get_settings()
    url = settings.supabase_database_url or settings.database_url
    if not url.startswith(('postgresql', 'postgres://')):
        raise RuntimeError('Set SUPABASE_DATABASE_URL to the Supabase session-pooler URL. SQLite is not migrated.')
    if context.is_offline_mode():
        raise RuntimeError('Use the connected operator migration command; offline mode cannot protect schema setup.')
    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            schema = settings.database_schema  # validated by make_engine
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            connection.commit()
            context.configure(connection=connection, version_table_schema=schema, transactional_ddl=True)
            with context.begin_transaction():
                context.run_migrations()
                # The private application schema is not a browser/PostgREST API.
                connection.execute(text(f'REVOKE ALL ON SCHEMA "{schema}" FROM PUBLIC'))
                connection.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA "{schema}" FROM PUBLIC'))
                for role in ('anon', 'authenticated'):
                    if connection.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:role'), {'role': role}).scalar():
                        connection.execute(text(f'REVOKE ALL ON SCHEMA "{schema}" FROM "{role}"'))
                        connection.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA "{schema}" FROM "{role}"'))
                connection.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" REVOKE ALL ON TABLES FROM PUBLIC'))
    finally:
        engine.dispose()


run_migrations()

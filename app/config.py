from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Backend config, loaded from environment variables / project .env."""

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), ".env"),
        extra="ignore",
    )

    # All LLM calls go through OpenRouter; the chosen model must support tool calling.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = ""
    tavily_api_key: str = ""
    web_search_max_queries: int = 3
    web_search_max_pages: int = 8

    frontend_origin: str = "http://localhost:5173"
    environment: Literal['development', 'production'] = 'development'
    auth_mode: Literal['local', 'supabase'] = 'local'
    supabase_url: str = ''
    supabase_publishable_key: str = ''
    supabase_secret_key: str = ''
    database_schema: str = 'career_ops'
    database_ssl_root_cert: str = str(ROOT_DIR / 'data/supabase/prod-ca-2021.crt')
    supabase_database_url: str = ''
    search_daily_user_limit: int = 5
    search_daily_global_limit: int = 20
    model_daily_global_limit: int = 90
    web_daily_global_limit: int = 60
    search_timeout_seconds: int = 600
    database_url: str = "sqlite:///./data/career_ops.db"
    artifact_dir: str = "./data/artifacts"
    sources_file: str = "./data/sources.json"
    geonames_db: str = str(ROOT_DIR / "data/geonames/geography.sqlite")
    max_upload_bytes: int = 5_000_000
    research_cache_days: int = 60
    personalization_min_outcomes: int = 6
    personalization_recalibrate_every: int = 5
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    latex_compile_timeout_seconds: int = 240

    def validate_runtime(self):
        if self.environment == 'production' and (self.auth_mode != 'supabase' or not self.database_url.startswith('postgresql')):
            raise ValueError('Production requires Supabase authentication and PostgreSQL.')
        if self.auth_mode == 'supabase':
            from urllib.parse import urlparse
            url = urlparse(self.supabase_url)
            if url.scheme != 'https' or not url.hostname or url.username or url.query or url.fragment:
                raise ValueError('Configure an HTTPS SUPABASE_URL without credentials or query parameters.')
            if not self.supabase_publishable_key:
                raise ValueError('Configure SUPABASE_PUBLISHABLE_KEY.')
            if not self.supabase_publishable_key.startswith('sb_publishable_'):
                import jwt
                try:
                    role = jwt.decode(self.supabase_publishable_key, options={'verify_signature': False}).get('role')
                except jwt.PyJWTError:
                    role = None
                if role != 'anon':
                    raise ValueError('SUPABASE_PUBLISHABLE_KEY must be a publishable/anon key, never a secret/service-role key.')
            if not self.database_url.startswith('postgresql'):
                raise ValueError('Supabase mode requires PostgreSQL; local SQLite data is not imported.')

    @property
    def free_model_selected(self) -> bool:
        return self.openrouter_model.endswith(":free") or self.openrouter_model == "openrouter/free"

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()


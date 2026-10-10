from functools import lru_cache
from pathlib import Path

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

    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./data/career_ops.db"
    artifact_dir: str = "./data/artifacts"
    sources_file: str = "./data/sources.json"
    max_upload_bytes: int = 5_000_000
    research_cache_days: int = 60
    personalization_min_outcomes: int = 6
    personalization_recalibrate_every: int = 5
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    latex_compile_timeout_seconds: int = 240

    @property
    def free_model_selected(self) -> bool:
        return self.openrouter_model.endswith(":free") or self.openrouter_model == "openrouter/free"

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()


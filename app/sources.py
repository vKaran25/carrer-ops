"""Explicit source registry. Industry/tier metadata is supplied, never guessed."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import get_settings


class JobSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str = Field(min_length=1, max_length=120)
    url: str
    enabled: bool = True
    provider: Literal["auto", "greenhouse", "lever", "workday", "static"] = "auto"
    industry: str | None = None
    company_tier: Literal["high", "mid", "low"] | None = None

    @model_validator(mode="after")
    def public_url(self):
        parts = urlparse(self.url)
        if parts.scheme not in ("https", "http") or not parts.hostname or parts.username:
            raise ValueError("Provide a public HTTP(S) careers URL")
        if parts.hostname in ("localhost", "localhost.localdomain") or parts.hostname.endswith(".local"):
            raise ValueError("Sources must be public career pages")
        return self


def load_sources() -> list[JobSource]:
    path = Path(get_settings().sources_file)
    if not path.exists():
        path = Path(__file__).parent / "default_sources.json"
    return [JobSource.model_validate(item) for item in json.loads(path.read_text())]


def save_sources(items: list[JobSource]):
    if len(items) > 40:
        raise ValueError("Configure at most 40 career sources")
    names = [s.company.casefold() for s in items]
    if len(names) != len(set(names)):
        raise ValueError("Use one source per company")
    path = Path(get_settings().sources_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps([s.model_dump() for s in items], indent=2))
    temporary.replace(path)


def known_ats(source: JobSource) -> str | None:
    host = urlparse(source.url).hostname or ""
    if source.provider != "auto":
        return None if source.provider == "static" else source.provider
    if host == "greenhouse.io" or host.endswith(".greenhouse.io"):
        return "greenhouse"
    if host == "lever.co" or host.endswith(".lever.co"):
        return "lever"
    if host == "myworkdayjobs.com" or host.endswith(".myworkdayjobs.com"):
        return "workday"
    return None


def ats_board_token(url: str, provider: str) -> str:
    """Read employer identity from public board or vendor API URL shapes."""
    path = [part for part in urlparse(url).path.split('/') if part]
    if provider == 'greenhouse' and 'boards' in path:
        path = path[path.index('boards') + 1:]
    elif provider == 'lever' and path[:2] == ['v0', 'postings']:
        path = path[2:]
    if not path or path[0] in ('.', '..') or not re.fullmatch(r'[\w.-]+', path[0], re.ASCII):
        raise ValueError(f'{provider.title()} source needs an employer board token')
    return path[0]

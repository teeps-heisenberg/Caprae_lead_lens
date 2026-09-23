"""Runtime configuration. Every value has a local default so the app runs with no .env."""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "sqlite:///./leadlens.db"
    # auto: bundled fixture site if one exists for the domain, otherwise the real web. fixture / live force one.
    enrich_mode: Literal["auto", "fixture", "live"] = "auto"
    llm_provider: Literal["none", "gemini"] = "none"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cache_ttl_days: int = 7
    fetch_timeout_s: float = 8.0
    fetch_concurrency: int = 6
    fixtures_dir: Path = BACKEND_DIR / "fixtures" / "sites"
    data_dir: Path = REPO_DIR / "data"
    score_config_path: Path = BACKEND_DIR / "score_config.json"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

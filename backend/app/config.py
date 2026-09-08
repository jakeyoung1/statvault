"""Application configuration loaded from environment / .env."""
from __future__ import annotations

import getpass

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    # Homebrew Postgres uses the current OS user as superuser with no password.
    user = getpass.getuser()
    return f"postgresql+psycopg2://{user}@localhost:5432/statvault"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = _default_database_url()
    default_monthly_limit: int = 1000
    frontend_origin: str = "http://localhost:5173"


settings = Settings()

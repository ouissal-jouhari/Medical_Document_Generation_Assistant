"""Configuration : tout vient de l'environnement, aucun secret dans le code (N-05)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_env: str = "dev"
    database_url: SecretStr = SecretStr("postgresql+psycopg://xeleron@localhost:5432/xeleron")
    log_dir: str = "logs"
    log_retention_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()

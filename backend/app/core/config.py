"""Configuration : tout vient de l'environnement, aucun secret dans le code (N-05)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_env: str = "dev"
    # Connexion de l'application : rôle xeleron_app (pas d'UPDATE/DELETE sur l'audit).
    database_url: SecretStr = SecretStr("postgresql+psycopg://xeleron_app@localhost:5432/xeleron")
    # Connexion des migrations : propriétaire de la base. Absente = database_url.
    migration_database_url: SecretStr | None = None
    log_dir: str = "logs"
    log_retention_days: int = 30
    # Fournisseur d'identité (Keycloak).
    oidc_issuer: str = "https://localhost/auth/realms/xeleron"
    oidc_jwks_url: str = "http://keycloak:8080/auth/realms/xeleron/protocol/openid-connect/certs"
    oidc_client_id: str = "xeleron-web"
    # Niveau d'authentification (claim acr) que Keycloak émet après le second facteur.
    oidc_required_acr: str = "2"
    # Superbills : stockage (volume chiffré par l'hôte), limite de taille, extraction.
    storage_dir: str = "storage"
    max_upload_bytes: int = 50 * 1024 * 1024
    docling_artifacts_path: str | None = None
    extraction_timeout_seconds: float = 300.0
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.8-flash"
    llm_fallback_models: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
    gemini_api_key: SecretStr = SecretStr("")
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "gpt-oss-20b"
    # Délai par appel LLM, et délai total d'une génération (tous modèles et tentatives confondus).
    llm_timeout_seconds: float = 90.0
    llm_total_timeout_seconds: float = 150.0
    template_dir: str = "app/templates"


@lru_cache
def get_settings() -> Settings:
    return Settings()

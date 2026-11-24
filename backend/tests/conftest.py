import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from app.adapters import models  # noqa: F401
from app.adapters.db import Base
from app.adapters.oidc import OidcIdentityProvider
from app.api.deps import get_clock, get_identity_provider, get_ocr_provider, get_session
from app.api.main import create_app
from app.core.config import get_settings
from app.domain.clock import FixedClock
from app.domain.values import OcrResult
from tests.helpers_auth import CLIENT_ID, ISSUER, MFA_ACR, FakeKeys, make_token, new_rsa_key

CANARY = "Zzyxq-Canari-Patient-7f3a91"


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    return tmp_path / "logs"


@pytest.fixture
def client(log_dir: Path) -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()


class SwitchableOcr:
    """OcrProvider de test : renvoie `text`, ou lève `error` si défini."""

    def __init__(self, text: str = "", pages: int = 1) -> None:
        self.text = text
        self.pages = pages
        self.error: Exception | None = None
        self.calls = 0

    def extract_text(self, content: bytes, content_type: str) -> OcrResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return OcrResult(text=self.text, pages=self.pages, engine="test")


@dataclass
class Api:
    app: FastAPI
    client: TestClient
    engine: Engine
    private_key: rsa.RSAPrivateKey
    keys: FakeKeys
    clock: FixedClock
    ocr: SwitchableOcr

    def token(self, **kwargs: object) -> str:
        return make_token(self.private_key, **kwargs)  # type: ignore[arg-type]

    def headers(self, **kwargs: object) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(**kwargs)}"}

    def session(self) -> Session:
        return sessionmaker(self.engine, expire_on_commit=False)()


@pytest.fixture
def api(log_dir: Path) -> Iterator[Api]:
    """Application avec identité factice signée et base SQLite en mémoire."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    private_key = new_rsa_key()
    keys = FakeKeys(private_key)
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    ocr = SwitchableOcr()
    provider = OidcIdentityProvider(ISSUER, CLIENT_ID, MFA_ACR, keys)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override_session() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_identity_provider] = lambda: provider
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[get_ocr_provider] = lambda: ocr
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield Api(app, test_client, engine, private_key, keys, clock, ocr)
    get_settings.cache_clear()


def require_postgres_url() -> str:
    """URL d'administration PostgreSQL pour les tests de droits de base (F-21)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    if os.environ.get("CI"):
        pytest.fail("TEST_DATABASE_URL est obligatoire en CI : test de droits non exécuté")
    pytest.skip("TEST_DATABASE_URL absent : test PostgreSQL ignoré en local")


BACKEND = Path(__file__).resolve().parents[1]
APP_PW = "app-test-pw"  # noqa: S105 - mot de passe de test, base jetable
PURGE_PW = "purge-test-pw"  # noqa: S105


@pytest.fixture
def migrated(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Base PostgreSQL jetable migrée par Alembic (droits réels des migrations)."""
    admin_url = require_postgres_url()
    name = f"xeleron_test_{uuid4().hex[:10]}"
    admin = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    base = make_url(admin_url)
    owner_url = base.set(database=name).render_as_string(hide_password=False)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", owner_url)
    monkeypatch.setenv("DATABASE_URL", owner_url)
    monkeypatch.setenv("APP_DB_PASSWORD", APP_PW)
    monkeypatch.setenv("PURGE_DB_PASSWORD", PURGE_PW)
    get_settings.cache_clear()
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(config, "head")
    urls = {
        "owner": owner_url,
        "app": base.set(database=name, username="xeleron_app", password=APP_PW).render_as_string(
            hide_password=False
        ),
        "purge": base.set(
            database=name, username="xeleron_purge", password=PURGE_PW
        ).render_as_string(hide_password=False),
    }
    yield urls
    get_settings.cache_clear()
    with admin.connect() as conn:
        conn.execute(sa.text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()

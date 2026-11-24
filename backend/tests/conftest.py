import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters import models  # noqa: F401
from app.adapters.db import Base
from app.adapters.oidc import OidcIdentityProvider
from app.api.deps import get_clock, get_identity_provider, get_session
from app.api.main import create_app
from app.core.config import get_settings
from app.domain.clock import FixedClock
from tests.helpers_auth import CLIENT_ID, ISSUER, MFA_ACR, FakeKeys, make_token, new_rsa_key

CANARY = "Zzyxq-Canari-Patient-7f3a91"


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    get_settings.cache_clear()
    return tmp_path / "logs"


@pytest.fixture
def client(log_dir: Path) -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()


@dataclass
class Api:
    app: FastAPI
    client: TestClient
    engine: Engine
    private_key: rsa.RSAPrivateKey
    keys: FakeKeys
    clock: FixedClock

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
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield Api(app, test_client, engine, private_key, keys, clock)
    get_settings.cache_clear()


def require_postgres_url() -> str:
    """URL d'administration PostgreSQL pour les tests de droits de base (F-21)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    if os.environ.get("CI"):
        pytest.fail("TEST_DATABASE_URL est obligatoire en CI : test de droits non exécuté")
    pytest.skip("TEST_DATABASE_URL absent : test PostgreSQL ignoré en local")

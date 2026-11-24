"""Dépendances d'API : session, horloge, identité. Toute route protégée dépend de
`require_permission`, qui s'appuie sur `get_current_user` (test de parcours des routes, F-02)."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db import make_engine
from app.adapters.models import User
from app.adapters.oidc import OidcIdentityProvider
from app.core.config import get_settings
from app.domain.auth import Permission, permissions_of
from app.domain.clock import Clock, SystemClock
from app.domain.errors import AuthenticationRequired, Forbidden, MfaRequired
from app.ports import IdentityProvider

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    display_name: str
    permissions: frozenset[Permission]


def get_clock() -> Clock:
    return SystemClock()


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    engine = make_engine(get_settings().database_url.get_secret_value())
    return sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with _session_factory()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@lru_cache
def get_identity_provider() -> IdentityProvider:
    settings = get_settings()
    return OidcIdentityProvider.from_jwks_url(
        settings.oidc_issuer,
        settings.oidc_jwks_url,
        settings.oidc_client_id,
        settings.oidc_required_acr,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    provider: IdentityProvider = Depends(get_identity_provider),
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> CurrentUser:
    if credentials is None:
        raise AuthenticationRequired
    identity = provider.verify_token(credentials.credentials)
    if not identity.mfa_verified:
        raise MfaRequired
    user = session.scalars(select(User).where(User.subject == identity.subject)).first()
    if user is None:
        user = User(
            subject=identity.subject, display_name=identity.display_name, created_at=clock.now()
        )
        session.add(user)
        session.flush()
    elif user.display_name != identity.display_name:
        user.display_name = identity.display_name
    return CurrentUser(
        id=user.id,
        display_name=user.display_name,
        permissions=permissions_of(identity.roles),
    )


def require_permission(permission: Permission) -> Callable[[CurrentUser], CurrentUser]:
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if permission not in user.permissions:
            raise Forbidden
        return user

    return dependency


ClinicianUser = Annotated[CurrentUser, Depends(require_permission(Permission.USE_DOCUMENTS))]

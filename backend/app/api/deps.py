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
from app.adapters.docling_converter import DoclingMarkdownConverter
from app.adapters.extraction import HybridOcrProvider
from app.adapters.icd_table import load_known_icd
from app.adapters.llm import GeminiLlmProvider, OllamaLlmProvider
from app.adapters.models import User
from app.adapters.oidc import OidcIdentityProvider
from app.adapters.storage import LocalFileStore
from app.adapters.templates import DocumentTemplate, load_templates
from app.core.config import get_settings
from app.domain.auth import Permission, permissions_of
from app.domain.clinic import ClinicProfile
from app.domain.clock import Clock, SystemClock
from app.domain.errors import AuthenticationRequired, Forbidden, MfaRequired
from app.ports import IdentityProvider, OcrProvider
from app.ports.llm import LlmProvider
from app.services.consultations import ConsultationService
from app.services.generation import GenerationService
from app.services.review import ReviewService

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


@lru_cache
def get_ocr_provider() -> OcrProvider:
    settings = get_settings()
    return HybridOcrProvider(
        DoclingMarkdownConverter(settings.docling_artifacts_path),
        settings.extraction_timeout_seconds,
    )


@lru_cache
def get_known_icd() -> frozenset[str]:
    return load_known_icd()


def get_file_store() -> LocalFileStore:
    return LocalFileStore(get_settings().storage_dir)


@lru_cache
def get_llm_provider() -> LlmProvider:
    settings = get_settings()
    if settings.llm_provider.lower() == "ollama":
        return OllamaLlmProvider(
            settings.ollama_base_url,
            settings.ollama_model,
            settings.llm_timeout_seconds,
        )
    return GeminiLlmProvider(
        settings.gemini_api_key.get_secret_value(),
        settings.llm_model,
        settings.llm_timeout_seconds,
        tuple(m.strip() for m in settings.llm_fallback_models.split(",") if m.strip()),
        total_timeout_seconds=settings.llm_total_timeout_seconds,
    )


@lru_cache
def get_templates() -> dict[str, DocumentTemplate]:
    return load_templates(get_settings().template_dir)


def get_consultation_service(
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    ocr: OcrProvider = Depends(get_ocr_provider),
    store: LocalFileStore = Depends(get_file_store),
    known_icd: frozenset[str] = Depends(get_known_icd),
) -> ConsultationService:
    return ConsultationService(
        session, clock, ocr, store, known_icd, get_settings().max_upload_bytes
    )


def get_generation_service(
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    llm: LlmProvider = Depends(get_llm_provider),
    templates: dict[str, DocumentTemplate] = Depends(get_templates),
) -> GenerationService:
    return GenerationService(session, clock, llm, templates)


def get_clinic_profile() -> ClinicProfile:
    """Coordonnées constantes de la clinique (H-01) : configuration seulement."""
    settings = get_settings()
    return ClinicProfile(
        name=settings.clinic_name,
        address=settings.clinic_address,
        city=settings.clinic_city,
        postal_code=settings.clinic_postal_code,
        phone=settings.clinic_phone,
        email=settings.clinic_email,
        website=settings.clinic_website,
    )


def get_review_service(
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    generation: GenerationService = Depends(get_generation_service),
    clinic: ClinicProfile = Depends(get_clinic_profile),
) -> ReviewService:
    return ReviewService(session, clock, generation, clinic)


ConsultationServiceDep = Annotated[ConsultationService, Depends(get_consultation_service)]
GenerationServiceDep = Annotated[GenerationService, Depends(get_generation_service)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]

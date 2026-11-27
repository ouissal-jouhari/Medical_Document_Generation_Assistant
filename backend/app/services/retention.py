"""Durées de conservation (N-10, L-02) avec horloge injectable.

- Consultation et ses données : 90 jours après la dernière approbation d'un de ses documents ;
  consultation jamais approuvée : 90 jours après sa dernière activité (P16).
- Audit sans donnée patient : 1 an, purgé par le rôle xeleron_purge (jamais le rôle applicatif).
- Logs techniques : 30 jours, par la rotation quotidienne des fichiers (app.core.logging).

Valeurs du MVP, remplacées au déploiement par celles de l'hôpital (configuration).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.adapters.audit import purge_audit_before
from app.adapters.models import Consultation, Document, DocumentVersion, DocumentVersionEvent
from app.adapters.storage import LocalFileStore
from app.domain.clock import Clock
from app.services.erasure import erase_consultation

# Acteur des purges automatiques : aucun utilisateur, identifiant nul réservé (ADR 0021).
SYSTEM_ACTOR = UUID(int=0)
PURGE_ACTION = "consultation_purged"


@dataclass(frozen=True)
class RetentionPolicy:
    consultation_days: int = 90
    audit_days: int = 365


def _latest(rows: Iterable[Row[UUID, datetime]]) -> dict[UUID, datetime]:
    return {key: value for key, value in rows if value is not None}


class RetentionService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        store: LocalFileStore,
        policy: RetentionPolicy | None = None,
    ) -> None:
        self._session = session
        self._clock = clock
        self._store = store
        self._policy = policy or RetentionPolicy()

    def reference_dates(self) -> dict[UUID, datetime]:
        """Repère de conservation par consultation : dernière approbation, sinon dernière
        activité (consultation, texte, documents, versions, marques)."""
        approvals = _latest(
            self._session.execute(
                select(Document.consultation_id, func.max(Document.approved_at)).group_by(
                    Document.consultation_id
                )
            )
        )
        activity: dict[UUID, datetime] = {}
        for consultation in self._session.scalars(select(Consultation)):
            dates = [consultation.updated_at, consultation.consultation_text_updated_at]
            activity[consultation.id] = _utc(max(d for d in dates if d is not None))
        statements = [
            select(Document.consultation_id, func.max(Document.created_at)).group_by(
                Document.consultation_id
            ),
            select(Document.consultation_id, func.max(DocumentVersion.created_at))
            .join(DocumentVersion, DocumentVersion.document_id == Document.id)
            .group_by(Document.consultation_id),
            select(Document.consultation_id, func.max(DocumentVersionEvent.occurred_at))
            .join(DocumentVersionEvent, DocumentVersionEvent.document_id == Document.id)
            .group_by(Document.consultation_id),
        ]
        for statement in statements:
            for key, value in _latest(self._session.execute(statement)).items():
                if key in activity:
                    activity[key] = max(activity[key], _utc(value))
        return {key: _utc(approvals.get(key, value)) for key, value in activity.items()}

    def purge_consultations(self) -> int:
        cutoff = self._clock.now() - timedelta(days=self._policy.consultation_days)
        expired = [key for key, value in self.reference_dates().items() if value < cutoff]
        for consultation_id in expired:
            consultation = self._session.get(Consultation, consultation_id)
            if consultation is not None:
                erase_consultation(
                    self._session,
                    self._store,
                    consultation,
                    SYSTEM_ACTOR,
                    PURGE_ACTION,
                    self._clock.now(),
                )
        return len(expired)

    def purge_audit(self, purge_session: Session) -> int:
        """Audit de plus d'un an supprimé avec la session du rôle de purge."""
        cutoff = self._clock.now() - timedelta(days=self._policy.audit_days)
        return purge_audit_before(purge_session, cutoff)


def _utc(value: datetime) -> datetime:
    """SQLite (tests) renvoie des dates sans fuseau : elles sont stockées en UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

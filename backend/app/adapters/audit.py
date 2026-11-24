"""Journal d'audit en ajout seul (F-20, F-21).

`record` ajoute l'événement dans la session de l'action : même transaction, donc l'action et
sa trace réussissent ou échouent ensemble. Aucune fonction de modification n'existe.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.adapters.models import AuditEventRow
from app.domain.audit import AuditAction, AuditEvent
from app.domain.clock import Clock


class SqlAuditLog:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def record(
        self,
        session: Session,
        actor_id: UUID,
        action: AuditAction,
        document_id: UUID | None = None,
        version: int | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor_id=actor_id,
            action=action,
            occurred_at=self._clock.now(),
            document_id=document_id,
            version=version,
        )
        session.add(
            AuditEventRow(
                occurred_at=event.occurred_at,
                actor_id=event.actor_id,
                action=event.action.value,
                document_id=event.document_id,
                version=event.version,
            )
        )
        return event


def purge_audit_before(purge_session: Session, cutoff: datetime) -> int:
    """Purge à 1 an (N-10). La session utilise le rôle xeleron_purge, jamais le rôle applicatif."""
    result = purge_session.execute(delete(AuditEventRow).where(AuditEventRow.occurred_at < cutoff))
    return int(result.rowcount or 0)  # type: ignore[attr-defined]

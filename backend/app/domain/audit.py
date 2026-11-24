"""Événements d'audit (F-20, F-21) : acteur, action, date, document et version."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AuditAction(StrEnum):
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLBACK = "rollback"
    EXPORTED = "exported"
    PROVENANCE_REPORT_GENERATED = "provenance_report_generated"


@dataclass(frozen=True)
class AuditEvent:
    actor_id: UUID
    action: AuditAction
    occurred_at: datetime
    document_id: UUID | None = None
    version: int | None = None

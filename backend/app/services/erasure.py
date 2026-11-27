"""Effacement complet d'une consultation (F-22, N-10), partagé par la suppression manuelle et la
purge de conservation.

Sont supprimés : fichier déposé, texte, données extraites, corrections, documents, versions,
marques et exports. Les exports PDF et rapports de provenance ne sont jamais stockés (rendus en
mémoire et téléchargés) et l'extraction ne laisse aucun fichier temporaire : il n'y a ni
fichier temporaire ni cache à effacer (ADR 0021). L'audit ne garde qu'une trace minimale :
acteur, action, date, sans identifiant de consultation ni donnée patient.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.models import (
    AuditEventRow,
    Consultation,
    ConsultationCorrection,
    Document,
    DocumentVersion,
    DocumentVersionEvent,
    Export,
)
from app.adapters.storage import LocalFileStore


def erase_consultation(
    session: Session,
    store: LocalFileStore,
    consultation: Consultation,
    actor_id: UUID,
    action: str,
    at: datetime,
) -> None:
    storage_key = consultation.storage_key
    documents = select(Document.id).where(Document.consultation_id == consultation.id)
    for child in (Export, DocumentVersionEvent, DocumentVersion):
        session.execute(delete(child).where(child.document_id.in_(documents)))
    session.execute(delete(Document).where(Document.consultation_id == consultation.id))
    session.execute(
        delete(ConsultationCorrection).where(
            ConsultationCorrection.consultation_id == consultation.id
        )
    )
    session.delete(consultation)
    session.add(AuditEventRow(occurred_at=at, actor_id=actor_id, action=action))
    session.flush()
    if storage_key:
        store.delete(storage_key)

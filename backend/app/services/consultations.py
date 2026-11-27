"""Cas d'usage du flux Uploaded -> Parsed -> Validated (F-03 à F-06).

L'accès aux données passe uniquement par AuthorScopedRepository : une consultation d'un autre
auteur est indiscernable d'une consultation inexistante (F-25).
"""

from collections.abc import Container
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.author_scoped import AuthorScopedRepository
from app.adapters.file_inspector import FileInfo, inspect_upload
from app.adapters.models import AuditEventRow, Consultation, ConsultationCorrection, Document
from app.adapters.storage import LocalFileStore
from app.domain.clock import Clock
from app.domain.consultation import ConsultationState
from app.domain.errors import NotFound, ValidationFailed, WrongState
from app.domain.superbill import (
    REQUIRED_FIELD_COUNT,
    Issue,
    SuperbillData,
    canonical,
    diff,
    from_dict,
    has_blocking_issue,
    missing_required,
    to_dict,
    validate,
)
from app.domain.superbill_parser import parse_superbill_text
from app.ports import OcrProvider

log = structlog.get_logger()


@dataclass(frozen=True)
class UploadOutcome:
    consultation: Consultation
    extraction: str  # "parsed" ou "failed"


class ConsultationService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        ocr: OcrProvider,
        store: LocalFileStore,
        known_icd: Container[str],
        max_bytes: int,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ocr = ocr
        self._store = store
        self._known_icd = known_icd
        self._max_bytes = max_bytes
        self._repo = AuthorScopedRepository(session, Consultation)

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    # -- lecture ---------------------------------------------------------------------------
    def list_for_author(self, author_id: UUID) -> list[Consultation]:
        return sorted(self._repo.list(author_id), key=lambda c: c.created_at, reverse=True)

    def get(self, author_id: UUID, consultation_id: UUID) -> Consultation:
        consultation = self._repo.get(consultation_id, author_id)
        if consultation is None:
            raise NotFound
        return consultation

    def issues(self, consultation: Consultation) -> list[Issue]:
        if consultation.data is None:
            return []
        return validate(from_dict(consultation.data), self._known_icd)

    def corrections(self, consultation: Consultation) -> list[ConsultationCorrection]:
        statement = (
            select(ConsultationCorrection)
            .where(ConsultationCorrection.consultation_id == consultation.id)
            .order_by(ConsultationCorrection.changed_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def delete(self, author_id: UUID, consultation_id: UUID) -> None:
        """F-22 : fichier, texte, documents, versions et corrections sont supprimés ; l'audit ne
        garde qu'une trace minimale (acteur, action, date), sans donnée patient."""
        consultation = self.get(author_id, consultation_id)
        storage_key = consultation.storage_key
        self._session.execute(delete(Document).where(Document.consultation_id == consultation.id))
        self._session.execute(
            delete(ConsultationCorrection).where(
                ConsultationCorrection.consultation_id == consultation.id
            )
        )
        self._session.delete(consultation)
        self._session.add(
            AuditEventRow(
                occurred_at=self._clock.now(), actor_id=author_id, action="consultation_deleted"
            )
        )
        self._session.flush()
        if storage_key:
            self._store.delete(storage_key)

    # -- dépôt et extraction ---------------------------------------------------------------
    def create(self, author_id: UUID, content: bytes, extension: str) -> UploadOutcome:
        info = inspect_upload(content, extension, self._max_bytes)  # refus : rien n'est créé
        extracted = self._extract(content, info)
        key = self._store.save(content)
        now = self._clock.now()
        consultation = Consultation(
            author_id=author_id,
            state=ConsultationState.UPLOADED.value,
            storage_key=key,
            file_kind=info.kind,
            file_size=len(content),
            extraction_failures=0,
            created_at=now,
            updated_at=now,
        )
        self._apply_extraction(consultation, extracted)
        try:
            self._repo.add(consultation)
        except Exception:
            self._store.delete(key)
            raise
        return UploadOutcome(consultation, "parsed" if extracted else "failed")

    def redeposit(
        self, author_id: UUID, consultation_id: UUID, content: bytes, extension: str
    ) -> UploadOutcome:
        consultation = self.get(author_id, consultation_id)
        if consultation.state != ConsultationState.UPLOADED:
            raise WrongState
        info = inspect_upload(content, extension, self._max_bytes)
        extracted = self._extract(content, info)
        old_key = consultation.storage_key
        consultation.storage_key = self._store.save(content)
        consultation.file_kind = info.kind
        consultation.file_size = len(content)
        self._apply_extraction(consultation, extracted)
        self._session.flush()
        if old_key:
            self._store.delete(old_key)
        return UploadOutcome(consultation, "parsed" if extracted else "failed")

    def _extract(self, content: bytes, info: FileInfo) -> SuperbillData | None:
        try:
            result = self._ocr.extract_text(content, info.content_type)
            data = parse_superbill_text(result.text, result.pages)
        except Exception as error:  # le détail peut contenir une donnée patient : type seul
            log.warning("extraction_failed", error_type=type(error).__name__)
            return None
        if len(missing_required(data)) == REQUIRED_FIELD_COUNT:
            log.warning("extraction_failed", error_type="NothingFound")
            return None
        return data

    def _apply_extraction(self, consultation: Consultation, data: SuperbillData | None) -> None:
        consultation.updated_at = self._clock.now()
        if data is None:  # F-06 : reste Uploaded, échec compté, nouveau dépôt possible
            consultation.extraction_failures += 1
            return
        consultation.state = ConsultationState.PARSED.value
        consultation.extracted_data = to_dict(canonical(data))
        consultation.data = to_dict(canonical(data))

    # -- correction et validation ----------------------------------------------------------
    def correct(
        self, author_id: UUID, consultation_id: UUID, new_raw: dict[str, Any]
    ) -> Consultation:
        consultation = self.get(author_id, consultation_id)
        if consultation.state != ConsultationState.PARSED or consultation.data is None:
            raise WrongState
        page_count = int((consultation.data.get("extraction") or {}).get("pageCount") or 0)
        new_data = replace(canonical(from_dict(new_raw)), page_count=page_count)
        updated = to_dict(new_data)
        now = self._clock.now()
        for change in diff(consultation.data, updated):
            self._session.add(
                ConsultationCorrection(
                    consultation_id=consultation.id,
                    author_id=author_id,
                    field=change.path,
                    old_value=None if change.old is None else str(change.old),
                    new_value=None if change.new is None else str(change.new),
                    changed_at=now,
                )
            )
        consultation.data = updated
        consultation.updated_at = now
        self._session.flush()
        return consultation

    def validate(self, author_id: UUID, consultation_id: UUID) -> Consultation:
        consultation = self.get(author_id, consultation_id)
        if consultation.state != ConsultationState.PARSED or consultation.data is None:
            raise WrongState
        issues = self.issues(consultation)
        if has_blocking_issue(issues):  # S-07 : aucune validation critique contournée
            raise ValidationFailed({"issues": [{"field": i.field, "code": i.code} for i in issues]})
        now = self._clock.now()
        consultation.state = ConsultationState.VALIDATED.value
        consultation.validated_at = now
        consultation.updated_at = now
        self._session.flush()
        return consultation
